import os
import urllib.parse

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Prefetch
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from django.core.cache import cache
from .models import Bike, BikeCategory, BikeColor, BikeImage, Showroom, ServiceStation, YouTubeVideo, Offer

from .models import (
    Bike, BikeCategory, BikeColor, BikeImage,
    Showroom, ServiceStation, YouTubeVideo,
)
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


# ══════════════════════════════════════════════════════════════════════════════
# SITE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

SITE_URL = 'https://skylinewheels.in'


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _send_push_notification(location, title, body, url=''):
    """Send browser push notification to location manager. Silently fails."""
    try:
        from webpush import send_user_notification
        from django.contrib.auth.models import User

        manager = getattr(location, 'manager', None) if location else None
        if not manager:
            manager = User.objects.filter(is_superuser=True).first()
        if not manager:
            return

        send_user_notification(
            user=manager,
            payload={
                'head':  title,
                'body':  body,
                'url':   url,
                'icon':  '/static/images/logo.png',
                'badge': '/static/images/logo.png',
            },
            ttl=1000,
        )
    except Exception:
        pass


def _color_prefetch(images_qs=None):
    if images_qs is None:
        images_qs = BikeImage.objects.filter(
            media_type__in=['image_upload', 'image_url', 'gif_upload']
        ).order_by('order')
    return Prefetch(
        'colors',
        queryset=BikeColor.objects.filter(
            is_available=True
        ).prefetch_related(
            Prefetch('images', queryset=images_qs)
        )
    )


def _send_html_email(subject, template_name, context, to_emails):
    if not to_emails:
        return
    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[e for e in to_emails if e],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass


def _wa_redirect_url(number, message):
    clean = ''.join(filter(str.isdigit, number or ''))
    if clean and not clean.startswith('91'):
        clean = '91' + clean
    return f"https://wa.me/{clean}?text={urllib.parse.quote(message)}"


def _master_email():
    return (
        getattr(settings, 'DEALER_MASTER_EMAIL', None)
        or getattr(settings, 'DEALER_EMAIL', None)
    )


def _collect_emails(*locations):
    emails = []
    for loc in locations:
        if not loc:
            continue
        if getattr(loc, 'email', None) and loc.email not in emails:
            emails.append(loc.email)
        manager = getattr(loc, 'manager', None)
        if manager and manager.email and manager.email not in emails:
            emails.append(manager.email)
    master = _master_email()
    if master and master not in emails:
        emails.append(master)
    return emails


# ══════════════════════════════════════════════════════════════════════════════
# CACHE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_all_showrooms():
    showrooms = cache.get('all_showrooms')
    if not showrooms:
        showrooms = list(Showroom.objects.filter(is_active=True).order_by('order'))
        cache.set('all_showrooms', showrooms, timeout=60 * 30)
    return showrooms


def _get_all_categories():
    categories = cache.get('all_categories')
    if not categories:
        categories = list(BikeCategory.objects.all().order_by('order'))
        cache.set('all_categories', categories, timeout=60 * 30)
    return categories


def _media_images_qs():
    return BikeImage.objects.filter(
        media_type__in=['image_upload', 'image_url', 'gif_upload']
    ).order_by('order')


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE VIEWS
# ══════════════════════════════════════════════════════════════════════════════

# ── home ──────────────────────────────────────────────────────────────────────

