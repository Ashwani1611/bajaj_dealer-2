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
    YouTubeVideo, ExchangeRequest,
)


# ── multiple-file widget ──────────────────────────────────────────────────────

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        # Force single-file return for form validation.
        # save_formset uses request.FILES.getlist() to grab the extras.
        return files.get(name)


# ── shared upload handler ─────────────────────────────────────────────────────

def handle_multiple_uploads(request, formset):
    """
    Handles multi-file uploads for BikeImage inlines on both Bike and BikeColor.
    First file goes into the existing inline row; extra files become new BikeImage rows.
    Also correctly auto-fills bike/color FKs using the updated model logic.
    """
    formset.save(commit=False)

    for obj in formset.deleted_objects:
        obj.delete()

    for f_form in formset.forms:
        if not f_form.cleaned_data or f_form.cleaned_data.get('DELETE'):
            continue

        file_key = f"{f_form.prefix}-image_file"
        files    = request.FILES.getlist(file_key)
        parent   = formset.instance

        # Resolve bike and color from the inline's parent model
        if isinstance(parent, Bike):
            target_bike  = parent
            target_color = f_form.cleaned_data.get('color')   # may be None
        elif isinstance(parent, BikeColor):
            target_bike  = parent.bike
            target_color = parent
        else:
            target_bike  = f_form.cleaned_data.get('bike')
            target_color = f_form.cleaned_data.get('color')

        if files:
            # First file → update the existing inline row
            f_form.instance.image_file  = files[0]
            f_form.instance.bike        = target_bike
            f_form.instance.color       = target_color
            # Auto-detect gif vs image (mirrors BikeImage.save() logic)
            import os
            ext = os.path.splitext(files[0].name)[1].lower()
            f_form.instance.media_type = 'gif_upload' if ext == '.gif' else 'image_upload'
            f_form.instance.save()

            # Extra files → new BikeImage objects
            for extra_file in files[1:]:
                ext = os.path.splitext(extra_file.name)[1].lower()
                BikeImage.objects.create(
                    bike       = target_bike,
                    color      = target_color,
                    image_file = extra_file,
                    media_type = 'gif_upload' if ext == '.gif' else 'image_upload',
                    order      = f_form.instance.order,
                )
        else:
            # No new file uploaded — just save other field changes (media_link, order, etc.)
            f_form.instance.bike  = target_bike
            f_form.instance.color = target_color
            f_form.instance.save()

    formset.save_m2m()


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_superadmin(user):
    return user.is_superuser

def _managed_showroom(user):
    return getattr(user, 'managed_showroom', None)

def _managed_station(user):
    return getattr(user, 'managed_station', None)


# ── CSV export action ─────────────────────────────────────────────────────────

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


