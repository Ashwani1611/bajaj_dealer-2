from django.contrib import admin
from .models import BikeCategory, Bike, Showroom, Enquiry, ServiceBooking, YouTubeVideo, ExchangeRequest


@admin.register(BikeCategory)
class BikeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'formatted_price', 'is_featured', 'is_active']
    list_filter = ['category', 'is_featured', 'is_active', 'fuel_type']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_featured', 'is_active']
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'name', 'slug', 'price', 'image', 'description')
        }),
        ('Specifications', {
            'fields': ('engine_cc', 'power', 'torque', 'fuel_type', 'mileage')
        }),
        ('Visibility', {
            'fields': ('is_featured', 'is_active')
        }),
    )


@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'working_hours', 'is_active', 'order']
    list_editable = ['is_active', 'order']


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'enquiry_type', 'bike', 'showroom', 'is_read', 'created_at']
    list_filter = ['enquiry_type', 'is_read', 'showroom', 'created_at']
    search_fields = ['name', 'phone']
    list_editable = ['is_read']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'bike_model', 'showroom', 'preferred_date', 'is_confirmed']
    list_filter = ['is_confirmed', 'showroom', 'preferred_date']
    search_fields = ['name', 'phone', 'bike_model', 'registration_number']
    list_editable = ['is_confirmed']
    readonly_fields = ['created_at']
    date_hierarchy = 'preferred_date'


@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'youtube_id', 'section', 'is_active', 'order']
    list_editable = ['is_active', 'order']


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'current_bike', 'current_bike_year', 'km_driven', 'created_at']
    readonly_fields = ['created_at']
