import logging
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from beancount_bot import transaction, config as conf, __VERSION__
from beancount_bot.config import get_config, load_config
from beancount_bot.dispatcher import Dispatcher
from beancount_bot.i18n import _
from beancount_bot.session import get_session, SESS_AUTH, set_session, SESS_TX_TAGS, load_session
from beancount_bot.session_config import SESSION_CONFIG
from beancount_bot.task import load_task, get_task
from beancount_bot.transaction import get_manager

# 设置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


#######
# 鉴权 #
#######

def check_auth(user_id: int) -> bool:
    """检查是否登录"""
    session = get_session(user_id, SESS_AUTH, False)
    return session


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """首次聊天时鉴权"""
    if check_auth(update.effective_user.id):
        await update.message.reply_text(_("已经鉴权过了！"))
    else:
        await update.message.reply_text(_("欢迎使用记账机器人！请输入鉴权令牌："))


#######
# 指令 #
#######

async def reload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """重载配置指令"""
    if not check_auth(update.effective_user.id):
        await update.message.reply_text(_("请先进行鉴权！"))
        return
    load_config()
    # 重新加载任务定义，但不需要重新启动调度线程
    load_task()
    # 注意：这里没有重新启动 JobQueue 的逻辑，因为这比较复杂。
    # 对于定时任务的修改，建议重启机器人。
    await update.message.reply_text(_("成功重载配置！"))


async def show_usage_for(message, d: Dispatcher):
    """显示特定处理器的使用方法"""
    usage = _("帮助：{name}\n\n{usage}").format(name=d.get_name(), usage=d.get_usage())
    await message.reply_text(usage)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助指令"""
    dispatchers = get_manager().dispatchers
    if not context.args:
        buttons = [[InlineKeyboardButton(_("帮助：{name}").format(name=d.get_name()), callback_data=f'help:{i}')]
                   for i, d in enumerate(dispatchers)]
        markup = InlineKeyboardMarkup(buttons)
        command_usage = [
            _("/start - 鉴权"), _("/help - 使用帮助"), _("/reload - 重新加载配置文件"),
            _("/task - 查看、运行任务"), _("/set - 设置用户特定配置"), _("/get - 获取用户特定配置"),
        ]
        help_text = _("记账 Bot\n\n可用指令列表：\n{command}\n\n交易语句语法帮助请选择对应模块，或使用 /help [模块名] 查看。").format(
            command='\n'.join(command_usage))
        await update.message.reply_text(help_text, reply_markup=markup)
    else:
        name = ' '.join(context.args)
        d = next((d for d in dispatchers if name.lower() == d.get_name().lower()), None)
        if d:
            await show_usage_for(update.message, d)
        else:
            await update.message.reply_text(_("对应名称的交易语句处理器不存在！"))


async def callback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助回调"""
    query = update.callback_query
    await query.answer()
    try:
        d_id = int(query.data[5:])
        dispatchers = get_manager().dispatchers
        await show_usage_for(query.message, dispatchers[d_id])
    except (ValueError, IndexError) as e:
        logger.error(f'{query.id}：帮助回调发生错误！', exc_info=e)
        await query.answer(_("发生未知错误！"), show_alert=True)


async def task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """任务指令"""
    if not check_auth(update.effective_user.id):
        await update.message.reply_text(_("请先进行鉴权！"))
        return
    tasks = get_task()
    if not context.args:
        all_tasks = ', '.join(tasks.keys())
        await update.message.reply_text(_("当前注册任务：{all_tasks}\n可以通过 /task [任务名] 主动触发").format(all_tasks=all_tasks))
    else:
        dest = ' '.join(context.args)
        task = tasks.get(dest)
        if not task:
            await update.message.reply_text(_("任务不存在！"))
            return
        try:
            # 手动触发任务
            await task.trigger(context)
        except Exception as e:
            logger.error(f'{update.effective_user.id}：执行任务失败。', exc_info=e)
            await update.message.reply_text(_("发生未知错误！执行任务失败。"))


