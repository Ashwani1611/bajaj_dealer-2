from django.conf import settings
from .models import BikeCategory, Showroom


def site_settings(request):
    return {
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'nav_categories': BikeCategory.objects.all(),
        'all_showrooms': Showroom.objects.filter(is_active=True),
        'SITE_NAME': 'Bajaj Dealer',   # change to real name later
    }
