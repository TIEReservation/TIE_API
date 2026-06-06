# StayFlexi CM Service API Configuration for Edenbeach
# This file contains all StayFlexi API settings

# ============================================
# STAYFLEXI API CONFIGURATION
# ============================================

# API Endpoints
STAYFLEXI_API_BASE_URL = "https://api.stayflexi.com/core/apiv1/cmservice"

# Hotel Credentials (From Postman Collection)
STAYFLEXI_PMS_ID = "20057"
STAYFLEXI_HOTEL_ID = "30357"
STAYFLEXI_API_KEY = "n9F3BrVUdLKABeG91ryvbdaAI1dffxb0"

# API Endpoints Dictionary
STAYFLEXI_ENDPOINTS = {
    "health": "/gethoteldetail",
    "get_bookings": "/get-booking-list-by-date",
    "get_booking_detail": "/bookingdetail",
    "get_channels": "/channels",
    "get_room_count": "/getroomcount",
    "get_room_rates": "/getroomrates",
    "get_room_counts_by_channel": "/get-room-counts",
    "get_room_rates_by_channel": "/get-room-rates",
    "create_booking": "/booking",
    "checkin": "/checkin",
    "checkout": "/checkout",
    "cancel_booking": "/cancel",
    "get_restriction": "/getrestriction",
    "send_rates": "/rates",
    "send_inventory": "/inventory",
    "send_restriction": "/sendrestriction",
    "get_invoice_items": "/getInvoiceItems",
}

# Timeout and retry settings
STAYFLEXI_TIMEOUT = 30  # seconds
STAYFLEXI_MAX_RETRIES = 3

# Database table mappings for Supabase
STAYFLEXI_TABLES = {
    "bookings": "reservations",
    "guests": "customers",
    "rooms": "rooms",
    "channels": "channels",
}

# Date format settings
STAYFLEXI_DATE_FORMAT = "%d-%m-%Y"
STAYFLEXI_DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"

# Sync settings
AUTO_SYNC_ENABLED = False
SYNC_INTERVAL_MINUTES = 60  # Auto-sync every hour if enabled

# Rate and Inventory Days
RATE_DAYS_INCLUDED = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Property Info
PROPERTY_NAME = "Eden Beach Resort"
PROPERTY_CODE = "EDEN_BEACH_RESORT"

# Default date range for initial fetch (in days from today)
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_LOOKAHEAD_DAYS = 90
