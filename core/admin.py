from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.http import HttpResponse
import csv

from .models import (
    BikeCategory, Bike, BikeColor, BikeImage,
    Showroom, ServiceStation, Enquiry, ServiceBooking,
    YouTubeVideo, ExchangeRequest
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_superadmin(user):
    return user.is_superuser

def _managed_showroom(user):
    return getattr(user, 'managed_showroom', None)

def _managed_station(user):
    return getattr(user, 'managed_station', None)


# ── CSV export ────────────────────────────────────────────────────────────────

def export_as_csv(modeladmin, request, queryset):
    meta        = modeladmin.model._meta
    field_names = [f.name for f in meta.fields]
    response    = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta}.csv'
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response
export_as_csv.short_description = 'Export selected as CSV'


# ── User admin — ONLY superadmin can create/edit/delete users ─────────────────

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    def has_module_perms(self, request):
        return _is_superadmin(request.user)

    def has_view_permission(self, request, obj=None):
        return _is_superadmin(request.user)

    def has_add_permission(self, request):
        return _is_superadmin(request.user)

    def has_change_permission(self, request, obj=None):
        return _is_superadmin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_superadmin(request.user)


# ── BikeImage inline form ─────────────────────────────────────────────────────

class BikeImageInlineForm(forms.ModelForm):
    class Meta:
        model   = BikeImage
        fields  = '__all__'
        widgets = {
            'media_link': forms.URLInput(attrs={
                'style': 'width:420px;',
                'placeholder': (
                    'Paste link — Image URL | YouTube (youtube.com/watch?v=...) | '
                    'Google Drive (drive.google.com/uc?export=view&id=FILE_ID)'
                )
            }),
        }


class BikeImageInline(admin.TabularInline):
    model           = BikeImage
    form            = BikeImageInlineForm
    extra           = 1
    fields          = ['media_type', 'image_file', 'video_file', 'media_link', 'order', 'media_preview']
    readonly_fields = ['media_preview']
    can_delete      = True

    def media_preview(self, obj):
        if not obj.pk:
            return '—'
        url = obj.get_display_url()
        if not url:
            return '—'
        if obj.is_image():
            return format_html(
                '<img src="{}" style="height:60px;width:90px;object-fit:cover;'
                'border-radius:5px;" referrerpolicy="no-referrer">', url)
        if obj.is_youtube():
            return format_html(
                '<img src="{}" style="height:60px;width:90px;object-fit:cover;'
                'border-radius:5px;">', obj.get_youtube_thumbnail())
        if obj.is_video():
            return format_html(
                '<video src="{}" style="height:60px;width:90px;object-fit:cover;'
                'border-radius:5px;" muted></video>', url)
        return '—'
    media_preview.short_description = 'Preview'


# ── BikeColor inline ──────────────────────────────────────────────────────────

class BikeColorInline(admin.StackedInline):
    model            = BikeColor
    extra            = 1
    fields           = ['name', 'color_hex', 'order', 'is_available']
    show_change_link = True


# ── BikeColor admin ───────────────────────────────────────────────────────────

@admin.register(BikeColor)
class BikeColorAdmin(admin.ModelAdmin):
    inlines       = [BikeImageInline]
    list_display  = ['bike', 'name', 'color_hex_preview', 'order', 'is_available']
    list_filter   = ['bike']
    search_fields = ['bike__name', 'name']

    def color_hex_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;'
            'background:{};border-radius:4px;border:1px solid #ccc;'
            'vertical-align:middle;"></span>&nbsp;{}',
            obj.color_hex, obj.color_hex)
    color_hex_preview.short_description = 'Color'


# ── Bike admin ────────────────────────────────────────────────────────────────

@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    inlines             = [BikeColorInline]
    list_display        = ['name', 'category', 'formatted_price', 'is_featured', 'is_active']
    list_filter         = ['category', 'is_featured', 'is_active']
    list_editable       = ['is_featured', 'is_active']
    search_fields       = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BikeCategory)
class BikeCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display        = ['name', 'slug', 'order']


# ── Showroom admin ────────────────────────────────────────────────────────────

@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'whatsapp_number', 'email', 'manager', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    search_fields = ['name', 'address']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'address', 'order', 'is_active')}),
        ('Contact',    {'fields': ('phone', 'phone2', 'whatsapp_number', 'email')}),
        ('Location',   {'fields': ('google_maps_url', 'google_maps_embed')}),
        ('Hours',      {'fields': ('working_hours',)}),
        ('Access',     {'fields': ('manager',)}),
    )

    def get_readonly_fields(self, request, obj=None):
        if not _is_superadmin(request.user):
            return ('manager',)
        return ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_superadmin(request.user):
            return qs
        showroom = _managed_showroom(request.user)
        if showroom:
            return qs.filter(pk=showroom.pk)
        return qs.none()

    def has_add_permission(self, request):
        return _is_superadmin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_superadmin(request.user)


# ── ServiceStation admin ──────────────────────────────────────────────────────

