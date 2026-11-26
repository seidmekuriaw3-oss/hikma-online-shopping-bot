from decimal import Decimal
from types import SimpleNamespace

from services import payments
from services.payments import PaymentService


def test_chapa_verification_compares_postgres_decimal_amounts(monkeypatch):
    service = PaymentService(SimpleNamespace())
    service.chapa_secret = 'test'
    service.chapa_api_url = 'https://payments.invalid'
    updated = []
    monkeypatch.setattr(
        payments.requests,
        'get',
        lambda *args, **kwargs: SimpleNamespace(
            status_code=200,
            text='',
            json=lambda: {
                'status': 'success',
                'data': {
                    'status': 'success',
                    'amount': '20',
                    'currency': 'ETB',
                    'tx_ref': 'transaction-1',
                },
            },
        ),
    )
    monkeypatch.setattr(service, 'update_payment_status', lambda *args: updated.append(args) or True)
    monkeypatch.setattr(service, 'get_payment', lambda payment_id: {'id': payment_id})
    payment = {
        'id': 8,
        'status': 'pending',
        'method': 'chapa',
        'transaction_id': 'transaction-1',
        'amount': Decimal('20.00'),
        'currency': 'ETB',
    }

    verified = service.verify_chapa_payment(payment)

    assert verified == {'id': 8}
    assert updated[0][1] == 'completed'