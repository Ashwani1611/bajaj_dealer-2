from django import forms
from .models import Enquiry, ServiceBooking, ExchangeRequest, Showroom, ServiceStation, Bike
import re


# ── validators ────────────────────────────────────────────────────────────────

def validate_indian_phone(value):
    pattern = re.compile(r'^[6-9]\d{9}$')
    if not pattern.match(value):
        raise forms.ValidationError('Enter a valid 10-digit Indian mobile number.')


# ── EnquiryForm ───────────────────────────────────────────────────────────────

class EnquiryForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={'placeholder': '10-digit mobile number'}),
    )

    class Meta:
        model  = Enquiry
        fields = ['name', 'phone', 'email', 'enquiry_type', 'bike', 'showroom', 'message']
        widgets = {
            'name':    forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'email':   forms.EmailInput(attrs={'placeholder': 'Email (optional)'}),
            'message': forms.Textarea(attrs={
                'rows':        3,
                'placeholder': 'Any specific requirements...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bike'].queryset     = Bike.objects.filter(is_active=True).order_by('category__name', 'name')
        self.fields['showroom'].queryset = Showroom.objects.filter(is_active=True)
        self.fields['email'].required    = False
        self.fields['message'].required  = False
        self.fields['bike'].required     = False
        self.fields['showroom'].required = False

        self.fields['bike'].empty_label     = '— Select a bike (optional) —'
        self.fields['showroom'].empty_label = '— Select nearest showroom (optional) —'

        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            if 'form-' not in existing:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'


# ── ServiceBookingForm ────────────────────────────────────────────────────────

class ServiceBookingForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={
            'placeholder': '10-digit mobile number',
            'class':       'form-control',
        }),
    )

    class Meta:
        model  = ServiceBooking
        fields = [
            'name', 'phone', 'email',
            'bike_model', 'registration_number',
            'showroom',         # showroom with service center
            'service_station',  # standalone service station
            'preferred_date',
            'issue_description',
        ]
        widgets = {
            'name':                forms.TextInput(attrs={
                'placeholder': 'Your full name', 'class': 'form-control'}),
            'email':               forms.EmailInput(attrs={
                'placeholder': 'Email (optional)', 'class': 'form-control'}),
            'bike_model':          forms.TextInput(attrs={
                'placeholder': 'e.g. Pulsar NS200', 'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={
                'placeholder': 'e.g. DL01AB1234', 'class': 'form-control'}),
            'showroom':            forms.Select(attrs={'class': 'form-select'}),
            'service_station':     forms.Select(attrs={'class': 'form-select'}),
            'preferred_date':      forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control'}),
            'issue_description':   forms.Textarea(attrs={
                'rows':        3,
                'placeholder': 'Describe the issue or service required (optional)',
                'class':       'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only showrooms that have a service center (mirrors limit_choices_to on the model)
        self.fields['showroom'].queryset = Showroom.objects.filter(
            has_service_center=True, is_active=True
        )
        self.fields['service_station'].queryset = ServiceStation.objects.filter(is_active=True)

        # Optional fields
        self.fields['email'].required               = False
        self.fields['registration_number'].required = False
        self.fields['issue_description'].required   = False

        # Both location fields are optional individually — clean() enforces exactly one
        self.fields['showroom'].required        = False
        self.fields['service_station'].required = False

        # Labels and empty labels
        self.fields['showroom'].label             = 'Showroom with Service Center'
        self.fields['showroom'].empty_label        = '— Choose a showroom —'
        self.fields['showroom'].help_text          = 'Select if your preferred showroom provides service'

        self.fields['service_station'].label       = 'Service Station'
        self.fields['service_station'].empty_label = '— Choose a service station —'
        self.fields['service_station'].help_text   = 'Select a dedicated service station'

    def clean(self):
        """
        Mirrors the ServiceBooking.clean() model validation so errors surface
        in the form before the object is saved — gives users inline field errors
        rather than a 500 or silent failure.
        """
        cleaned = super().clean()
        showroom        = cleaned.get('showroom')
        service_station = cleaned.get('service_station')

        if not showroom and not service_station:
            raise forms.ValidationError(
                'Please select either a showroom with service center '
                'or a service station.'
            )
        if showroom and service_station:
            raise forms.ValidationError(
                'Please select only one service location — '
                'either a showroom or a service station, not both.'
            )
        return cleaned


# ── ExchangeForm ──────────────────────────────────────────────────────────────

class ExchangeForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=10,
        validators=[validate_indian_phone],
        widget=forms.TextInput(attrs={
            'placeholder': '10-digit mobile number',
            'class':       'form-control',
        }),
    )

    class Meta:
        model  = ExchangeRequest
        # Uses related_name='exchange_requests' on interested_in FK in updated model
        fields = [
            'name', 'phone',
            'current_bike', 'current_bike_year', 'km_driven',
            'interested_in', 'showroom',
        ]
        widgets = {
            'name':              forms.TextInput(attrs={
                'placeholder': 'Your full name', 'class': 'form-control'}),
            'current_bike':      forms.TextInput(attrs={
                'placeholder': 'e.g. Hero Splendor Plus', 'class': 'form-control'}),
            'current_bike_year': forms.NumberInput(attrs={
                'placeholder': 'e.g. 2019', 'class': 'form-control',
                'min': 1990, 'max': 2100}),
            'km_driven':         forms.NumberInput(attrs={
                'placeholder': 'e.g. 25000', 'class': 'form-control', 'min': 0}),
            'interested_in':     forms.Select(attrs={'class': 'form-select'}),
            'showroom':          forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interested_in'].queryset = (
            Bike.objects.filter(is_active=True).order_by('category__name', 'name')
        )
        self.fields['showroom'].queryset = Showroom.objects.filter(is_active=True)

        self.fields['interested_in'].required = False
        self.fields['showroom'].required      = False

        self.fields['interested_in'].empty_label = '— Select a Bajaj model (optional) —'
        self.fields['showroom'].empty_label      = '— Select nearest showroom (optional) —'

    def clean_current_bike_year(self):
        year = self.cleaned_data.get('current_bike_year')
        if year and (year < 1990 or year > 2100):
            raise forms.ValidationError('Please enter a valid manufacture year.')
        return year

    def clean_km_driven(self):
        km = self.cleaned_data.get('km_driven')
        if km is not None and km < 0:
            raise forms.ValidationError('KM driven cannot be negative.')
        return km