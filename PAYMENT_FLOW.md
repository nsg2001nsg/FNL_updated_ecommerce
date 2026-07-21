# F&L Payment Flow & Transaction Safety Architecture

This document describes the hardened payment gateway architecture implemented in Phase 8 to ensure zero data loss, exact inventory sync, and resilience against race conditions during checkout.

## Request Flow

1. **User Checkout (Frontend)**
   - The user selects "ONLINE PAYMENT" on the checkout page.
   - The backend `checkout` view renders with a pre-created Razorpay `order_id` (created via `payment_service.py`).
   - The user completes payment in the Razorpay popup.
   - Razorpay returns `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature` to the frontend via JS, which submits them to the backend `checkout` view via POST.

2. **Backend Orchestration (`views.checkout`)**
   - The view extracts the Gateway identifiers.
   - It calls `payment_service.verify_payment(...)`.
     - **If Verification Fails**: The view rejects the request immediately, throwing an error and rendering `payment_failed.html`. No `Payment` record is created, and the `Cart` is untouched.
     - **If Verification Succeeds**: The view delegates the complex orchestration to `services.process_checkout`.

3. **Transaction Safety Layer (`services.process_checkout`)**
   - The transaction enters a rigid `with transaction.atomic():` block to guarantee database consistency.
   - **Step 1: Idempotency Check.** The system queries `Payment.objects.select_for_update().filter(gateway_payment_id=...)`. If this exact payment ID has already been processed, it safely returns the existing `Order` to prevent duplicate processing on webhook/callback races.
   - **Step 2: Order Creation.** An `Order` record is instantiated with `status='PAID'`.
   - **Step 3: Payment Record Creation.** A `Payment` record is created and linked one-to-one with the `Order`. The `Payment` has `status='SUCCESS'` and strict `gateway_payment_id` unique constraints.
   - **Step 4: Inventory Locking & Deduction.** The cart items are iterated. For each item:
     - The product is fetched via `Product.objects.select_for_update()`. This creates a row-level database lock.
     - If `product.prod_stock < item.quantity`, an `InsufficientStockException` is raised.
     - Otherwise, the stock is reduced and saved.
   - **Step 5: Cart Cleared.** The user's cart is deleted.
   - **Step 6: Commit.** The atomic block completes, releasing locks and persisting changes.

## Rollback Behavior

If `InsufficientStockException` is raised during Step 4:
- The entire `transaction.atomic()` block is **rolled back**.
- The `Order` creation, `Payment` creation, and `Cart` clearance are all reverted.
- The exception bubbles up to `views.checkout`.
- **Note on Failed Payments:** Currently, because `Payment` strictly requires an `Order` (OneToOne Primary Key), a failed business transaction completely scrubs the Order/Payment pair. *In future iterations, making Payment independent of Order will allow us to store a FAILED Payment record while rolling back the Order.*

## Security & Best Practices Decisions

- **Why `select_for_update()`?**
  Without row-locking, two users buying the last item at the exact same millisecond could both bypass the `if stock > 0` check. Row-locking ensures the second user's database query blocks until the first user's transaction is committed, properly throwing an out-of-stock error for the loser of the race.
- **Why Verify Outside the Transaction?**
  Signature verification involves cryptographic hashing. Moving it before `transaction.atomic()` ensures we don't hold critical database locks (like the user's Cart) while computing hashes or potentially making future network calls.
- **Why is there no `amount` from the Frontend?**
  The frontend `amount` is entirely ignored by the POST handler. `cart.cart_total + 49` is always recalculated fresh from the database before order creation.

## Future Improvements

- **Webhook reconciliation**: Implement async listening on `/payment/webhook/` to mark orders paid even if the user closes their browser before the frontend callback.
- **Automatic refunds**: If an order rolls back due to insufficient stock but the payment was already captured by Razorpay, automatically fire an API request to refund the user.
- **Retry queue**: For failed webhooks or intermittent database errors.
- **Email receipts**: Attach PDF invoices to the payment success email.
- **Inventory reservation timeout**: Lock stock for 15 minutes when the user opens the Razorpay popup, releasing it if they don't pay.
- **Payment expiry**: Expire the Razorpay order ID after a certain timeframe.
- **Coupon support**: Support applying discount codes safely during the `process_checkout` calculation step.
- **Multi-gateway support**: Add a second gateway (e.g., Stripe or PayPal) alongside Razorpay, utilizing the generic `payment_service` design.

> [!TODO]
> Production systems supporting fractional currencies should eventually migrate all monetary fields (like `product.price` and `Order.order_total`) from `IntegerField` to `DecimalField`. This was omitted in Phase 8 to minimize database migration risk on legacy data.
