# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-16 23:23
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stackoverflow', '0002_auto_20180816_2322'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answer',
            name='is_correct',
        ),
    ]
