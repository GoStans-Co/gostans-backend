import hashlib
import hmac
import requests
import random
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    
    check_hash = data.pop('hash', '')
    sorted_data = sorted([f"{k}={v}" for k, v in data.items()])
    data_check_string = '\n'.join(sorted_data)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac_hash == check_hash

def verify_facebook_token(access_token):
    
    user_info_url = f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={access_token}"
    response = requests.get(user_info_url)
    
    if response.status_code != 200:
        return None

    return response.json()


def generate_otp():
    return random.randint(100000, 999999)

def send_otp_email(email, otp,name="User"):
    subject = "Your Password Reset OTP"
    message = f"Use this OTP to reset your password: {otp}"
    from_email = 'Gostans verification <noreply@gostans.com>'
    # html_content = render_to_string("emails/otp_email.html", {"otp": otp})

    # Pass name to the HTML template
    html_content = render_to_string("emails/otp_email_card.html", {
        "otp": otp,
        "userName": name
    })

    text_content = f"Use this OTP to reset your password: {otp}"
    email = EmailMultiAlternatives(subject, text_content, from_email, [email])
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_verification_email(user):
    from_email = 'Gostans  <noreply@gostans.com>'
    """
    Sends an email verification link to the newly registered user.
    """
    verification_link = f"https://api.gostans.com/api/v1/auth/verify-email/?token={user.email_verification_token}"
    subject = "Welcome to Gostans! Verify your email"
    html_content = render_to_string("emails/verify_email.html", {
        "userName": user.name or "User",
        "verification_link": verification_link
    })
    text_content = f"Hi {user.name}, please verify your email by visiting {verification_link}"

    email_message = EmailMultiAlternatives(subject, text_content, from_email, [user.email])
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()


def send_welcome_email(user):
    from_email = 'Gostans  <noreply@gostans.com>'
    """
    Sends a welcome email after successful registration (optional).
    """
    subject = "Welcome to Gostans 🎉"
    html_content = render_to_string("emails/welcome_email.html", {
        "userName": user.name or "User",
    })
    text_content = f"Hi {user.name}, welcome to Gostans!"

    email_message = EmailMultiAlternatives(subject, text_content, from_email, [user.email])
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()
