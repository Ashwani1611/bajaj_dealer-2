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
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import urllib.parse
import json

from .models import (
    Bike, BikeCategory, BikeColor, BikeImage,
    Showroom, ServiceStation, YouTubeVideo,
)
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS

def _send_push_notification(location, title, body, url=''):
    """Send browser push notification to location manager. Silently fails."""
    try:
        from webpush import send_user_notification
        from django.contrib.auth.models import User

        # get manager of this location
        manager = getattr(location, 'manager', None) if location else None

        # fallback to superadmin if no manager
        if not manager:
            manager = User.objects.filter(is_superuser=True).first()

        if not manager:
            return

        payload = {
            'head':  title,
            'body':  body,
            'url':   url,
            'icon':  '/static/images/logo.png',
            'badge': '/static/images/logo.png',
        }
        send_user_notification(user=manager, payload=payload, ttl=1000)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════

# def _color_prefetch(images_qs=None):
#     if images_qs is None:
#         images_qs = BikeImage.objects.filter(
#             media_type__in=['image_upload', 'image_url', 'gif_upload']
#         ).order_by('order')
#     return Prefetch(
#         'colors',
#         queryset=BikeColor.objects.filter(
#             is_available=True
#         ).prefetch_related(
#             Prefetch('images', queryset=images_qs)
#         )
#     )
def _color_prefetch(images_qs=None):
    if images_qs is None:
        # Remove the media_type filter temporarily to see if images exist
        images_qs = BikeImage.objects.all().order_by('order')
    return Prefetch(
        'colors',
        queryset=BikeColor.objects.all().prefetch_related( # Remove is_available=True for now
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


def _base_context():
    return {
        'primary_showroom': Showroom.objects.filter(is_active=True).first(),
    }


def _collect_emails(*locations):
    emails = []
    for loc in locations:
        if not loc:
            continue
        # showroom/station email
        if getattr(loc, 'email', None) and loc.email not in emails:
            emails.append(loc.email)
        # manager personal email
        manager = getattr(loc, 'manager', None)
        if manager and manager.email and manager.email not in emails:
            emails.append(manager.email)
    # always notify master admin
    master = _master_email()
    if master and master not in emails:
        emails.append(master)
    return emails


def _serialize_media(m):
    return {
        'id':         m.pk,
        'media_type': m.media_type,
        'url':        m.get_display_url(),
        'order':      m.order,
        'is_image':   m.is_image(),
        'is_video':   m.is_video(),
        'is_youtube': m.is_youtube(),
    }


def _serialize_color(c):
    images = [_serialize_media(m) for m in c.all_media_items()]
    return {
        'id':          c.pk,
        'name':        c.name,
        'hex':         c.color_hex,
        'order':       c.order,
        'available':   c.is_available,
        'first_image': c.first_image_url(),
        'all_images':  c.all_image_urls(),
        'total_media': len(images),
        'images':      images,
    }


def _serialize_bike_summary(b):
    return {
        'id':            b.pk,
        'name':          b.name,
        'slug':          b.slug,
        'price':         str(b.price) if b.price else None,
        'price_display': b.formatted_price(),
        'category':      {'id': b.category.pk, 'name': b.category.name, 'slug': b.category.slug},
        'engine_cc':     b.engine_cc,
        'power':         b.power,
        'torque':        b.torque,
        'fuel_type':     b.fuel_type,
        'mileage':       b.mileage,
        'is_featured':   b.is_featured,
        'primary_image': b.get_primary_image_url(),
        'colors': [
            {
                'id':     c.pk,
                'name':   c.name,
                'hex':    c.color_hex,
                'images': c.all_image_urls(),
            }
            for c in b.colors.all()
        ],
    }


def _validate_media_fields(media_type, media_link, image_file, video_file):
    errors = {}
    if media_type in ('image_url', 'video_url') and not media_link:
        errors['media_link'] = 'URL is required for this media type.'
    if media_type == 'youtube' and not media_link:
        errors['media_link'] = 'YouTube URL or video ID is required.'
    if media_type in ('image_upload', 'gif_upload') and not image_file:
        errors['image_file'] = 'Image file is required for upload type.'
    if media_type == 'video_upload' and not video_file:
        errors['video_file'] = 'Video file is required for upload type.'
    return errors


def _parse_request_data(request):
    is_multipart = request.content_type and 'multipart' in request.content_type
    if is_multipart:
        return (
            request.POST.dict(),
            request.FILES.get('image_file'),
            request.FILES.get('video_file'),
            True,
        )
    try:
        return json.loads(request.body), None, None, False
    except Exception:
        return {}, None, None, False


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

    featured_bikes = (
        Bike.objects
        .filter(is_featured=True, is_active=True)
        .select_related('category')
        .prefetch_related(
            _color_prefetch(
                images_qs=BikeImage.objects.filter(
                    media_type__in=['image_upload', 'image_url', 'gif_upload']
                ).order_by('order')
            )
        )
    )

    all_bikes = (
        Bike.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related(
            _color_prefetch(
                images_qs=BikeImage.objects.filter(
                    media_type__in=['image_upload', 'image_url', 'gif_upload']
                ).order_by('order')
            )
        )
    )

    all_showrooms = Showroom.objects.filter(is_active=True).order_by('order')

    categories = BikeCategory.objects.all().order_by('order')

    videos = (
        YouTubeVideo.objects
        .filter(is_active=True, section='home')
        .order_by('order')[:6]
    )

    return render(request, 'core/home.html', {
        'featured_bikes': featured_bikes,
        'all_bikes':      all_bikes,
        'all_showrooms':  all_showrooms,
        'showrooms':      all_showrooms,    # showroom badge strip at bottom
        'nav_categories': categories,       # navbar dropdown
        'categories':     categories,       # category strip
        'videos':         videos,
        'offers':         [],               # no Offer model yet — keeps {% if offers %} block hidden
        'enquiry_form':   form,
    })


# ── bike list ─────────────────────────────────────────────────────────────────

def bike_list(request):
    categories        = BikeCategory.objects.prefetch_related('bikes').all()
    selected_category = request.GET.get('category')

    bikes_qs = (
        Bike.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related(
            _color_prefetch(images_qs=BikeImage.objects.order_by('order'))
        )
    )
    if selected_category:
        bikes_qs = bikes_qs.filter(category__slug=selected_category)

    return render(request, 'core/bike_list.html', {
        'bikes':             bikes_qs,
        'categories':        categories,
        'selected_category': selected_category,
    })


# ── bike detail ───────────────────────────────────────────────────────────────

def bike_detail(request, slug):
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

    related_bikes = (
        Bike.objects
        .filter(category=bike.category, is_active=True)
        .exclude(pk=bike.pk)
        .select_related('category')
        .prefetch_related(
            _color_prefetch(images_qs=BikeImage.objects.order_by('order'))
        )[:4]
    )
    showrooms    = Showroom.objects.filter(is_active=True)
    enquiry_form = EnquiryForm(initial={'bike': bike})

    return render(request, 'core/bike_detail.html', {
        'bike':             bike,
        'related_bikes':    related_bikes,
        'enquiry_form':     enquiry_form,
        'showrooms':        showrooms,
        'primary_showroom': showrooms.first(),
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

            wa_number = ''
            if enq.showroom:
                wa_number = enq.showroom.get_whatsapp_number()
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', enq.phone)

            bike_name = enq.bike.name if enq.bike else 'Not specified'
            wa_msg = (
                f"New Bajaj Enquiry!\n"
                f"Name: {enq.name}\n"
                f"Phone: {enq.phone}\n"
                f"Type: {enq.get_enquiry_type_display()}\n"
                f"Bike: {bike_name}\n"
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

    return render(request, 'core/enquiry.html', {'form': form})


def enquiry_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')
    name     = urllib.parse.unquote(request.GET.get('name', ''))
    enq_type = urllib.parse.unquote(request.GET.get('type', ''))
    wa_url   = _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else ''

    return render(request, 'core/success.html', {
        'title':      'Enquiry Submitted!',
        'message':    'Our team will call you within 24 hours.',
        'icon':       'bi-check-circle-fill',
        'icon_color': '#22c55e',
        'wa_url':     wa_url,
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',         'value': name},
            {'label': 'Enquiry Type', 'value': enq_type},
        ],
    })


# ── service booking ───────────────────────────────────────────────────────────

def book_service(request):
    service_stations       = ServiceStation.objects.filter(is_active=True)
    showrooms_with_service = Showroom.objects.filter(has_service_center=True, is_active=True)

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
                location=booking.get_location(),
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

    return render(request, 'core/book_service.html', {
        'form':                   form,
        'service_stations':       service_stations,
        'showrooms_with_service': showrooms_with_service,
    })


def service_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')
    name     = urllib.parse.unquote(request.GET.get('name', ''))
    bike     = urllib.parse.unquote(request.GET.get('bike', ''))
    date     = request.GET.get('date', '')
    wa_url   = _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else ''

    return render(request, 'core/success.html', {
        'title':      'Service Booked!',
        'message':    'We will confirm your appointment within 2 hours.',
        'icon':       'bi-wrench-adjustable-circle-fill',
        'icon_color': '#003087',
        'wa_url':     wa_url,
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',           'value': name},
            {'label': 'Bike',           'value': bike},
            {'label': 'Preferred Date', 'value': date},
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

            wa_number = ''
            if exchange.showroom:
                wa_number = exchange.showroom.get_whatsapp_number()
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', exchange.phone)

            interested = (
                exchange.interested_in.name if exchange.interested_in else 'Not specified'
            )
            wa_msg = (
                f"New Exchange Request!\n"
                f"Name: {exchange.name}\n"
                f"Phone: {exchange.phone}\n"
                f"Current Bike: {exchange.current_bike} ({exchange.current_bike_year})\n"
                f"KM Driven: {exchange.km_driven}\n"
                f"Interested In: {interested}"
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

    return render(request, 'core/exchange.html', {'form': form})


def exchange_success(request):
    wa_msg   = urllib.parse.unquote(request.GET.get('wa', ''))
    wa_phone = request.GET.get('phone', '')
    name     = urllib.parse.unquote(request.GET.get('name', ''))
    bike     = urllib.parse.unquote(request.GET.get('bike', ''))
    wa_url   = _wa_redirect_url(wa_phone, wa_msg) if wa_msg and wa_phone else ''

    return render(request, 'core/success.html', {
        'title':      'Exchange Request Received!',
        'message':    'Our team will evaluate your bike and get back to you.',
        'icon':       'bi-arrow-left-right',
        'icon_color': '#f59e0b',
        'wa_url':     wa_url,
        'wa_msg':     wa_msg,
        'details': [
            {'label': 'Name',         'value': name},
            {'label': 'Current Bike', 'value': bike},
        ],
    })


# ── contact ───────────────────────────────────────────────────────────────────

def contact(request):
    showrooms        = Showroom.objects.filter(is_active=True)
    service_stations = ServiceStation.objects.filter(is_active=True)
    return render(request, 'core/contact.html', {
        'showrooms':        showrooms,
        'service_stations': service_stations,
    })


# ══════════════════════════════════════════════════════════════════════════════
# JSON API VIEWS — GET endpoints
# ══════════════════════════════════════════════════════════════════════════════

@require_GET
def api_categories(request):
    cats = BikeCategory.objects.all()
    return JsonResponse({
        'count':   cats.count(),
        'results': [
            {'id': c.pk, 'name': c.name, 'slug': c.slug, 'order': c.order}
            for c in cats
        ]
    })


@require_GET
def api_bike_list(request):
    category = request.GET.get('category')
    featured = request.GET.get('featured')

    bikes = (
        Bike.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related(_color_prefetch())
    )
    if category:
        bikes = bikes.filter(category__slug=category)
    if featured:
        bikes = bikes.filter(is_featured=True)

    data = [_serialize_bike_summary(b) for b in bikes]
    return JsonResponse({'count': len(data), 'results': data})


@require_GET
def api_bike_detail(request, slug):
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

    colors = []
    for c in bike.colors.all():
        images = [_serialize_media(m) for m in c.all_media_items()]
        colors.append({
            'id':          c.pk,
            'name':        c.name,
            'hex':         c.color_hex,
            'order':       c.order,
            'available':   c.is_available,
            'first_image': c.first_image_url(),
            'images':      images,
        })

    general_media = [
        _serialize_media(m) for m in getattr(bike, 'general_media', [])
    ]

    return JsonResponse({
        'id':            bike.pk,
        'name':          bike.name,
        'slug':          bike.slug,
        'price':         str(bike.price) if bike.price else None,
        'price_display': bike.formatted_price(),
        'category':      {'id': bike.category.pk, 'name': bike.category.name, 'slug': bike.category.slug},
        'description':   bike.description,
        'engine_cc':     bike.engine_cc,
        'power':         bike.power,
        'torque':        bike.torque,
        'fuel_type':     bike.fuel_type,
        'mileage':       bike.mileage,
        'is_featured':   bike.is_featured,
        'primary_image': bike.get_primary_image_url(),
        'colors':        colors,
        'general_media': general_media,
    })


@require_GET
def api_bike_colors(request, slug):
    bike   = get_object_or_404(Bike, slug=slug, is_active=True)
    colors = BikeColor.objects.filter(bike=bike).prefetch_related(
        Prefetch('images', queryset=BikeImage.objects.all().order_by('order'))
    )
    return JsonResponse({
        'bike_id':      bike.pk,
        'bike_name':    bike.name,
        'bike_slug':    bike.slug,
        'total_colors': colors.count(),
        'colors':       [_serialize_color(c) for c in colors],
    })


@require_GET
def api_bike_images(request, slug):
    bike = get_object_or_404(Bike, slug=slug, is_active=True)

    color_id    = request.GET.get('color')
    media_type  = request.GET.get('type')
    only_images = request.GET.get('images_only')
    only_videos = request.GET.get('videos_only')

    qs = BikeImage.objects.filter(bike=bike).select_related('color').order_by('color', 'order')

    if color_id:
        qs = qs.filter(color__pk=color_id)
    if media_type:
        qs = qs.filter(media_type=media_type)
    if only_images:
        qs = qs.filter(media_type__in=['image_upload', 'image_url', 'gif_upload'])
    if only_videos:
        qs = qs.filter(media_type__in=['video_upload', 'video_url', 'youtube'])

    data = []
    for m in qs:
        row = _serialize_media(m)
        row['color'] = {
            'id':   m.color.pk,
            'name': m.color.name,
            'hex':  m.color.color_hex,
        } if m.color else None
        data.append(row)

    return JsonResponse({
        'bike_id':   bike.pk,
        'bike_name': bike.name,
        'bike_slug': bike.slug,
        'total':     len(data),
        'results':   data,
    })


@require_GET
def api_showrooms(request):
    showrooms = Showroom.objects.filter(is_active=True)
    return JsonResponse({
        'count':   showrooms.count(),
        'results': [
            {
                'id':                 s.pk,
                'name':               s.name,
                'address':            s.address,
                'phone':              s.phone,
                'phone2':             s.phone2,
                'whatsapp':           s.get_whatsapp_number(),
                'email':              s.email,
                'working_hours':      s.working_hours,
                'has_service_center': s.has_service_center,
                'google_maps_url':    s.google_maps_url,
            }
            for s in showrooms
        ]
    })


@require_GET
def api_service_stations(request):
    stations = ServiceStation.objects.filter(is_active=True)
    return JsonResponse({
        'count':   stations.count(),
        'results': [
            {
                'id':            s.pk,
                'name':          s.name,
                'address':       s.address,
                'phone':         s.phone,
                'phone2':        s.phone2,
                'whatsapp':      s.get_whatsapp_number(),
                'email':         s.email,
                'working_hours': s.working_hours,
            }
            for s in stations
        ]
    })


# ══════════════════════════════════════════════════════════════════════════════
# JSON API VIEWS — POST endpoints
# ══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def api_enquiry(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    form = EnquiryForm(data)
    if form.is_valid():
        enq = form.save()
        _send_html_email(
            subject=f"New Enquiry: {enq.get_enquiry_type_display()} — {enq.name}",
            template_name='emails/enquiry_notification.html',
            context={'enquiry': enq, 'settings': settings},
            to_emails=_collect_emails(enq.showroom),
        )
        return JsonResponse({
            'success':      True,
            'id':           enq.pk,
            'message':      'Enquiry submitted successfully.',
            'name':         enq.name,
            'phone':        enq.phone,
            'enquiry_type': enq.get_enquiry_type_display(),
            'bike':         enq.bike.name if enq.bike else None,
            'showroom':     enq.showroom.name if enq.showroom else None,
        }, status=201)

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@csrf_exempt
@require_POST
def api_service_booking(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    form = ServiceBookingForm(data)
    if form.is_valid():
        booking  = form.save()
        location = booking.get_location()
        _send_html_email(
            subject=f"Service Booking: {booking.name} — {booking.bike_model}",
            template_name='emails/service_notification.html',
            context={'booking': booking, 'settings': settings},
            to_emails=_collect_emails(location),
        )
        return JsonResponse({
            'success':        True,
            'id':             booking.pk,
            'message':        'Service booked successfully.',
            'name':           booking.name,
            'phone':          booking.phone,
            'bike_model':     booking.bike_model,
            'preferred_date': str(booking.preferred_date),
            'location':       booking.get_location_name(),
            'status':         booking.status,
        }, status=201)

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@csrf_exempt
@require_POST
def api_exchange(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    form = ExchangeForm(data)
    if form.is_valid():
        exchange = form.save()
        _send_html_email(
            subject=f"Exchange Request: {exchange.name} — {exchange.current_bike}",
            template_name='emails/exchange_notification.html',
            context={'exchange': exchange, 'settings': settings},
            to_emails=_collect_emails(exchange.showroom),
        )
        return JsonResponse({
            'success':           True,
            'id':                exchange.pk,
            'message':           'Exchange request submitted.',
            'name':              exchange.name,
            'phone':             exchange.phone,
            'current_bike':      exchange.current_bike,
            'current_bike_year': exchange.current_bike_year,
            'km_driven':         exchange.km_driven,
            'interested_in':     exchange.interested_in.name if exchange.interested_in else None,
            'showroom':          exchange.showroom.name if exchange.showroom else None,
        }, status=201)

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


# ══════════════════════════════════════════════════════════════════════════════
# JSON API VIEWS — Bike image & color endpoints
# ══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def api_add_color(request, slug):
    bike = get_object_or_404(Bike, slug=slug, is_active=True)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    name      = data.get('name', '').strip()
    hex_code  = data.get('color_hex', '#cccccc').strip()
    order     = data.get('order', 0)
    available = data.get('is_available', True)

    errors = {}
    if not name:
        errors['name'] = 'Color name is required.'
    if not hex_code.startswith('#') or len(hex_code) not in [4, 7]:
        errors['color_hex'] = 'Enter a valid hex color e.g. #FF0000'
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    color = BikeColor.objects.create(
        bike=bike, name=name, color_hex=hex_code,
        order=order, is_available=available,
    )
    return JsonResponse({
        'success': True,
        'message': f'Color "{name}" added to {bike.name}.',
        'color': {
            'id': color.pk, 'name': color.name, 'hex': color.color_hex,
            'order': color.order, 'available': color.is_available,
            'bike': {'id': bike.pk, 'name': bike.name, 'slug': bike.slug},
        }
    }, status=201)


@csrf_exempt
@require_POST
def api_add_color_image(request, color_id):
    color = get_object_or_404(BikeColor, pk=color_id)
    data, image_file, video_file, is_multipart = _parse_request_data(request)

    media_type = data.get('media_type', 'image_upload' if is_multipart else 'image_url')
    media_link = data.get('media_link', '')
    order      = int(data.get('order', 0))

    errors = _validate_media_fields(media_type, media_link, image_file, video_file)
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    img = BikeImage(
        color=color, media_type=media_type,
        media_link=media_link or None, order=order,
    )
    if image_file:
        img.image_file = image_file
    if video_file:
        img.video_file = video_file
    img.save()

    result = _serialize_media(img)
    result['color'] = {'id': color.pk, 'name': color.name, 'hex': color.color_hex}
    result['bike']  = {'id': img.bike.pk, 'name': img.bike.name, 'slug': img.bike.slug}

    return JsonResponse({
        'success': True,
        'message': f'Media added to color "{color.name}".',
        'image':   result,
    }, status=201)


@csrf_exempt
@require_POST
def api_add_color_images_bulk(request, color_id):
    color = get_object_or_404(BikeColor, pk=color_id)

    if not (request.content_type and 'multipart' in request.content_type):
        return JsonResponse(
            {'success': False, 'errors': {'content_type': 'multipart/form-data required.'}},
            status=400
        )

    files       = request.FILES.getlist('image_file')
    start_order = int(request.POST.get('start_order', 0))

    if not files:
        return JsonResponse(
            {'success': False, 'errors': {'image_file': 'At least one image file is required.'}},
            status=400
        )

    created = []
    errors  = []

    for i, f in enumerate(files):
        import os
        ext     = os.path.splitext(f.name)[1].lower()
        allowed = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.heic']
        if ext not in allowed:
            errors.append(f'"{f.name}" skipped — unsupported format {ext}')
            continue

        media_type = 'gif_upload' if ext == '.gif' else 'image_upload'
        img = BikeImage(color=color, media_type=media_type, order=start_order + i)
        img.image_file = f
        img.save()

        result = _serialize_media(img)
        result['filename'] = f.name
        created.append(result)

    return JsonResponse({
        'success':       True,
        'message':       f'{len(created)} image(s) added to color "{color.name}".',
        'total_created': len(created),
        'skipped':       errors,
        'color': {
            'id': color.pk, 'name': color.name, 'hex': color.color_hex,
            'bike': {'id': color.bike.pk, 'name': color.bike.name, 'slug': color.bike.slug},
        },
        'images': created,
    }, status=201)


@csrf_exempt
@require_POST
def api_add_bike_image(request, slug):
    bike = get_object_or_404(Bike, slug=slug, is_active=True)
    data, image_file, video_file, is_multipart = _parse_request_data(request)

    media_type = data.get('media_type', 'image_upload' if is_multipart else 'image_url')
    media_link = data.get('media_link', '')
    order      = int(data.get('order', 0))

    errors = _validate_media_fields(media_type, media_link, image_file, video_file)
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    img = BikeImage(
        bike=bike, color=None, media_type=media_type,
        media_link=media_link or None, order=order,
    )
    if image_file:
        img.image_file = image_file
    if video_file:
        img.video_file = video_file
    img.save()

    result = _serialize_media(img)
    result['color'] = None
    result['bike']  = {'id': bike.pk, 'name': bike.name, 'slug': bike.slug}

    return JsonResponse({
        'success': True,
        'message': f'Media added to bike "{bike.name}" (no color).',
        'image':   result,
    }, status=201)


@csrf_exempt
@require_POST
def api_add_bike_images_bulk(request, slug):
    bike = get_object_or_404(Bike, slug=slug, is_active=True)

    if not (request.content_type and 'multipart' in request.content_type):
        return JsonResponse(
            {'success': False, 'errors': {'content_type': 'multipart/form-data required.'}},
            status=400
        )

    files       = request.FILES.getlist('image_file')
    start_order = int(request.POST.get('start_order', 0))

    if not files:
        return JsonResponse(
            {'success': False, 'errors': {'image_file': 'At least one image file is required.'}},
            status=400
        )

    created = []
    errors  = []

    for i, f in enumerate(files):
        import os
        ext     = os.path.splitext(f.name)[1].lower()
        allowed = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.heic']
        if ext not in allowed:
            errors.append(f'"{f.name}" skipped — unsupported format {ext}')
            continue

        media_type = 'gif_upload' if ext == '.gif' else 'image_upload'
        img = BikeImage(bike=bike, color=None, media_type=media_type, order=start_order + i)
        img.image_file = f
        img.save()

        result = _serialize_media(img)
        result['filename'] = f.name
        created.append(result)

    return JsonResponse({
        'success':       True,
        'message':       f'{len(created)} image(s) added to bike "{bike.name}".',
        'total_created': len(created),
        'skipped':       errors,
        'bike':          {'id': bike.pk, 'name': bike.name, 'slug': bike.slug},
        'images':        created,
    }, status=201)


@csrf_exempt
def api_delete_image(request, pk):
    if request.method not in ('DELETE', 'POST'):
        return JsonResponse({'error': 'DELETE or POST required'}, status=405)

    img        = get_object_or_404(BikeImage, pk=pk)
    color_info = {'id': img.color.pk, 'name': img.color.name} if img.color else None
    bike_info  = {'id': img.bike.pk,  'name': img.bike.name}  if img.bike  else None

    if img.image_file:
        img.image_file.delete(save=False)
    if img.video_file:
        img.video_file.delete(save=False)
    img.delete()

    return JsonResponse({
        'success':   True,
        'message':   f'Image pk={pk} deleted successfully.',
        'was_color': color_info,
        'was_bike':  bike_info,
    })