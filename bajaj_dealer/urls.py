from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap

from core import admin_views
from core.sitemaps import (
    BikeSitemap,
    ChetakBikeSitemap,
    CategorySitemap,
    StaticSitemap,
)

# ── Sitemap registry ──────────────────────────────────────────────────────────
sitemaps = {
    'bikes':    BikeSitemap,
    'chetak':   ChetakBikeSitemap,
    'category': CategorySitemap,
    'static':   StaticSitemap,
}

urlpatterns = [
    # ── Admin custom views ────────────────────────────────────────
    path('admin/manage-users/',               admin_views.manage_users,   name='admin_manage_users'),
    path('admin/create-manager/',             admin_views.create_manager, name='admin_create_manager'),
    path('admin/delete-manager/<int:user_id>/', admin_views.delete_manager, name='admin_delete_manager'),
    path('admin/reset-password/<int:user_id>/', admin_views.reset_password, name='admin_reset_password'),
    path('admin/',                            admin.site.urls),

    # ── Core app ──────────────────────────────────────────────────
    path('', include('core.urls')),

    # ── WebPush ───────────────────────────────────────────────────
    path('webpush/', include('webpush.urls')),

    # ── SEO: sitemap.xml ──────────────────────────────────────────
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),

    # ── SEO: robots.txt ───────────────────────────────────────────
    path(
        'robots.txt',
        TemplateView.as_view(
            template_name='robots.txt',
            content_type='text/plain',
        ),
    ),
]

# ── Media files in development ────────────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)