import click
import logging

# 注意这里我们导入了新的 bot 模块，以及其他需要的模块
from beancount_bot import bot, config as conf, __VERSION__
from beancount_bot.config import load_config, get_config
from beancount_bot.i18n import _
from beancount_bot.session import load_session
from beancount_bot.task import get_task  # 注意：这里只导入 get_task，不再需要 start_schedule_thread
from beancount_bot.transaction import get_manager
from beancount_bot.util import logger



# 设置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@click.command()
@click.version_option(__VERSION__, '-V', '--version', help=_("显示版本信息"))
@click.help_option(help=_("显示帮助信息"))
@click.option('-c', '--config', default='beancount_bot.yml', help=_("配置文件路径"))
def main(config):
    """
    适用于 Beancount 的 Telegram 机器人
    """
    # 加载配置
    logger.info("加载配置：%s", config)
    conf.config_file = config
    load_config()
    
    # 设置日志等级
    log_level = get_config('log.level', 'INFO')
    logger.setLevel(log_level)
    # 也为 beancount_bot 包下的所有 logger 设置级别
    logging.getLogger('beancount_bot').setLevel(log_level)

    # 加载会话
    logger.info("加载会话...")
    load_session()
    
    # 创建管理对象
    logger.info("创建管理对象...")
    get_manager()
    
    # 加载定时任务定义
    # logger.info("加载定时任务定义...")
    # get_task()
    
    # 删除了旧的 start_schedule_thread() 调用
    
    # 启动 Bot
    logger.info("启动 Bot...")
    bot.serving() # 调用 bot.py 中的 serving 函数来启动机器人


if __name__ == '__main__':
    main()
