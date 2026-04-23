from .models import BikeCategory, Showroom
from django.conf import settings


def site_globals(request):
    """
    Injects into every template:
      - nav_categories  : all bike categories (for navbar dropdown + footer)
      - all_showrooms   : all active showrooms (for footer strip)
      - primary_showroom: first active showroom (for global WhatsApp float button)
      - SITE_NAME       : from settings
      - LOGO_URL        : from settings (path to your Skyline Bajaj logo image)
      - WHATSAPP_NUMBER : fallback global WA number from settings
    """
    showrooms = Showroom.objects.filter(is_active=True)
    return {
        'nav_categories':   BikeCategory.objects.order_by('order'),
        'all_showrooms':    showrooms,
        'primary_showroom': showrooms.first(),
        'SITE_NAME':        getattr(settings, 'SITE_NAME', 'Skyline Bajaj'),
        'LOGO_URL':         getattr(settings, 'LOGO_URL', ''),
        'WHATSAPP_NUMBER':  getattr(settings, 'WHATSAPP_NUMBER', ''),
    }