from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import admin_views

urlpatterns = [
    path('admin/manage-users/', admin_views.manage_users, name='admin_manage_users'),
    path('admin/create-manager/', admin_views.create_manager, name='admin_create_manager'),
    path('admin/delete-manager/<int:user_id>/', admin_views.delete_manager, name='admin_delete_manager'),
    path('admin/reset-password/<int:user_id>/', admin_views.reset_password, name='admin_reset_password'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('webpush/', include('webpush.urls')),
]

# Only one static() call needed — you had it twice before
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)