from django.db import models
from django.core.exceptions import ValidationError
import re
import os
from django.contrib.auth.models import User


# ── validators ────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.heic']
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
    image       = models.ImageField(upload_to='bikes/', blank=True, null=True,
                                    help_text='Main thumbnail image for the bike listing')
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
    formatted_price.short_description = 'Price' 

    # def get_primary_image_url(self):
    # # Use prefetched colors — filter in Python, not DB
    #     for color in self.colors.all():
    #         if color.is_available:
    #             url = color.first_image_url()
    #             if url:
    #                 return url
    #     # Fall back to main image field
    #     if self.image:
    #         return self.image.url
    #     return ''


    def get_primary_image_url(self):
        # 1. Try to get the first available color image
        # Note: .all() uses the prefetch_related if you called it in your view
        for color in self.colors.all():
            if color.is_available:
                # Ensure we are calling this correctly based on your Color model
                try:
                    url = color.first_image_url() if callable(color.first_image_url) else color.first_image_url
                    if url:
                        return url
                except Exception:
                    continue

        # 2. Fallback to the main Bike image
        if self.image:
            try:
                return self.image.url
            except AttributeError:
                return ''

        # 3. Final Fallback: Return a default placeholder so the UI doesn't break
        # Make sure this file exists in your static/images folder
        from django.templatetags.static import static
        return static('images/bike-placeholder.jpg')



# ── BikeColor ─────────────────────────────────────────────────────────────────

class BikeColor(models.Model):
    bike         = models.ForeignKey(Bike, on_delete=models.CASCADE, related_name='colors')
    name         = models.CharField(max_length=100)
    color_hex    = models.CharField(max_length=7, default='#cccccc',
                                    help_text='Hex color code e.g. #ff0000')
    order        = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name        = 'Bike Color'
        verbose_name_plural = 'Bike Colors'

    def __str__(self):
        return f'{self.bike.name} — {self.name}'

    def first_image_url(self):
        """Returns the display URL of the first image assigned to this color."""
        first = self.images.filter(
            media_type__in=['image_upload', 'image_url', 'gif_upload']
        ).order_by('order').first()
        if first:
            return first.get_display_url()
        return ''

    def all_image_urls(self):
        """Returns a list of display URLs for all images of this color."""
        return [
            m.get_display_url()
            for m in self.images.filter(
                media_type__in=['image_upload', 'image_url', 'gif_upload']
            ).order_by('order')
            if m.get_display_url()
        ]

    def all_media_items(self):
        """Returns all media (images + videos) for this color, ordered."""
        return self.images.all().order_by('order')


# ── BikeImage ─────────────────────────────────────────────────────────────────

