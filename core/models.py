from django.db import models
from django.core.exceptions import ValidationError
import re
import os
from django.contrib.auth.models import User


# ── validators ────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg','HEIC']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv']

def validate_image_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Unsupported image format: {ext}. '
            f'Allowed: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        )

def validate_video_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(
            f'Unsupported video format: {ext}. '
            f'Allowed: {", ".join(ALLOWED_VIDEO_EXTENSIONS)}'
        )


# ── BikeCategory ──────────────────────────────────────────────────────────────

class BikeCategory(models.Model):
    name  = models.CharField(max_length=100)
    slug  = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Bike Categories'

    def __str__(self):
        return self.name


# ── Bike ──────────────────────────────────────────────────────────────────────

class Bike(models.Model):
    category    = models.ForeignKey(BikeCategory, on_delete=models.CASCADE, related_name='bikes')
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(unique=True)
    price       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image       = models.ImageField(upload_to='bikes/', blank=True, null=True)
    description = models.TextField(blank=True)

    engine_cc   = models.CharField(max_length=50, blank=True)
    power       = models.CharField(max_length=50, blank=True)
    torque      = models.CharField(max_length=50, blank=True)
    fuel_type   = models.CharField(max_length=50, default='Petrol')
    mileage     = models.CharField(max_length=50, blank=True)

    is_featured = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    def formatted_price(self):
        if self.price:
            return f'₹{self.price:,.0f}'
        return 'On Request'


# ── BikeColor ─────────────────────────────────────────────────────────────────

class BikeColor(models.Model):
    bike         = models.ForeignKey(Bike, on_delete=models.CASCADE, related_name='colors')
    name         = models.CharField(max_length=100)
    color_hex    = models.CharField(max_length=7, default='#cccccc')
    order        = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Bike Color'
        verbose_name_plural = 'Bike Colors'

    def __str__(self):
        return f'{self.bike.name} — {self.name}'

    def first_image_url(self):
        first = self.images.filter(
            media_type__in=['image_upload', 'image_url', 'gif_upload']
        ).first()
        if first:
            return first.get_display_url()
        return ''


# ── BikeImage ─────────────────────────────────────────────────────────────────

