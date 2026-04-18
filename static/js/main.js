// ============================================
// BAJAJ DEALER - Main JS
// Lightweight, no jQuery dependency
// ============================================

document.addEventListener('DOMContentLoaded', function () {

    // ---- AUTO-DISMISS ALERTS after 4 seconds ----
    document.querySelectorAll('.alert.alert-success').forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 4000);
    });

    // ---- PHONE NUMBER - allow only digits ----
    document.querySelectorAll('input[name="phone"]').forEach(function (input) {
        input.addEventListener('input', function () {
            this.value = this.value.replace(/\D/g, '').slice(0, 10);
        });
    });

    // ---- YEAR FIELD - restrict to reasonable range ----
    var yearField = document.querySelector('input[name="current_bike_year"]');
    if (yearField) {
        var currentYear = new Date().getFullYear();
        yearField.setAttribute('min', '1990');
        yearField.setAttribute('max', currentYear);
        yearField.setAttribute('placeholder', 'e.g. ' + (currentYear - 3));
    }

    // ---- PREFERRED DATE - disable past dates ----
    var dateField = document.querySelector('input[name="preferred_date"]');
    if (dateField) {
        var today = new Date().toISOString().split('T')[0];
        dateField.setAttribute('min', today);
    }

    // ---- SMOOTH SCROLL for anchor links ----
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ---- LAZY LOAD YouTube iframes ----
    // Already handled by loading="lazy" attribute in HTML
    // This is just a fallback for older browsers
    if ('IntersectionObserver' in window) {
        var iframes = document.querySelectorAll('iframe[src*="youtube.com"]');
        iframes.forEach(function (iframe) {
            iframe.setAttribute('loading', 'lazy');
        });
    }

});
