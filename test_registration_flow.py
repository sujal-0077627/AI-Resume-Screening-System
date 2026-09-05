"""Test end-to-end registration flow and OTP verification."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'screening.settings')
django.setup()

from django.test import Client
from core.models import User

def test_registration():
    client = Client()

    # Clean up test user if exists
    User.objects.filter(username='testreguser').delete()
    User.objects.filter(email='testreg@example.com').delete()

    print("1. Submitting Registration Form...")
    response = client.post('/register/', {
        'username': 'testreguser',
        'email': 'testreg@example.com',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
    })

    print(f"   Registration status: {response.status_code}, redirect: {getattr(response, 'url', None)}")
    assert response.status_code == 302, f"Expected 302 redirect, got {response.status_code}"
    assert response.url == '/verify-otp/', f"Expected redirect to /verify-otp/, got {response.url}"

    user = User.objects.get(username='testreguser')
    assert not user.is_verified, "User should initially be unverified"
    print(f"   User created in DB successfully. ID: {user.id}, is_verified: {user.is_verified}")

    print("2. Viewing /verify-otp/ page...")
    get_res = client.get('/verify-otp/')
    assert get_res.status_code == 200, f"Expected 200, got {get_res.status_code}"
    demo_otp = client.session.get('demo_otp')
    print(f"   Session demo_otp: {demo_otp}")

    # If SMTP was configured and sent email, demo_otp is None, so let's get OTP from user model for verification
    test_otp = demo_otp
    if not test_otp:
        # In test with real SMTP, retrieve otp from raw token or generate another test
        print("   (Email was sent via configured SMTP!)")
        # Let's verify by testing verify_otp directly with user.set_otp
        test_otp = "123456"
        user.set_otp(test_otp)
        user.save()

    print("3. Submitting invalid OTP...")
    bad_res = client.post('/verify-otp/', {'otp': '000000'})
    assert bad_res.status_code == 200
    user.refresh_from_db()
    assert not user.is_verified

    print("4. Submitting valid OTP...")
    good_res = client.post('/verify-otp/', {'otp': test_otp})
    assert good_res.status_code == 302 and good_res.url == '/login/', f"Expected redirect to /login/, got {good_res.url}"
    user.refresh_from_db()
    assert user.is_verified, "User should now be verified!"
    print(f"   User successfully verified! is_verified: {user.is_verified}")

    print("5. Logging in with newly registered user...")
    login_res = client.post('/login/', {
        'username': 'testreguser',
        'password': 'Password123!',
    })
    assert login_res.status_code == 302 and login_res.url == '/dashboard/', "Login should succeed for newly registered user"
    print("   Login succeeded! Redirected to /dashboard/")

    print("6. Testing re-registration cleanup of unverified accounts...")
    # Create another unverified user
    User.objects.filter(username='unverified_user').delete()
    unv_client = Client()
    unv_client.post('/register/', {
        'username': 'unverified_user',
        'email': 'unv@example.com',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
    })
    # Re-register with the same info before verifying
    re_res = unv_client.post('/register/', {
        'username': 'unverified_user',
        'email': 'unv@example.com',
        'password': 'NewPassword123!',
        'confirm_password': 'NewPassword123!',
    })
    assert re_res.status_code == 302 and re_res.url == '/verify-otp/', "Re-registration of unverified account should succeed"
    print("   Unverified account re-registration passed cleanly!")

    print("7. Testing Demo Mode (No SMTP configured)...")
    from unittest.mock import patch
    with patch('core.views.send_otp_email', return_value=False):
        User.objects.filter(username='demouser').delete()
        demo_client = Client()
        d_res = demo_client.post('/register/', {
            'username': 'demouser',
            'email': 'demouser@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })
        assert d_res.status_code == 302 and d_res.url == '/verify-otp/'
        # Check that demo_otp is stored in session and rendered in HTML
        v_res = demo_client.get('/verify-otp/')
        assert v_res.status_code == 200
        d_otp = demo_client.session.get('demo_otp')
        assert d_otp is not None, "demo_otp should be in session"
        assert str(d_otp).encode() in v_res.content, "demo_otp should be visible on verify_otp page"
        # Verify using demo_otp
        verify_res = demo_client.post('/verify-otp/', {'otp': d_otp})
        assert verify_res.status_code == 302 and verify_res.url == '/login/'
        assert User.objects.get(username='demouser').is_verified, "Demo user should be verified"
        print("   Demo mode OTP display and verification passed cleanly!")

    # Clean up
    User.objects.filter(username='testreguser').delete()
    User.objects.filter(username='unverified_user').delete()
    User.objects.filter(username='demouser').delete()

    print("\nALL REGISTRATION TESTS PASSED PERFECTLY [OK]")

if __name__ == '__main__':
    test_registration()
