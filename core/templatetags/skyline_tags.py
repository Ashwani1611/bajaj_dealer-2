# core/templatetags/skyline_tags.py

from django import template

register = template.Library()

# fl_relative  → makes w_ a fraction of the base image width (not fixed pixels)
# w_0.12       → logo = 12% of image width (looks consistent at all sizes)
# x_10,y_10    → 10px padding from corner
LOGO_TRANSFORM = "l_fetch:aHR0cHM6Ly93d3cuc2t5bGluZXdoZWVscy5pbi9zdGF0aWMvaW1hZ2VzL2xvZ28ucG5n,g_south_east,x_10,y_10,w_0.12,fl_relative"


@register.filter(name='with_logo')
def with_logo(url):
    """
    Injects Skyline watermark logo into a Cloudinary image URL.
    Safe: returns unchanged URL if not a Cloudinary URL.
    Always call BEFORE cloudinary_w so the logo sits inside the
    final resize step, not after it.
    """
    if not url:
        return url
    url = str(url)
    if 'res.cloudinary.com' not in url:
        return url
    return url.replace('/upload/', f'/upload/{LOGO_TRANSFORM}/', 1)


@register.filter(name='cloudinary_w')
def cloudinary_w(url, width):
    """
    Injects width + format + quality into a Cloudinary URL.

    Usage: {{ img_url|with_logo|cloudinary_w:1920 }}

    Produces a SINGLE clean transformation step:
        /upload/f_auto,q_auto:best,w_<width>/...
    Never call on a URL that already has f_auto or q_auto baked in
    (models.py no longer does that — get_display_url returns raw URLs).
    """
    if not url:
        return url
    url = str(url)
    if 'res.cloudinary.com' not in url or '/upload/' not in url:
        return url
    return url.replace('/upload/', f'/upload/f_auto,q_auto:best,w_{int(width)}/', 1)