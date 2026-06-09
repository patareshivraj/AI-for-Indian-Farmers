from django.core.management.base import BaseCommand
from schemes_discovery.services import discover_and_process_schemes

class Command(BaseCommand):
    help = 'Triggers the dynamic AI discovery pipeline to find and process new agricultural schemes.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the Farmer Scheme Discovery Pipeline...'))
        discover_and_process_schemes()
        self.stdout.write(self.style.SUCCESS('Pipeline execution completed.'))
