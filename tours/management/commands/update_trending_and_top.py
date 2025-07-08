from django.core.management.base import BaseCommand
from common.utils import calculate_trending_score, calculate_top_destinations

class Command(BaseCommand):
    help = "Recalculate trending scores and top destination popularity"

    def handle(self, *args, **kwargs):
        self.stdout.write("Recalculating trending tour scores...")
        calculate_trending_score()
        self.stdout.write("Trending scores updated.")

        self.stdout.write("Recalculating top destination popularity...")
        calculate_top_destinations()
        self.stdout.write("Top destination scores updated.")
