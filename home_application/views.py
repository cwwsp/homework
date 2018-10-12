# -*- coding: utf-8 -*-

import base64
from common.mymako import render_mako_context, render_json
from blueking.component.shortcuts import get_client_by_request
from utils import get_job_instance_id, get_job_log_content
from models import Operations, ResourceData, CeleryTask
from datetime import datetime
from time import sleep


def home(request):
    return render_mako_context(request, '/home_application/home.html')


def get_biz_list(request):
    bizs = []
    client = get_client_by_request(request)
    resp = client.cc.search_business({'fields': ['bk_biz_name', 'bk_biz_id']})
    if resp.get('result'):
        datas = resp.get('data', {}).get('info', {})
        for data in datas:
            bizs.append({'id':data.get('bk_biz_id'),'name':data.get('bk_biz_name')})
    result = {'result': resp.get('result'), 'bizs': bizs}
    return render_json(result)


def get_hosts_by_biz_id(request):
    biz_id = request.GET.get('biz_id')
    hosts = []
    match_host = []
    client = get_client_by_request(request)
    args = {
        "page": {"start": 0, "limit": 5, "sort": "bk_host_id"},
        "ip": {
            "flag": "bk_host_innerip|bk_host_outerip",
            "exact": 1,
            "data": []
        },
        "condition": [
            {
                "bk_obj_id": "host",
                "fields": [],
                "condition": []
            },
            {"bk_obj_id": "module", "fields": [], "condition": []},
            {"bk_obj_id": "set", "fields": [], "condition": []},
            {
                "bk_obj_id": "biz",
                "fields": [
                    "default",
                    "bk_biz_id",
                    "bk_biz_name",
                ],
                "condition": [
                    {
                        "field": "bk_biz_id",
                        "operator": "$eq",
                        "value": int(biz_id)
                    }
                ]
            }
        ]
    }
    resp = client.cc.search_host(**args)
    if resp.get('result'):
        datas = resp.get('data', {}).get('info', {})
        for data in datas:
            host_info = data.get('host', {})
            hosts.append({
                'id': host_info['bk_host_id'],
                'ip': host_info['bk_host_innerip'],
                'resource': '-',
                'last_time': '-',
                'set': data['set'][0]['bk_set_name'],
                'module': data['module'][0]['bk_module_name'],
                'area': host_info['bk_cloud_id'][0]['bk_inst_name'],
                'os': host_info['bk_os_name']
            })
    if request.GET.get('ip'):
        ip = request.GET.get('ip')
        match_host = [host for host in hosts if host['ip'] == ip]
    result = {'result': resp.get('result'), 'hosts': hosts, 'match_host': match_host}
    return render_json(result)


def get_hosts_and_status_by_ip(request):
    biz_id = request.GET.get('biz_id')
    ip = request.GET.get('ip')
    hosts = []
    match_host = []
    client = get_client_by_request(request)
    args = {
        "page": {"start": 0, "limit": 5, "sort": "bk_host_id"},
        "ip": {
            "flag": "bk_host_innerip|bk_host_outerip",
            "exact": 1,
            "data": [ip]
        },
        "condition": [
            {
                "bk_obj_id": "host",
                "fields": [],
                "condition": []
            },
            {"bk_obj_id": "module", "fields": [], "condition": []},
            {"bk_obj_id": "set", "fields": [], "condition": []},
            {
                "bk_obj_id": "biz",
                "fields": [
                    "default",
                    "bk_biz_id",
                    "bk_biz_name",
                ],
                "condition": [
                    {
                        "field": "bk_biz_id",
                        "operator": "$eq",
                        "value": int(biz_id)
                    }
                ]
            }
        ]
    }
    resp = client.cc.search_host(**args)
    if resp.get('result'):
        datas = resp.get('data', {}).get('info', {})
        for data in datas:
            host_info = data.get('host', {})
            hosts.append({
                'id': host_info['bk_host_id'],
                'ip': host_info['bk_host_innerip'],
                'resource': '-',
                'last_time': '-',
                'set': data['set'][0]['bk_set_name'],
                'module': data['module'][0]['bk_module_name'],
                'area': host_info['bk_cloud_id'][0]['bk_inst_name'],
                'os': host_info['bk_os_name']
            })
    if request.GET.get('ip'):
        try:
            Operations.objects.create(ip=ip, user=request.user.username, type='立即检查')
        except Exception, e:
            print e
        execute_result, job_instance_id = get_job_instance_id(client, biz_id, ip)

        # # 执行脚本
        # str = "#!/bin/bash\nMEMORY=$(free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }')\nDISK=$(df -h | awk '$NF==\"/\"{printf \"%s\", $5}')\nCPU=$(top -bn1 | grep load | awk '{printf \"%.2f%%\", $(NF-2)}')\nDATE=$(date \"+%Y-%m-%d %H:%M:%S\")\necho -e \"$DATE|$MEMORY|$DISK|$CPU\""
        # cmd = base64.b64encode(str)
        # ip_list = [{'ip': ip, 'bk_cloud_id': 0}]
        # args = {"bk_biz_id": biz_id, "script_content": cmd, "account": "root", "script_type": 1, "ip_list": ip_list}
        # client = get_client_by_request(request)
        # execute_script_result = client.job.fast_execute_script(**args)

        match_host = [host for host in hosts if host['ip'] == ip]

        if execute_result:
            is_finished = False
            while not is_finished:
                sleep(0.5)
                is_finished, log_content, latest_time = get_job_log_content(client, biz_id, job_instance_id)
                match_host[0]['resource'] = log_content
                match_host[0]['last_time'] = latest_time

    result = {'result': resp.get('result'), 'hosts': hosts, 'match_host': match_host}
    return render_json(result)


