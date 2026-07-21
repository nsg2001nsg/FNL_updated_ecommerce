from django.db import transaction
from .models import Order, Payment, OrderItem, Track, CartItem, Cart, product
import logging

logger = logging.getLogger(__name__)

class EmptyCartException(Exception):
    pass

class InsufficientStockException(Exception):
    pass

def process_checkout(customer, cart_obj, is_online_payment, rzp_order_id=None, rzp_payment_id=None, rzp_signature=None):
    """
    Creates an Order, Payment, OrderItems, and Tracking records based on the Cart.
    Ensures safe stock deduction and idempotency using select_for_update row-locks.
    Wraps all operations in an atomic transaction.
    """
    if not cart_obj.items.exists():
        raise EmptyCartException("Cannot create an order from an empty cart.")

    cart_total = cart_obj.cart_total
    total_amount = cart_total + 49

    try:
        with transaction.atomic():
            # 1. Lock the Cart to prevent race conditions from duplicate tabs
            # We fetch it fresh to ensure we lock it properly
            cart = Cart.objects.select_for_update().get(customer=customer)
            
            # Re-check empty cart after lock
            if not cart.items.exists():
                raise EmptyCartException("Cannot create an order from an empty cart.")
            
            # 2. Check Idempotency. If Payment exists with gateway_payment_id, return existing Order.
            if is_online_payment and rzp_payment_id:
                existing_payment = Payment.objects.select_for_update().filter(gateway_payment_id=rzp_payment_id).first()
                if existing_payment:
                    logger.info(f"Payment Duplicate: Payment {rzp_payment_id} already processed. Returning existing order.")
                    return existing_payment.payment_against

            # 3. Create Order
            order_obj = Order.objects.create(
                customer=customer,
                order_total=cart.cart_total,
                order_quantity=cart.total_item,
                status='PAID' if is_online_payment else 'PENDING_PAYMENT'
            )
            
            # 4. Create the payment record as SUCCESS (or PENDING if COD)
            payment = Payment.objects.create(
                payment_against=order_obj,
                customer=customer,
                payment_gateway='RAZORPAY' if is_online_payment else 'CASH_ON_DELIVERY',
                gateway_order_id=rzp_order_id,
                gateway_payment_id=rzp_payment_id,
                gateway_signature=rzp_signature,
                status='SUCCESS' if is_online_payment else 'PENDING',
                amount=total_amount,
                currency='INR'
            )

            # 5. Lock Inventory & Reduce Stock
            for item in cart.items.all():
                # Lock product row
                prod = product.objects.select_for_update().get(id=item.prod_id)
                if prod.prod_stock < item.quantity:
                    logger.warning(f"Stock Update Failed: Insufficient stock for {prod.prod_name}.")
                    raise InsufficientStockException(f"Insufficient stock for {prod.prod_name}")
                
                # Reduce stock
                prod.prod_stock -= item.quantity
                prod.save()
                logger.info(f"Stock Updated: {prod.prod_name} reduced by {item.quantity}. Remaining: {prod.prod_stock}")

                track_item = Track.objects.create()
                OrderItem.objects.create(
                    order_id=order_obj,
                    prod=prod,
                    quantity=item.quantity,
                    track_id=track_item
                )
            
            # 6. Clear Cart
            cart.items.all().delete()
            logger.info(f"Order Created: Order {order_obj.order_id} successfully created.")
            
            return order_obj

    except InsufficientStockException:
        # If it rolls back due to stock, and it was an online payment that succeeded,
        # we create a FAILED payment record outside the transaction.
        if is_online_payment and rzp_payment_id:
            logger.warning(f"Rollback: Creating FAILED payment record for {rzp_payment_id} due to stock out.")
            Payment.objects.create(
                customer=customer,
                payment_gateway='RAZORPAY',
                gateway_order_id=rzp_order_id,
                gateway_payment_id=rzp_payment_id,
                gateway_signature=rzp_signature,
                status='FAILED',
                amount=total_amount,
                currency='INR'
            )
        raise
