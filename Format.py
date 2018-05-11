from datetime import datetime
import pytz
import time

from django.conf import settings


class Format:
    tzinfo = pytz.timezone(settings.TIME_ZONE)
    SECONDS_TO_MILLISECONDS = 1000.0

    def __init__(self):
        pass

    @staticmethod
    def is_not_numeric(value):
        try:
            int(value)
            return False
        except ValueError:
            return True

    def millisecond_timestamp_to_utc_datetime(self, milliseconds):
        return datetime.utcfromtimestamp(milliseconds/self.SECONDS_TO_MILLISECONDS).replace(tzinfo=self.tzinfo)

    def datetime_timedelta_to_milliseconds(self, _datetime):
        return _datetime.total_seconds() * self.SECONDS_TO_MILLISECONDS

    def convert_datetime_to_milliseconds(self, _datetime):
        transaction_time_field = _datetime.timetuple()
        return time.mktime(transaction_time_field) * self.SECONDS_TO_MILLISECONDS

    def millisecond_timestamp_from_utc_to_time_zone(self, utc_datetime):
        if utc_datetime is None:
            return 0
        return (float(utc_datetime.strftime("%s")) + 5 * 60 * 60) * self.SECONDS_TO_MILLISECONDS
