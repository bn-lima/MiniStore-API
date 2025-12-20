from django.test import TestCase
from django.urls import reverse
from .models import Client, Product
from rest_framework.authtoken.models import Token
from unittest.mock import patch

def fake_get_payment_data(data_id):
    return {
        "id": 1234567890,
        "status": "approved",
        "status_detail": "accredited",
        "transaction_amount": 100.00,
        "currency_id": "BRL",
        "external_reference": 1
    }

def fake_product():
    return Product.objects.create(
        name='Test Product',
        category='Test Category',
        price=100.00,
        stock=10,
        active=True
    )

class MockMercadoPagoWebhook(TestCase):
    
    @classmethod
    def setUpTestData(cls):

        cls.mock_request_data = {
            'data': {
                'id': '1234567890'
            },
        }

        cls.mock_headers = {
            'HTTP_X_REQUEST_ID': 'req-987654321',
            'HTTP_X_SIGNATURE': 'ts=1234567890,signature=fakesignature123'
        }

    @patch('store.views.get_payment_data', side_effect=fake_get_payment_data)
    @patch('store.views.validate_signature', return_value=True)
    def test_webhook_flow(self, mock_validate_signature, mock_get_payment_data):

        url = reverse('webhook')
        
        response = self.client.post(url, data=self.mock_request_data,content_type='application/json', **self.mock_headers)
        mock_validate_signature.assert_called_once()

        mock_get_payment_data.assert_called_once()
        print(response.text)
