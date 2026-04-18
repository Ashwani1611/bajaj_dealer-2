from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Bike, BikeCategory, Showroom, YouTubeVideo
from .forms import EnquiryForm, ServiceBookingForm, ExchangeForm


def home(request):
    featured_bikes = Bike.objects.filter(is_featured=True, is_active=True).select_related('category')[:6]
    categories = BikeCategory.objects.all()
    videos = YouTubeVideo.objects.filter(section='home', is_active=True)
    showrooms = Showroom.objects.filter(is_active=True)
    enquiry_form = EnquiryForm()

    context = {
        'featured_bikes': featured_bikes,
        'categories': categories,
        'videos': videos,
        'showrooms': showrooms,
        'enquiry_form': enquiry_form,
    }
    return render(request, 'core/home.html', context)


def bike_list(request):
    categories = BikeCategory.objects.prefetch_related('bikes').all()
    selected_category = request.GET.get('category')

    if selected_category:
        bikes = Bike.objects.filter(category__slug=selected_category, is_active=True).select_related('category')
    else:
        bikes = Bike.objects.filter(is_active=True).select_related('category')

    context = {
        'bikes': bikes,
        'categories': categories,
        'selected_category': selected_category,
    }
    return render(request, 'core/bike_list.html', context)


def bike_detail(request, slug):
    bike = get_object_or_404(Bike, slug=slug, is_active=True)
    related_bikes = Bike.objects.filter(category=bike.category, is_active=True).exclude(pk=bike.pk)[:4]
    enquiry_form = EnquiryForm(initial={'bike': bike})

    context = {
        'bike': bike,
        'related_bikes': related_bikes,
        'enquiry_form': enquiry_form,
    }
    return render(request, 'core/bike_detail.html', context)


def enquiry(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We will contact you shortly.')
            return redirect('enquiry_success')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = EnquiryForm()

    return render(request, 'core/enquiry.html', {'form': form})


def enquiry_success(request):
    return render(request, 'core/success.html', {
        'title': 'Enquiry Submitted!',
        'message': 'Our team will call you within 24 hours.',
        'icon': 'bi-check-circle-fill',
    })


def book_service(request):
    if request.method == 'POST':
        form = ServiceBookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service booked successfully!')
            return redirect('service_success')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ServiceBookingForm()

    return render(request, 'core/book_service.html', {'form': form})


def service_success(request):
    return render(request, 'core/success.html', {
        'title': 'Service Booked!',
        'message': 'We will confirm your service appointment shortly.',
        'icon': 'bi-wrench-adjustable-circle-fill',
    })


def exchange_bike(request):
    if request.method == 'POST':
        form = ExchangeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exchange request submitted!')
            return redirect('exchange_success')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ExchangeForm()

    return render(request, 'core/exchange.html', {'form': form})


def exchange_success(request):
    return render(request, 'core/success.html', {
        'title': 'Exchange Request Received!',
        'message': 'Our team will evaluate your bike and get back to you.',
        'icon': 'bi-arrow-left-right',
    })


def contact(request):
    showrooms = Showroom.objects.filter(is_active=True)
    return render(request, 'core/contact.html', {'showrooms': showrooms})
