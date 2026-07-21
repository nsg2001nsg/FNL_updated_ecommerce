import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_razorpay_client():
    """Initialize and return a Razorpay client."""
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_payment_order(amount_inr):
    """
    Create an order on the payment gateway for the given amount (in INR).
    Returns the Gateway Order ID.
    """
    logger.info(f"Payment Started: Creating Razorpay order for {amount_inr} INR")
    client = get_razorpay_client()
    data = {
        "amount": int(amount_inr * 100),
        "currency": "INR",
        "receipt": "receipt_dummy",
        "payment_capture": "1"
    }
    logger.info(f"Razorpay Options: Amount: {data['amount']}, Currency: {data['currency']}, Receipt: {data.get('receipt', 'None')}")
    try:
        payment = client.order.create(data=data)
        logger.info(f"Generated Razorpay order_id: {payment['id']}")
        return payment['id']
    except Exception as e:
        logger.error(f"Payment Failed: Error creating Razorpay order: {str(e)}")
        raise

def verify_payment(payment_id, order_id, signature):
    """
    Verify the payment signature returned by the gateway.
    Returns True if valid, False otherwise.
    """
    logger.info(f"Payment Verification Started: Payment ID {payment_id} for Order ID {order_id}")
    client = get_razorpay_client()
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        logger.info(f"Payment Verified: Signature matches for {payment_id}")
        return True
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Payment Failed: Invalid signature for {payment_id} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Payment Failed: Unexpected error during verification for {payment_id} - {str(e)}")
        return False

def capture_payment(payment_id, amount):
    """
    Stub for future implementation.
    """
    pass

def refund_payment(payment_id, amount):
    """
    Stub for future implementation.
    """
    pass
