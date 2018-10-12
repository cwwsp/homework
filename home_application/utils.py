# -*- coding: utf-8 -*-
from datetime import datetime
from models import ResourceData
import base64


def get_job_instance_id(client, biz_id, ip):
    str = "#!/bin/bash\nMEMORY=$(free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }')\nDISK=$(df -h | awk '$NF==\"/\"{printf \"%s\", $5}')\nCPU=$(top -bn1 | grep load | awk '{printf \"%.2f%%\", $(NF-2)}')\nDATE=$(date \"+%Y-%m-%d %H:%M:%S\")\necho -e \"$DATE|$MEMORY|$DISK|$CPU\""
    cmd = base64.b64encode(str)
    ip_list = [{'ip': ip, 'bk_cloud_id': 0}]
    args = {"bk_biz_id": biz_id, "script_content": cmd, "account": "root", "script_type": 1, "ip_list": ip_list}
    resp = client.job.fast_execute_script(**args)

    if resp.get('result'):
        job_instance_id = resp.get('data').get('job_instance_id')
    else:
        job_instance_id = -1
    return resp.get('result'), job_instance_id


def get_job_log_content(client, biz_id, job_instance_id):
    args = {
        'bk_biz_id': biz_id,
        'job_instance_id': job_instance_id,
    }
    resp = client.job.get_job_instance_log(**args)
    is_finished = False
    log_content = ''
    latest_time = ''
    if resp.get('result'):
        data = resp.get('data')[0]
        if data.get('is_finished'):
            is_finished = True
            result = data['step_results'][0]['ip_logs'][0]['log_content'].strip('\n').split("|")
            log_content = "/".join(result[1:])
            ip = data['step_results'][0]['ip_logs'][0]['ip']
            latest_record = ResourceData.objects.filter(ip=ip).last()
            if latest_record is not None:
                latest_time = datetime.strftime(latest_record.exec_time, '%Y-%m-%d %H:%M:%S')
            try:
                exec_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                ResourceData.objects.create(
                    exec_time=exec_time,
                    biz_id=biz_id,
                    ip=ip,
                    memory=float(result[1][:-1]),
                    disk=int(result[2][:-1]),
                    cpu=float(result[3][:-1]),
                )
            except Exception, e:
                print(e)
    return is_finished, log_content, latest_time
