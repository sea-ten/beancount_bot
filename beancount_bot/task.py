import asyncio
from typing import Dict

import schedule
from telegram.ext import ContextTypes

# 注意： get_config, get_global, GLOBAL_TASK, logger, load_class 的导入保持不变
from beancount_bot.config import get_config, get_global, GLOBAL_TASK
from beancount_bot.util import logger, load_class


class ScheduleTask:
    """
    定时任务
    """

    def __init__(self):
        """
        处理器的构造函数将在载入配置时时执行。如启动时、/reload 时
        构造函数参数通过 **kwargs 形式传入
        """
        self.config = None
        self.name = None

    def register(self, fire: callable):
        """
        注册定时任务。将在构造任务对象后立刻执行。如果不注册，将不会定时触发
        :param fire: 待执行函数
        """
        # schedule 的注册逻辑可以保持，但调用方式会改变
        pass

    async def trigger(self, context: ContextTypes.DEFAULT_TYPE):
        """
        触发任务。任务可通过两种方式触发：定时执行（register 中注册）、/task 任务名
        :param context: PTB 的上下文对象，可以通过 context.bot 访问机器人实例
        """
        # 这里需要您根据具体任务来实现异步逻辑
        # 例如： await context.bot.send_message(chat_id=..., text=...)
        pass


def load_task() -> Dict[str, ScheduleTask]:
    """
    加载定时任务
    :return:
    """
    # 这个函数不再需要导入 bot，也不再注册 schedule
    ret = {}
    schedule.clear()
    for conf in get_config('schedule', []):
        name = conf['name']
        clazz = load_class(conf['class'])
        args = conf['args']

        logger.info('加载定时任务定义：%s', name)
        task: ScheduleTask = clazz(**args)
        # task.register(...) 的逻辑将移至 bot.py
        task.config = conf
        task.name = name
        ret[name] = task
    return ret


def get_task() -> Dict[str, ScheduleTask]:
    """
    获得任务
    :return:
    """
    return get_global(GLOBAL_TASK, load_task)

# start_schedule_thread 函数可以安全地删除了
# def start_schedule_thread(...):
