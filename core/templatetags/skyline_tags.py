# core/templatetags/skyline_tags.py
# Adds Skyline logo to bottom-left corner of all Cloudinary bike images

from django import template

register = template.Library()

# Cloudinary overlay transformation:
# l_logos:skyline_logo  → your logo public_id (logos/skyline_logo)
# g_south_west          → bottom-left corner
# x_15,y_15            → 15px padding from edges
# w_100                 → logo width 100px (adjust if needed)
LOGO_TRANSFORM = "l_fetch:aHR0cHM6Ly93d3cuc2t5bGluZXdoZWVscy5pbi9zdGF0aWMvaW1hZ2VzL2xvZ28ucG5n,g_south_east,x_15,y_15,w_100"


@register.filter(name='with_logo')
def with_logo(url):
    """
    Injects Skyline watermark logo into a Cloudinary image URL.
    Safe: returns unchanged URL if not a Cloudinary URL (local files, placeholders, etc.)

    Usage in template:
        {{ some_url|with_logo }}
        {{ item.get_display_url|with_logo }}
        {{ bike.get_primary_image_url|with_logo }}
    """
    if not url:
        return url
    url = str(url)
    # Only transform Cloudinary URLs
    if 'res.cloudinary.com' not in url:
        return url
    # Insert transformation after /upload/
    return url.replace('/upload/', f'/upload/{LOGO_TRANSFORM}/', 1)