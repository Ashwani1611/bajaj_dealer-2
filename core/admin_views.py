import os

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Showroom, ServiceStation, Enquiry, ServiceBooking, ExchangeRequest


# ── auth guard ────────────────────────────────────────────────────────────────

def superadmin_required(view_func):
    return user_passes_test(
        lambda u: u.is_superuser,
        login_url='/admin/login/'
    )(view_func)


# ── permission helpers ────────────────────────────────────────────────────────

def _get_permissions_for_model(model, actions=('view', 'change')):
    """Returns a list of Permission objects for the given model and actions."""
    ct = ContentType.objects.get_for_model(model)
    return list(
        Permission.objects.filter(
            content_type=ct,
            codename__in=[f'{action}_{model._meta.model_name}' for action in actions]
        )
    )


def _assign_showroom_permissions(user):
    """
    Assign permissions a showroom manager needs:
    - Enquiry      → view + change
    - ExchangeRequest → view + change
    - Showroom     → view + change (own record)
    """
    perms = []
    for model in [Enquiry, ExchangeRequest, Showroom]:
        perms += _get_permissions_for_model(model, actions=('view', 'change'))
    user.user_permissions.set(perms)


def _assign_station_permissions(user):
    """
    Assign permissions a station manager needs:
    - ServiceBooking  → view + change
    - ServiceStation  → view + change (own record)
    """
    perms = []
    for model in [ServiceBooking, ServiceStation]:
        perms += _get_permissions_for_model(model, actions=('view', 'change'))
    user.user_permissions.set(perms)


def _assign_basic_permissions(user):
    """
    Minimum permission so staff user can log into admin
    without being assigned to any location.
    """
    perms = _get_permissions_for_model(Enquiry, actions=('view',))
    user.user_permissions.set(perms)


def _strip_permissions(user):
    """Remove all permissions from a user (used when unassigning a manager)."""
    user.user_permissions.clear()


def _safe_revoke_staff(user):
    """
    Revoke is_staff + clear permissions from a user ONLY if they are
    not managing any other location (showroom or station).
    Prevents accidentally locking out a user who manages multiple entities.
    """
    is_managing_showroom = Showroom.objects.filter(manager=user).exists()
    is_managing_station  = ServiceStation.objects.filter(manager=user).exists()
    if not is_managing_showroom and not is_managing_station:
        user.is_staff = False
        _strip_permissions(user)
        user.save()


# ── manage users (HTML page — superadmin only) ────────────────────────────────

@superadmin_required
def manage_users(request):
    showrooms = Showroom.objects.select_related('manager').all()
    stations  = ServiceStation.objects.select_related('manager').all()
    all_staff = User.objects.filter(is_staff=True, is_superuser=False)

    return render(request, 'admin/manage_users.html', {
        'showrooms': showrooms,
        'stations':  stations,
        'all_staff': all_staff,
        'title':     'Manage Users',
    })


# ── create manager ────────────────────────────────────────────────────────────

@superadmin_required
@require_POST
def create_manager(request):
    username    = request.POST.get('username', '').strip()
    password    = request.POST.get('password', '').strip()
    entity_type = request.POST.get('entity_type')
    entity_id   = request.POST.get('entity_id')

    # ── validate inputs ───────────────────────────────────────────────────────
    if not username or not password:
        messages.error(request, 'Username and password are required.')
        return redirect('admin_manage_users')

    if User.objects.filter(username=username).exists():
        messages.error(request, f'Username "{username}" already exists.')
        return redirect('admin_manage_users')

    # ── create user ───────────────────────────────────────────────────────────
    user = User.objects.create_user(
        username=username,
        password=password,
        is_staff=True,
        is_superuser=False,
    )

    # ── assign to showroom ────────────────────────────────────────────────────
    if entity_type == 'showroom' and entity_id:
        showroom = get_object_or_404(Showroom, pk=entity_id)

        # safely revoke old manager only if not managing anything else
        if showroom.manager:
            _safe_revoke_staff(showroom.manager)

        showroom.manager = user
        showroom.save()

        # give showroom manager permissions so admin login works
        _assign_showroom_permissions(user)

        messages.success(
            request,
            f'User "{username}" created and assigned to showroom "{showroom.name}".'
        )

    # ── assign to station ─────────────────────────────────────────────────────
    elif entity_type == 'station' and entity_id:
        station = get_object_or_404(ServiceStation, pk=entity_id)

        # safely revoke old manager only if not managing anything else
        if station.manager:
            _safe_revoke_staff(station.manager)

        station.manager = user
        station.save()

        # give station manager permissions so admin login works
        _assign_station_permissions(user)

        messages.success(
            request,
            f'User "{username}" created and assigned to station "{station.name}".'
        )

    # ── no entity — still give basic permission to log in ─────────────────────
    else:
        _assign_basic_permissions(user)
        messages.success(
            request,
            f'User "{username}" created as staff (no location assigned).'
        )

    return redirect('admin_manage_users')


# ── delete manager ────────────────────────────────────────────────────────────

@superadmin_required
@require_POST
def delete_manager(request, user_id):
    user     = get_object_or_404(User, pk=user_id, is_superuser=False)
    username = user.username
    user.delete()   # cascade removes permissions and location FK automatically
    messages.success(request, f'User "{username}" deleted.')
    return redirect('admin_manage_users')


# ── reset password ────────────────────────────────────────────────────────────

@superadmin_required
@require_POST
def reset_password(request, user_id):
    user     = get_object_or_404(User, pk=user_id, is_superuser=False)
    password = request.POST.get('password', '').strip()
    if not password:
        messages.error(request, 'Password cannot be empty.')
    else:
        user.set_password(password)
        user.save()
        messages.success(request, f'Password reset for "{user.username}".')
    return redirect('admin_manage_users')