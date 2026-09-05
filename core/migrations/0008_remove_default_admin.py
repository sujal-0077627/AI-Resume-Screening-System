from django.db import migrations


def remove_default_admin(apps, schema_editor):
    User = apps.get_model('core', 'User')
    # Delete default dummy admin account
    User.objects.filter(username='admin', email='admin@example.com').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_user_otp_secret_alter_user_reset_token'),
    ]

    operations = [
        migrations.RunPython(remove_default_admin, migrations.RunPython.noop),
    ]
