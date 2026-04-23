from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Showroom, ServiceStation


def superadmin_required(view_func):
    return user_passes_test(
        lambda u: u.is_superuser,
        login_url='/admin/login/'
    )(view_func)


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


@superadmin_required
def create_manager(request):
    if request.method == 'POST':
        username    = request.POST.get('username', '').strip()
        password    = request.POST.get('password', '').strip()
        entity_type = request.POST.get('entity_type')   # 'showroom' or 'station'
        entity_id   = request.POST.get('entity_id')

        # Validate
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('admin:manage_users')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect('admin:manage_users')

        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=True,
            is_superuser=False,
        )

        # Assign to showroom or station
        if entity_type == 'showroom' and entity_id:
            showroom = get_object_or_404(Showroom, pk=entity_id)
            # Remove old manager if any
            if showroom.manager:
                old = showroom.manager
                old.is_staff = False
                old.save()
            showroom.manager = user
            showroom.save()
            messages.success(request, f'User "{username}" created and assigned to showroom "{showroom.name}".')

        elif entity_type == 'station' and entity_id:
            station = get_object_or_404(ServiceStation, pk=entity_id)
            if station.manager:
                old = station.manager
                old.is_staff = False
                old.save()
            station.manager = user
            station.save()
            messages.success(request, f'User "{username}" created and assigned to station "{station.name}".')
        else:
            messages.success(request, f'User "{username}" created as staff (no location assigned).')

    return redirect('admin_manage_users')


@superadmin_required
def delete_manager(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id, is_superuser=False)
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted.')
    return redirect('admin_manage_users')


@superadmin_required
def reset_password(request, user_id):
    if request.method == 'POST':
        user     = get_object_or_404(User, pk=user_id, is_superuser=False)
        password = request.POST.get('password', '').strip()
        if not password:
            messages.error(request, 'Password cannot be empty.')
        else:
            user.set_password(password)
            user.save()
            messages.success(request, f'Password reset for "{user.username}".')
    return redirect('admin_manage_users')