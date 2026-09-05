"""Quick smoke test for the modern auth login flow."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'screening.settings')
django.setup()

from django.test import Client
from core.models import User


def main():
    # Create a verified demo user
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={'email': 'demo@test.com', 'full_name': 'Demo User', 'is_verified': True},
    )
    if created:
        user.set_password('Passw0rd!')
        user.save()
    else:
        user.email = 'demo@test.com'
        user.is_verified = True
        user.set_password('Passw0rd!')
        user.save()

    client = Client()

    # 1. Login via EMAIL (as the new design's placeholder suggests)
    r = client.post('/login/', {'username': 'demo@test.com', 'password': 'Passw0rd!'})
    print('EMAIL LOGIN:', r.status_code, r.url if r.status_code == 302 else '')
    assert r.status_code == 302 and r.url == '/dashboard/', 'Email login failed'

    # Logout
    client.get('/logout/')

    # 2. Login via USERNAME (the original backend way)
    r2 = client.post('/login/', {'username': 'demo_user', 'password': 'Passw0rd!'})
    print('USERNAME LOGIN:', r2.status_code, r2.url if r2.status_code == 302 else '')
    assert r2.status_code == 302 and r2.url == '/dashboard/', 'Username login failed'

    # 3. Wrong password must fail (logout first so no stale session)
    client.get('/logout/')
    r3 = client.post('/login/', {'username': 'demo_user', 'password': 'wrongpass'})
    print('WRONG PASSWORD -> stays on login page:', r3.status_code)
    assert r3.status_code == 200, 'Wrong password should render login page'

    # 4. Root URL shows login page when logged out
    client.get('/logout/')
    root = client.get('/')
    print('ROOT (logged out) -> login page:', root.status_code)
    assert root.status_code == 200 and b'auth-split' in root.content and b'Welcome back' in root.content, \
        'Root should render the login page when logged out'

    # 5. Dashboard requires auth & lives at /dashboard/
    r4 = client.get('/dashboard/')
    print('UNAUTHENTICATED DASHBOARD -> redirected:', r4.status_code, r4.url if r4.status_code == 302 else '')
    assert r4.status_code == 302 and r4.url == '/login/', 'Dashboard should redirect to login'

    # 6. User hits root -> always gets login page as configured
    client.post('/login/', {'username': 'demo_user', 'password': 'Passw0rd!'})
    root_logged = client.get('/')
    print('ROOT -> login page:', root_logged.status_code)
    assert root_logged.status_code == 200 and b'auth-split' in root_logged.content, 'Root should always render login page'

    print('\nALL AUTH TESTS PASSED [OK]')


if __name__ == '__main__':
    main()