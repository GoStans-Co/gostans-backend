from django.db import migrations
import uuid

def generate_uuids(apps, schema_editor):
    Tour = apps.get_model('tours', 'Tour')
    for tour in Tour.objects.all():
        if not tour.uuid:
            tour.uuid = uuid.uuid4()
            tour.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0006_tour_uuid_alter_tour_id'),
    ]

    operations = [
        migrations.RunPython(generate_uuids),
    ]
