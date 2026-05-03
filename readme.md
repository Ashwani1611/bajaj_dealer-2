# 🏍️ Bajaj Dealership Website

A professional Django-based dealership website built for a Bajaj motorcycle dealer. Features bike listings, enquiry forms, push notifications, and a full admin panel.

---

## 🌐 Live Demo

🔗 [https://web-production-0f894.up.railway.app](https://web-production-0f894.up.railway.app)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django (Python) |
| **Database** | PostgreSQL (Supabase) |
| **Image Storage** | Cloudinary |
| **Hosting** | Railway |
| **CI/CD** | GitHub Actions |
| **Web Server** | Gunicorn |
| **Frontend** | HTML, CSS, Bootstrap |

---

## ✨ Features

- 🏍️ Bike listings with detailed pages
- 📋 Customer enquiry forms
- 🔔 Push notifications (VAPID)
- 🗺️ Google Maps integration
- 📱 WhatsApp, Facebook, Instagram links
- 🔒 Admin panel for management
- ☁️ Cloudinary image uploads
- 🔐 Secure environment variable management

---

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Ashwani1611/bajaj_dealer-2.git
cd bajaj_dealer-2
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup environment variables

```bash
cp .env.example .env
# Fill in your actual values in .env
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create superuser

```bash
python manage.py createsuperuser
```

### 7. Run development server

```bash
python manage.py runserver
```

Visit → http://localhost:8000

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=your-db-host
DB_PORT=5432

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Social Media
WHATSAPP_NUMBER=your-number
FACEBOOK_URL=your-facebook-url
INSTAGRAM_URL=your-instagram-url

# Google Maps
GOOGLE_MAPS_API_KEY=your-maps-key

# Push Notifications (VAPID)
VAPID_PUBLIC_KEY=your-public-key
VAPID_PRIVATE_KEY=your-private-key
VAPID_ADMIN_EMAIL=your-email
```

---

## 🚀 CI/CD Pipeline

This project uses **GitHub Actions** for CI/CD:

```
git push → GitHub Actions
               ↓
        Install dependencies
               ↓
        Run Django checks
               ↓
        Railway auto deploys
               ↓
        Site updated! ✅
```

Pipeline file: `.github/workflows/django.yml`

---

## 🗄️ Database

- **Production**: Supabase PostgreSQL (free tier)
- **Local**: Configure via `.env` file

### Run migrations
```bash
python manage.py migrate
```

### Export/Import data
```bash
# Export
python manage.py dumpdata --output=data.json

# Import
python manage.py loaddata data.json
```

---

## 📁 Project Structure

```
bajaj_dealer-2/
├── bajaj_dealer/          # Main Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                  # Main app
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── media/                 # Uploaded files
├── .github/
│   └── workflows/
│       └── django.yml     # CI/CD pipeline
├── .env.example           # Environment template
├── Procfile               # Railway deployment
├── requirements.txt
└── manage.py
```

---

## 🚢 Deployment

This project is deployed on **Railway** with **Supabase** PostgreSQL.

### Environment Variables on Railway
Add all variables from `.env.example` in Railway dashboard under **Variables** tab.

### Deploy manually
```bash
git add .
git commit -m "your changes"
git push
# Railway auto deploys! ✅
```

---

## 👨‍💻 Developer

**Ashwani Kumar**
- GitHub: [@Ashwani1611](https://github.com/Ashwani1611)
- Email: a4ashwanik4kr@gmail.com

---

## 📄 License

This project is private and built for a client.
© 2026 Ashwani Kumar. All rights reserved.
