# Skyline Bajaj — All Fixes Applied

## Files in this package

| File | What changed |
|---|---|
| `admin.py` | Fixed 3 bugs + major improvements |
| `views.py` | Per-showroom/station email + WhatsApp |
| `context_processors.py` | NEW — injects logo, showrooms into all templates |
| `settings_additions.py` | All required settings |
| `templates/base.html` | Real logo, per-showroom WA float, scroll shadow |
| `templates/core/success.html` | Branded card with submitted details + WA CTA |
| `templates/core/book_service.html` | Service station primary, Tuesday closed note |
| `templates/core/contact.html` | Per-showroom WA fix, service stations section added |
| `templates/emails/enquiry_notification.html` | HTML email to showroom |
| `templates/emails/service_notification.html` | HTML email to service station |
| `templates/emails/exchange_notification.html` | HTML email to showroom |

---

## Bugs fixed

### 1. admin.py — ServiceStation never registered (CRASH)
- Added `@admin.register(ServiceStation)` with full fieldsets

### 2. admin.py — ServiceBooking list_filter crashed
- `is_confirmed` is a `@property`, not a DB field — can't filter on it
- Changed to `list_filter = ['status']`

### 3. contact.html — wrong WhatsApp URL
- Was using raw `showroom.phone` in wa.me link
- Now uses `showroom.whatsapp_url` method (proper country code handling)

### 4. base.html — global WA number for all showrooms
- Float button now uses `primary_showroom.whatsapp_url` (first active showroom)
- Each showroom and service station has its own WA number used in forms

### 5. book_service.html — showroom shown instead of service station
- `service_station` is now the primary/first field
- Shows station info card dynamically when station is selected
- Tuesday closed note displayed prominently
- Correct timing: Mon, Wed–Sun: 9:00 AM – 6:00 PM

### 6. Email routing
- Enquiry email → selected showroom's email (+ CC master)
- Service email → selected service_station's email (+ CC master)
- Exchange email → selected showroom's email (+ CC master)

---

## Quick setup (5 steps)

### Step 1 — Copy files
```
your_project/
  core/
    admin.py                          ← replace
    views.py                          ← replace
    context_processors.py             ← NEW file
  templates/
    base.html                         ← replace
    core/
      success.html                    ← replace
      book_service.html               ← replace
      contact.html                    ← replace
    emails/
      enquiry_notification.html       ← NEW
      service_notification.html       ← NEW
      exchange_notification.html      ← NEW
```

### Step 2 — Add context processor to settings.py
Open `settings.py`, find `TEMPLATES`, add to `context_processors`:
```python
'core.context_processors.site_globals',
```

### Step 3 — Add settings values to settings.py
Copy from `settings_additions.py` and fill in real values:
- `SITE_NAME`
- `LOGO_URL`
- `WHATSAPP_NUMBER`
- `DEALER_MASTER_EMAIL`
- Email SMTP settings

### Step 4 — Copy your logo
```bash
mkdir -p static/images/
cp bajaj_logo-1.png static/images/skyline_bajaj_logo.png
```
Then in settings: `LOGO_URL = '/static/images/skyline_bajaj_logo.png'`

### Step 5 — Add ServiceStation data in admin
Go to `/admin/` → Service Stations → Add each station with:
- Name, address, phone
- **WhatsApp number** (with country code, no +, e.g. `919876543210`)
- **Email** (service booking emails will go here)
- Working hours (default: Mon, Wed–Sun: 9:00 AM – 6:00 PM | Tuesday Closed)

---

## Admin improvements summary

- **Enquiry**: mark_as_read/unread bulk action, export CSV, color-coded type badges, "New" indicator
- **ServiceBooking**: status dropdown bulk actions (confirm/complete), export CSV, status badges
- **ServiceStation**: now fully registered and manageable
- **Bike**: list_editable for is_featured + is_active
- **YouTubeVideo**: thumbnail preview in list, list_editable order
- **All forms**: export_as_csv action available

---

## WhatsApp routing summary

| Form | WhatsApp goes to |
|---|---|
| Enquiry form | Selected showroom's WA number |
| Service booking | Selected service station's WA number |
| Exchange request | Selected showroom's WA number |
| Navbar float button | First active showroom's WA number |
| Fallback (none selected) | `settings.WHATSAPP_NUMBER` |