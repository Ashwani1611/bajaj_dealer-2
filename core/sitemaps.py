"""
core/sitemaps.py
─────────────────────────────────────────────────────────────────────────────
Django XML sitemap for Skyline Wheels / Skyline Bajaj.

SETUP STEPS:
1. Add 'django.contrib.sitemaps' to INSTALLED_APPS in settings.py
2. Wire up in bajaj_dealer/urls.py  (see bottom of this file)
─────────────────────────────────────────────────────────────────────────────
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Bike, BikeCategory


# ── Individual bike pages ──────────────────────────────────────────────────

class BikeSitemap(Sitemap):
    changefreq = 'weekly'
    priority   = 0.9
    protocol   = 'https'

    def items(self):
        return Bike.objects.filter(is_active=True, is_chetak=False).order_by('slug')

    def location(self, bike):
        return f'/bikes/{bike.slug}/'

    def lastmod(self, bike):
        return bike.created_at


# ── Chetak bike pages ──────────────────────────────────────────────────────

class ChetakBikeSitemap(Sitemap):
    changefreq = 'weekly'
    priority   = 0.9
    protocol   = 'https'

    def items(self):
        return Bike.objects.filter(is_active=True, is_chetak=True).order_by('slug')

    def location(self, bike):
        return f'/bikes/{bike.slug}/'

    def lastmod(self, bike):
        return bike.created_at


# ── Category filtered bike list pages ─────────────────────────────────────

class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority   = 0.8
    protocol   = 'https'

    def items(self):
        return BikeCategory.objects.all().order_by('slug')

    def location(self, cat):
        return f'/bikes/?category={cat.slug}'


# ── Static pages ───────────────────────────────────────────────────────────

class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    protocol   = 'https'

    # (url_name, priority)
    pages = [
        ('home',          1.0),
        ('bike_list',     0.9),
        ('chetak',        0.9),
        ('contact',       0.8),
        ('enquiry',       0.8),
        ('book_service',  0.8),
        ('exchange_bike', 0.7),
    ]

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]


# ═══════════════════════════════════════════════════════════════════════════
# HOW TO WIRE UP IN bajaj_dealer/urls.py
# ═══════════════════════════════════════════════════════════════════════════
#
# from django.contrib.sitemaps.views import sitemap
# from core.sitemaps import BikeSitemap, ChetakBikeSitemap, CategorySitemap, StaticSitemap
#
# sitemaps = {
#     'bikes':    BikeSitemap,
#     'chetak':   ChetakBikeSitemap,
#     'category': CategorySitemap,
#     'static':   StaticSitemap,
# }
#
# urlpatterns = [
#     ...
#     path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
#          name='django.contrib.sitemaps.views.sitemap'),
# ]
#
# Also add to INSTALLED_APPS in settings.py:
#   'django.contrib.sitemaps',