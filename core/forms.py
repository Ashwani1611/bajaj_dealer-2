from django import forms
from .models import Enquiry, ServiceBooking, ExchangeRequest, Showroom, Bike
import re


def validate_indian_phone(value):
    pattern = re.compile(r'^[6-9]\d{9}$')
    if not pattern.match(value):
        raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')


class EnquiryForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number'})
    )

    class Meta:
        model = Enquiry
        fields = ['name', 'phone', 'email', 'enquiry_type', 'bike', 'showroom', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email (optional)'}),
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any specific requirements...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bike'].queryset = Bike.objects.filter(is_active=True).order_by('category__name', 'name')
        self.fields['showroom'].queryset = Showroom.objects.filter(is_active=True)
        self.fields['email'].required = False
        self.fields['message'].required = False
        self.fields['bike'].required = False
        self.fields['showroom'].required = False
        # Add Bootstrap classes
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ServiceBookingForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number', 'class': 'form-control'})
    )

    class Meta:
        model = ServiceBooking
        fields = ['name', 'phone', 'email', 'bike_model', 'registration_number', 'showroom', 'preferred_date', 'issue_description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email (optional)', 'class': 'form-control'}),
            'bike_model': forms.TextInput(attrs={'placeholder': 'e.g. Pulsar NS200', 'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'e.g. DL01AB1234', 'class': 'form-control'}),
            'showroom': forms.Select(attrs={'class': 'form-select'}),
            'preferred_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'issue_description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the issue (optional)', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['showroom'].queryset = Showroom.objects.filter(is_active=True)
        self.fields['email'].required = False
        self.fields['registration_number'].required = False
        self.fields['issue_description'].required = False


class ExchangeForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number', 'class': 'form-control'})
    )

    class Meta:
        model = ExchangeRequest
        fields = ['name', 'phone', 'current_bike', 'current_bike_year', 'km_driven', 'interested_in', 'showroom']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name', 'class': 'form-control'}),
            'current_bike': forms.TextInput(attrs={'placeholder': 'e.g. Hero Splendor Plus', 'class': 'form-control'}),
            'current_bike_year': forms.NumberInput(attrs={'placeholder': 'e.g. 2019', 'class': 'form-control'}),
            'km_driven': forms.NumberInput(attrs={'placeholder': 'e.g. 25000', 'class': 'form-control'}),
            'interested_in': forms.Select(attrs={'class': 'form-select'}),
            'showroom': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interested_in'].queryset = Bike.objects.filter(is_active=True)
        self.fields['showroom'].queryset = Showroom.objects.filter(is_active=True)
        self.fields['interested_in'].required = False
        self.fields['showroom'].required = False