async def session_config_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置或获取 session 配置"""
    if not check_auth(update.effective_user.id):
        await update.message.reply_text(_("请先进行鉴权！"))
        return
    
    is_set = update.message.text.startswith('/set')
    command = '/set' if is_set else '/get'

    if not context.args:
        desc = '\n'.join(v.make_help(k, is_set=is_set) for k, v in SESSION_CONFIG.items())
        await update.message.reply_text(_("使用方法：\n{desc}").format(desc=desc))
        return
    
    conf_key = context.args[0]
    obj_conf = SESSION_CONFIG.get(conf_key)
    if not obj_conf:
        await update.message.reply_text(_("配置不存在！命令使用方法请参考 {cmd}").format(cmd=command))
        return

    value_str = ' '.join(context.args[1:])
    try:
        if is_set:
            await obj_conf.set(value_str, update, context)
        else:
            await obj_conf.get(value_str, update, context)
    except Exception as e:
        logger.error(f'Session config handler failed for {conf_key}', exc_info=e)
        await update.message.reply_text(_("处理配置时发生错误。"))


async def transaction_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """交易语句或鉴权处理"""
    user = update.effective_user
    message = update.message
    
    if not check_auth(user.id):
        auth_token = get_config('bot.auth_token')
        if auth_token == message.text:
            set_session(user.id, SESS_AUTH, True)
            await message.reply_text(_("鉴权成功！"))
        else:
            await message.reply_text(_("鉴权令牌错误！"))
        return
    
    manager = get_manager()
    try:
        tags = get_config('transaction.tags', []) + get_session(user.id, SESS_TX_TAGS, [])
        tx_uuid, tx = manager.create_from_str(message.text, add_tags=tags)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(_("撤回交易"), callback_data=f'withdraw:{tx_uuid}')]])
        await message.reply_text(transaction.stringfy(tx), reply_markup=markup)
    except ValueError as e:
        logger.info(f'{user.id}：无法添加交易', exc_info=e)
        await message.reply_text(e.args[0])
    except Exception as e:
        logger.error(f'{user.id}：添加交易失败。', exc_info=e)
        await message.reply_text(_("发生未知错误！添加交易失败。"))


async def callback_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """交易撤回回调"""
    query = update.callback_query
    if not check_auth(query.from_user.id):
        await query.answer(_("请先进行鉴权！"), show_alert=True)
        return
    
    await query.answer()
    tx_uuid = query.data[9:]
    manager = get_manager()
    try:
        manager.remove(tx_uuid)
        message_text = _("交易已撤回")
        entities = [MessageEntity(type=MessageEntity.CODE, offset=0, length=len(message_text))]
        await query.edit_message_text(text=message_text, entities=entities)
    except ValueError as e:
        logger.info(f'{query.id}：无法撤回交易', exc_info=e)
        await query.answer(e.args[0], show_alert=True)
    except Exception as e:
        logger.error(f'{query.id}：撤回交易失败。', exc_info=e)
        await query.answer(_("发生未知错误！撤回交易失败。"), show_alert=True)

def serving():
    """
    启动 Bot 服务的主函数。由 main.py 调用。
    """
    # 此函数假设所有配置（config, session等）已由 main.py 加载完毕
    
    # 创建 Application
    token = get_config('bot.token')
    builder = Application.builder().token(token)
    proxy = get_config('bot.proxy')
    if proxy:
        builder.proxy_url(proxy)
    application = builder.build()

    # 注册指令处理器
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("reload", reload_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("task", task_handler))
    application.add_handler(CommandHandler(["set", "get"], session_config_handler))

    # 注册回调查询处理器
    application.add_handler(CallbackQueryHandler(callback_help, pattern=r'^help:'))
    application.add_handler(CallbackQueryHandler(callback_withdraw, pattern=r'^withdraw:'))

    # 注册消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, transaction_query_handler))

    # 注册定时任务
    tasks = get_task()
    job_queue = application.job_queue
    logger.info("注册定时任务调度...")
    # 您需要在这里根据您的业务逻辑实现任务调度
    # for task_name, task_obj in tasks.items():
    #     job_queue.run_daily(task_obj.trigger, time=..., name=task_name)
    
    logger.info("Bot polling astarted...")
    application.run_polling()
