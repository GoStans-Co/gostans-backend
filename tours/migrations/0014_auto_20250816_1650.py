from django.db import migrations

def clean_duration(apps, schema_editor):
    Tour = apps.get_model('tours', 'Tour')
    for tour in Tour.objects.all():
        if isinstance(tour.duration, str):
            try:
                # extract the first number, e.g. "7 day" -> 7
                number = int(tour.duration.split()[0])
                tour.duration = str(number)  # keep as string for now
                tour.save(update_fields=["duration"])
            except Exception:
                pass

class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0013_tour_is_active'),
    ]

    operations = [
        migrations.RunPython(clean_duration, reverse_code=migrations.RunPython.noop),
    ]
