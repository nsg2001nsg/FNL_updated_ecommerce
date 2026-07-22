import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from .models import Profile, Customer
import logging
import requests

logger = logging.getLogger(__name__)


class OTPVerificationFailed(Exception):
    pass


class CustomerCreationError(Exception):
    pass


def send_otp_email(email, otp):
    """
    Sends the OTP email to the user via Brevo HTTP API to bypass cloud SMTP blocks.
    """
    subject = "Welcome to Shop - F&L login!"
    message = f"Hello!\n{otp} is your OTP to login to F&L\n-F&L"
    logger.info("Calling Brevo HTTP API for send_otp_email()")
    
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": "F&L Shop", "email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": email}],
        "subject": subject,
        "textContent": message
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=settings.EMAIL_TIMEOUT)
        response.raise_for_status()
        logger.info("Email successfully sent via Brevo HTTP API")
    except Exception as e:
        logger.exception(f"Brevo API failed. HTTP Status Code: {getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A'}")
        raise CustomerCreationError("Failed to send OTP email. Please try again later.")


def generate_and_send_otp(email, password):
    """
    Generates a secure OTP, saves it in a temporary Profile, and sends an email.
    """
    if Customer.objects.filter(email=email).exists():
        raise CustomerCreationError("A user with this email already exists.")

    # Check rate limit and cooldown
    profile = Profile.objects.filter(email=email).first()
    if profile:
        # Block if 5 attempts within the last hour
        if profile.attempts >= 5 and timezone.now() - profile.created_at < timedelta(hours=1):
            logger.warning(f"Rate limit hit for signup: {email}")
            raise CustomerCreationError("Too many signup attempts. Please try again later.")
            
        # Cooldown check: 60 seconds between OTPs
        if timezone.now() - profile.updated_at < timedelta(seconds=60):
            raise CustomerCreationError("Please wait 60 seconds before requesting another OTP.")

    # Generate secure 4-digit OTP using secrets
    otp = secrets.randbelow(9000) + 1000  # ensures 1000-9999
    logger.info(f"OTP generated for {email}")

    # Send email BEFORE saving profile to prevent incrementing attempts on network errors
    send_otp_email(email, otp)
    
    # Save to temporary profile with hashed password ONLY if email succeeds
    hashed_password = make_password(password)
    
    if profile:
        profile.otp = otp
        profile.password = hashed_password
        profile.attempts += 1
        profile.save()
    else:
        profile = Profile.objects.create(email=email, otp=otp, password=hashed_password, attempts=1)
    
    return profile


def verify_otp_and_create_customer(email, submitted_otp):
    """
    Verifies the submitted OTP against the temporary Profile.
    If valid, creates the Customer and cleans up the Profile.
    """
    profile = Profile.objects.filter(email=email).first()
    
    if not profile:
        raise OTPVerificationFailed("No pending signup found for this email.")
        
    # Check Expiry (10 minutes)
    if timezone.now() - profile.updated_at > timedelta(minutes=10):
        profile.delete()
        raise OTPVerificationFailed("OTP has expired. Please request a new one.")
        
    if str(profile.otp) != str(submitted_otp):
        raise OTPVerificationFailed("Invalid OTP.")
        
    if Customer.objects.filter(email=email).exists():
        profile.delete()
        raise CustomerCreationError("A user with this email already exists.")
        
    # Create the user without a password, then manually assign the hashed password
    # This prevents the password from being double-hashed by create_user
    customer = Customer.objects.create_user(email=email, password=None)
    customer.password = profile.password
    customer.save()
    
    # Cleanup
    profile.delete()
    
    logger.info(f"Business Event: Successful signup for {email}")
    return customer