def home(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We will contact you soon.')
            return redirect('home')
    else:
        form = EnquiryForm()

    featured_bikes = cache.get('featured_bikes')
    if not featured_bikes:
        featured_bikes = list(
            Bike.objects
            .filter(is_featured=True, is_active=True)
            .select_related('category')
            .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
            .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
        )
        cache.set('featured_bikes', featured_bikes, timeout=60 * 15)

    home_bikes = cache.get('home_all_bikes')
    if not home_bikes:
        home_bikes = list(
            Bike.objects
            .filter(is_active=True)
            .select_related('category')
            .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
            .only('id', 'name', 'slug', 'price', 'category')
            [:24]
        )
        cache.set('home_all_bikes', home_bikes, timeout=60 * 15)

    videos = cache.get('home_videos')
    if not videos:
        videos = list(
            YouTubeVideo.objects
            .filter(is_active=True, section='home')
            .order_by('order')[:6]
        )
        cache.set('home_videos', videos, timeout=60 * 30)

    all_showrooms = _get_all_showrooms()
    categories    = _get_all_categories()

    offers = cache.get('home_offers')
    if not offers:
        offers = list(Offer.objects.filter(is_active=True).order_by('order'))
        cache.set('home_offers', offers, timeout=60 * 30)

    return render(request, 'core/home.html', {
        'featured_bikes': featured_bikes,
        'all_bikes':      home_bikes,
        'all_showrooms':  all_showrooms,
        'showrooms':      all_showrooms,
        'footer_showrooms': all_showrooms,
        'nav_categories': categories,
        'categories':     categories,
        'videos':         videos,
        'offers':         offers,
        'enquiry_form':   form,
        'showroom_count': len(all_showrooms),
        # ── SEO ──
        'canonical_url':  SITE_URL + '/',
        'seo_title':      'Bajaj Showroom in Noida | Bhangel | Greater Noida | Skyline Bajaj',
        'seo_description': (
            'Skyline Bajaj – Authorized Bajaj & Chetak dealer in Noida, Bhangel, '
            'Greater Noida and Sector 10. New bikes, test rides, EMI, exchange and service.'
        ),
    })


# ── bike list ─────────────────────────────────────────────────────────────────

def bike_list(request):
    selected_category = request.GET.get('category', '')
    categories = _get_all_categories()

    cache_key = f'bike_list_{selected_category or "all"}'
    bikes = cache.get(cache_key)
    if not bikes:
        bikes_qs = (
            Bike.objects
            .filter(is_active=True, is_chetak=False)
            .select_related('category')
            .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
            .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
        )
        if selected_category:
            bikes_qs = bikes_qs.filter(category__slug=selected_category)
        bikes = list(bikes_qs)
        cache.set(cache_key, bikes, timeout=60 * 15)

    active_cat = next((c for c in categories if c.slug == selected_category), None)
    if active_cat:
        seo_title       = f'Bajaj {active_cat.name} Bikes in Noida | Skyline Bajaj Dealer'
        seo_description = (
            f'Buy Bajaj {active_cat.name} bikes in Noida at Skyline Bajaj. '
            f'Best price, EMI options, test ride at our Noida showrooms.'
        )
        canonical_url   = f'{SITE_URL}/bikes/?category={selected_category}'
    else:
        seo_title       = 'All Bajaj Bikes in Noida | Pulsar, Platina, CT, Dominar | Skyline Bajaj'
        seo_description = (
            'Explore all Bajaj bikes available at Skyline Bajaj showrooms in Noida, '
            'Bhangel and Greater Noida. Best price, EMI, exchange and test ride.'
        )
        canonical_url   = f'{SITE_URL}/bikes/'

    return render(request, 'core/bike_list.html', {
        'bikes':             bikes,
        'categories':        categories,
        'selected_category': selected_category,
        # ── SEO ──
        'canonical_url':     canonical_url,
        'seo_title':         seo_title,
        'seo_description':   seo_description,
    })


# ── bike detail ───────────────────────────────────────────────────────────────

def bike_detail(request, slug):
    bike = cache.get(f'bike_{slug}')
    if not bike:
        bike = get_object_or_404(
            Bike.objects
            .select_related('category')
            .prefetch_related(
                _color_prefetch(),
                Prefetch(
                    'all_media',
                    queryset=BikeImage.objects.filter(
                        color__isnull=True
                    ).order_by('order'),
                    to_attr='general_media',
                ),
            ),
            slug=slug,
            is_active=True,
        )
        cache.set(f'bike_{slug}', bike, timeout=60 * 15)

    related_bikes = cache.get(f'related_bikes_{slug}')
    if not related_bikes:
        related_bikes = list(
            Bike.objects
            .filter(category=bike.category, is_active=True, is_chetak=False)
            .exclude(pk=bike.pk)
            .select_related('category')
            .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
            .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
            [:4]
        )
        cache.set(f'related_bikes_{slug}', related_bikes, timeout=60 * 15)

    showrooms = _get_all_showrooms()

    # ── SEO — use custom meta fields if set, else auto-generate ───
    price_str = f'₹{bike.price:,.0f}' if bike.price else 'On Request'

    seo_title = bike.meta_title if bike.meta_title else (
        f'{bike.name} Price in Noida – {price_str} | Skyline Bajaj Dealer'
    )
    seo_desc = bike.meta_description if bike.meta_description else (
        f'Buy {bike.name} in Noida at Skyline Bajaj. '
        f'Price {price_str}. '
        + (f'Engine {bike.engine_cc}, mileage {bike.mileage}. ' if bike.engine_cc else '')
        + 'Book test ride at Bhangel, Sector 10, Sector 58 or Greater Noida showroom.'
    )
    canonical_url = f'{SITE_URL}/bikes/{bike.slug}/'
    og_image = bike.get_primary_image_url() if callable(bike.get_primary_image_url) else bike.get_primary_image_url

    return render(request, 'core/bike_detail.html', {
        'bike':             bike,
        'related_bikes':    related_bikes,
        'enquiry_form':     EnquiryForm(initial={'bike': bike}),
        'showrooms':        showrooms,
        'primary_showroom': showrooms[0] if showrooms else None,
        # ── SEO ──
        'canonical_url':    canonical_url,
        'seo_title':        seo_title,
        'seo_description':  seo_desc,
        'og_image_url':     og_image,
    })


# ── delete bike image (staff only) ────────────────────────────────────────────

@staff_member_required
def delete_bike_image(request, pk):
    img       = get_object_or_404(BikeImage, pk=pk)
    bike_slug = (img.color.bike if img.color else img.bike).slug

    if request.method == 'POST':
        if img.image_file:
            img.image_file.delete(save=False)
        if img.video_file:
            img.video_file.delete(save=False)
        img.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'deleted'})
        return redirect('bike_detail', slug=bike_slug)

    return JsonResponse({'error': 'POST required'}, status=405)


