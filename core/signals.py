from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import urllib.parse

from .models import Enquiry, ServiceBooking, ExchangeRequest


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