# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-14 12:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0031_auto_20170624_0124'),
    ]

    operations = [
        migrations.AddField(
            model_name='variantnote',
            name='submit_to_clinvar',
            field=models.BooleanField(default=False),
        ),
    ]