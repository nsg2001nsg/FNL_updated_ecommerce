import secrets
from django.core.mail import send_mail
from django.conf import settings
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
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False
        )
        logger.info("Email successfully sent")
    except Exception as e:
        logger.exception("send_mail failed")
        raise

def generate_and_send_otp(email, password):
    """
    Generates a secure OTP, saves it in a temporary Profile, and sends an email.
    """
    if Customer.objects.filter(email=email).exists():
        raise CustomerCreationError("A user with this email already exists.")

    # Clean up old profile if user requested OTP again
    Profile.objects.filter(email=email).delete()

    # Generate secure 4-digit OTP using secrets
    otp = secrets.randbelow(9000) + 1000  # ensures 1000-9999
    logger.info("OTP generated: %s", otp)

    # Save to temporary profile
    profile = Profile.objects.create(email=email, otp=otp, password=password)
    
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
        
    if str(profile.otp) != str(submitted_otp):
        raise OTPVerificationFailed("Invalid OTP.")
        
    if Customer.objects.filter(email=email).exists():
        profile.delete()
        raise CustomerCreationError("A user with this email already exists.")
        
    # Create the user using the password stored in the temporary profile
    customer = Customer.objects.create_user(email=email, password=profile.password)
    
    # Cleanup
    profile.delete()
    
    return customer
