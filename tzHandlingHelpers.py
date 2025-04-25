# -*- coding: utf-8 -*-
"""
Created on Thu Apr 24 21:26:26 2025

@author: DTRManning
"""

import datetime

def get_utc_now():
    """Get current time in UTC with timezone info"""
    return datetime.now(datetime.timezone.utc)