# ── enquiry ───────────────────────────────────────────────────────────────────

def enquiry(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            enq = form.save()

            _send_html_email(
                subject=f"New Enquiry: {enq.get_enquiry_type_display()} — {enq.name}",
                template_name='emails/enquiry_notification.html',
                context={'enquiry': enq, 'settings': settings},
                to_emails=_collect_emails(enq.showroom),
            )
            _send_push_notification(
                location=enq.showroom,
                title=f'New Enquiry — {enq.get_enquiry_type_display()}',
                body=f'{enq.name} | {enq.phone} | Bike: {enq.bike.name if enq.bike else "Not specified"}',
                url=f'/admin/core/enquiry/{enq.pk}/change/',
            )

            wa_number = enq.showroom.get_whatsapp_number() if enq.showroom else ''
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', enq.phone)

            wa_msg = (
                f"New Bajaj Enquiry!\n"
                f"Name: {enq.name}\n"
                f"Phone: {enq.phone}\n"
                f"Type: {enq.get_enquiry_type_display()}\n"
                f"Bike: {enq.bike.name if enq.bike else 'Not specified'}\n"
                f"Message: {enq.message or 'None'}"
            )

            messages.success(request, 'Thank you! We will contact you shortly.')
            params = urllib.parse.urlencode({
                'wa':    wa_msg,
                'phone': wa_number,
                'name':  enq.name,
                'type':  enq.get_enquiry_type_display(),
            })
            return redirect(f"{reverse('enquiry_success')}?{params}")

        messages.error(request, 'Please fix the errors below.')
    else:
        bike_pk = request.GET.get('bike')
        form    = EnquiryForm(initial={'bike': bike_pk} if bike_pk else {})

    return render(request, 'core/enquiry.html', {
        'form': form,
        # ── SEO ──
        'canonical_url':  f'{SITE_URL}/enquiry/',
        'seo_title':      'Book Test Ride | Bajaj Bike Enquiry Noida | Skyline Bajaj',
        'seo_description': (
            'Book a Bajaj bike test ride or send an enquiry at Skyline Bajaj Noida. '
            'Available at Bhangel, Sector 58, Sector 10 and Greater Noida showrooms.'
        ),
    })


def enquiry_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')
    name     = urllib.parse.unquote(request.GET.get('name', ''))
    enq_type = urllib.parse.unquote(request.GET.get('type', ''))

    return render(request, 'core/success.html', {
        'title':      'Enquiry Submitted!',
        'message':    'Our team will call you within 24 hours.',
        'icon':       'bi-check-circle-fill',
        'icon_color': '#22c55e',
        'wa_url':     _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else '',
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',         'value': name},
            {'label': 'Enquiry Type', 'value': enq_type},
        ],
    })


