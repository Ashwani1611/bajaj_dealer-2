from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.home,              name='home'),
    path('bikes/',                        views.bike_list,         name='bike_list'),
    path('bikes/<slug:slug>/',            views.bike_detail,       name='bike_detail'),
    path('chetak/',                       views.chetak,            name='chetak'),        # ← NEW
    path('enquiry/',                      views.enquiry,           name='enquiry'),
    path('enquiry/success/',              views.enquiry_success,   name='enquiry_success'),
    path('service/',                      views.book_service,      name='book_service'),
    path('service/success/',              views.service_success,   name='service_success'),
    path('exchange/',                     views.exchange_bike,     name='exchange_bike'),
    path('exchange/success/',             views.exchange_success,  name='exchange_success'),
    path('contact/',                      views.contact,           name='contact'),
    path('media/delete/<int:pk>/',        views.delete_bike_image, name='delete_bike_image'),
]