# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-20 20:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
        ('stackoverflow', '0003_remove_answer_is_correct'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.SmallIntegerField()),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('object_id', models.PositiveIntegerField()),
                ('object_type', models.CharField(choices=[('Q', 'Question'), ('A', 'Answer')], max_length=1)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='votes', to='user.User')),
            ],
        ),
        migrations.RemoveField(
            model_name='voteanswer',
            name='answer',
        ),
        migrations.RemoveField(
            model_name='votequestion',
            name='question',
        ),
        migrations.DeleteModel(
            name='VoteAnswer',
        ),
        migrations.DeleteModel(
            name='VoteQuestion',
        ),
    ]
