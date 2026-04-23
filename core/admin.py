from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BikeCategory, Bike, BikeColor, BikeImage,
    Showroom, Enquiry, ServiceBooking, YouTubeVideo, ExchangeRequest
)


# ── Custom form for BikeImage inline ─────────────────────────────────────────

class BikeImageInlineForm(forms.ModelForm):

    class Meta:
        model = BikeImage
        fields = '__all__'
        widgets = {
            'media_link': forms.URLInput(attrs={
                'style': 'width:420px;',
                'placeholder': (
                    'Paste link here — '
                    'Image URL (.jpg/.png/.gif) | '
                    'YouTube (youtube.com/watch?v=...) | '
                    'Google Drive (drive.google.com/uc?export=view&id=FILE_ID)'
                )
            }),
        }
        help_texts = {
            'media_type': (
                'Select type first, then either upload a file OR paste a link below.'
            ),
            'image_file': 'Upload JPG, PNG, GIF, WebP, SVG.',
            'video_file': 'Upload MP4, WebM, MOV, AVI.',
            'media_link': (
                '<b>Image URL</b> — any direct .jpg/.png/.gif/.webp link<br>'
                '<b>Google Drive</b> — '
                'https://drive.google.com/uc?export=view&id=YOUR_FILE_ID<br>'
                '<b>YouTube</b> — '
                'https://youtube.com/watch?v=VIDEO_ID '
                'or https://youtu.be/VIDEO_ID<br>'
                '<b>Direct video</b> — any .mp4/.webm link'
            ),
        }


class BikeImageInline(admin.TabularInline):
    model  = BikeImage
    form   = BikeImageInlineForm
    extra  = 1
    fields = ['media_type', 'image_file', 'video_file', 'media_link', 'order']
    can_delete = True

    # preview thumbnail in the inline row
    readonly_fields = ['media_preview']

    def get_fields(self, request, obj=None):
        return ['media_type', 'image_file', 'video_file',
                'media_link', 'order', 'media_preview']

    def media_preview(self, obj):
        if not obj.pk:
            return '—'
        url = obj.get_display_url()
        if not url:
            return '—'
        if obj.is_image():
            return format_html(
                '<img src="{}" style="height:60px; width:90px; '
                'object-fit:cover; border-radius:5px;" '
                'referrerpolicy="no-referrer">',
                url
            )
        if obj.is_youtube():
            thumb = obj.get_youtube_thumbnail()
            return format_html(
                '<img src="{}" style="height:60px; width:90px; '
                'object-fit:cover; border-radius:5px;">',
                thumb
            )
        if obj.is_video():
            return format_html(
                '<video src="{}" style="height:60px; width:90px; '
                'object-fit:cover; border-radius:5px;" muted></video>',
                url
            )
        return '—'
    media_preview.short_description = 'Preview'


# ── Color inline inside Bike ──────────────────────────────────────────────────

class BikeColorInline(admin.StackedInline):
    model            = BikeColor
    extra            = 1
    fields           = ['name', 'color_hex', 'order', 'is_available']
    show_change_link = True   # "Change" link → opens color page → manage images


# ── BikeColor admin ───────────────────────────────────────────────────────────

@admin.register(BikeColor)
class BikeColorAdmin(admin.ModelAdmin):
    inlines       = [BikeImageInline]
    list_display  = ['bike', 'name', 'color_hex_preview', 'order', 'is_available']
    list_filter   = ['bike']
    search_fields = ['bike__name', 'name']

    def color_hex_preview(self, obj):
        return format_html(
            '<span style="display:inline-block; width:20px; height:20px; '
            'background:{}; border-radius:4px; border:1px solid #ccc; '
            'vertical-align:middle;"></span>&nbsp;{}',
            obj.color_hex, obj.color_hex
        )
    color_hex_preview.short_description = 'Color'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # show a tip in the change page heading area
        return form

    # admin instructions panel at the top of the BikeColor change page
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['media_help'] = True
        return super().changeform_view(request, object_id, form_url, extra_context)


# ── Bike admin ────────────────────────────────────────────────────────────────

@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    inlines             = [BikeColorInline]
    list_display        = ['name', 'category', 'price', 'is_featured', 'is_active']
    list_filter         = ['category', 'is_featured', 'is_active']
    search_fields       = ['name']
    prepopulated_fields = {'slug': ('name',)}


# ── Rest of models ────────────────────────────────────────────────────────────

@admin.register(BikeCategory)
class BikeCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'slug', 'order']


@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'is_active', 'order']


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'enquiry_type', 'bike', 'showroom', 'is_read', 'created_at']
    list_filter   = ['enquiry_type', 'is_read']
    search_fields = ['name', 'phone']


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'bike_model', 'preferred_date', 'is_confirmed']
    list_filter   = ['is_confirmed']
    search_fields = ['name', 'phone', 'bike_model']


@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'is_active', 'order']
    list_filter  = ['section', 'is_active']


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'current_bike', 'current_bike_year', 'km_driven']
    search_fields = ['name', 'phone']