from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
import urllib.parse

from .models import (
    Enquiry, ServiceBooking, ExchangeRequest,
    Bike, Showroom, BikeCategory, YouTubeVideo, ServiceStation,
)


def _master_email():
    return getattr(settings, 'DEALER_MASTER_EMAIL', None) or \
           getattr(settings, 'DEALER_EMAIL', None)


def _send_notification(subject, message, to_emails):
    """Send plain email. Never crashes."""
    recipients = [e for e in to_emails if e]
    if not recipients:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL NOTIFICATIONS  (existing — unchanged)
# ══════════════════════════════════════════════════════════════════════════════

# ── Enquiry ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Enquiry)
def notify_new_enquiry(sender, instance, created, **kwargs):
    if not created:
        return

    to_emails = []
    if instance.showroom and instance.showroom.email:
        to_emails.append(instance.showroom.email)
    master = _master_email()
    if master and master not in to_emails:
        to_emails.append(master)

    bike_name = instance.bike.name if instance.bike else 'Not specified'
    message = (
        f"New {instance.get_enquiry_type_display()} received!\n\n"
        f"Name    : {instance.name}\n"
        f"Phone   : {instance.phone}\n"
        f"Email   : {instance.email or '—'}\n"
        f"Bike    : {bike_name}\n"
        f"Showroom: {instance.showroom or '—'}\n"
        f"Message : {instance.message or '—'}\n"
    )
    _send_notification(
        subject=f"New Enquiry: {instance.get_enquiry_type_display()} — {instance.name}",
        message=message,
        to_emails=to_emails,
    )


# ── ServiceBooking ────────────────────────────────────────────────────────────

@receiver(post_save, sender=ServiceBooking)
def notify_new_service_booking(sender, instance, created, **kwargs):
    if not created:
        return

    to_emails = []
    if instance.service_station and instance.service_station.email:
        to_emails.append(instance.service_station.email)
    if instance.showroom and instance.showroom.email:
        if instance.showroom.email not in to_emails:
            to_emails.append(instance.showroom.email)
    master = _master_email()
    if master and master not in to_emails:
        to_emails.append(master)

    message = (
        f"New Service Booking received!\n\n"
        f"Name    : {instance.name}\n"
        f"Phone   : {instance.phone}\n"
        f"Bike    : {instance.bike_model}\n"
        f"Reg No  : {instance.registration_number or '—'}\n"
        f"Station : {instance.service_station or '—'}\n"
        f"Date    : {instance.preferred_date}\n"
        f"Issue   : {instance.issue_description or '—'}\n"
    )
    _send_notification(
        subject=f"Service Booking: {instance.name} — {instance.bike_model}",
        message=message,
        to_emails=to_emails,
    )


# ── ExchangeRequest ───────────────────────────────────────────────────────────

@receiver(post_save, sender=ExchangeRequest)
def notify_new_exchange(sender, instance, created, **kwargs):
    if not created:
        return

    to_emails = []
    if instance.showroom and instance.showroom.email:
        to_emails.append(instance.showroom.email)
    master = _master_email()
    if master and master not in to_emails:
        to_emails.append(master)

    interested = instance.interested_in.name if instance.interested_in else 'Not specified'
    message = (
        f"New Exchange Request received!\n\n"
        f"Name        : {instance.name}\n"
        f"Phone       : {instance.phone}\n"
        f"Current Bike: {instance.current_bike} ({instance.current_bike_year})\n"
        f"KM Driven   : {instance.km_driven}\n"
        f"Interested In: {interested}\n"
        f"Showroom    : {instance.showroom or '—'}\n"
    )
    _send_notification(
        subject=f"Exchange Request: {instance.name} — {instance.current_bike}",
        message=message,
        to_emails=to_emails,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CACHE INVALIDATION  (new)
# ══════════════════════════════════════════════════════════════════════════════

@receiver(post_save, sender=Bike)
@receiver(post_delete, sender=Bike)
def clear_bike_cache(sender, instance, **kwargs):
    cache.delete('featured_bikes')
    cache.delete('home_all_bikes')
    cache.delete(f'bike_{instance.slug}')
    cache.delete(f'related_bikes_{instance.slug}')
    cache.delete_pattern('bike_list_*')


@receiver(post_save, sender=Showroom)
@receiver(post_delete, sender=Showroom)
def clear_showroom_cache(sender, **kwargs):
    cache.delete('all_showrooms')
    cache.delete('showrooms_with_service')


@receiver(post_save, sender=BikeCategory)
@receiver(post_delete, sender=BikeCategory)
def clear_category_cache(sender, **kwargs):
    cache.delete('all_categories')
    cache.delete_pattern('bike_list_*')


@receiver(post_save, sender=YouTubeVideo)
@receiver(post_delete, sender=YouTubeVideo)
def clear_video_cache(sender, **kwargs):
    cache.delete('home_videos')


@receiver(post_save, sender=ServiceStation)
@receiver(post_delete, sender=ServiceStation)
def clear_service_station_cache(sender, **kwargs):
    cache.delete('service_stations')