# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-26 00:19
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import dju_common.fields.json


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PrivateUrl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.SlugField(max_length=32, verbose_name='action')),
                ('token', models.SlugField(max_length=64, verbose_name='token')),
                ('expire', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='expire')),
                ('data', dju_common.fields.json.JSONField(blank=True, default=None, verbose_name='data')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created')),
                ('used_limit', models.PositiveIntegerField(default=1, help_text='Set 0 to unlimit.', verbose_name='used limit')),
                ('used_counter', models.PositiveIntegerField(default=0, verbose_name='used counter')),
                ('first_used', models.DateTimeField(blank=True, null=True, verbose_name='first used')),
                ('last_used', models.DateTimeField(blank=True, null=True, verbose_name='last used')),
                ('auto_delete', models.BooleanField(db_index=True, default=False, help_text='Delete object if it can no longer be used.', verbose_name='auto delete')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'ordering': ('-created',),
                'db_table': 'dju_privateurl',
                'verbose_name': 'private url',
                'verbose_name_plural': 'private urls',
            },
        ),
        migrations.AlterUniqueTogether(
            name='privateurl',
            unique_together=set([('action', 'token')]),
        ),
    ]
