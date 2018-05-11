from .Order import Order
from orders.models import Order as OrderModel
from payment.models import PaycomTransaction
from .Format import Format
from django.utils import timezone

from datetime import datetime
import time
import json
import pytz


class Transaction:
    TIMEOUT = 43200000
    STATE_CREATED = 1
    STATE_COMPLETED = 2
    STATE_CANCELLED = -1
    STATE_CANCELLED_AFTER_COMPLETE = -2

    REASON_RECEIVERS_NOT_FOUND = 1
    REASON_PROCESSING_EXECUTION_FAILED = 2
    REASON_EXECUTION_FAILED = 3
    REASON_CANCELLED_BY_TIMEOUT = 4
    REASON_FUND_RETURNED = 5
    REASON_UNKNOWN = 10

    TRANSACTION_CAN_NOT_PERFORM = -31008
    TRANSACTION_CAN_NOT_CANCEL = -31007
    TRANSACTION_INVALID_AMOUNT = -31001
    TRANSACTION_NOT_FOUND = -31003

    params = None
    paycom_transaction_id = None
    transaction = None
    formatter = Format()

    def __init__(self, params):
        self.params = params
        self.paycom_transaction_id = params['id'] if 'id' in params else 0

    def exist(self):
        try:
            self.transaction = PaycomTransaction.objects.get(paycom_transaction_id=self.paycom_transaction_id)
            return True
        except PaycomTransaction.DoesNotExist:
            return False

    def save_transaction(self):
        order = OrderModel.objects.get(pk=self.params['account']['order_id'])
        order.state = Order.STATE_WAITING_PAY
        order.save()
        """
            Comment:
            Save transaction with state = 1 and set order state STATE_WAITING_PAY = 1
            self.transaction = new transaction
        """
        data = {
            'paycom_transaction_id': self.paycom_transaction_id,
            'paycom_time': self.params['time'],
            'paycom_time_datetime': self.formatter.millisecond_timestamp_to_utc_datetime(milliseconds=self.params['time']),
            'create_time': timezone.now(),
            'amount': self.params['amount'],
            'state': self.STATE_CREATED,
            'order': order
        }
        self.transaction = PaycomTransaction.objects.create(**data)

    def check_transaction_state(self, state=None):
        if state is None:
            state = self.STATE_CREATED
        return True if self.transaction.state == state else False

    def transaction_is_expired(self):
        time_interval = (timezone.now() - self.transaction.create_time)
        if self.formatter.datetime_timedelta_to_milliseconds(_datetime=time_interval) > self.TIMEOUT:
            return True
        else:
            return False

    def return_transaction_details(self, field=None):

        """
            Comment: state, create_time|perform_time, transaction, receivers
        """
        if field is None:
            field = 'create_time'
        _datetime = getattr(self.transaction, field)
        time_in_milliseconds = self.formatter.millisecond_timestamp_from_utc_to_time_zone(utc_datetime=_datetime)
        response = {
            'result': {
                'state': self.transaction.state,
                'transaction': str(self.transaction.id)
            }
        }
        response['result'][field] = time_in_milliseconds
        return json.dumps(response)

    def cancel_transaction(self, reason, state=None):
        if state is None:
            state = self.STATE_CANCELLED
        self.transaction.state = state

        self.transaction.cancel_time = timezone.now()
        self.transaction.reason = reason
        self.transaction.save()

    def complete_transaction(self):
        self.transaction.state = self.STATE_COMPLETED
        self.transaction.perform_time = timezone.now()
        self.transaction.save()

    def get_transaction_details(self):
        cancel_time = self.formatter.millisecond_timestamp_from_utc_to_time_zone(utc_datetime=
                                                                                 self.transaction.cancel_time)
        perform_time = self.formatter.millisecond_timestamp_from_utc_to_time_zone(utc_datetime=
                                                                                  self.transaction.perform_time)
        create_time = self.formatter.millisecond_timestamp_from_utc_to_time_zone(utc_datetime=
                                                                                 self.transaction.create_time)
        reason = self.transaction.reason if self.transaction.reason is not None else None

        data = {
            "result": {
                "create_time": create_time,
                "perform_time": perform_time,
                "cancel_time": cancel_time,
                "transaction": str(self.transaction.id),
                "state": self.transaction.state,
                "reason": reason
            }
        }
        return json.dumps(data)

    def get_statement(self, _from, _to):
        datetime_from = datetime.utcfromtimestamp(_from / 1000.0)
        datetime_to = datetime.utcfromtimestamp(_to / 1000.0)
        timezone_from = timezone.make_aware(datetime_from, timezone.get_current_timezone())
        timezone_to = timezone.make_aware(datetime_to, timezone.get_current_timezone())
        transactions = PaycomTransaction.objects.filter(
            create_time__range=[timezone_from, timezone_to], reason__isnull=True
        )

        regenerated_transactions = [{
            "id": item.paycom_transaction_id,
            "time": item.paycom_time,
            "amount": item.amount,
            "account": {
                "order_id": item.order.id,
                "customer_id": item.order.customer.id
            },
            "create_time": self.formatter.millisecond_timestamp_from_utc_to_time_zone(item.create_time),
            "perform_time": self.formatter.millisecond_timestamp_from_utc_to_time_zone(item.perform_time),
            "cancel_time": 0,
            "transaction": item.id,
            "state": 2,
            "reason": None,
            "receivers": []
        } for item in transactions]
        data = {
            "result": {
                "transactions": regenerated_transactions
            }
        }
        return json.dumps(data)
