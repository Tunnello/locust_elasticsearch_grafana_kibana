'''
1.定时获取locust_stats--与web上的一致
2.存入数据库
locust 2.5.1
'''
import os
import time
import gevent
import subprocess
import json
#import six
#import requests
#import threading

from datetime import datetime
from itertools import chain
from elasticsearch import Elasticsearch
#from influxdb import InfluxDBClient
from locust import events
from locust.stats import sort_stats
from locust.runners import LocalRunner, STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, MasterRunner, WorkerRunner
from utils.LogUitl import logger
from conf import *


#__all__ = ['start']

# 连接InfluxDB数据库
# influxdbclient = InfluxDBClient('localhost', 8086, database='locust')

# 连接es数据库
es = Elasticsearch(
    ["http://localhost:9200"], # 连接集群，以列表的形式存放各节点的IP地址或url
    sniff_on_start=True,    # 连接前测试
    sniff_on_connection_fail=True,  # 节点无响应时刷新节点
    sniff_timeout=60    # 设置超时时间
)


def proper_round(val, digits=0):
    return round(val + 10 ** (-len(str(val)) - 1), digits)

def save2es(project_name, data):
    """
    保存数据到 elasticsearch 数据库
    : param project_name: current project - string
    : data: data that will be writed into es - dict/json
    """
    try:    
        logger.info("save monitor data to elasticsearch ...")

        if isinstance(data, dict):
            data.update({"@timestamp" : datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+0800" )})
            data = json.dumps(data, indent = 2)

        logger.info(f"writing to es:\n{data}")
        es.index(index=project_name, document=data)
    except Exception as e:
        logger.error("写入数据到 elasticsearch 出错，请检查！")
        logger.error(e)


# reference: https://github.com/locustio/locust/blob/2.5.1/locust/web.py
def request_stats(environment):
    """
    获得locust训练的过程数据
    return: <class 'dict'>
    """
    stats = []

    for s in chain(sort_stats(environment.runner.stats.entries), [environment.runner.stats.total]):
        stats.append(
            {
                "method": s.method,
                "name": s.name,
                "num_requests": s.num_requests,
                "num_failures": s.num_failures,
                "avg_response_time": s.avg_response_time,
                "min_response_time": 0 if s.min_response_time is None else proper_round(s.min_response_time),
                "max_response_time": proper_round(s.max_response_time),
                "current_rps": s.current_rps,
                "current_fail_per_sec": s.current_fail_per_sec,
                "median_response_time": s.median_response_time,
                "ninetieth_response_time": s.get_response_time_percentile(0.9),
                "avg_content_length": s.avg_content_length,
            }
        )

    errors = []
    for e in environment.runner.errors.values():
        err_dict = e.to_dict()
        err_dict["name"] = err_dict["name"]
        err_dict["error"] = err_dict["error"]
        errors.append(err_dict)

    # Truncate the total number of stats and errors displayed since a large number of rows will cause the app
    # to render extremely slowly. Aggregate stats should be preserved.
    report = {"stats": stats[:500], "errors": errors[:500]}
    if len(stats) > 500:
        report["stats"] += [stats[-1]]

    if stats:
        report["total_rps"] = stats[len(stats) - 1]["current_rps"]
        report["fail_ratio"] = environment.runner.stats.total.fail_ratio
        report[
            "current_response_time_percentile_95"
        ] = environment.runner.stats.total.get_current_response_time_percentile(0.95)
        report[
            "current_response_time_percentile_50"
        ] = environment.runner.stats.total.get_current_response_time_percentile(0.5)

        report["total_num_requests"] = environment.runner.stats.total.num_requests
        report["total_num_failures"] = environment.runner.stats.total.num_failures

    is_distributed = isinstance(environment.runner, MasterRunner)
    if is_distributed:
        workers = []
        for worker in environment.runner.clients.values():
            workers.append(
                {
                    "is_distributed": "yes",
                    "id": worker.id,
                    "state": worker.state,
                    "user_count": worker.user_count,
                    "cpu_usage": worker.cpu_usage,
                    "memory_usage": worker.memory_usage,
                }
            )
        report["num_workers"] = len(workers)
        report["workers"] = workers
    else:
        workers = [{"is_distributed": "no"}]
        report["num_workers"] = 1
        report["workers"] = workers
        
    report["state"] = environment.runner.state
    report["user_count"] = environment.runner.user_count

    return report


def monitor(environment, project_name, project_start_time):
    """
    获取测试过程数据，用于 @events.init.add_listener 进行监听
    - param interval: 间隔多久获取一次
    - return:
    """
    logger.info("loading monitor ...")
    logger.info(f"this project is {project_name}")

    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:
        gevent.sleep(interval)
        report = request_stats(environment)
        # 加上此次任务开始执行的时间
        report.update({"project_start_time": project_start_time})
        
        # logger.info(f"report is \n{report}")
        # os.system(f"echo '{report}' >> {current_project_monitor}")
        save2es(project_name, report)


@events.init.add_listener
def on_locust_init_monitor(environment, **_kwargs):
    """
    only run this on master & standalone
    - :param environment:
    - :param _kwargs:
    - :return:
    """
    try:
        output = subprocess.check_output(f'cat {current_project_file}', shell=True, stderr=subprocess.STDOUT)
    except Exception as ce:
        status = ce.returncode
        output = ce.output
        logger.info("command exec failed, return code: %s." % status)
    project_name = output.strip().decode().split()[0]
    start_time   = output.strip().decode().split()[2]
    project_start_time = project_name + "-" + start_time
    
    # only run this on master & standalone
    if not isinstance(environment.runner, WorkerRunner):
        gevent.spawn(monitor, environment, project_name, project_start_time)


if __name__ == '__main__':
    print('locust_monitoring')