# -*- coding: utf-8 -*-
"""
celery 任务示例

本地启动celery命令: python  manage.py  celery  worker  --settings=settings
周期性任务还需要启动celery调度命令：python  manage.py  celery beat --settings=settings
"""
import datetime, time

from models import CeleryTask
from utils import get_job_instance_id, get_job_log_content
from blueking.component.shortcuts import get_client_by_user
from celery.schedules import crontab
from celery import task
from celery.task import periodic_task

from common.log import logger


@task()
def async_task(client, biz_id, ip):
    """
    执行 celery 异步任务

    调用celery任务方法:
        task.delay(arg1, arg2, kwarg1='x', kwarg2='y')
        task.apply_async(args=[arg1, arg2], kwargs={'kwarg1': 'x', 'kwarg2': 'y'})
        delay(): 简便方法，类似调用普通函数
        apply_async(): 设置celery的额外执行选项时必须使用该方法，如定时（eta）等
                      详见 ：http://celery.readthedocs.org/en/latest/userguide/calling.html
    """
    result, job_instance_id = get_job_instance_id(client, biz_id, ip)
    while True:
        is_finished, log_content, latest_time = get_job_log_content(client, biz_id, job_instance_id)
        if is_finished:
            break
        time.sleep(1)
    now = datetime.datetime.now()
    logger.error(u"{}上的资源查询完成，当前时间：{}".format(ip,now))


@periodic_task(run_every=crontab(minute='*/1', hour='*', day_of_week="*"))
def get_time():
    """
    celery 周期任务示例

    run_every=crontab(minute='*/5', hour='*', day_of_week="*")：每 5 分钟执行一次任务
    periodic_task：程序运行时自动触发周期任务
    """
    client = get_client_by_user('admin')
    tasks = [{'biz_id': _t.biz_id, 'ip': _t.ip} for _t in CeleryTask.objects.all()]
    for _t in tasks:
        async_task.apply_async(args=[client, _t['biz_id'], _t['ip']])
    now = datetime.datetime.now()
    logger.error(u"资源查询 周期任务开始调用，当前时间：{}".format(now))
