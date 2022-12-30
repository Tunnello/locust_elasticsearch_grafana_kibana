# -*- coding:utf-8 -*-
import os 
import sys
import time
import yaml
import allure
import pytest
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.sys.path[0])))
from datetime import datetime
from utils.KubectlUtil import KubectlUtil
from utils.LogUitl import logger

global standard_users

def run_locust(**kwargs):
    #os.system("locust -f %s" %locust_file) # 可以调起，有web页面的
    # todo
    ### locust运行无页面，自动停
    ## 可由control.py里的StepLoadShape代替控制
    # --users, -u 100 # 目标100个并发
    # --spawn-rate, -r 10 # Rate to spawn users at (users per second)

    # --run-time, -t 2h # 2h后强制停止，--run-time {run_time}。与LoadTestShape不能同时存在
    # --expect-workers 2 # 无web使用。连接两个worker
    # --expect-workers-max-wait 180 # How long should the master wait for workers to connect before giving up. Defaults to wait forever

    # --csv lt 会保存四个文件在运行这个用例的文件夹
    # --csv-full-history 没用到

    # --stop-timeout 10 # 结束后等待多久让任务运行完成，默认是马上结束所有任务
    #cwd = os.getcwd()
    #os.chdir(root_path)

    csv_prefix = "locust_" + kwargs.get("csv_prefix", "default")
    
    
    if expect_workers <= 0:
        #master_cmd = "locust -f %s --headless -u 1 -r 1 -t 10s --csv lt --stop-timeout 10" %(locust_file)
        master_cmd = f"locust -f {locust_file} --headless --csv {csv_prefix} --csv-full-history --stop-timeout {stop_timeout} -r 1 -u 10"
    else:
        master_cmd = f"locust -f {locust_file} --headless --csv {csv_prefix} --csv-full-history --stop-timeout {stop_timeout} --expect-workers={expect_workers} --master"
        worker_cmd = f"locust -f {locust_file} --worker"

    for i in range(expect_workers):
        subprocess.Popen(worker_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"已启动 {i+1} 个worker")
        time.sleep(1)
    
    try:
        logger.info(f"locust_cmd = {master_cmd}")
        output = subprocess.check_output(master_cmd, shell=True, timeout=36000) # shell=True必须，stderr=subprocess.STDOUT若加上就不会打印详情
    except subprocess.CalledProcessError as ce:
        status = ce.returncode
        logger.info("locust return code: %s" % status)
        #logger.info("command exec failed, exception is:\n%s" % output) # 就是所有失败，不需要打出来
   

@allure.feature('训练专项')
#@pytest.mark.usefixtures('get_tasks_config')
class TestPerformanceOfK8S(object):
    def ssetup_method(self):
        logger.info("-------- setup_method of cases starts --------")
        ### 系统有关的命名空间下的pod要都为Running
        kube_config = get_tasks_config()[0]
        for item_ns in sys_ns:
            KubectlUtil().kube_command('get pod -n %s' %item_ns, configfile=kube_config, check_str="Running")
            output = KubectlUtil().kube_command('get pod -n %s --no-headers=true | wc -l ' %item_ns, configfile=kube_config, check_nostr="error")
            KubectlUtil().kube_command('get pod -n %s | grep Running | wc -l ' %item_ns, configfile=kube_config, check_str=output)

        logger.info("-------- setup_method of cases ends --------")

    def steardown_method(self):
        """
        after the execution of one single test case(no matter succeeded or failed),delete these exsiting works
        works : works names for deleting, including pod, mpi-job, batch-job, pytorch-job
        namespaces: corresponding namespaces of these works 
        usernames: corresponding user-configs of these works
        """
        logger.info("-------- teardown_method of cases starts --------")

        ### 系统有关的命名空间下的pod要都为Running
        kube_config = get_tasks_config()[0]
        for item_ns in sys_ns:
            KubectlUtil().kube_command('get pod -n %s' %item_ns, configfile=kube_config, check_str="Running")
            output = KubectlUtil().kube_command('get pod -n %s --no-headers=true | wc -l ' %item_ns, configfile=kube_config, check_nostr="error")
            KubectlUtil().kube_command('get pod -n %s | grep Running | wc -l ' %item_ns, configfile=kube_config, check_str=output)

        ### 清除可能残留的locust worker和master进程
        os.system('pgrep locust | xargs kill -s 9')

        logger.info("-------- teardown_method of cases ends --------")
        

    @allure.story('性能测试')
    @allure.title('xxxx')
    @pytest.mark.P0
    @pytest.mark.performance
    @pytest.mark.unready
    def test_xxxx(self):
        '''
        xxxx
        '''
        logger.info(get_tasks_config)
        logger.info("---- this is xxxx ----")
        
        ### 更改taskset.yaml需要执行的训练
        logger.info(taskset_file)
        current_taskset = 'test_xxxx'
        set_tasks_config(current_taskset)

        ### 引用并发数基准设置users增长StepLoadShape
        os.system(f"echo '{current_taskset} {standard_users}' > {current_project_file}")
        logger.info(f"设置并发数基准为standard_users = {standard_users}")
        
        ### 调起locust
        logger.info(locust_file)
        run_locust(csv_prefix=current_taskset)
        

if __name__ == "__main__":
    configs = YamlUtil.yaml_load(yaml_file=taskset_file)
    print(configs)    
    

