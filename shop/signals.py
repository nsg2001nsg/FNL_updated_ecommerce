from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer, Cart, Wishlist

@receiver(post_save, sender=Customer)
def create_customer_dependencies(sender, instance, created, **kwargs):
    """
    Signal to automatically create a Cart and Wishlist whenever a new 
    Customer is created. Uses get_or_create to ensure idempotency.
    """
    if created:
        Cart.objects.get_or_create(customer=instance)
        Wishlist.objects.get_or_create(customer=instance)
