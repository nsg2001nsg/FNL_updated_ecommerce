from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


# Create your models here.


class AccountManager(BaseUserManager):
    def create_user(self, email, password):
        if not email:
            raise ValueError("User must have an email address")
        user = self.model(
            email=self.normalize_email(email)
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email=email, password=password)
        user.is_staff = True
        user.is_admin = True
        user.is_superuser = True

        user.save(using=self._db)
        return user


class Customer(AbstractBaseUser):
    email = models.EmailField(max_length=40, unique=True, default=None)
    password = models.CharField(max_length=128, blank=False, null=False, default=0)
    default_ship = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_default')
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = AccountManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def __str__(self):
        return self.email


class Profile(models.Model):
    email = models.EmailField(max_length=40, null=False)
    otp = models.PositiveIntegerField(validators=[MaxValueValidator(9999)], null=False)
    password = models.CharField(max_length=128, blank=False, null=False, default=0)

    def __str__(self):
        return self.email


class Section(models.Model):
    section_id = models.CharField(primary_key=True, max_length=1)
    section_name = models.CharField(max_length=20)

    def __str__(self):
        return self.section_name


class Category(models.Model):
    category_id = models.PositiveIntegerField(primary_key=True)
    category_name = models.CharField(max_length=30)
    section_id = models.ForeignKey(Section, default="", on_delete=models.CASCADE)

    def __str__(self):
        return self.category_name


class SubCategory(models.Model):
    subcategory_id = models.PositiveIntegerField(primary_key=True)
    subcategory_name = models.CharField(max_length=30)
    category_id = models.ForeignKey(Category, default=1, on_delete=models.CASCADE)

    def __str__(self):
        return self.subcategory_name


class product(models.Model):
    prod_id = models.AutoField
    prod_name = models.CharField(max_length=50)
    section_id = models.ForeignKey(Section, default="", on_delete=models.CASCADE)
    category_id = models.ForeignKey(Category, default=1, on_delete=models.CASCADE)
    subcategory_id = models.ForeignKey(SubCategory, default=1, on_delete=models.CASCADE)
    prod_desc = models.CharField(max_length=300)
    price = models.IntegerField(default=0)
    pub_date = models.DateField()
    prod_stock = models.IntegerField(default=0)
    image = models.ImageField(upload_to='shop/images', default="")

    @property
    def prod_instock(self):
        if self.prod_stock:
            return True
        else:
            return False

    def __str__(self):
        return self.prod_name


class Track(models.Model):
    track_id = models.AutoField(primary_key=True)
    ITEM_CODE = (
        (1, 'Placed'),
        (0, 'Cancelled'),
        (2, 'Completed'),
    )
    STATUS_CHOICES = (
        ('placed', 'Order Placed'),
        ('packed', 'Packed'),
        ('dispatched', 'Dispatched'),
        ('shipped', 'Shipped'),
        ('in-transit', 'In-Transit'),
        ('out for delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    item_code = models.IntegerField(choices=ITEM_CODE, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='placed')


class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    order_quantity = models.PositiveIntegerField(default=0)
    order_total = models.IntegerField(default=0)
    order_date = models.DateField(auto_now_add=True)
    delivery_status = models.BooleanField(default=False)
    
    STATUS_CHOICES = (
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')

    @property
    def get_ship_details(self):
        return self.customer.default_ship

    @property
    def get_payment_status(self):
        return self.payment_id.status == 'SUCCESS'

    @property
    def delivery_date(self):
        return self.order_date + timedelta(days=7)


class OrderItem(models.Model):
    order_id = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    prod = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    track_id = models.OneToOneField(Track, on_delete=models.CASCADE, null=False)

    @property
    def item_total(self):
        return self.prod.price * self.quantity


class Cart(models.Model):
    customer = models.OneToOneField(Customer, primary_key=True, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer}'s Cart"

    @property
    def cart_total(self):
        total = sum(item.item_total for item in self.items.all())
        return total

    @property
    def total_item(self):
        total = sum(item.quantity for item in self.items.all())
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    prod = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    @property
    def item_total(self):
        return self.quantity * self.prod.price


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="address")
    name = models.CharField(max_length=40, null=False)
    contact = models.PositiveIntegerField(validators=[MinValueValidator(6000000000), MaxValueValidator(9999999999)], null=False)
    ship_to = models.CharField(max_length=150, null=False)
    pincode = models.PositiveIntegerField(validators=[MinValueValidator(100000), MaxValueValidator(999999)])
    city = models.CharField(max_length=30, null=False)
    State = models.CharField(max_length=30, null=False)


class Payment(models.Model):
    PAYMENT_GATEWAY_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
        ('CASH_ON_DELIVERY', 'Cash on Delivery'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    )

    payment_against = models.OneToOneField(Order, on_delete=models.SET_NULL, related_name="payment_id", null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments")
    
    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAY_CHOICES, default='CASH_ON_DELIVERY')
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    gateway_signature = models.CharField(max_length=200, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    amount = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, default='INR')
    
    # We use timezone.now as default or auto_now_add
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['gateway_payment_id']),
            models.Index(fields=['gateway_order_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['customer']),
            models.Index(fields=['payment_against']),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_payment = Payment.objects.get(pk=self.pk)
                if old_payment.status == 'SUCCESS' and self.status in ['PENDING', 'FAILED', 'CANCELLED']:
                    raise ValueError(f"Illegal transition from {old_payment.status} to {self.status}")
                if old_payment.status == 'REFUNDED' and self.status != 'REFUNDED':
                    raise ValueError(f"Illegal transition from {old_payment.status} to {self.status}")
            except Payment.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="wishlist")

    @property
    def total_items(self):
        return self.items.count()

    def __str__(self):
        return f"{self.customer}'s Wishlist"


class wishItems(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    prod = models.ForeignKey(product, on_delete=models.CASCADE)
