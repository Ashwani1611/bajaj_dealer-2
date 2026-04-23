from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Prefetch
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import urllib.parse

from .models import Bike, BikeCategory, BikeColor, BikeImage, Showroom, YouTubeVideo
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


# ── reusable prefetch helper ──────────────────────────────────────────────────

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


# ── notification helpers ──────────────────────────────────────────────────────

def _send_enquiry_email(enquiry):
    """Send email notification to dealer when a new enquiry is submitted."""
    if not getattr(settings, 'DEALER_EMAIL', None):
        return
    try:
        subject = f"🏍️ New Enquiry: {enquiry.get_enquiry_type_display()} — {enquiry.name}"
        context = {'enquiry': enquiry, 'settings': settings}
        html_content = render_to_string('emails/enquiry_notification.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEALER_EMAIL],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        pass  # Never crash the user flow due to email failure


def _send_service_email(booking):
    """Send email notification for service bookings."""
    if not getattr(settings, 'DEALER_EMAIL', None):
        return
    try:
        subject = f"🔧 Service Booking: {booking.name} — {booking.bike_model}"
        context = {'booking': booking, 'settings': settings}
        html_content = render_to_string('emails/service_notification.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEALER_EMAIL],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        pass


def _send_exchange_email(exchange):
    """Send email notification for exchange requests."""
    if not getattr(settings, 'DEALER_EMAIL', None):
        return
    try:
        subject = f"🔄 Exchange Request: {exchange.name} — {exchange.current_bike}"
        context = {'exchange': exchange, 'settings': settings}
        html_content = render_to_string('emails/exchange_notification.html', context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEALER_EMAIL],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        pass


def _whatsapp_redirect_url(phone, message):
    """Build a WhatsApp URL with pre-filled message."""
    clean_phone = ''.join(filter(str.isdigit, phone))
    if not clean_phone.startswith('91'):
        clean_phone = '91' + clean_phone
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded}"


# ── home ──────────────────────────────────────────────────────────────────────

def home(request):
    featured_bikes = (
        Bike.objects
        .filter(is_featured=True, is_active=True)
        .select_related('category')
        .prefetch_related(_color_prefetch())
        [:6]
    )
    categories   = BikeCategory.objects.all()
    videos       = YouTubeVideo.objects.filter(section='home', is_active=True)
    showrooms    = Showroom.objects.filter(is_active=True)
    enquiry_form = EnquiryForm()

    return render(request, 'core/home.html', {
        'featured_bikes': featured_bikes,
        'categories':     categories,
        'videos':         videos,
        'showrooms':      showrooms,
        'all_showrooms':  showrooms,
        'enquiry_form':   enquiry_form,
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
        .prefetch_related(_color_prefetch()),
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
        )
        [:4]
    )
    enquiry_form = EnquiryForm(initial={'bike': bike})

    return render(request, 'core/bike_detail.html', {
        'bike':          bike,
        'related_bikes': related_bikes,
        'enquiry_form':  enquiry_form,
    })


# ── delete bike image (staff only) ────────────────────────────────────────────

@staff_member_required
def delete_bike_image(request, pk):
    img = get_object_or_404(BikeImage, pk=pk)
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
            enquiry_obj = form.save()

            # Send email to dealer
            _send_enquiry_email(enquiry_obj)

            # Build WhatsApp message for dealer notification
            bike_name = enquiry_obj.bike.name if enquiry_obj.bike else 'Not specified'
            wa_msg = (
                f"🏍️ New Bajaj Enquiry!\n"
                f"Name: {enquiry_obj.name}\n"
                f"Phone: {enquiry_obj.phone}\n"
                f"Type: {enquiry_obj.get_enquiry_type_display()}\n"
                f"Bike: {bike_name}\n"
                f"Message: {enquiry_obj.message or 'None'}"
            )

            messages.success(request, 'Thank you! We will contact you shortly.')
            return redirect(
                f"{request.build_absolute_uri('/enquiry/success/')}?wa={urllib.parse.quote(wa_msg)}&phone={enquiry_obj.phone}"
            )
        messages.error(request, 'Please fix the errors below.')
    else:
        bike_pk = request.GET.get('bike')
        form = EnquiryForm(initial={'bike': bike_pk} if bike_pk else {})

    return render(request, 'core/enquiry.html', {'form': form})


def enquiry_success(request):
    wa_msg   = request.GET.get('wa', '')
    phone    = request.GET.get('phone', '')
    wa_url   = ''
    if wa_msg and phone:
        wa_url = _whatsapp_redirect_url(
            getattr(settings, 'WHATSAPP_NUMBER', phone),
            urllib.parse.unquote(wa_msg)
        )
    return render(request, 'core/success.html', {
        'title':   'Enquiry Submitted!',
        'message': 'Our team will call you within 24 hours.',
        'icon':    'bi-check-circle-fill',
        'icon_color': '#22c55e',
        'wa_url':  wa_url,
        'wa_msg':  urllib.parse.unquote(wa_msg),
    })


# ── service booking ───────────────────────────────────────────────────────────

def book_service(request):
    if request.method == 'POST':
        form = ServiceBookingForm(request.POST)
        if form.is_valid():
            booking = form.save()
            _send_service_email(booking)

            wa_msg = (
                f"🔧 New Service Booking!\n"
                f"Name: {booking.name}\n"
                f"Phone: {booking.phone}\n"
                f"Bike: {booking.bike_model}\n"
                f"Date: {booking.preferred_date}\n"
                f"Issue: {booking.issue_description or 'None'}"
            )
            messages.success(request, 'Service booked successfully!')
            return redirect(
                f"/service/success/?wa={urllib.parse.quote(wa_msg)}&phone={booking.phone}"
            )
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ServiceBookingForm()

    return render(request, 'core/book_service.html', {'form': form})


def service_success(request):
    wa_msg = request.GET.get('wa', '')
    phone  = request.GET.get('phone', '')
    wa_url = ''
    if wa_msg and phone:
        wa_url = _whatsapp_redirect_url(
            getattr(settings, 'WHATSAPP_NUMBER', phone),
            urllib.parse.unquote(wa_msg)
        )
    return render(request, 'core/success.html', {
        'title':      'Service Booked!',
        'message':    'We will confirm your appointment shortly.',
        'icon':       'bi-wrench-adjustable-circle-fill',
        'icon_color': '#003087',
        'wa_url':     wa_url,
        'wa_msg':     urllib.parse.unquote(wa_msg),
    })


# ── exchange ──────────────────────────────────────────────────────────────────

def exchange_bike(request):
    if request.method == 'POST':
        form = ExchangeForm(request.POST)
        if form.is_valid():
            exchange = form.save()
            _send_exchange_email(exchange)

            wa_msg = (
                f"🔄 New Exchange Request!\n"
                f"Name: {exchange.name}\n"
                f"Phone: {exchange.phone}\n"
                f"Current Bike: {exchange.current_bike} ({exchange.current_bike_year})\n"
                f"KM Driven: {exchange.km_driven}\n"
                f"Interested In: {exchange.interested_in.name if exchange.interested_in else 'Not specified'}"
            )
            messages.success(request, 'Exchange request submitted!')
            return redirect(
                f"/exchange/success/?wa={urllib.parse.quote(wa_msg)}&phone={exchange.phone}"
            )
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ExchangeForm()

    return render(request, 'core/exchange.html', {'form': form})


def exchange_success(request):
    wa_msg = request.GET.get('wa', '')
    phone  = request.GET.get('phone', '')
    wa_url = ''
    if wa_msg and phone:
        wa_url = _whatsapp_redirect_url(
            getattr(settings, 'WHATSAPP_NUMBER', phone),
            urllib.parse.unquote(wa_msg)
        )
    return render(request, 'core/success.html', {
        'title':      'Exchange Request Received!',
        'message':    'Our team will evaluate your bike and get back to you.',
        'icon':       'bi-arrow-left-right',
        'icon_color': '#f59e0b',
        'wa_url':     wa_url,
        'wa_msg':     urllib.parse.unquote(wa_msg),
    })


# ── contact ───────────────────────────────────────────────────────────────────

def contact(request):
    showrooms = Showroom.objects.filter(is_active=True)
    return render(request, 'core/contact.html', {'showrooms': showrooms})