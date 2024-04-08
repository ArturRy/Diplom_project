# Generated by Django 5.0.3 on 2024-03-18 17:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_user_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='company',
            field=models.CharField(blank=True, max_length=40, verbose_name='Компания'),
        ),
        migrations.AddField(
            model_name='user',
            name='position',
            field=models.CharField(blank=True, max_length=40, verbose_name='Должность'),
        ),
    ]