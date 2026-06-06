# Eden Beach Resort API Integration Guide

## Overview
This integration enables direct connection to Eden Beach Resort API for real-time booking, guest, and room data synchronization.

## Components

### 1. **eden_beach_integration.py**
Core integration module containing:
- `EdenBeachAPIConfig`: API configuration management
- `EdenBeachAPIClient`: API client with request handling and retry logic
- `EdenBeachDataSync`: Data synchronization between Eden Beach and Supabase

### 2. **eden_beach_ui.py**
Streamlit UI for managing the integration:
- API configuration interface
- Connection testing
- Data synchronization controls
- Booking fetch with date filters
- Sync status monitoring

### 3. **eden_beach_config.py**
Configuration settings and endpoints

## Setup Instructions

### Step 1: Get Your API Credentials
Contact Eden Beach Resort support and request:
- API Base URL (e.g., `https://api.edenbeach.com`)
- API Key/Token

### Step 2: Configure in Streamlit

1. Navigate to the "Eden Beach Integration" section in your app
2. Go to the **Configuration** tab
3. Enter your API Key
4. Enter your API Base URL
5. Click **Save Configuration**
6. Click **Test Connection** to verify

### Step 3: Use the Sync Features

#### Sync Individual Data Types
- **Sync Bookings**: Fetches bookings from Eden Beach and imports to Supabase
- **Sync Guests**: Fetches guest information
- **Sync Rooms**: Fetches room inventory

#### Sync All Data
Click **Sync All** to synchronize bookings, guests, and rooms in one operation.

#### Fetch Specific Date Range
1. Go to **Fetch Data** tab
2. Select start and end dates
3. Click **Fetch Bookings**
4. Review the data
5. Click **Import to Supabase** to save

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Test connection |
| `/api/bookings` | GET | Fetch all bookings |
| `/api/bookings/{id}` | GET | Get booking details |
| `/api/availability` | GET | Check room availability |
| `/api/bookings` | POST | Create new booking |
| `/api/bookings/{id}` | PUT | Update booking |
| `/api/guests` | GET | Fetch guest information |
| `/api/rooms` | GET | Fetch room inventory |

## Data Transformation

### Bookings
Eden Beach booking data is transformed to match your Supabase schema:
```python
{
    "booking_id": "...",
    "property": "Eden Beach Resort",
    "guest_name": "...",
    "email": "...",
    "phone": "...",
    "checkin_date": "...",
    "checkout_date": "...",
    "room_type": "...",
    "number_of_guests": ...,
    "total_price": ...,
    "status": "confirmed",
    "source": "Eden Beach API"
}
```

### Guests
Guest data is transformed to:
```python
{
    "guest_id": "...",
    "name": "...",
    "email": "...",
    "phone": "...",
    "country": "...",
    "city": "..."
}
```

### Rooms
Room data is transformed to:
```python
{
    "room_id": "...",
    "room_number": "...",
    "room_type": "...",
    "capacity": ...,
    "price_per_night": ...,
    "amenities": [...],
    "status": "available"
}
```

## Error Handling

The integration includes:
- **Automatic Retries**: Up to 3 retry attempts on network errors
- **Timeout Handling**: 30-second timeout per request
- **Connection Testing**: Validate credentials before syncing
- **Error Logging**: Detailed error messages for troubleshooting

## Troubleshooting

### Connection Failed
- ✅ Verify API Key is correct
- ✅ Check API Base URL format (must be https://)
- ✅ Ensure your network allows outbound connections
- ✅ Contact Eden Beach support to confirm credentials

### Sync Errors
- ✅ Check error message for details
- ✅ Verify Supabase connection is active
- ✅ Check that required tables exist in Supabase
- ✅ Review logs for specific error details

### Timeout Issues
- ✅ Try again (automatic retries may succeed)
- ✅ Check your network connection
- ✅ Reduce data range when fetching
- ✅ Contact Eden Beach support if server is slow

## Advanced Usage

### Programmatic Sync
```python
from eden_beach_integration import (
    EdenBeachAPIConfig,
    EdenBeachAPIClient,
    EdenBeachDataSync
)
from app import supabase

# Initialize
config = EdenBeachAPIConfig()
config.set_api_key("your-api-key")
config.set_api_url("https://api.edenbeach.com")

client = EdenBeachAPIClient(config)
sync = EdenBeachDataSync(client, supabase)

# Sync data
result = sync.sync_all()
print(result)
```

### Custom Data Fetching
```python
# Fetch bookings for specific date range
success, bookings, message = client.fetch_bookings(
    start_date="2026-06-01",
    end_date="2026-06-30"
)

if success:
    for booking in bookings:
        print(booking)
```

## Security Notes

- 🔒 API keys are stored in Streamlit session state (not persistent)
- 🔒 Never commit API keys to version control
- 🔒 Use environment variables for production
- 🔒 API keys are displayed as password fields in UI (hidden input)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review error logs in Streamlit console
3. Contact TIE Reservation team
4. Contact Eden Beach Resort support for API issues
