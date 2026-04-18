from django.db import models


class BikeCategory(models.Model):
    name = models.CharField(max_length=100)          # e.g. Pulsar, Dominar, Chetak
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Bike Categories'

    def __str__(self):
        return self.name


class Bike(models.Model):
    category = models.ForeignKey(BikeCategory, on_delete=models.CASCADE, related_name='bikes')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='bikes/', blank=True, null=True)
    description = models.TextField(blank=True)

    # Specs
    engine_cc = models.CharField(max_length=50, blank=True)
    power = models.CharField(max_length=50, blank=True)        # e.g. 12.4 bhp
    torque = models.CharField(max_length=50, blank=True)       # e.g. 11 Nm
    fuel_type = models.CharField(max_length=50, default='Petrol')
    mileage = models.CharField(max_length=50, blank=True)      # e.g. 60 kmpl

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    def formatted_price(self):
        if self.price:
            return f'₹{self.price:,.0f}'
        return 'On Request'


class Showroom(models.Model):
    name = models.CharField(max_length=200)             # e.g. Global Bajaj Narela
    address = models.TextField()
    phone = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    google_maps_url = models.URLField(blank=True)       # full Google Maps link
    google_maps_embed = models.TextField(blank=True)    # iframe embed code
    working_hours = models.CharField(max_length=100, default='10:00 AM - 6:30 PM')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class Enquiry(models.Model):
    ENQUIRY_TYPE_CHOICES = [
        ('test_ride', 'Book Test Ride'),
        ('purchase', 'Purchase Enquiry'),
        ('general', 'General Enquiry'),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    enquiry_type = models.CharField(max_length=20, choices=ENQUIRY_TYPE_CHOICES, default='test_ride')
    bike = models.ForeignKey(Bike, on_delete=models.SET_NULL, null=True, blank=True)
    showroom = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f'{self.name} - {self.get_enquiry_type_display()} - {self.created_at.strftime("%d %b %Y")}'


class ServiceBooking(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    bike_model = models.CharField(max_length=200)       # free text, not FK (might be old model)
    registration_number = models.CharField(max_length=20, blank=True)
    showroom = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_date = models.DateField()
    issue_description = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.bike_model} - {self.preferred_date}'


class YouTubeVideo(models.Model):
    SECTION_CHOICES = [
        ('home', 'Home Page'),
        ('bikes', 'Bikes Page'),
        ('events', 'Events'),
    ]

    title = models.CharField(max_length=200)
    youtube_id = models.CharField(max_length=20, help_text='Just the video ID from YouTube URL. e.g. dQw4w9WgXcQ')
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, default='home')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def embed_url(self):
        return f'https://www.youtube.com/embed/{self.youtube_id}'

    def thumbnail_url(self):
        return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'


class ExchangeRequest(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    current_bike = models.CharField(max_length=200)
    current_bike_year = models.PositiveIntegerField()
    km_driven = models.PositiveIntegerField()
    interested_in = models.ForeignKey(Bike, on_delete=models.SET_NULL, null=True, blank=True)
    showroom = models.ForeignKey(Showroom, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.current_bike} exchange'