class BikeImage(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image_upload', '📁 Image Upload  (JPG / PNG / GIF / WebP / BMP / SVG)'),
        ('image_url',    '🔗 Image URL     (Google Drive / Photos / any direct link)'),
        ('gif_upload',   '🎞 GIF Upload'),
        ('video_upload', '📁 Video Upload  (MP4 / WebM / MOV / AVI)'),
        ('video_url',    '🔗 Video URL     (MP4 / WebM direct link or Google Drive)'),
        ('youtube',      '▶  YouTube Link  (any youtube.com / youtu.be format)'),
    ]

    color      = models.ForeignKey(BikeColor, on_delete=models.CASCADE, related_name='images')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='image_upload')
    image_file = models.FileField(upload_to='bikes/images/', blank=True, null=True, validators=[validate_image_file])
    video_file = models.FileField(upload_to='bikes/videos/', blank=True, null=True, validators=[validate_video_file])
    media_link = models.URLField(blank=True, null=True, max_length=1000)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Bike Media'
        verbose_name_plural = 'Bike Media'

    def __str__(self):
        return f'{self.color} — {self.get_media_type_display()} (#{self.order})'

    def is_image(self):   return self.media_type in ('image_upload', 'image_url', 'gif_upload')
    def is_gif(self):     return self.media_type == 'gif_upload'
    def is_video(self):   return self.media_type in ('video_upload', 'video_url', 'youtube')
    def is_youtube(self): return self.media_type == 'youtube'

    def get_youtube_embed_url(self):
        url = self.media_link or ''
        patterns = [
            r'youtube\.com/watch\?v=([^&\s]+)',
            r'youtu\.be/([^?\s]+)',
            r'youtube\.com/embed/([^?\s]+)',
            r'youtube\.com/shorts/([^?\s]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return f'https://www.youtube.com/embed/{match.group(1)}'
        return url

    def get_youtube_thumbnail(self):
        embed = self.get_youtube_embed_url()
        match = re.search(r'embed/([^?]+)', embed)
        if match:
            return f'https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg'
        return ''

    def get_drive_direct_url(self, url):
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            return f'https://drive.google.com/uc?export=view&id={match.group(1)}'
        return url

    def get_display_url(self):
        if self.media_type == 'image_upload':
            return self.image_file.url if self.image_file else ''
        elif self.media_type == 'gif_upload':
            return self.image_file.url if self.image_file else ''
        elif self.media_type == 'video_upload':
            return self.video_file.url if self.video_file else ''
        elif self.media_type == 'image_url':
            url = self.media_link or ''
            if 'drive.google.com' in url and '/uc?' not in url:
                return self.get_drive_direct_url(url)
            return url
        elif self.media_type == 'video_url':
            url = self.media_link or ''
            if 'drive.google.com' in url and '/uc?' not in url:
                return self.get_drive_direct_url(url)
            return url
        elif self.media_type == 'youtube':
            return self.get_youtube_embed_url()
        return ''

    def get_file_extension(self):
        url = self.get_display_url()
        return os.path.splitext(url)[1].lower()


# ── Showroom ──────────────────────────────────────────────────────────────────

class Showroom(models.Model):
    name               = models.CharField(max_length=200)
    address            = models.TextField()
    phone              = models.CharField(max_length=20, help_text='Primary contact number')
    phone2             = models.CharField(max_length=20, blank=True, help_text='Secondary number (optional)')
    whatsapp_number    = models.CharField(
        max_length=15, blank=True,
        help_text='WhatsApp number WITH country code, no + sign. e.g. 919953807755'
    )
    email              = models.EmailField(blank=True, help_text='Enquiries from this showroom go here')
    google_maps_url    = models.URLField(blank=True)
    google_maps_embed  = models.TextField(blank=True, help_text='Paste full Google Maps iframe embed code')
    working_hours      = models.CharField(max_length=150, default='Mon–Sun: 10:00 AM – 6:30 PM | Tuesday Off')
    is_active          = models.BooleanField(default=True)
    order              = models.PositiveIntegerField(default=0)
    manager            = models.OneToOneField(          # ← NEW
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_showroom',
        help_text='This user can only see this showroom\'s data in admin'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    def get_whatsapp_number(self):
        num = (self.whatsapp_number or self.phone).replace(' ', '').replace('-', '').replace('+', '')
        if num and not num.startswith('91'):
            num = '91' + num
        return num

    def whatsapp_url(self, message=''):
        import urllib.parse
        num = self.get_whatsapp_number()
        if message:
            return f"https://wa.me/{num}?text={urllib.parse.quote(message)}"
        return f"https://wa.me/{num}"


# ── ServiceStation ────────────────────────────────────────────────────────────

class ServiceStation(models.Model):
    name              = models.CharField(max_length=200)
    address           = models.TextField()
    phone             = models.CharField(max_length=20)
    phone2            = models.CharField(max_length=20, blank=True)
    whatsapp_number   = models.CharField(
        max_length=15, blank=True,
        help_text='WhatsApp number with country code, no + sign. e.g. 919953807755'
    )
    email             = models.EmailField(blank=True, help_text='Service booking notifications go here')
    google_maps_url   = models.URLField(blank=True)
    google_maps_embed = models.TextField(blank=True)
    working_hours     = models.CharField(
        max_length=150,
        default='Mon, Wed–Sun: 9:00 AM – 6:00 PM | Tuesday Closed'
    )
    is_active         = models.BooleanField(default=True)
    order             = models.PositiveIntegerField(default=0)
    manager           = models.OneToOneField(          # ← NEW
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_station',
        help_text='This user can only see this station\'s data in admin'
    )

    class Meta:
        ordering = ['order']
        verbose_name        = 'Service Station'
        verbose_name_plural = 'Service Stations'

    def __str__(self):
        return self.name

    def get_whatsapp_number(self):
        num = (self.whatsapp_number or self.phone).replace(' ', '').replace('-', '').replace('+', '')
        if num and not num.startswith('91'):
            num = '91' + num
        return num

    def whatsapp_url(self, message=''):
        import urllib.parse
        num = self.get_whatsapp_number()
        if message:
            return f"https://wa.me/{num}?text={urllib.parse.quote(message)}"
        return f"https://wa.me/{num}"


# ── Enquiry ───────────────────────────────────────────────────────────────────

class Enquiry(models.Model):
    ENQUIRY_TYPE_CHOICES = [
        ('test_ride', 'Book Test Ride'),
        ('purchase',  'Purchase Enquiry'),
        ('general',   'General Enquiry'),
    ]
    name         = models.CharField(max_length=200)
    phone        = models.CharField(max_length=15)
    email        = models.EmailField(blank=True)
    enquiry_type = models.CharField(max_length=20, choices=ENQUIRY_TYPE_CHOICES, default='test_ride')
    bike         = models.ForeignKey(Bike, on_delete=models.SET_NULL, null=True, blank=True)
    showroom     = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True)
    message      = models.TextField(blank=True)
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f'{self.name} - {self.get_enquiry_type_display()} - {self.created_at.strftime("%d %b %Y")}'


# ── ServiceBooking ────────────────────────────────────────────────────────────

class ServiceBooking(models.Model):
    """
    Service booking — links to a ServiceStation (not Showroom).
    Each station has its own WhatsApp and email.
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    name                = models.CharField(max_length=200)
    phone               = models.CharField(max_length=15)
    email               = models.EmailField(blank=True)
    bike_model          = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=20, blank=True)
    showroom            = models.ForeignKey(
        Showroom, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Preferred showroom (optional)'
    )
    service_station     = models.ForeignKey(
        ServiceStation, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Select the service station for the appointment'
    )
    preferred_date      = models.DateField()
    issue_description   = models.TextField(blank=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at          = models.DateTimeField(auto_now_add=True)

    # Keep backward compat
    @property
    def is_confirmed(self):
        return self.status == 'confirmed'

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Service Booking'
        verbose_name_plural = 'Service Bookings'

    def __str__(self):
        return f'{self.name} - {self.bike_model} - {self.preferred_date}'


# ── YouTubeVideo ──────────────────────────────────────────────────────────────

class YouTubeVideo(models.Model):
    SECTION_CHOICES = [
        ('home',   'Home Page'),
        ('bikes',  'Bikes Page'),
        ('events', 'Events'),
    ]
    title      = models.CharField(max_length=200)
    youtube_id = models.CharField(max_length=20, help_text='e.g. dQw4w9WgXcQ')
    section    = models.CharField(max_length=20, choices=SECTION_CHOICES, default='home')
    is_active  = models.BooleanField(default=True)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def embed_url(self):
        return f'https://www.youtube.com/embed/{self.youtube_id}'

    def thumbnail_url(self):
        return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'


# ── ExchangeRequest ───────────────────────────────────────────────────────────

class ExchangeRequest(models.Model):
    name               = models.CharField(max_length=200)
    phone              = models.CharField(max_length=15)
    current_bike       = models.CharField(max_length=200)
    current_bike_year  = models.PositiveIntegerField()
    km_driven          = models.PositiveIntegerField()
    interested_in      = models.ForeignKey(Bike, on_delete=models.SET_NULL, null=True, blank=True)
    showroom           = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.current_bike} exchange'