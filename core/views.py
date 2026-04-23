from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Prefetch
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import urllib.parse

from .models import (
    Bike, BikeCategory, BikeColor, BikeImage,
    Showroom, ServiceStation, YouTubeVideo
)
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


# ── helpers ───────────────────────────────────────────────────────────────────

def _color_prefetch(images_qs=None):
    if images_qs is None:
        images_qs = BikeImage.objects.all()
    return Prefetch(
        'colors',
        queryset=BikeColor.objects.filter(
            is_available=True
        ).prefetch_related(
            Prefetch('images', queryset=images_qs)
        )
    )


def _send_html_email(subject, template_name, context, to_emails):
    """Send HTML email to a list of addresses. Never crashes user flow."""
    if not to_emails:
        return
    try:
        html_content  = render_to_string(template_name, context)
        text_content  = strip_tags(html_content)
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
    """Build wa.me URL. number can be raw 10-digit or include country code."""
    clean = ''.join(filter(str.isdigit, number or ''))
    if clean and not clean.startswith('91'):
        clean = '91' + clean
    return f"https://wa.me/{clean}?text={urllib.parse.quote(message)}"


def _master_email():
    return getattr(settings, 'DEALER_MASTER_EMAIL', None) or \
           getattr(settings, 'DEALER_EMAIL', None)


# ── context processor helper (used in views that need showrooms everywhere) ───

def _base_context():
    return {
        'primary_showroom': Showroom.objects.filter(is_active=True).first(),
    }


# ── home ──────────────────────────────────────────────────────────────────────

def home(request):
    featured_bikes = (
        Bike.objects
        .filter(is_featured=True, is_active=True)
        .select_related('category')
        .prefetch_related(_color_prefetch())[:6]
    )
    categories  = BikeCategory.objects.all()
    videos      = YouTubeVideo.objects.filter(section='home', is_active=True)
    showrooms   = Showroom.objects.filter(is_active=True)
    enquiry_form = EnquiryForm()

    return render(request, 'core/home.html', {
        'featured_bikes':  featured_bikes,
        'categories':      categories,
        'videos':          videos,
        'showrooms':       showrooms,
        'all_showrooms':   showrooms,
        'enquiry_form':    enquiry_form,
        'primary_showroom': showrooms.first(),
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
        Bike.objects.select_related('category').prefetch_related(_color_prefetch()),
        slug=slug, is_active=True,
    )
    related_bikes = (
        Bike.objects
        .filter(category=bike.category, is_active=True)
        .exclude(pk=bike.pk)
        .select_related('category')
        .prefetch_related(_color_prefetch(images_qs=BikeImage.objects.order_by('order')))[:4]
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


# ── delete bike image ─────────────────────────────────────────────────────────

@staff_member_required
def delete_bike_image(request, pk):
    img       = get_object_or_404(BikeImage, pk=pk)
    bike_slug = img.color.bike.slug
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

            # Determine target email: use showroom email if selected, else master
            to_emails = []
            if enq.showroom and enq.showroom.email:
                to_emails.append(enq.showroom.email)
            if _master_email() and _master_email() not in to_emails:
                to_emails.append(_master_email())

            _send_html_email(
                subject=f"New Enquiry: {enq.get_enquiry_type_display()} — {enq.name}",
                template_name='emails/enquiry_notification.html',
                context={'enquiry': enq, 'settings': settings},
                to_emails=to_emails,
            )

            # WhatsApp: use showroom's WA number if selected, else master
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
            return redirect(
                f"/enquiry/success/?wa={urllib.parse.quote(wa_msg)}"
                f"&phone={wa_number}"
                f"&name={urllib.parse.quote(enq.name)}"
                f"&type={urllib.parse.quote(enq.get_enquiry_type_display())}"
            )
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
            {'label': 'Name', 'value': name},
            {'label': 'Enquiry Type', 'value': enq_type},
        ],
    })


# ── service booking ───────────────────────────────────────────────────────────

def book_service(request):
    service_stations = ServiceStation.objects.filter(is_active=True)

    if request.method == 'POST':
        form = ServiceBookingForm(request.POST)
        if form.is_valid():
            booking = form.save()

            # Email goes to service_station.email, CC master
            to_emails = []
            if booking.service_station and booking.service_station.email:
                to_emails.append(booking.service_station.email)
            if _master_email() and _master_email() not in to_emails:
                to_emails.append(_master_email())

            _send_html_email(
                subject=f"Service Booking: {booking.name} — {booking.bike_model}",
                template_name='emails/service_notification.html',
                context={'booking': booking, 'settings': settings},
                to_emails=to_emails,
            )

            # WhatsApp: use service_station WA
            wa_number = ''
            if booking.service_station:
                wa_number = booking.service_station.get_whatsapp_number()
            if not wa_number:
                wa_number = getattr(settings, 'WHATSAPP_NUMBER', booking.phone)

            wa_msg = (
                f"New Service Booking!\n"
                f"Name: {booking.name}\n"
                f"Phone: {booking.phone}\n"
                f"Bike: {booking.bike_model}\n"
                f"Date: {booking.preferred_date}\n"
                f"Station: {booking.service_station or 'Not specified'}\n"
                f"Issue: {booking.issue_description or 'None'}"
            )

            messages.success(request, 'Service booked successfully!')
            return redirect(
                f"/service/success/?wa={urllib.parse.quote(wa_msg)}"
                f"&phone={wa_number}"
                f"&name={urllib.parse.quote(booking.name)}"
                f"&bike={urllib.parse.quote(booking.bike_model)}"
                f"&date={booking.preferred_date}"
            )
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ServiceBookingForm()

    return render(request, 'core/book_service.html', {
        'form':             form,
        'service_stations': service_stations,
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
            {'label': 'Name', 'value': name},
            {'label': 'Bike', 'value': bike},
            {'label': 'Preferred Date', 'value': date},
        ],
    })


# ── exchange ──────────────────────────────────────────────────────────────────

def exchange_bike(request):
    if request.method == 'POST':
        form = ExchangeForm(request.POST)
        if form.is_valid():
            exchange = form.save()

            to_emails = []
            if exchange.showroom and exchange.showroom.email:
                to_emails.append(exchange.showroom.email)
            if _master_email() and _master_email() not in to_emails:
                to_emails.append(_master_email())

            _send_html_email(
                subject=f"Exchange Request: {exchange.name} — {exchange.current_bike}",
                template_name='emails/exchange_notification.html',
                context={'exchange': exchange, 'settings': settings},
                to_emails=to_emails,
            )

            wa_number = ''
            if exchange.showroom:
                wa_number = exchange.showroom.get_whatsapp_number()
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
            return redirect(
                f"/exchange/success/?wa={urllib.parse.quote(wa_msg)}"
                f"&phone={wa_number}"
                f"&name={urllib.parse.quote(exchange.name)}"
                f"&bike={urllib.parse.quote(exchange.current_bike)}"
            )
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
            {'label': 'Name', 'value': name},
            {'label': 'Current Bike', 'value': bike},
        ],
    })


# ── contact / showrooms ───────────────────────────────────────────────────────

def contact(request):
    showrooms        = Showroom.objects.filter(is_active=True)
    service_stations = ServiceStation.objects.filter(is_active=True)
    return render(request, 'core/contact.html', {
        'showrooms':        showrooms,
        'service_stations': service_stations,
    })