def get_ip_by_biz_id(request):
    client = get_client_by_request(request)
    biz_id = request.GET.get('biz_id')
    ip_list = []
    args = {
        "page": {"start": 0, "limit": 5, "sort": "bk_host_id"},
        "ip": {
            "flag": "bk_host_innerip|bk_host_outerip",
            "exact": 1,
            "data": []
        },
        "condition": [
            {
                "bk_obj_id": "host",
                "fields": [],
                "condition": []
            },
            {"bk_obj_id": "module", "fields": [], "condition": []},
            {"bk_obj_id": "set", "fields": [], "condition": []},
            {
                "bk_obj_id": "biz",
                "fields": [
                    "default",
                    "bk_biz_id",
                    "bk_biz_name",
                ],
                "condition": [
                    {
                        "field": "bk_biz_id",
                        "operator": "$eq",
                        "value": int(biz_id)
                    }
                ]
            }
        ]
    }
    resp = client.cc.search_host(**args)
    if resp.get('result'):
        datas = resp.get('data', {}).get('info', {})
        for data in datas:
            host_info = data.get('host', {})
            ip_list.append({
                'id': host_info['bk_host_id'],
                'text': host_info['bk_host_innerip'],
            })
    return render_json({'results': ip_list})


def execute_script(request):
    client = get_client_by_request(request)
    ip = request.POST.get('ip')
    biz_id = request.POST.get('biz_id')
    try:
        Operations.objects.create(ip=ip, user=request.user.username, type='立即检查')
    except Exception, e:
        print e
    result, job_instance_id = get_job_instance_id(client, biz_id, ip)
    result = {
        'result': result,
        'job_instance_id': job_instance_id,
    }
    return render_json(result)


def get_script_log_content(request):
    client = get_client_by_request(request)
    biz_id = request.GET.get('biz_id')
    job_instance_id = request.GET.get('job_instance_id')
    is_finished, log_content, latest_time = get_job_log_content(client, biz_id, job_instance_id)
    return render_json({
        'code': 0,
        'message': 'success',
        'data': {
            'log_content': log_content,
            'latest_time': latest_time
        }
    })


def operations(request):
    return render_mako_context(request, '/home_application/operations.html')


def get_op_page_rows(request):
    total_count = Operations.objects.count()
    return render_json({'rows': total_count, 'per_page': 10})


def get_op_page_data(request):
    page = request.GET.get('current_page')
    begin = int(page) * 10
    end = begin + 9
    data = []
    ops = Operations.objects.order_by('-id')[begin: end]
    for op in ops:
        data.append({
            'id': op.id,
            'ip': op.ip,
            'user': op.user,
            'exec_time': datetime.strftime(op.exec_time, '%Y-%m-%d %H:%M:%S'),
            'type': op.type
        })
    return render_json({'data': data})


def host_state(request):
    return render_mako_context(request, '/home_application/host.html')


def get_host_state(request):
    biz_id = request.GET.get('biz_id')
    ip = request.GET.get('ip')
    state_records = ResourceData.objects.order_by('-id').filter(biz_id=biz_id, ip=ip)[:20]
    memory_data = list(reversed([record.memory for record in state_records]))
    disk_data = list(reversed([record.disk for record in state_records]))
    cpu_data = list(reversed([record.cpu for record in state_records]))
    datetime_data = list(reversed([datetime.strftime(record.exec_time, '%H:%M:%S') for record in state_records]))
    result = {
        'code': 0,
        'result': True,
        'message': 'success',
        'data': {
            'series':[
                {
                    'color': '#f9ce1d',
                    'name': 'memory',
                    'data': memory_data
                },
                {
                    'color': '#f91d1d',
                    'name': 'disk',
                    'data': disk_data
                },
                {
                    'color': '#1d2bf9',
                    'name': 'cpu',
                    'data': cpu_data
                }
            ],
            'categories': datetime_data
        }
    }
    return render_json(result)


def add_to_celery(request):
    biz_id = request.POST.get('biz_id')
    ip = request.POST.get('ip')
    if CeleryTask.objects.filter(biz_id=biz_id, ip=ip):
        return render_json({'result': False})
    CeleryTask.objects.create(biz_id=biz_id, ip=ip)
    Operations.objects.create(exec_time=datetime.now(), ip=ip, user=request.user.username, type='加入自动检查')
    return render_json({'result': True})


def remove_from_celery(request):
    biz_id = request.POST.get('biz_id')
    ip = request.POST.get('ip')
    if not CeleryTask.objects.filter(biz_id=biz_id, ip=ip):
        return render_json({'result': False})
    CeleryTask.objects.filter(biz_id=biz_id, ip=ip).delete()
    Operations.objects.create(exec_time=datetime.now(), ip=ip, user=request.user.username, type='取消自动检查')
    return render_json({'result': True})