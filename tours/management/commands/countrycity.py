from django.core.management.base import BaseCommand
from tours.models import Tour, Country, City

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        data = {
            "Uzbekistan": ["Tashkent", "Samarkand", "Bukhara"],
            "Kazakhstan": ["Almaty", "Astana", "Shymkent"],
            "Kyrgyzstan": ["Bishkek", "Osh", "Karakol"],
            "Turkmenistan": ["Ashgabat", "Turkmenabat", "Mary"],
            "Tajikistan": ["Dushanbe", "Khujand", "Kulob"],
            "Azerbaijan": ["Baku", "Ganja", "Sumqayit"],
        }

        # Clear and recreate countries and cities
        Country.objects.all().delete()
        City.objects.all().delete()

        country_city_map = {}
        for country_name, cities in data.items():
            country = Country.objects.create(name=country_name)
            city_objs = []
            for city_name in cities:
                city = City.objects.create(name=city_name, country=country)
                city_objs.append(city)
            country_city_map[country_name] = (country, city_objs)

        tours = Tour.objects.all().order_by('id')
        tour_index = 0
        country_cycle = list(data.items())

        for tour in tours:
            group_index = (tour_index // 20) % len(country_cycle)
            country_name, city_names = country_cycle[group_index]
            country_obj, city_objs = country_city_map[country_name]

            city = city_objs[tour_index % len(city_objs)]

            tour.country = country_obj
            tour.city = city
            tour.save()

            tour_index += 1

        self.stdout.write(self.style.SUCCESS("✅ Tours updated with Central Asian & Middle Eastern countries and cities"))