# ── service booking ───────────────────────────────────────────────────────────

def book_service(request):
    if request.method == 'POST':
        form = ServiceBookingForm(request.POST)
        if form.is_valid():
            booking  = form.save()
            location = booking.get_location()

            _send_html_email(
                subject=f"Service Booking: {booking.name} — {booking.bike_model}",
                template_name='emails/service_notification.html',
                context={'booking': booking, 'settings': settings},
                to_emails=_collect_emails(location),
            )
            _send_push_notification(
                location=location,
                title=f'New Service Booking — {booking.bike_model}',
                body=f'{booking.name} | {booking.phone} | Date: {booking.preferred_date}',
                url=f'/admin/core/servicebooking/{booking.pk}/change/',
            )

            wa_number = location.get_whatsapp_number() if location else ''
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', booking.phone)

            wa_msg = (
                f"New Service Booking!\n"
                f"Name: {booking.name}\n"
                f"Phone: {booking.phone}\n"
                f"Bike: {booking.bike_model}\n"
                f"Date: {booking.preferred_date}\n"
                f"Location: {booking.get_location_name()}\n"
                f"Issue: {booking.issue_description or 'None'}"
            )

            messages.success(request, 'Service booked successfully!')
            params = urllib.parse.urlencode({
                'wa':    wa_msg,
                'phone': wa_number,
                'name':  booking.name,
                'bike':  booking.bike_model,
                'date':  booking.preferred_date,
            })
            return redirect(f"{reverse('service_success')}?{params}")

        messages.error(request, 'Please fix the errors below.')
    else:
        form = ServiceBookingForm()

    service_stations = cache.get('service_stations')
    if not service_stations:
        service_stations = list(ServiceStation.objects.filter(is_active=True))
        cache.set('service_stations', service_stations, timeout=60 * 30)

    showrooms_with_service = cache.get('showrooms_with_service')
    if not showrooms_with_service:
        showrooms_with_service = list(
            Showroom.objects.filter(has_service_center=True, is_active=True)
        )
        cache.set('showrooms_with_service', showrooms_with_service, timeout=60 * 30)

    return render(request, 'core/book_service.html', {
        'form':                   form,
        'service_stations':       service_stations,
        'showrooms_with_service': showrooms_with_service,
        # ── SEO ──
        'canonical_url':  f'{SITE_URL}/service/',
        'seo_title':      'Bajaj Bike Service Booking Noida | Skyline Bajaj Service Centre',
        'seo_description': (
            'Book Bajaj bike service at Skyline Bajaj service centres in Noida, Bhangel '
            'and Greater Noida. Expert mechanics, genuine spare parts, free pickup.'
        ),
    })


