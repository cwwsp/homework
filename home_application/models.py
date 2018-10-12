# -*- coding: utf-8 -*-
from django.db import models


class ResourceData(models.Model):
    exec_time = models.DateTimeField()
    biz_id = models.IntegerField('biz_id')
    ip = models.CharField('ip',max_length=64)
    memory = models.FloatField('Memory')
    disk = models.IntegerField('Disk')
    cpu = models.FloatField('CPU')

    class Meta:
        verbose_name = u'主机资源消耗'
        verbose_name_plural = u'主机资源消耗'



class Operations(models.Model):
    exec_time = models.DateTimeField(auto_now=True)
    ip = models.CharField('ip', max_length=64)
    user = models.CharField('user', max_length=20)
    type = models.CharField('type', max_length=100)

    class Meta:
        verbose_name = u'操作记录'
        verbose_name_plural = u'操作记录'

    def total_page(self):
        return Operations.objects.count() / 5


class CeleryTask(models.Model):
    biz_id = models.IntegerField('biz_id')
    ip = models.CharField('ip', max_length=64)