# ── User admin — superadmin only ──────────────────────────────────────────────

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
    image_file = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label='📁 Image / GIF Upload (select multiple)',
    )

    class Meta:
        model  = BikeImage
        fields = '__all__'
        widgets = {
            'media_link': forms.URLInput(attrs={
                'style':       'width:420px;',
                'placeholder': (
                    'Paste: Image URL | YouTube (youtube.com/watch?v=...) | '
                    'Google Drive share link (drive.google.com/file/d/...)'
                ),
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type', 'image_upload')
        image_file = cleaned_data.get('image_file')
        video_file = cleaned_data.get('video_file')
        media_link = (cleaned_data.get('media_link') or '').strip()  # ← the fix

        # Empty extra inline row — skip validation entirely
        if not image_file and not video_file and not media_link:
            return cleaned_data

        if media_type in ('image_upload', 'gif_upload') and not image_file:
            self.add_error('image_file', 'Please upload an image file.')
        if media_type == 'video_upload' and not video_file:
            self.add_error('video_file', 'Please upload a video file.')
        if media_type in ('image_url', 'video_url') and not media_link:
            self.add_error('media_link', 'Please provide a URL.')
        if media_type == 'youtube' and not media_link:
            self.add_error('media_link', 'Please provide a YouTube URL or video ID.')

        return cleaned_data


# ── shared media_preview method ───────────────────────────────────────────────

def _media_preview(obj):
    """
    Returns an HTML preview thumbnail for a BikeImage object.
    Uses get_youtube_thumbnail_url() from the updated model.
    """
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
        # Use the correct method name from the updated model
        thumb = obj.get_youtube_thumbnail_url()
        return format_html(
            '<img src="{}" style="height:60px;width:90px;object-fit:cover;'
            'border-radius:5px;">', thumb)
    if obj.is_video():
        return format_html(
            '<video src="{}" style="height:60px;width:90px;object-fit:cover;'
            'border-radius:5px;" muted></video>', url)
    return '—'


# ── GeneralBikeImageInline (bike-level media, no color) ───────────────────────

class GeneralBikeImageInline(admin.TabularInline):
    model           = BikeImage
    form            = BikeImageInlineForm
    extra           = 1
    fields          = ['media_type', 'image_file', 'video_file', 'media_link', 'color', 'order', 'media_preview']
    readonly_fields = ['media_preview']
    can_delete      = True
    verbose_name        = 'General Media (no color)'
    verbose_name_plural = 'General Media (no color assigned)'

    def get_queryset(self, request):
        # Only show media NOT assigned to any color variant
        return super().get_queryset(request).filter(color__isnull=True)

    def media_preview(self, obj):
        return _media_preview(obj)
    media_preview.short_description = 'Preview'


# ── BikeImageInline (color-level media) ──────────────────────────────────────

class BikeImageInline(admin.TabularInline):
    model           = BikeImage
    form            = BikeImageInlineForm
    extra           = 1
    fields          = ['media_type', 'image_file', 'video_file', 'media_link', 'order', 'media_preview']
    readonly_fields = ['media_preview']
    can_delete      = True
    verbose_name        = 'Color Media'
    verbose_name_plural = 'Color Media (images & videos for this color)'

    def media_preview(self, obj):
        return _media_preview(obj)
    media_preview.short_description = 'Preview'


# ── BikeColor inline (inside BikeAdmin) ──────────────────────────────────────

class BikeColorInline(admin.StackedInline):
    model            = BikeColor
    extra            = 1
    fields           = ['name', 'color_hex', 'order', 'is_available']
    show_change_link = True   # links to BikeColorAdmin where images are managed


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

    def save_formset(self, request, form, formset, change):
        if formset.model == BikeImage:
            handle_multiple_uploads(request, formset)
        else:
            formset.save()


# ── BikeCategory admin ────────────────────────────────────────────────────────

@admin.register(BikeCategory)
class BikeCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display        = ['name', 'slug', 'order']
    list_editable       = ['order']


# ── Bike admin ────────────────────────────────────────────────────────────────

@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    inlines             = [GeneralBikeImageInline, BikeColorInline]
    list_display        = ['name', 'category', 'formatted_price', 'is_featured', 'is_active', 'primary_image_preview']
    list_filter         = ['category', 'is_featured', 'is_active']
    list_editable       = ['is_featured', 'is_active']
    search_fields       = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def primary_image_preview(self, obj):
        url = obj.get_primary_image_url()
        if url:
            return format_html(
                '<img src="{}" style="height:40px;width:60px;object-fit:cover;'
                'border-radius:4px;" referrerpolicy="no-referrer">', url)
        return '—'
    primary_image_preview.short_description = 'Image'

    def save_formset(self, request, form, formset, change):
        if formset.model == BikeImage:
            handle_multiple_uploads(request, formset)
        else:
            formset.save()


# ── Showroom admin ────────────────────────────────────────────────────────────

@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'whatsapp_number', 'has_service_center',
                     'manager', 'is_active', 'order']
    list_editable = ['has_service_center', 'is_active', 'order']
    search_fields = ['name', 'address']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'address', 'order', 'is_active', 'has_service_center')}),
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
    list_display  = ['name', 'phone', 'whatsapp_number', 'email',
                     'manager', 'is_active', 'order']
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
    list_display    = ['name', 'phone', 'enquiry_type_badge', 'bike',
                       'showroom', 'read_status', 'created_at']
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
        # Uses related_name='enquiries' added in updated models
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
    list_display    = ['name', 'phone', 'bike_model', 'location_display',
                       'preferred_date', 'status_badge', 'created_at']
    list_filter     = ['status', 'service_station', 'showroom', 'preferred_date']
    search_fields   = ['name', 'phone', 'bike_model', 'registration_number']
    readonly_fields = ['created_at', 'location_display']
    actions         = [mark_confirmed, mark_completed, export_as_csv]
    date_hierarchy  = 'created_at'

    STATUS_COLORS = {
        'pending':   ('#fff3cd', '#856404'),
        'confirmed': ('#d4edda', '#155724'),
        'completed': ('#e8f0fb', '#003087'),
        'cancelled': ('#f8d7da', '#721c24'),
    }

    def location_display(self, obj):
        """Shows the active location (service_station OR showroom) in list/detail."""
        name = obj.get_location_name()
        loc  = obj.get_location()
        if loc is None:
            return format_html('<span style="color:#999;">—</span>')
        label = 'Station' if obj.service_station else 'Showroom'
        return format_html(
            '<span style="font-size:.8rem;color:#666;">[{}]</span> {}', label, name)
    location_display.short_description = 'Location'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('service_station', 'showroom')
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
                form.base_fields['service_station'].queryset = (
                    ServiceStation.objects.filter(pk=station.pk)
                )
            showroom = _managed_showroom(request.user)
            if showroom and 'showroom' in form.base_fields:
                form.base_fields['showroom'].queryset = (
                    Showroom.objects.filter(pk=showroom.pk)
                )
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
        # Uses related_name='exchange_requests' added in updated models
        qs = super().get_queryset(request).select_related('interested_in', 'showroom')
        if _is_superadmin(request.user):
            return qs
        showroom = _managed_showroom(request.user)
        if showroom:
            return qs.filter(showroom=showroom)
        return qs.none()


# ── Custom admin site template ────────────────────────────────────────────────

admin.site.index_template = 'admin/custom_index.html'