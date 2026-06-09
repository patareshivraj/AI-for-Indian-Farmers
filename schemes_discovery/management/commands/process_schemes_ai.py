from django.core.management.base import BaseCommand
from schemes_discovery.models import ExtractedContent
from schemes_discovery.ai_processor import process_extracted_content

class Command(BaseCommand):
    help = 'Triggers the AI processing pipeline to extract structured schemes from clean text.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the AI Extraction Pipeline...'))
        
        # Find all un-processed content that is valid
        unprocessed_contents = ExtractedContent.objects.filter(
            url__is_processed=True, # URL was fetched
            is_valid_scheme_page=True, # High enough heuristic score
            schemes__isnull=True # Has no extracted schemes linked to it yet
        ).distinct()
        
        count = unprocessed_contents.count()
        self.stdout.write(f'Found {count} unprocessed valid pages.')
        
        for idx, content in enumerate(unprocessed_contents, 1):
            self.stdout.write(f'[{idx}/{count}] Processing Content ID {content.id} (URL: {content.url.url})')
            try:
                process_extracted_content(content.id)
                self.stdout.write(self.style.SUCCESS(f'Successfully processed Content ID {content.id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed Content ID {content.id}: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS('AI Pipeline execution completed.'))
