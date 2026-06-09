from django.core.management.base import BaseCommand
from schemes_discovery.models import Scheme as ExtractedScheme, SourceMapping
from schemes_discovery.intelligence import process_extracted_scheme

class Command(BaseCommand):
    help = 'Runs the Phase 4 Intelligence Layer to consolidate and deduplicate extracted schemes into Golden Records.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the Scheme Intelligence Pipeline...'))
        
        # Find schemes that haven't been mapped to a Master yet
        unmapped_schemes = ExtractedScheme.objects.exclude(
            id__in=SourceMapping.objects.values('extracted_scheme_id')
        )
        
        count = unmapped_schemes.count()
        self.stdout.write(f'Found {count} unmapped extracted schemes.')
        
        for idx, scheme in enumerate(unmapped_schemes, 1):
            self.stdout.write(f'[{idx}/{count}] Consolidating: {scheme.scheme_name}')
            try:
                process_extracted_scheme(scheme)
                self.stdout.write(self.style.SUCCESS(f'Successfully consolidated ID {scheme.id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed ID {scheme.id}: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS('Intelligence Pipeline execution completed.'))
