# -*- coding: utf-8 -*-

import os
import sys
import math
import time

import subprocess
from subprocess import CalledProcessError, STDOUT
from utils.LogUitl import logger
import gevent

from locust import events, LoadTestShape
from locust.runners import LocalRunner, STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, MasterRunner, WorkerRunner
from conf import *

def checker(environment):
    """
    定义退出 locust 的条件，用于 @events.init.add_listener 进行监听
    - param environment:
    - return:
    """
    logger.info("loading checker ...")
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:
        time.sleep(0.5)
        logger.info(f"num_requests were {environment.runner.stats.total.num_requests}")
        
        if environment.runner.stats.total.num_failures >= num_failures:
            logger.error(f"num_failures were {environment.runner.stats.total.num_failures} >= {num_failures}, quitting")
            environment.runner.quit()
            return
        elif environment.runner.stats.total.fail_ratio > fail_ratio:
            logger.error(f"fail ratio was {environment.runner.stats.total.fail_ratio} > {fail_ratio}, quitting")
            environment.runner.quit()
            return
        elif environment.runner.stats.total.avg_response_time > avg_response_time:
            logger.error(f"average response time ratio was {environment.runner.stats.total.avg_response_time} > {avg_response_time}, quitting")
            environment.runner.quit()
            return
        elif environment.runner.stats.total.get_response_time_percentile(0.95) > response_time_percentile_95:
            logger.error(f"95th percentile response time was {environment.runner.stats.total.get_response_time_percentile(0.95)} > {response_time_percentile_95}, quitting")
            environment.runner.quit()
            return
        
        elif environment.runner.stats.total.num_requests >=num_requests:
            logger.info(f"num_requests were {environment.runner.stats.total.num_requests} > {num_requests}, quitting")
            environment.runner.quit()
            # raise exit()
            # import greenlet
            # greenlet.kill(block=True)
            return
        else:
            pass


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    """
    only run this on master & standalone
    - :param environment:
    - :param _kwargs:
    - :return:
    """
    # only run this on master & standalone
    if not isinstance(environment.runner, WorkerRunner):
        gevent.spawn(checker, environment)


# 未生效
@events.request.add_listener
def request_running_on(environment, **_kwargs):
    logger.info("-------------------------------------------")
    if isinstance(environment.runner, WorkerRunner):
        logger.info("this request running on Worker")
    elif isinstance(environment.runner, MasterRunner):
        logger.info("this request running on Worker")
    else:
        logger.info("this request running on {environment.runner}")


'''
Controlling the exit code of the Locust process
http://docs.locust.io/en/2.2.0/running-without-web-ui.html
- More than 1% of the requests failed
- The average response time is longer than 200 ms
- The 95th percentile for response time is larger than 800 ms
this code could go into the locustfile.py or in any other file that is imported in the locustfile
'''
@events.quitting.add_listener
def _(environment, **kw):
    logger.info(f"total num_failures were {environment.stats.total.num_failures}")
    if environment.stats.total.num_failures >= num_failures:
        logger.error(f"num_failures were {environment.runner.stats.total.num_failures} >= {num_failures}")
        environment.process_exit_code = 10
    elif environment.stats.total.fail_ratio > fail_ratio:
        logger.error(f"fail ratio was {environment.runner.stats.total.fail_ratio} > {fail_ratio}")
        environment.process_exit_code = 20
    elif environment.stats.total.avg_response_time > avg_response_time:
        logger.error(f"average response time ratio was {environment.runner.stats.total.avg_response_time} > {avg_response_time}")
        environment.process_exit_code = 30
    elif environment.stats.total.get_response_time_percentile(0.95) > response_time_percentile_95:
        logger.error(f"95th percentile response time was {environment.runner.stats.total.get_response_time_percentile(0.95)} > {response_time_percentile_95}")
        environment.process_exit_code = 40

    elif environment.runner.stats.total.num_requests >= num_requests:
        logger.info(f"num_requests were {environment.runner.stats.total.num_requests} > {num_requests}")
        environment.process_exit_code = 50
    else:
        environment.process_exit_code = 0


'''
class StepLoadShape(LoadTestShape):
    """
    根据性能基准阶梯化达到并发数
    http://docs.locust.io/en/2.5.1/custom-load-shape.html
    """
    def tick(self):
        users_limit = 100000 # 最大并发数，此处设置很大，不做限制
        try:
            output = subprocess.check_output(f'cat {current_project_file}', shell=True, stderr=STDOUT)
        except Exception as ce:
            status = ce.returncode
            output = ce.output
            logger.info("command exec failed, return code: %s." % status)
        standard_users = int(output.strip().decode().split()[1])

        current_run_time = self.get_run_time()
        current_users    = self.get_current_user_count()
        logger.info(f"================================================================{current_users}")

        if current_users == math.floor(0.8 * standard_users):
            return (math.floor(0.8 * standard_users), 0)
            logger.info(f"+++++++++++++++++++++++++++++++++++++++++++{current_users}")
            time.sleep(10)

        if standard_users <= 0 or isinstance(standard_users, str):
            user_count = users_limit
            spawn_rate = 5
            logger.info(f"请输入正确的并发数基准！当前运行user_count = {user_count}, spawn_rate = {spawn_rate}")
            return (user_count, spawn_rate)

        if current_users < math.floor(0.8 * standard_users):
            user_count = math.floor(0.8 * standard_users)
            spawn_rate = math.floor(0.4 * standard_users)
            return (user_count, spawn_rate)
        else:
            if math.floor(0.2 * standard_users) < 10:
                user_count = users_limit
                spawn_rate = 2
                return (user_count, spawn_rate)
            else:
                user_count = users_limit
                spawn_rate = 5
                return (user_count, spawn_rate)

        if current_run_time > self.time_limit: # 超出设置时间后退出
            return None
'''


if __name__ == '__main__':
    #通过引入os，直接在此录入命令行运行信息。
    import os
    os.system("locust -f locustfile.py")
    # 无UI模式运行
    # 使用脚本locustfile.py压测1分钟，以每秒新增2用户的速率爬升到10个用户。--headless才有用
    # locust -f locustfile.py --headless --users 10 --spawn-rate 2 -H http://127.0.0.1:7890 --run-time 1m
