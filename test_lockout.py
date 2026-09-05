"""Temp test: verify brute-force lockout in the rewritten login_view."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'screening.settings')
django.setup()

from django.test import Client
from core.models import User


def main():
    user, _ = User.objects.get_or_create(
        username='lock_test',
        defaults={'email': 'lock@test.com', 'is_verified': True},
    )
    user.is_verified = True
    user.set_password('RightPass1!')
    user.save()

    c = Client()  # single client => shared session => lockout state persists
    lock_key = 'login_lock_lock_test'
    locked_at_attempt = None
    msg_shown = False

    for i in range(1, 8):
        r = c.post('/login/', {'username': 'lock_test', 'password': 'totally-wrong'})
        body = r.content.decode('utf-8', errors='replace')
        if 'Account locked' in body:
            msg_shown = True
        if lock_key in c.session:
            locked_at_attempt = i
            break
    print(f'Lock engaged at attempt: {locked_at_attempt}; message shown: {msg_shown}')
    assert locked_at_attempt == 5, f'expected lock at attempt 5, got {locked_at_attempt}'

    # Correct password must be REJECTED while the account is locked
    r2 = c.post('/login/', {'username': 'lock_test', 'password': 'RightPass1!'})
    loc = r2.headers.get('Location', '')
    print('While locked, correct password ->', r2.status_code, loc)
    assert r2.status_code == 200 and '/dashboard' not in loc, 'login should be blocked during lockout'

    # Security fix verification: a fresh session (cleared cookies) must ALSO be blocked
    # because account lockout is tracked in server cache per user/IP.
    c2 = Client()
    r3 = c2.post('/login/', {'username': 'lock_test', 'password': 'RightPass1!'})
    print('Fresh session during lockout ->', r3.status_code, r3.headers.get('Location', ''))
    assert r3.status_code == 200 and '/dashboard' not in r3.headers.get('Location', ''), \
        'fresh session must be blocked during lockout (cookie clearing bypass prevented)'

    # Cleanup cache and user
    from django.core.cache import cache
    cache.delete('login_lock_lock_test')
    cache.delete('login_count_lock_test')
    User.objects.filter(username='lock_test').delete()
    print('\nLOCKOUT TEST PASSED (SERVER CACHE LOCKOUT CONFIRMED)')


if __name__ == '__main__':
    main()