class BikeImage(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image_upload', '📁 Image Upload'),
        ('image_url',    '🔗 Image URL'),
        ('gif_upload',   '🎞 GIF Upload'),
        ('video_upload', '📁 Video Upload'),
        ('video_url',    '🔗 Video URL'),
        ('youtube',      '▶  YouTube Link'),
    ]

    # Both FKs allow null; bike is auto-filled from color in save() if missing
    bike  = models.ForeignKey(
        Bike, on_delete=models.CASCADE,
        related_name='all_media', null=True, blank=True,
        help_text='Auto-filled from color if left empty'
    )
    color = models.ForeignKey(
        BikeColor, on_delete=models.CASCADE,
        related_name='images', null=True, blank=True,
        help_text='Assign to a specific color variant, or leave blank for generic bike media'
    )
    media_type = models.CharField(
        max_length=20, choices=MEDIA_TYPE_CHOICES, default='image_upload'
    )
    image_file = models.FileField(
        upload_to='bikes/images/', blank=True, null=True,
        validators=[validate_image_file],
        help_text='Upload image/GIF file (jpg, png, gif, webp, heic, svg, bmp)'
    )
    video_file = models.FileField(
        upload_to='bikes/videos/', blank=True, null=True,
        validators=[validate_video_file],
        help_text='Upload video file (mp4, webm, mov, avi, mkv, ogg)'
    )
    media_link = models.URLField(
        blank=True, null=True, max_length=1000,
        help_text='Paste image URL, Google Drive share link, video URL, or YouTube URL'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name        = 'Bike Media'
        verbose_name_plural = 'Bike Media'

    def __str__(self):
        owner = self.color if self.color else self.bike
        return f'{owner} — {self.get_media_type_display()} (#{self.order})'

    # ── type helpers ──────────────────────────────────────────────────────────

    def is_image(self):
        return self.media_type in ('image_upload', 'image_url', 'gif_upload')

    def is_video(self):
        return self.media_type in ('video_upload', 'video_url', 'youtube')

    def is_youtube(self):
        return self.media_type == 'youtube'

    def is_drive_link(self):
        return bool(self.media_link and 'drive.google.com' in self.media_link)

    # ── URL helpers ───────────────────────────────────────────────────────────

    def get_drive_direct_url(self, url):
        """
        Converts Google Drive share links to direct stream/view URLs.
        Supports:
          https://drive.google.com/file/d/<ID>/view
          https://drive.google.com/open?id=<ID>
          https://drive.google.com/uc?id=<ID>
        """
        try:
            if 'id=' in url:
                drive_id = url.split('id=')[-1].split('&')[0]
            else:
                parts = url.split('/')
                drive_id = parts[parts.index('d') + 1]
            return f'https://drive.google.com/uc?export=view&id={drive_id}'
        except Exception:
            return url

    def get_youtube_embed_url(self):
        """Returns the YouTube embed URL using the stored video ID."""
        return f'https://www.youtube.com/embed/{self.media_link}'

    def get_youtube_thumbnail_url(self):
        """Returns the HQ thumbnail URL for the YouTube video."""
        return f'https://img.youtube.com/vi/{self.media_link}/hqdefault.jpg'

    def get_display_url(self):
        """
        Returns the correct URL for display/embedding depending on media_type:
          - image_upload / gif_upload  → uploaded file URL
          - video_upload               → uploaded video URL
          - image_url / video_url      → raw URL, or Drive direct link if Drive
          - youtube                    → YouTube embed URL
        """
        if self.media_type in ('image_upload', 'gif_upload'):
            return self.image_file.url if self.image_file else ''

        elif self.media_type == 'video_upload':
            return self.video_file.url if self.video_file else ''

        elif self.media_type in ('image_url', 'video_url'):
            url = self.media_link or ''
            if 'drive.google.com' in url:
                return self.get_drive_direct_url(url)
            return url

        elif self.media_type == 'youtube':
            return self.get_youtube_embed_url()

        return ''

    # ── save logic ────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        # 1. AUTO-FILL BIKE: derive bike from color if bike not explicitly set
        if self.color_id and not self.bike_id:
            self.bike = self.color.bike

        # 2. VALIDATE: at least one of bike or color must be set
        # if not self.bike_id and not self.color_id:
        #     raise ValidationError('BikeImage must be linked to a Bike or a BikeColor.')
        if not self.bike_id and not self.color_id:
            raise ValueError('BikeImage must be linked to a Bike or a BikeColor.')

        # 3. AUTO-SET MEDIA TYPE from uploaded file extension
        if self.image_file and self.media_type == 'image_upload':
            ext = os.path.splitext(self.image_file.name)[1].lower()
            self.media_type = 'gif_upload' if ext == '.gif' else 'image_upload'

        if self.video_file and self.media_type == 'image_upload':
            self.media_type = 'video_upload'

        # 4. YOUTUBE: extract and store only the video ID from any YouTube URL
        if self.media_type == 'youtube' and self.media_link:
            # Handles: youtu.be/<ID>, ?v=<ID>, /embed/<ID>, /shorts/<ID>
            pattern = r'(?:v=|\/embed\/|\/v\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})'
            match = re.search(pattern, self.media_link)
            if match:
                self.media_link = match.group(1)

        super().save(*args, **kwargs)

    # def clean(self):
    #     """Field-level validation called by Django forms and admin."""
    #     # image_url / video_url need a link
    #     if self.media_type in ('image_url', 'video_url') and not self.media_link:
    #         raise ValidationError(
    #             {'media_link': 'Please provide a URL for this media type.'}
    #         )
    #     # youtube needs a link
    #     if self.media_type == 'youtube' and not self.media_link:
    #         raise ValidationError(
    #             {'media_link': 'Please provide a YouTube URL or video ID.'}
    #         )
    #     # image_upload needs a file
    #     if self.media_type in ('image_upload', 'gif_upload') and not self.image_file:
    #         raise ValidationError(
    #             {'image_file': 'Please upload an image file.'}
    #         )
    #     # video_upload needs a file
    #     if self.media_type == 'video_upload' and not self.video_file:
    #         raise ValidationError(
    #             {'video_file': 'Please upload a video file.'}
    #         )
    def clean(self):
    # Skip validation for empty extra inline forms
        has_data = self.image_file or self.video_file or self.media_link
        if not has_data:
            return

        if self.media_type in ('image_url', 'video_url') and not self.media_link:
            raise ValidationError({'media_link': 'Please provide a URL for this media type.'})
        if self.media_type == 'youtube' and not self.media_link:
            raise ValidationError({'media_link': 'Please provide a YouTube URL or video ID.'})
        if self.media_type in ('image_upload', 'gif_upload') and not self.image_file:
            raise ValidationError({'image_file': 'Please upload an image file.'})
        if self.media_type == 'video_upload' and not self.video_file:
            raise ValidationError({'video_file': 'Please upload a video file.'})


# ── Showroom ──────────────────────────────────────────────────────────────────

class Showroom(models.Model):
    name               = models.CharField(max_length=200)
    address            = models.TextField()
    phone              = models.CharField(max_length=20, help_text='Primary contact number')
    phone2             = models.CharField(max_length=20, blank=True,
                                          help_text='Secondary number (optional)')
    whatsapp_number    = models.CharField(
        max_length=15, blank=True,
        help_text='WhatsApp number WITH country code, no + sign. e.g. 919953807755'
    )
    email              = models.EmailField(blank=True,
                                           help_text='Enquiries from this showroom go here')
    google_maps_url    = models.URLField(blank=True)
    google_maps_embed  = models.TextField(blank=True,
                                          help_text='Paste full Google Maps iframe embed code')
    working_hours      = models.CharField(
        max_length=150, default='Mon–Sun: 10:00 AM – 6:30 PM | Tuesday Off'
    )
    is_active          = models.BooleanField(default=True)
    has_service_center = models.BooleanField(default=False,
                                             help_text='Check if this showroom provides service')
    order              = models.PositiveIntegerField(default=0)
    manager            = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_showroom',
        help_text="This user can only see this showroom's data in admin"
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
    email             = models.EmailField(blank=True,
                                          help_text='Service booking notifications go here')
    google_maps_url   = models.URLField(blank=True)
    google_maps_embed = models.TextField(blank=True)
    working_hours     = models.CharField(
        max_length=150,
        default='Mon, Wed–Sun: 9:00 AM – 6:00 PM | Tuesday Closed'
    )
    is_active         = models.BooleanField(default=True)
    order             = models.PositiveIntegerField(default=0)
    manager           = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_station',
        help_text="This user can only see this station's data in admin"
    )

    class Meta:
        ordering            = ['order']
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
    enquiry_type = models.CharField(
        max_length=20, choices=ENQUIRY_TYPE_CHOICES, default='test_ride'
    )
    bike         = models.ForeignKey(
        Bike, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='enquiries'
    )
    showroom     = models.ForeignKey(
        Showroom, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='enquiries'
    )
    message      = models.TextField(blank=True)
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f'{self.name} - {self.get_enquiry_type_display()} - {self.created_at.strftime("%d %b %Y")}'


