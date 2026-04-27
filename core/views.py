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
from django.views.decorators.cache import cache_page

from .models import (
    Bike, BikeCategory, BikeColor, BikeImage,
    Showroom, ServiceStation, YouTubeVideo,
)
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


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
# TEMPLATE VIEWS
# ══════════════════════════════════════════════════════════════════════════════

# ── home ──────────────────────────────────────────────────────────────────────

def home(request):
    # Handle POST before cache — cache_page never caches POST requests
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We will contact you soon.')
            return redirect('home')
    else:
        form = EnquiryForm()

    # Define images_qs once — reused in both querysets
    images_qs = BikeImage.objects.filter(
        media_type__in=['image_upload', 'image_url', 'gif_upload']
    ).order_by('order')

    color_pf = _color_prefetch(images_qs=images_qs)

    featured_bikes = list(
        Bike.objects
        .filter(is_featured=True, is_active=True)
        .select_related('category')
        .prefetch_related(color_pf)
        .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
    )

    all_bikes = list(
        Bike.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related(color_pf)
        .only('id', 'name', 'slug', 'price', 'category')
        [:24]  # cap — no need to load every bike on the home page
    )

    # Evaluated once as a list — reused for both `all_showrooms` and `showrooms`
    all_showrooms = list(
        Showroom.objects.filter(is_active=True).order_by('order')
    )

    # Evaluated once — reused for both `nav_categories` and `categories`
    categories = list(
        BikeCategory.objects.all().order_by('order')
    )

    videos = list(
        YouTubeVideo.objects
        .filter(is_active=True, section='home')
        .order_by('order')[:6]
    )

    return render(request, 'core/home.html', {
        'featured_bikes': featured_bikes,
        'all_bikes':      all_bikes,
        'all_showrooms':  all_showrooms,
        'showrooms':      all_showrooms,       # showroom badge strip
        'nav_categories': categories,          # navbar dropdown
        'categories':     categories,          # category strip
        'videos':         videos,
        'offers':         [],
        'enquiry_form':   form,
        'showroom_count': len(all_showrooms),  # use in template instead of .count
    })


# ── bike list ─────────────────────────────────────────────────────────────────

def bike_list(request):
    selected_category = request.GET.get('category')

    categories = list(BikeCategory.objects.all().order_by('order'))

    bikes_qs = (
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
        .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
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

    related_bikes = list(
        Bike.objects
        .filter(category=bike.category, is_active=True)
        .exclude(pk=bike.pk)
        .select_related('category')
        .prefetch_related(
            _color_prefetch(
                images_qs=BikeImage.objects.filter(
                    media_type__in=['image_upload', 'image_url', 'gif_upload']
                ).order_by('order')
            )
        )
        .only('id', 'name', 'slug', 'price', 'engine_cc', 'mileage', 'category')
        [:4]
    )

    showrooms = list(Showroom.objects.filter(is_active=True))

    return render(request, 'core/bike_detail.html', {
        'bike':             bike,
        'related_bikes':    related_bikes,
        'enquiry_form':     EnquiryForm(initial={'bike': bike}),
        'showrooms':        showrooms,
        'primary_showroom': showrooms[0] if showrooms else None,
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

    return render(request, 'core/enquiry.html', {'form': form})


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

    return render(request, 'core/book_service.html', {
        'form':                   form,
        'service_stations':       ServiceStation.objects.filter(is_active=True),
        'showrooms_with_service': Showroom.objects.filter(has_service_center=True, is_active=True),
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

    return render(request, 'core/exchange.html', {'form': form})


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
    return render(request, 'core/contact.html', {
        'showrooms':        Showroom.objects.filter(is_active=True),
        'service_stations': ServiceStation.objects.filter(is_active=True),
    })