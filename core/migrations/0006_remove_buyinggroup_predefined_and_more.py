# Generated by Django 5.1 on 2024-09-13 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_buyinggroup_referral_count_buyinggroup_referral_link'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='buyinggroup',
            name='predefined',
        ),
        migrations.RemoveField(
            model_name='buyinggroup',
            name='referral_count',
        ),
        migrations.RemoveField(
            model_name='buyinggroup',
            name='referral_link',
        ),
        migrations.AlterField(
            model_name='buyinggroup',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]