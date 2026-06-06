"""
Integration setup guide for Eden Beach API

Add these imports and route to your app.py to enable Eden Beach integration
"""

# ============================================
# ADD THESE IMPORTS TO YOUR app.py
# ============================================

# At the top of app.py, add:
from eden_beach_ui import show_eden_beach_page

# ============================================
# ADD THIS PAGE ROUTE IN app.py main()
# ============================================

# In the page routing section (around line 425), add:

"""
elif page == "Eden Beach Integration":
    show_eden_beach_page(supabase)
    log_activity(supabase, st.session_state.username, "Accessed Eden Beach Integration")
"""

# ============================================
# ADD SCREEN TO VISIBLE SCREENS LIST
# ============================================

# In the all_screens list for users (around line 208-216), add:
"""
all_screens = [
    "Inventory Dashboard", "Night Report Dashboard", "Accounts Report",
    "Date-wise Booking Report", "Date-wise Check-in Report", "Booking Date Report",
    "Direct Reservations", "View Reservations", "Edit Direct Reservation",
    "Online Reservations", "Edit Online Reservations", "Daily Status",
    "Daily Management Status", "Analytics", "Monthly Consolidation",
    "Summary Report", "Target Achievement", "User Management", "Log Report",
    "Expense Tracker", "Eden Beach Integration"  # ✅ ADD THIS LINE
]
"""

# ============================================
# UPDATED app.py SNIPPET
# ============================================

UPDATED_IMPORTS = """
import streamlit as st
import os
from supabase import create_client, Client
from directreservation import show_new_reservation_form, show_reservations, show_edit_reservations, show_analytics, load_reservations_from_supabase
from online_reservation import show_online_reservations, load_online_reservations_from_supabase
from booking_date_report import show_booking_date_report
from booking_date_report_datewise import show_datewise_booking_report  
from checkin_date_report_datewise import show_checkin_date_report
from editOnline import show_edit_online_reservations  # or with try/except
from inventory import show_daily_status
from dms import show_dms
from dashboard import show_dashboard
from summary_report import show_summary_report
import pandas as pd
import json
from log import show_log_report, log_activity
from users import validate_user, create_user, update_user, delete_user, load_users
from accounts_report import show_accounts_report
from nrd_report import show_nrd_report
from expense_tracker import display_expense_tracker
from target_achievement_report import show_target_achievement_report
from eden_beach_ui import show_eden_beach_page  # ✅ ADD THIS LINE
"""

UPDATED_PAGE_ROUTING = """
# In main() function page routing section (around line 425+):

elif page == "Eden Beach Integration":
    show_eden_beach_page(supabase)
    log_activity(supabase, st.session_state.username, "Accessed Eden Beach Integration")
"""

UPDATED_SCREENS = """
# In show_user_management() function, update all_screens:

all_screens = [
    "Inventory Dashboard", "Night Report Dashboard", "Accounts Report",
    "Date-wise Booking Report", "Date-wise Check-in Report", "Booking Date Report",
    "Direct Reservations", "View Reservations", "Edit Direct Reservation",
    "Online Reservations", "Edit Online Reservations", "Daily Status",
    "Daily Management Status", "Analytics", "Monthly Consolidation",
    "Summary Report", "Target Achievement", "User Management", "Log Report",
    "Expense Tracker", "Eden Beach Integration"  # ✅ ADDED
]
"""
