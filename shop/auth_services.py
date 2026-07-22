import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from .models import Profile, Customer
import logging

logger = logging.getLogger(__name__)


class OTPVerificationFailed(Exception):
    pass


class CustomerCreationError(Exception):
    pass


def send_otp_email(email, otp):
    """
    Sends the OTP email to the user. Isolated to easily replace with Celery later.
    """
    subject = "Welcome to Shop - F&L login!"
    message = f"Hello!\n{otp} is your OTP to login to F&L\n-F&L"
    logger.info("Calling send_mail()")
    try:
        logger.info(f"EMAIL_HOST={settings.EMAIL_HOST}")
        logger.info(f"EMAIL_PORT={settings.EMAIL_PORT}")
        logger.info(f"EMAIL_USE_TLS={settings.EMAIL_USE_TLS}")
        logger.info(f"EMAIL_USE_SSL={getattr(settings, 'EMAIL_USE_SSL', False)}")
        logger.info(f"EMAIL_HOST_USER={settings.EMAIL_HOST_USER}")
        logger.info(f"DEFAULT_FROM_EMAIL={settings.DEFAULT_FROM_EMAIL}")
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        logger.info("Email successfully sent")
    except Exception as e:
        logger.exception("send_mail failed")
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

    # Save to temporary profile with hashed password
    hashed_password = make_password(password)
    
    if profile:
        profile.otp = otp
        profile.password = hashed_password
        profile.attempts += 1
        profile.save()
    else:
        profile = Profile.objects.create(email=email, otp=otp, password=hashed_password, attempts=1)
    
    # Send email
    send_otp_email(email, otp)
    
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
