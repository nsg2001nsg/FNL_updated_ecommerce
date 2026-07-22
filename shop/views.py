from django.core.paginator import Paginator
from django.db.models import Q
from nltk.stem import SnowballStemmer
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from FL import settings
from .models import *
from .forms import AddressForm, SignupForm, SigninForm
from .services import process_checkout, EmptyCartException, InsufficientStockException
from .auth_services import generate_and_send_otp, verify_otp_and_create_customer, OTPVerificationFailed, CustomerCreationError
from .payment_service import create_payment_order, verify_payment
import logging

logger = logging.getLogger(__name__)
from django.conf import settings


# Create your views here.


def menu(request, myid):
    category = SubCategory.objects.filter(subcategory_id=myid).first()
    if category:
        categor = 0
        cat = category
    else:
        categor = get_object_or_404(Category, category_id=myid)
        category = 0
        cat = categor
    prods = Product.objects.filter(Q(subcategory_id=category) | Q(category_id=categor)).order_by('id')
    
    paginator = Paginator(prods, settings.PRODUCTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "menu.html", {'prods': page_obj, 'cat': cat})


def cat_gen(cat_list):
    for i in cat_list:
        yield i


def Bag(request):
    return render(request, "Bag.html", {"customer": request.user})


def index(request):
    bestseller = Product.objects.all().order_by('-id')[:12]
    param = {'bestseller': bestseller}
    if request.user.is_authenticated:
        wishlisted_ids = wishItems.objects.filter(wishlist__customer=request.user).values_list('prod_id', flat=True)
        param['wishlisted_ids'] = set(wishlisted_ids)
    return render(request, "index.html", param)


