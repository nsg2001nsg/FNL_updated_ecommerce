from django.contrib import admin

# Register your models here.

from .models import *

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'is_admin', 'date_joined')
    list_filter = ('is_active', 'is_admin')
    search_fields = ('email',)
    ordering = ('-date_joined',)
    list_per_page = 50

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'city', 'State', 'pincode', 'contact')
    list_filter = ('State', 'city')
    search_fields = ('name', 'customer__email', 'city', 'pincode')
    autocomplete_fields = ('customer',)
    list_select_related = ('customer',)
    list_per_page = 50

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('section_id', 'section_name')
    search_fields = ('section_name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'section_id')
    list_filter = ('section_id',)
    search_fields = ('category_name',)
    list_select_related = ('section_id',)

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('subcategory_id', 'subcategory_name', 'category_id')
    list_filter = ('category_id',)
    search_fields = ('subcategory_name',)
    list_select_related = ('category_id',)
    autocomplete_fields = ('category_id',)

@admin.register(product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('prod_name', 'category_id', 'price', 'prod_stock', 'pub_date')
    list_filter = ('category_id', 'subcategory_id', 'section_id')
    search_fields = ('prod_name', 'prod_desc')
    autocomplete_fields = ('category_id', 'subcategory_id', 'section_id')
    list_select_related = ('category_id', 'subcategory_id', 'section_id')
    ordering = ('-pub_date',)
    list_per_page = 50

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'customer', 'order_quantity', 'order_total', 'order_date', 'delivery_status')
    list_filter = ('delivery_status', 'order_date')
    search_fields = ('order_id', 'customer__email')
    autocomplete_fields = ('customer',)
    list_select_related = ('customer',)
    readonly_fields = ('order_date',)
    ordering = ('-order_date',)
    list_per_page = 50

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'prod', 'quantity')
    search_fields = ('order_id__order_id', 'prod__prod_name')
    autocomplete_fields = ('order_id', 'prod')
    list_select_related = ('order_id', 'prod')

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('track_id', 'status', 'item_code')
    list_filter = ('status', 'item_code')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_against', 'customer', 'status', 'payment_gateway', 'amount', 'created_at')
    list_filter = ('status', 'payment_gateway')
    search_fields = ('payment_against__order_id', 'customer__email')
    autocomplete_fields = ('payment_against', 'customer')
    list_select_related = ('payment_against', 'customer')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'created_at', 'updated_at')
    search_fields = ('customer__email',)
    autocomplete_fields = ('customer',)
    list_select_related = ('customer',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'prod', 'quantity')
    search_fields = ('cart__customer__email', 'prod__prod_name')
    autocomplete_fields = ('cart', 'prod')
    list_select_related = ('cart', 'prod')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('customer',)
    search_fields = ('customer__email',)
    autocomplete_fields = ('customer',)
    list_select_related = ('customer',)

@admin.register(wishItems)
class WishItemsAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'prod')
    search_fields = ('wishlist__customer__email', 'prod__prod_name')
    autocomplete_fields = ('wishlist', 'prod')
    list_select_related = ('wishlist', 'prod')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp')
    search_fields = ('email',)