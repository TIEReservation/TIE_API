# Eden Beach Resort API Integration Configuration
# Add this to your config.py file

# ============================================
# EDEN BEACH RESORT API CONFIGURATION
# ============================================

EDEN_BEACH_API_URL = "https://api.edenbeach.com"  # Replace with actual API URL
EDEN_BEACH_API_KEY = ""  # Set via UI or environment variable
EDEN_BEACH_PROPERTY_ID = "EDEN_BEACH_RESORT"

# API Endpoints
EDEN_BEACH_ENDPOINTS = {
    "health": "/api/health",
    "bookings": "/api/bookings",
    "booking_details": "/api/bookings/{id}",
    "availability": "/api/availability",
    "guests": "/api/guests",
    "rooms": "/api/rooms",
}

# Timeout and retry settings
EDEN_BEACH_TIMEOUT = 30  # seconds
EDEN_BEACH_MAX_RETRIES = 3

# Database table mappings for Supabase
EDEN_BEACH_TABLES = {
    "bookings": "reservations",
    "guests": "guests",
    "rooms": "rooms",
}

# Data transformation settings
EDEN_BEACH_DATE_FORMAT = "%Y-%m-%d"
EDEN_BEACH_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Sync settings
AUTO_SYNC_ENABLED = False
SYNC_INTERVAL_MINUTES = 60  # Auto-sync every hour if enabled