def search(request):
    customer = request.user
    query = request.GET.get('query', '')
    
    # Search normalization: trim, lowercase, collapse multiple spaces
    query = ' '.join(query.strip().lower().split())
    
    # 4. Empty search handling
    if not query:
        param = {'prods': [], 'query': '', 'empty_query': True}
        if request.user.is_authenticated:
            wishlisted_ids = wishItems.objects.filter(wishlist__customer=request.user).values_list('prod_id', flat=True)
            param['wishlisted_ids'] = set(wishlisted_ids)
        return render(request, "search.html", param)

    keywords = query.split()
    
    # 1. Exact match
    prods = Product.objects.filter(prod_name__iexact=query)
    
    # 2. Partial match (all keywords must be in product name)
    if not prods.exists():
        q_name = Q()
        for k in keywords:
            q_name &= Q(prod_name__icontains=k)
        prods = Product.objects.filter(q_name).order_by('id')
        
    # 3. Matching SubCategory
    if not prods.exists():
        q_subcat = Q()
        for k in keywords:
            q_subcat &= Q(subcategory_id__subcategory_name__icontains=k)
        prods = Product.objects.filter(q_subcat).order_by('id')
        
    # 4. Matching Category
    if not prods.exists():
        q_cat = Q()
        for k in keywords:
            q_cat &= Q(category_id__category_name__icontains=k)
        prods = Product.objects.filter(q_cat).order_by('id')
        
    # 5. Matching Section
    if not prods.exists():
        q_sec = Q()
        for k in keywords:
            q_sec &= Q(section_id__section_name__icontains=k)
        prods = Product.objects.filter(q_sec).order_by('id')
        
    # If still no results, it will gracefully fall through and return an empty queryset.
    
    paginator = Paginator(prods, settings.PRODUCTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    param = {'prods': page_obj, 'query': query}
    if request.user.is_authenticated:
        wishlisted_ids = wishItems.objects.filter(wishlist__customer=request.user).values_list('prod_id', flat=True)
        param['wishlisted_ids'] = set(wishlisted_ids)

    return render(request, "search.html", param)


def prodview(request, myid):
    prod = get_object_or_404(Product, id=myid)
    params = {'prod': prod}
    if request.user.is_authenticated:
        customer = request.user
        cart_obj = Cart.objects.get(customer=customer)
        cart_items = cart_obj.items.all()
        wish_obj = Wishlist.objects.get(customer=customer)
        wish_items = wish_obj.items.all()
        for item in cart_items:
            if item.prod.id == myid:
                is_present = True
                params.update({'is_present': is_present})
            else:
                is_present = False
                params.update({'is_present': is_present})
        for item in wish_items:
            if item.prod.id == myid:
                w_present = True
                params.update({'w_present': w_present})
            else:
                w_present = False
                params.update({'w_present': w_present})
    return render(request, "prodview.html", params)


@login_required(login_url="/signup/")
def wishlist(request):
    return render(request, "wishlist.html")


@login_required(login_url="/signup/")
def address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            ship = form.save(commit=False)
            ship.customer = request.user
            ship.save()
            if form.cleaned_data.get('default_address'):
                customer = Customer.objects.get(email=str(request.user))
                customer.default_ship = ship
                customer.save()
            return redirect("address")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("address")
    else:
        customer = Customer.objects.get(email=str(request.user))
        address_list = customer.address.all()
        cart_obj = Cart.objects.prefetch_related('items__prod').get(customer=customer)
        if address_list.exists():
            return render(request, "address.html", {'ADDRESS': address_list, 'customer': customer, 'tot': cart_obj.cart_total+49})
        return render(request, "address.html")


def signup(request):
    if request.method == 'POST':
        logger.info("Signup request received")
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                profile = generate_and_send_otp(email, password)
                messages.success(request, "We have sent you the OTP to your email address!")
                context = {'customer': profile}
                return render(request, 'verify.html', context)
            except CustomerCreationError as e:
                messages.error(request, str(e))
                return redirect('index')
            except Exception as e:
                messages.error(request, "An error occurred while sending the OTP. Please try again.")
                return redirect('signup')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect('index')

    return render(request, 'signup.html')


def signin(request):
    if request.method == "POST":
        form = SigninForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"Business Event: Successful login for {user.email}")
            messages.success(request, "Logged in succesfully")
            return redirect('index')
        else:
            logger.warning(f"Business Event: Failed login attempt for {request.POST.get('email')}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("signin")

    return render(request, "signin.html")


def signout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')


def verify(request):
    if request.method == "POST":
        email = request.POST.get('email')
        submitted_otp = request.POST.get('otpx')
        
        try:
            customer = verify_otp_and_create_customer(email, submitted_otp)
            
            messages.success(request, "Your account was successfully created. Login now!")
            return redirect("signin")
            
        except OTPVerificationFailed as e:
            messages.error(request, str(e))
            return redirect("signup")
            
        except CustomerCreationError as e:
            messages.error(request, str(e))
            return redirect("index")
    else:
        return redirect('index')


def add_to_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == 'POST':
        customer = request.user
        cart_obj = get_object_or_404(Cart, customer=customer)
        product_id = request.POST.get('product_id')
        prod = get_object_or_404(Product, id=product_id)
        # add the product to the cart
        cart_item = CartItem.objects.create(cart=cart_obj, prod=prod)
        cart_item.save()
        return JsonResponse({'success': True})


def add_to_wish(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == 'POST':
        customer = request.user
        wish_obj = get_object_or_404(Wishlist, customer=customer)
        product_id = request.POST.get('product_id')
        prod = get_object_or_404(Product, id=product_id)
        # add the product to the cart
        wish_item = wishItems.objects.create(wishlist=wish_obj, prod=prod)
        wish_item.save()
        return JsonResponse({'success': True})


def update_item(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == 'POST':
        cart_obj = get_object_or_404(Cart, customer=request.user)
        qty = request.POST.get('new_qty')
        prod = request.POST.get('product_id')
        cart_item = get_object_or_404(CartItem, cart=cart_obj, prod_id=prod)
        cart_item.quantity = qty
        cart_item.save()
        return JsonResponse({'success': True})


def cancel_order_item(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == 'POST':
        prod = get_object_or_404(Product, id=request.POST.get('cancel_item'))
        order_obj = get_object_or_404(Order, order_id=request.POST.get('order_id'), customer=request.user)
        item_obj = get_object_or_404(OrderItem, order_id=order_obj, prod=prod)
        track_item = get_object_or_404(Track, track_id=item_obj.track_id.track_id)
        track_item.status = 'cancelled'
        track_item.item_code = 0
        track_item.save()
        item_obj.save()
        return redirect("orders")


def empty_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    cart = Cart.objects.get(customer=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_items.delete()
    return redirect("Bag")


def remove_item(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == "POST":
        cart_obj = get_object_or_404(Cart, customer=request.user)
        prod = request.POST.get('product_id')
        cart_item = get_object_or_404(CartItem, cart=cart_obj, prod_id=prod)
        cart_item.delete()
        return JsonResponse({'success': True})


def del_wish(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == "POST":
        wish_obj = get_object_or_404(Wishlist, customer=request.user)
        wish_item = get_object_or_404(wishItems, wishlist=wish_obj, id=request.POST.get('del_item'))
        wish_item.delete()
        return redirect("wishlist")


def remove_address(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    if request.method == "POST":
        address_id = request.POST.get('address_id')
        address_obj = get_object_or_404(Address, customer=request.user, id=address_id)
        address_obj.delete()
        return JsonResponse({'success': True})


from django.views.decorators.cache import never_cache

@login_required(login_url="/signup/")
@never_cache
def checkout(request):
    customer = request.user
    cart_obj = Cart.objects.prefetch_related('items__prod').get(customer=customer)
    amt = cart_obj.cart_total + 49
    inr = 100
    ship = Address.objects.get(customer=customer)
    
    if request.method == 'POST':
        meth = request.POST.get('payment')
        is_online_payment = True if meth != "cash" else False
        
        rzp_order_id = None
        rzp_payment_id = None
        rzp_signature = None
        
        if is_online_payment:
            rzp_payment_id = request.POST.get('razorpay_payment_id')
            rzp_order_id = request.POST.get('razorpay_order_id')
            rzp_signature = request.POST.get('razorpay_signature')
            
            if not all([rzp_payment_id, rzp_order_id, rzp_signature]):
                messages.error(request, "Payment details missing. Please try again.")
                return redirect('checkout')
                
            is_valid = verify_payment(rzp_payment_id, rzp_order_id, rzp_signature)
            if not is_valid:
                messages.error(request, "Payment verification failed. Please contact support.")
                return redirect('payment_failed')
        
        try:
            order = process_checkout(customer, cart_obj, is_online_payment, rzp_order_id, rzp_payment_id, rzp_signature)
            request.session['last_order_id'] = order.order_id
            request.session['last_payment_id'] = rzp_payment_id or 'COD'
            return redirect('payment_success')
        except EmptyCartException as e:
            messages.error(request, str(e))
            return redirect('Bag')
        except InsufficientStockException as e:
            messages.error(request, "Some items in your cart went out of stock. Please review your cart.")
            return redirect('Bag')
        except Exception as e:
            logger.error(f"Unexpected error in checkout: {str(e)}")
            messages.error(request, "An unexpected error occurred during checkout.")
            return redirect('payment_failed')
    else:
        try:
            razorpay_order_id = create_payment_order(amt)
        except Exception as e:
            razorpay_order_id = None

        return render(request, 'checkout.html', {
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order_id,
            'amt': amt * inr, 
            'ship': ship
        })


def catalogue(request, query):
    if query == 'fashion':
        return render(request, 'catalogue.html', {'name': 'fashion'})

    elif query == 'beauty':
        return render(request, 'catalogue.html', {'name': 'beauty'})

    elif query == 'lifestyle':
        return render(request, 'catalogue.html', {'name': 'lifestyle'})


@login_required(login_url="/signup/")
def payment_success(request):
    order_id = request.session.get('last_order_id')
    payment_id = request.session.get('last_payment_id')
    try:
        order = Order.objects.get(order_id=order_id, customer=request.user)
    except Order.DoesNotExist:
        return redirect('index')

    customer = Customer.objects.get(email=request.user)
    email = customer.email
    name = customer.default_ship.name if customer.default_ship else "Customer"
    subject = "F&L- Order Placed Successfully!"
    message = "Hello \n" + name + "! Your order is confirmed! Head back to F&L to track your order or for order cancellation"
    from_email = settings.EMAIL_HOST_USER
    to_list = [email]
    try:
        send_mail(subject, message, from_email, to_list, fail_silently=False)
    except Exception as e:
        logger.exception("Failed to send order confirmation email")
        
    return render(request, 'payment_success.html', {
        'name': name,
        'order': order,
        'payment_id': payment_id
    })

@login_required(login_url="/signup/")
def payment_failed(request):
    return render(request, 'payment_failed.html')

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from .payment_service import get_razorpay_client

@csrf_exempt
def payment_webhook(request):
    if request.method == 'POST':
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_body = request.body.decode('utf-8')
        
        try:
            client = get_razorpay_client()
            webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', settings.RAZORPAY_KEY_SECRET)
            client.utility.verify_webhook_signature(webhook_body, webhook_signature, webhook_secret)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return HttpResponse(status=400)
            
        try:
            payload = json.loads(webhook_body)
            event = payload.get('event')
            
            if event == 'payment.captured':
                payment_entity = payload['payload']['payment']['entity']
                rzp_payment_id = payment_entity.get('id')
                
                if rzp_payment_id:
                    payment = Payment.objects.filter(gateway_payment_id=rzp_payment_id).first()
                    if payment and payment.status != 'SUCCESS':
                        payment.status = 'SUCCESS'
                        payment.save()
                        if payment.payment_against:
                            payment.payment_against.status = 'PAID'
                            payment.payment_against.save()
                        logger.info(f"Webhook: Payment {rzp_payment_id} captured successfully.")
                        
            return HttpResponse(status=200)
        except Exception as e:
            logger.exception("Error processing webhook")
            return HttpResponse(status=500)
            
    return HttpResponse(status=200)


@login_required(login_url="/signup/")
def orders(request):
    order_obj = Order.objects.filter(customer=request.user).prefetch_related('order_items__prod')
    customer = Customer.objects.get(email=str(request.user))
    return render(request, "orders.html", {'ORDER': order_obj, 'customer': customer})