@admin.register(ServiceStation)
class ServiceStationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'whatsapp_number', 'email', 'manager', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    search_fields = ['name', 'address']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'address', 'order', 'is_active')}),
        ('Contact',    {'fields': ('phone', 'phone2', 'whatsapp_number', 'email')}),
        ('Location',   {'fields': ('google_maps_url', 'google_maps_embed')}),
        ('Hours',      {'fields': ('working_hours',)}),
        ('Access',     {'fields': ('manager',)}),
    )

    def get_readonly_fields(self, request, obj=None):
        if not _is_superadmin(request.user):
            return ('manager',)
        return ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_superadmin(request.user):
            return qs
        station = _managed_station(request.user)
        if station:
            return qs.filter(pk=station.pk)
        return qs.none()

    def has_add_permission(self, request):
        return _is_superadmin(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_superadmin(request.user)


# ── Enquiry admin ─────────────────────────────────────────────────────────────

def mark_as_read(modeladmin, request, queryset):
    queryset.update(is_read=True)
mark_as_read.short_description = 'Mark selected as read'

def mark_as_unread(modeladmin, request, queryset):
    queryset.update(is_read=False)
mark_as_unread.short_description = 'Mark selected as unread'


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display    = ['name', 'phone', 'enquiry_type_badge', 'bike', 'showroom', 'read_status', 'created_at']
    list_filter     = ['enquiry_type', 'is_read', 'showroom']
    search_fields   = ['name', 'phone', 'email']
    readonly_fields = ['created_at']
    actions         = [mark_as_read, mark_as_unread, export_as_csv]
    date_hierarchy  = 'created_at'

    BADGE_COLORS = {
        'test_ride': ('#e8f0fb', '#003087'),
        'purchase':  ('#d4edda', '#155724'),
        'general':   ('#fff3cd', '#856404'),
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('bike', 'showroom')
        if _is_superadmin(request.user):
            return qs
        showroom = _managed_showroom(request.user)
        if showroom:
            return qs.filter(showroom=showroom)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not _is_superadmin(request.user):
            showroom = _managed_showroom(request.user)
            if showroom and 'showroom' in form.base_fields:
                form.base_fields['showroom'].queryset = Showroom.objects.filter(pk=showroom.pk)
        return form

    def enquiry_type_badge(self, obj):
        bg, color = self.BADGE_COLORS.get(obj.enquiry_type, ('#eee', '#333'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:.8rem;font-weight:600;">{}</span>',
            bg, color, obj.get_enquiry_type_display())
    enquiry_type_badge.short_description = 'Type'

    def read_status(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color:#155724;font-weight:600;">&#10003; Read</span>')
        return format_html(
            '<span style="color:#003087;font-weight:700;">&#9679; New</span>')
    read_status.short_description = 'Status'


# ── ServiceBooking admin ──────────────────────────────────────────────────────

def mark_confirmed(modeladmin, request, queryset):
    queryset.update(status='confirmed')
mark_confirmed.short_description = 'Mark selected as Confirmed'

def mark_completed(modeladmin, request, queryset):
    queryset.update(status='completed')
mark_completed.short_description = 'Mark selected as Completed'


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display    = ['name', 'phone', 'bike_model', 'service_station',
                       'preferred_date', 'status_badge', 'created_at']
    list_filter     = ['status', 'service_station', 'preferred_date']
    search_fields   = ['name', 'phone', 'bike_model', 'registration_number']
    readonly_fields = ['created_at']
    actions         = [mark_confirmed, mark_completed, export_as_csv]
    date_hierarchy  = 'created_at'

    STATUS_COLORS = {
        'pending':   ('#fff3cd', '#856404'),
        'confirmed': ('#d4edda', '#155724'),
        'completed': ('#e8f0fb', '#003087'),
        'cancelled': ('#f8d7da', '#721c24'),
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_superadmin(request.user):
            return qs
        station = _managed_station(request.user)
        if station:
            return qs.filter(service_station=station)
        showroom = _managed_showroom(request.user)
        if showroom:
            return qs.filter(showroom=showroom)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not _is_superadmin(request.user):
            station = _managed_station(request.user)
            if station and 'service_station' in form.base_fields:
                form.base_fields['service_station'].queryset = ServiceStation.objects.filter(pk=station.pk)
            showroom = _managed_showroom(request.user)
            if showroom and 'showroom' in form.base_fields:
                form.base_fields['showroom'].queryset = Showroom.objects.filter(pk=showroom.pk)
        return form

    def status_badge(self, obj):
        bg, color = self.STATUS_COLORS.get(obj.status, ('#eee', '#333'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:.8rem;font-weight:600;">{}</span>',
            bg, color, obj.get_status_display())
    status_badge.short_description = 'Status'


# ── YouTubeVideo admin ────────────────────────────────────────────────────────

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display  = ['title', 'section', 'is_active', 'order', 'thumbnail_preview']
    list_filter   = ['section', 'is_active']
    list_editable = ['is_active', 'order']

    def thumbnail_preview(self, obj):
        return format_html(
            '<img src="{}" style="height:40px;width:70px;object-fit:cover;'
            'border-radius:4px;">',
            obj.thumbnail_url())
    thumbnail_preview.short_description = 'Preview'


# ── ExchangeRequest admin ─────────────────────────────────────────────────────

@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display    = ['name', 'phone', 'current_bike', 'current_bike_year',
                       'km_driven', 'interested_in', 'showroom', 'created_at']
    search_fields   = ['name', 'phone', 'current_bike']
    list_filter     = ['showroom']
    readonly_fields = ['created_at']
    actions         = [export_as_csv]
    date_hierarchy  = 'created_at'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _is_superadmin(request.user):
            return qs
        showroom = _managed_showroom(request.user)
        if showroom:
            return qs.filter(showroom=showroom)
        return qs.none()
# ── Custom admin site header link ─────────────────────────────────────────────
admin.site.index_template = 'admin/custom_index.html'