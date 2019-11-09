# -*- coding: utf-8 -*-
from .PaycomException import PaycomException
from .Format import Format

# Import your app's Order model
from basic.models import Order as OrderModel

class Order:
    STATE_AVAILABLE = 0
    STATE_WAITING_PAY = 1
    STATE_PAY_ACCEPTED = 2
    STATE_CANCELLED = 3
    STATE_DELIVERED = 4

    # If order will not be validated, set and return this error message
    response_message = None

    def __init__(self, request_id):
        self.request_id = request_id

    def validate(self, account_params):
        account = account_params['account']
        order_id_str = 'order_id'
        customer_id_str = 'customer_id'
        amount_str = 'amount'

        if order_id_str not in account or account[order_id_str] == '' or \
                Format.is_not_numeric(value=account[order_id_str]):
            self.response_message = {
                "code": PaycomException.ERROR_INVALID_ACCOUNT,
                "message": {
                    "ru": "Идентификатор заказа не существует.",
                    "uz": "Buyurtma raqami mavjud emas.",
                    "en": "Order id does not exist."
                },
                "data": "order_id"
            }
            return False
        elif customer_id_str not in account or account[customer_id_str] == '' or \
                Format.is_not_numeric(value=account[customer_id_str]):
            self.response_message = {
                "code": PaycomException.ERROR_INVALID_ACCOUNT,
                "message": {
                    "ru": "Клиент заказа не существует.",
                    "uz": "Buyurtmachi mavjud emas.",
                    "en": "Order customer does not exist."
                },
                "data": "customer_id"
            }
            return False
        elif amount_str not in account_params or account_params[amount_str] == '' or \
                Format.is_not_numeric(value=account_params[amount_str]):
            self.response_message = {
                "code": PaycomException.ERROR_INVALID_AMOUNT,
                "message": {
                    "ru": "Сумма заказа не существует.",
                    "uz": "Buyurtma narxi mavjud emas.",
                    "en": "Order amount does not exist."
                },
                "data": "amount"
            }
            return False
        else:
            try:
                order_id = int(account[order_id_str])
                customer = int(account[customer_id_str])
                amount = account_params[amount_str]
                order = OrderModel.objects.get(pk=order_id, phone=customer)

                if int(order.state) != self.STATE_AVAILABLE:
                    self.response_message = {
                        "code": -31050,
                        "message": {
                            "ru": "Состояние заказа является недействительным.",
                            "uz": "Buyurtma holati to'g'ri emas.",
                            "en": "Order state is invalid."
                        },
                        "data": "state"
                    }
                    return False
                elif int(order.total_price) != int(amount) / 100:
                    self.response_message = {
                        "code": PaycomException.ERROR_INVALID_AMOUNT,
                        "message": {
                            "ru": "Сумма заказа неверна.",
                            "uz": "Buyurtma narxi noto'g'ri.",
                            "en": "Incorrect amount."
                        },
                        "data": "amount"
                    }
                    return False
                else:
                    self.response_message = {'allow': True}
                    return True
            except OrderModel.DoesNotExist:
                self.response_message = {
                    "code": PaycomException.ERROR_INVALID_ACCOUNT,
                    "message": {
                        "ru": "Заказ не найден.",
                        "uz": "Buyurtma topilmadi.",
                        "en": "Order not found."
                    },
                    "data": "order"
                }
                return False
