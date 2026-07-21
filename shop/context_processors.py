from django.db.models import Prefetch
from .models import Cart, CartItem, Wishlist, wishItems

def shop_context(request):
    context = {'CART': None, 'wish': None}
    
    if request.user.is_authenticated:
        # Cart Items have a ForeignKey to Product.
        # We use select_related('prod') to join the product table.
        # Then we use Prefetch to fetch CartItems (and their products) with the Cart.
        cart_items_qs = CartItem.objects.select_related('prod')
        context['CART'] = Cart.objects.prefetch_related(
            Prefetch('items', queryset=cart_items_qs)
        ).filter(customer=request.user).first()
        
        wish_items_qs = wishItems.objects.select_related('prod')
        context['wish'] = Wishlist.objects.prefetch_related(
            Prefetch('items', queryset=wish_items_qs)
        ).filter(customer=request.user).first()
        
    return context