def service_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')

    return render(request, 'core/success.html', {
        'title':      'Service Booked!',
        'message':    'We will confirm your appointment within 2 hours.',
        'icon':       'bi-wrench-adjustable-circle-fill',
        'icon_color': '#003087',
        'wa_url':     _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else '',
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',           'value': urllib.parse.unquote(request.GET.get('name', ''))},
            {'label': 'Bike',           'value': urllib.parse.unquote(request.GET.get('bike', ''))},
            {'label': 'Preferred Date', 'value': request.GET.get('date', '')},
        ],
    })


# ── exchange ──────────────────────────────────────────────────────────────────

def exchange_bike(request):
    if request.method == 'POST':
        form = ExchangeForm(request.POST)
        if form.is_valid():
            exchange = form.save()

            _send_html_email(
                subject=f"Exchange Request: {exchange.name} — {exchange.current_bike}",
                template_name='emails/exchange_notification.html',
                context={'exchange': exchange, 'settings': settings},
                to_emails=_collect_emails(exchange.showroom),
            )
            _send_push_notification(
                location=exchange.showroom,
                title=f'New Exchange Request — {exchange.current_bike}',
                body=f'{exchange.name} | {exchange.phone} | KM: {exchange.km_driven}',
                url=f'/admin/core/exchangerequest/{exchange.pk}/change/',
            )

            wa_number = exchange.showroom.get_whatsapp_number() if exchange.showroom else ''
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', exchange.phone)

            wa_msg = (
                f"New Exchange Request!\n"
                f"Name: {exchange.name}\n"
                f"Phone: {exchange.phone}\n"
                f"Current Bike: {exchange.current_bike} ({exchange.current_bike_year})\n"
                f"KM Driven: {exchange.km_driven}\n"
                f"Interested In: {exchange.interested_in.name if exchange.interested_in else 'Not specified'}"
            )

            messages.success(request, 'Exchange request submitted!')
            params = urllib.parse.urlencode({
                'wa':    wa_msg,
                'phone': wa_number,
                'name':  exchange.name,
                'bike':  exchange.current_bike,
            })
            return redirect(f"{reverse('exchange_success')}?{params}")

        messages.error(request, 'Please fix the errors below.')
    else:
        form = ExchangeForm()

    return render(request, 'core/exchange.html', {
        'form': form,
        # ── SEO ──
        'canonical_url':  f'{SITE_URL}/exchange/',
        'seo_title':      'Exchange Old Bike for New Bajaj | Best Exchange Value | Skyline Bajaj Noida',
        'seo_description': (
            'Exchange your old bike for a new Bajaj at Skyline Bajaj Noida. '
            'Best exchange value, instant evaluation, easy EMI on new bike.'
        ),
    })


def exchange_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')

    return render(request, 'core/success.html', {
        'title':      'Exchange Request Received!',
        'message':    'Our team will evaluate your bike and get back to you.',
        'icon':       'bi-arrow-left-right',
        'icon_color': '#f59e0b',
        'wa_url':     _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else '',
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',         'value': urllib.parse.unquote(request.GET.get('name', ''))},
            {'label': 'Current Bike', 'value': urllib.parse.unquote(request.GET.get('bike', ''))},
        ],
    })


# ── contact ───────────────────────────────────────────────────────────────────

def contact(request):
    showrooms = _get_all_showrooms()

    service_stations = cache.get('service_stations')
    if not service_stations:
        service_stations = list(ServiceStation.objects.filter(is_active=True))
        cache.set('service_stations', service_stations, timeout=60 * 30)

    return render(request, 'core/contact.html', {
        'showrooms':        showrooms,
        'service_stations': service_stations,
        # ── SEO ──
        'canonical_url':  f'{SITE_URL}/contact/',
        'seo_title':      'Bajaj Showroom Locations Noida | Skyline Bajaj Dealer Address',
        'seo_description': (
            'Find all Skyline Bajaj showroom addresses in Noida, Bhangel, Sector 10, '
            'Sector 58 and Greater Noida. Contact numbers, directions and working hours.'
        ),
    })


