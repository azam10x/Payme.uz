# -*- coding: utf-8 -*-
from payment.models import *
from orders.models import Order as OrderModel
from .Request import Request
from .Response import Response
from .PaycomException import PaycomException
from .Merchant import Merchant
from .Order import Order
from .Transaction import Transaction
from .Format import Format
from .conf import config
from django.utils import timezone

import os
import json


class Application:
    method = None
    request = None
    response = None
    merchant = None
    json_content = None
    formatter = Format()

    def __init__(self, request):
        if request.method == 'POST':
            self.request = Request(request=request)
            self.method = self.request.method
            self.response = Response(request=self.request)
            self.merchant = Merchant(conf=config, request=request)
        else:
            raise PaycomException(request_id=None, message='No post request detected', code=-32300)

    def run(self):

        if self.merchant.authorize():
            try:
                if self.method == 'CheckPerformTransaction':
                    self.check_perform_transaction()
                elif self.method == 'CreateTransaction':
                    self.create_transaction()
                elif self.method == 'PerformTransaction':
                    self.perform_transaction()
                elif self.method == 'CancelTransaction':
                    self.cancel_transaction()
                elif self.method == 'CheckTransaction':
                    self.check_transaction()
                elif self.method == 'GetStatement':
                    self.get_statement()
                elif self.method == 'ChangePassword':
                    self.change_password()
                else:
                    self.json_content = self.response.error(code=PaycomException.ERROR_METHOD_NOT_FOUND,
                                                            message='Method not found', data=self.request.method)
            except PaycomException:
                self.json_content = self.response.error(
                    code=PaycomException.ERROR_INVALID_JSON_RPC_OBJECT,
                    message='Invalid RPC Object',
                    data='rpc data'
                )
        else:

            self.json_content = self.response.error(
                    code=PaycomException.ERROR_INSUFFICIENT_PRIVILEGE,
                    message='Invalid login/password',
                    data='account'
                )
        return self.json_content

    def check_perform_transaction(self):
        order = Order(request_id=self.request.id)
        if order.validate(account_params=self.request.params):
            """ 
                Comment: Order successfully validated 
            """
            data = {
                "result": order.response_message
            }
            self.json_content = json.dumps(data)
        else:
            self.json_content = self.response.send(result=None, error=order.response_message)

    def create_transaction(self):

        transaction = Transaction(params=self.request.params)
        if transaction.exist():
            """
                Comment: If transaction already exists, 
                then check transaction state is available and time is not expired
            """
            if transaction.check_transaction_state():
                if transaction.transaction_is_expired():
                    transaction.cancel_transaction(reason=Transaction.REASON_CANCELLED_BY_TIMEOUT)
                    """ 
                        Comment: If transaction's time is expired, 
                        cancel transaction and return error message code: -31008 
                    """
                    self.json_content = self.response.error(code=Transaction.TRANSACTION_CAN_NOT_PERFORM,
                                                            message='Transaction is expired.',
                                                            data='timeout')
                else:
                    """ 
                        Comment: If transaction's time is not expired, 
                        return transaction details
                    """
                    self.json_content = transaction.return_transaction_details()
            else:
                """ 
                    Comment: If transaction not exist, return error message code: -31008 
                """
                self.json_content = self.response.error(code=Transaction.TRANSACTION_CAN_NOT_PERFORM,
                                                        message='Transaction found, but is not active.',
                                                        data='timeout')
        else:
            """ 
                Comment: If transaction not exist, try to create new one
            """
            order = Order(request_id=self.request.id)
            if order.validate(account_params=self.request.params) is False:
                self.json_content = self.response.send(result=None, error=order.response_message)
            else:
                now_in_milliseconds = self.formatter.millisecond_timestamp_from_utc_to_time_zone(utc_datetime=timezone.now())
                if (now_in_milliseconds - self.request.params['time']) > Transaction.TIMEOUT:
                    self.json_content = self.response.error(code=PaycomException.ERROR_INVALID_ACCOUNT,
                                                            message='Transaction is expired.',
                                                            data='timeout')
                else:
                    transaction.save_transaction()
                    self.json_content = transaction.return_transaction_details()

    def perform_transaction(self):
        transaction = Transaction(params=self.request.params)
        if transaction.exist():
            if transaction.check_transaction_state(state=Transaction.STATE_CREATED):
                if transaction.transaction_is_expired():
                    transaction.cancel_transaction(reason=Transaction.REASON_CANCELLED_BY_TIMEOUT)
                    """ 
                        Comment: If transaction's time is expired, 
                        cancel transaction and return error message code: -31008 
                    """
                    self.json_content = self.response.error(code=Transaction.TRANSACTION_CAN_NOT_PERFORM,
                                                            message='Transaction is expired.',
                                                            data='time')
                else:
                    order = OrderModel.objects.get(pk=transaction.transaction.order.pk)
                    order.state = Order.STATE_PAY_ACCEPTED
                    order.save()
                    transaction.complete_transaction()
                    self.json_content = transaction.return_transaction_details(field='perform_time')
            elif transaction.check_transaction_state(state=Transaction.STATE_COMPLETED):
                """
                    Comment: Return transaction details if transaction was completed
                """
                self.json_content = transaction.return_transaction_details(field='perform_time')
            else:
                self.json_content = self.response.error(code=Transaction.TRANSACTION_CAN_NOT_PERFORM,
                                                        message='Transaction state is not valid.',
                                                        data='state')

        else:
            self.json_content = self.response.error(code=Transaction.TRANSACTION_NOT_FOUND,
                                                    message='Transaction is not found',
                                                    data='id')

    def cancel_transaction(self):
        transaction = Transaction(params=self.request.params)
        if transaction.exist():
            order = OrderModel.objects.get(pk=transaction.transaction.order.pk)
            if transaction.check_transaction_state(state=Transaction.STATE_CREATED):
                transaction.cancel_transaction(reason=self.request.params['reason'])
                order.state = Order.STATE_CANCELLED
                order.save()
                self.json_content = transaction.return_transaction_details(field='cancel_time')
            elif transaction.check_transaction_state(state=Transaction.STATE_COMPLETED):
                """
                    Comment: Here is checked, whether Transaction can be cancelable ?
                    If order is shipped then transaction will not be cancelled, 
                    otherwise will be cancelled and so is "Order" .
                """
                if int(order.state) == Order.STATE_DELIVERED:
                    self.json_content = self.response.error(code=Transaction.TRANSACTION_CAN_NOT_CANCEL,
                                                            message='Transaction can not be cancelled.',
                                                            data='order.state')
                else:
                    order.state = Order.STATE_CANCELLED
                    order.save()
                    transaction.cancel_transaction(reason=self.request.params['reason'],
                                                   state=Transaction.STATE_CANCELLED_AFTER_COMPLETE)
                    self.json_content = transaction.return_transaction_details(field='cancel_time')
            else:
                self.json_content = transaction.return_transaction_details(field='cancel_time')
        else:
            self.json_content = self.response.error(code=Transaction.TRANSACTION_NOT_FOUND,
                                                    message='Transaction is not found',
                                                    data='id')

    def check_transaction(self):
        transaction = Transaction(params=self.request.params)
        if transaction.exist():
            self.json_content = transaction.get_transaction_details()
        else:
            self.json_content = self.response.error(code=Transaction.TRANSACTION_NOT_FOUND,
                                                    message='Transaction is not found',
                                                    data='id')

    def get_statement(self):
        all_transactions = Transaction.get_statement(_from=self.request.params['from'], _to=self.request.params['to'])
        self.json_content = all_transactions

    def change_password(self):
        pass
