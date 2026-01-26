from django.core.management.base import BaseCommand
from store.models import MPPreference, Cart
from django.db import transaction
from store.services import return_product_stock

class Command(BaseCommand):

    help= 'Devolve o estoque reservado de todos os itens do cart para o estoque normal.'

    def handle(self, *args, **kwargs):
        query = MPPreference.objects.filter(expired=False, finalized=False)

        if not query.exists():
            return 'Does not have any expired preferences'

        for preference in query:

            with transaction.atomic():
                cart = Cart.objects.get(preference=preference)

                if preference.is_preference_expired():

                    return_product_stock(cart)                    