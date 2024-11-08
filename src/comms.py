"""
Author: <Chuanyu> (skewcy@gmail.com)
comms.py (c) 2024
Desc: description
Created:  2024-11-08T02:33:15.502Z
"""

import pytz
from datetime import datetime, date
from config import TIMEZONE


def get_local_date() -> date:
    """Get the current date in the local timezone"""
    local_tz = pytz.timezone(TIMEZONE)
    return datetime.now(local_tz).date()


def get_local_datetime() -> datetime:
    """Get the current datetime in the local timezone"""
    local_tz = pytz.timezone(TIMEZONE)
    return datetime.now(local_tz)