# ── chetak ────────────────────────────────────────────────────────────────────

def chetak(request):
    cache_key = 'chetak_bikes'
    bikes = cache.get(cache_key)
    if not bikes:
        bikes = list(
            Bike.objects
            .filter(is_active=True, is_chetak=True)
            .select_related('category')
            .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
            .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage',
                  'power', 'torque', 'fuel_type', 'description', 'category')
        )
        cache.set(cache_key, bikes, timeout=60 * 15)

    showrooms = _get_all_showrooms()

    return render(request, 'core/chetak.html', {
        'bikes':        bikes,
        'showrooms':    showrooms,
        'enquiry_form': EnquiryForm(),
        # ── SEO ──
        'canonical_url':  f'{SITE_URL}/chetak/',
        'seo_title':      'Bajaj Chetak Electric Scooter Dealer Noida | Skyline Chetak Greater Noida',
        'seo_description': (
            'Buy Bajaj Chetak electric scooter in Greater Noida at Skyline Bajaj. '
            'Authorized Chetak EV dealer at Site 4, Greater Noida. Test ride available, EMI options.'
        ),
    })


# ── showroom detail ───────────────────────────────────────────────────────────

def showroom_detail(request, slug):
    showroom = get_object_or_404(Showroom, slug=slug, is_active=True)

    bikes = list(
        Bike.objects
        .filter(is_active=True, is_chetak=False)
        .select_related('category')
        .prefetch_related(_color_prefetch(images_qs=_media_images_qs()))
        .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
    )

    other_showrooms = Showroom.objects.filter(
        is_active=True
    ).exclude(slug=slug).order_by('order')

    # ── Areas served per showroom ─────────────────────────────────
    # Keys must match your actual showroom slugs.
    # Run: python manage.py shell -c "from core.models import Showroom; [print(s.slug) for s in Showroom.objects.all()]"
    # to confirm your slugs, then update the keys below.
    areas_map = {
        'skyline-bajaj-sector-58': [
            'Sector 58 Noida', 'Bishanpura', 'Sector 57 Noida',
            'Sector 59 Noida', 'Sector 62 Noida', 'Sector 63 Noida',
        ],
        'skyline-bajaj-bhangel': [
            'Bhangel', 'Noida Extension', 'Greater Noida West',
            'Sector 93 Noida', 'Sector 121 Noida', 'Gaur City',
        ],
        'skyline-bajaj-greater-noida': [
            'Greater Noida', 'Site 4', 'Gamma 1', 'Gamma 2',
            'Alpha 1', 'Alpha 2', 'Beta 1', 'Beta 2',
        ],
        'skyline-bajaj-sector-10': [
            'Sector 10 Noida', 'Sector 12 Noida', 'Sector 15 Noida',
            'Sector 18 Noida', 'Sector 16 Noida', 'Sector 20 Noida',
        ],
    }
    areas_served = areas_map.get(showroom.slug, [showroom.city or showroom.name])

    city = showroom.city or showroom.name

    return render(request, 'core/showroom_detail.html', {
        'showroom':        showroom,
        'bikes':           bikes,
        'other_showrooms': other_showrooms,
        'areas_served':    areas_served,
        'enquiry_form':    EnquiryForm(initial={'showroom': showroom}),
        # ── SEO ──
        'canonical_url':   f'https://www.skylinewheels.in/showroom/{showroom.slug}/',
        'seo_title':       f'Bajaj Bikes in {city} | {showroom.name} | Skyline Bajaj',
        'seo_description': (
            f'Buy Bajaj bikes at {showroom.name} – authorized Bajaj dealer in {city}. '
            f'Pulsar, Dominar, Platina, CT100 and more. '
            f'EMI, exchange, test ride available. Call {showroom.phone}.'
        ),
    })