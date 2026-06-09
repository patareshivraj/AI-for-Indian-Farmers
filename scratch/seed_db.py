import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farm_360_backend.settings')
django.setup()

from schemes_discovery.models import DiscoveredURL, ExtractedContent

# Mock a DiscoveredURL
url, _ = DiscoveredURL.objects.get_or_create(
    url="https://pmfby.gov.in/guidelines",
    defaults={
        'title': "Pradhan Mantri Fasal Bima Yojana",
        'source_domain': "pmfby.gov.in",
        'discovery_score': 95,
        'is_relevant': True,
        'is_processed': True
    }
)

# Mock ExtractedContent
content_text = """
Pradhan Mantri Fasal Bima Yojana (PMFBY) is the government sponsored crop insurance scheme that integrates multiple stakeholders on a single platform.
Eligibility:
- All farmers growing notified crops in a notified area during the season who have insurable interest in the crop are eligible.
- Specifically targets Small and Marginal farmers.
- Tenant farmers and sharecroppers are also eligible.
Benefits:
- Provides comprehensive insurance cover against failure of the crop thus helping in stabilizing the income of the farmers.
- Encourages farmers to adopt innovative and modern agricultural practices.
- Covers pre-sowing, standing crop, post-harvest losses, and localized calamities.
Documents Required:
- Aadhaar Card
- Land records (7/12, 8A)
- Bank Passbook
Apply URL: https://pmfby.gov.in/apply
"""

ExtractedContent.objects.get_or_create(
    url=url,
    defaults={
        'raw_html': '<html><body>' + content_text + '</body></html>',
        'clean_content': content_text,
        'heuristic_score': 80,
        'is_valid_scheme_page': True
    }
)

print("Successfully seeded DB with PMFBY mock data!")
