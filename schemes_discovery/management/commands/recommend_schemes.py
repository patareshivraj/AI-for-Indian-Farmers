from django.core.management.base import BaseCommand
from schemes_discovery.models import FarmerProfile
from schemes_discovery.recommender import generate_recommendations

class Command(BaseCommand):
    help = 'Runs the Phase 5 Recommendation Engine for test farmers.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the Farmer Recommendation Engine...'))
        
        # Create a dummy farmer for testing if none exist
        farmer, created = FarmerProfile.objects.get_or_create(
            user_id="TEST-FARMER-001",
            defaults={
                'state': 'Maharashtra',
                'district': 'Pune',
                'land_holding_size': 1.5,
                'farmer_category': 'Marginal',
                'crop_type': ['Cotton', 'Soybean'],
                'irrigation_status': 'Rainfed',
                'annual_income': 85000,
                'gender': 'Male',
                'age': 35
            }
        )
        
        if created:
            self.stdout.write(f"Created dummy farmer profile: {farmer}")
            
        generate_recommendations(farmer)
        
        self.stdout.write(self.style.SUCCESS('Recommendation Pipeline execution completed.'))
