from django.db import models

class DiscoveredURL(models.Model):
    url = models.URLField(max_length=1024, unique=True)
    is_processed = models.BooleanField(default=False)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_checked_at = models.DateTimeField(auto_now=True)
    status_code = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.url

class ExtractedContent(models.Model):
    url = models.OneToOneField(DiscoveredURL, on_delete=models.CASCADE, related_name='extracted_content')
    page_title = models.CharField(max_length=512, null=True, blank=True)
    raw_content = models.TextField(help_text="The raw HTML or raw PDF text")
    clean_content = models.TextField(help_text="The normalized, boilerplate-free text")
    content_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash of clean_content")
    quality_score = models.FloatField(default=0.0, help_text="Heuristic score of relevance")
    is_valid_scheme_page = models.BooleanField(default=False)
    extracted_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.page_title} - {self.url.url}"

class Scheme(models.Model):
    SCHEME_TYPES = [
        ('LOAN', 'Loan'),
        ('INSURANCE', 'Insurance'),
        ('SUBSIDY', 'Subsidy'),
        ('ASSISTANCE', 'Financial Assistance'),
        ('OTHER', 'Other')
    ]

    scheme_name = models.CharField(max_length=512)
    scheme_type = models.CharField(max_length=50, choices=SCHEME_TYPES)
    description = models.TextField()
    
    eligibility = models.JSONField(help_text="List of eligibility criteria") 
    benefits = models.JSONField(help_text="List of financial or material benefits")
    documents_required = models.JSONField(help_text="List of required documents")
    
    official_url = models.URLField(max_length=1024)
    apply_url = models.URLField(max_length=1024, null=True, blank=True)
    
    source_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 of AI extracted content")
    discovered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.scheme_name