# ── ServiceBooking ────────────────────────────────────────────────────────────

class ServiceBooking(models.Model):
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

    # Only showrooms that have a service center are shown here
    showroom = models.ForeignKey(
        Showroom, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'has_service_center': True},
        related_name='service_bookings',
        help_text='Select a showroom that provides service (leave blank if using a service station)'
    )
    # Optional standalone service station
    service_station = models.ForeignKey(
        ServiceStation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_bookings',
        help_text='Select a standalone service station (leave blank if using a showroom)'
    )

    preferred_date    = models.DateField()
    issue_description = models.TextField(blank=True)
    status            = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Service Booking'
        verbose_name_plural = 'Service Bookings'

    def __str__(self):
        return f'{self.name} - {self.bike_model} - {self.preferred_date}'

    def clean(self):
        """Ensure at least one service location is selected."""
        if not self.showroom and not self.service_station:
            raise ValidationError(
                'Please select either a showroom with service center or a service station.'
            )
        if self.showroom and self.service_station:
            raise ValidationError(
                'Please select only one location — either a showroom or a service station, not both.'
            )

    def get_location(self):
        """Returns whichever location is assigned to this booking."""
        return self.service_station or self.showroom

    def get_location_name(self):
        loc = self.get_location()
        return str(loc) if loc else '—'


# ── YouTubeVideo ──────────────────────────────────────────────────────────────

class YouTubeVideo(models.Model):
    SECTION_CHOICES = [
        ('home',   'Home Page'),
        ('bikes',  'Bikes Page'),
        ('events', 'Events'),
    ]
    title      = models.CharField(max_length=200)
    youtube_id = models.CharField(max_length=20,
                                  help_text='YouTube video ID only, e.g. dQw4w9WgXcQ')
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
    name              = models.CharField(max_length=200)
    phone             = models.CharField(max_length=15)
    current_bike      = models.CharField(max_length=200)
    current_bike_year = models.PositiveIntegerField()
    km_driven         = models.PositiveIntegerField()
    interested_in     = models.ForeignKey(
        Bike, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exchange_requests'
    )
    showroom          = models.ForeignKey(
        Showroom, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exchange_requests'
    )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.current_bike} exchange'