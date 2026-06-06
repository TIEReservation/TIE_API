# StayFlexi Integration Setup Guide - Edenbeach

## 📋 Overview

This guide walks you through integrating StayFlexi Channel Manager API with your TIE Reservation System to automatically sync Edenbeach bookings.

## ✅ Pre-Requirements

- ✓ StayFlexi Account with API Access
- ✓ Hotel Credentials (PMS ID: 20057, Hotel ID: 30357, API Key: n9F3BrVUdLKABeG91ryvbdaAI1dffxb0)
- ✓ Supabase Database Access
- ✓ Python 3.8+

## 🚀 Quick Start (5 Steps)

### Step 1: Update app.py Navigation

Add StayFlexi sync to your app's page navigation. Edit **app.py** and add this import at the top:

```python
from stayflexi_ui import show_stayflexi_sync
```

Then add this in the page routing section (around line 468):

```python
elif page == "StayFlexi Sync":
    show_stayflexi_sync()
    log_activity(supabase, st.session_state.username, "Accessed StayFlexi Sync")
```

Also add "StayFlexi Sync" to your `all_screens` list (around line 207):

```python
all_screens = [
    "Inventory Dashboard", "Night Report Dashboard", "Accounts Report", 
    "Date-wise Booking Report", "Date-wise Check-in Report", "Booking Date Report",
    "Direct Reservations", "View Reservations", "Edit Direct Reservation", 
    "Online Reservations", "Edit Online Reservations", "Daily Status", 
    "Daily Management Status", "Analytics", "Monthly Consolidation", 
    "Summary Report", "Target Achievement", "StayFlexi Sync",  # ← ADD THIS
    "Log Report"
]
```

### Step 2: Create Supabase Table

Create a table for StayFlexi bookings. In your Supabase dashboard, run this SQL:

```sql
CREATE TABLE IF NOT EXISTS reservations (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    booking_id TEXT UNIQUE NOT NULL,
    property TEXT NOT NULL,
    guest_name TEXT,
    email TEXT,
    phone TEXT,
    checkin_date DATE,
    checkout_date DATE,
    room_type TEXT,
    number_of_guests INTEGER,
    total_price DECIMAL(10, 2),
    status TEXT DEFAULT 'confirmed',
    notes TEXT,
    source TEXT DEFAULT 'StayFlexi API',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_booking_id ON reservations(booking_id);
CREATE INDEX idx_checkin_date ON reservations(checkin_date);
CREATE INDEX idx_source ON reservations(source);
```

### Step 3: Verify Configuration

All configuration is in **stayflexi_config.py** and is pre-configured with your hotel credentials:

```python
STAYFLEXI_PMS_ID = "20057"
STAYFLEXI_HOTEL_ID = "30357"
STAYFLEXI_API_KEY = "n9F3BrVUdLKABeG91ryvbdaAI1dffxb0"
```

✅ **No changes needed** - credentials are already set!

### Step 4: Grant User Access

Add users with "StayFlexi Sync" permission in User Management:

1. Login as Admin
2. Go to "User Management"
3. Create/Modify a user
4. Select "StayFlexi Sync" in "Visible Screens"
5. Save

### Step 5: Test & Deploy

1. **Restart your app:**
   ```bash
   streamlit run app.py
   ```

2. **Test the connection:**
   - Navigate to "StayFlexi Sync" page
   - Click "Test Connection" tab
   - Click "🔍 Test Connection" button
   - Should see ✅ Success message

3. **Sync bookings:**
   - Go to "📥 Sync Bookings" tab
   - Select date range
   - Click "🚀 Start Sync"
   - Review data and click "✅ Confirm & Sync to Database"

## 📊 Module Overview

### stayflexi_config.py
**Configuration management**
- API endpoints
- Hotel credentials
- Database mappings
- Date formats
- Sync settings

### stayflexi_integration.py
**Backend API integration**
- `StayFlexiAPIConfig`: Credential management
- `StayFlexiAPIClient`: API communication with retry logic
- `StayFlexiDataSync`: Data transformation & Supabase sync

**Supported Operations:**
- Fetch bookings by date range
- Fetch channels, room counts, rates
- Check-in/Check-out operations
- Cancel bookings
- Get booking details

### stayflexi_ui.py
**Streamlit user interface**
- 4-tab interface
- Connection testing
- Booking synchronization
- Booking view & export
- Sync status monitoring

## 🔄 Usage Workflow

### Manual Sync
1. Go to "StayFlexi Sync" → "📥 Sync Bookings"
2. Select date range (default: last 30 days to next 90 days)
3. Click "🚀 Start Sync"
4. Review fetched bookings
5. Click "✅ Confirm & Sync to Database"

### View Synced Bookings
1. Go to "StayFlexi Sync" → "📊 View Bookings"
2. See all bookings synced from StayFlexi
3. Export as CSV for external analysis

### Monitor Status
1. Go to "StayFlexi Sync" → "📈 Sync Status"
2. Check API connection status
3. View last sync time and error count

## 🔧 Advanced Configuration

### Auto-Sync (Coming Soon)
To enable automatic hourly sync, uncomment in **stayflexi_config.py**:

```python
AUTO_SYNC_ENABLED = True
SYNC_INTERVAL_MINUTES = 60  # Sync every hour
```

Then add scheduler to app.py:

```python
import schedule
import threading

def schedule_syncs():
    if config.AUTO_SYNC_ENABLED:
        schedule.every(config.SYNC_INTERVAL_MINUTES).minutes.do(run_sync)
        
def run_sync():
    # Sync logic here
    pass
```

### Custom Date Format
Modify in **stayflexi_config.py**:

```python
STAYFLEXI_DATE_FORMAT = "%d-%m-%Y"  # Format used by StayFlexi API
```

### Error Retry Settings
Adjust in **stayflexi_config.py**:

```python
STAYFLEXI_TIMEOUT = 30  # Request timeout in seconds
STAYFLEXI_MAX_RETRIES = 3  # Number of retry attempts
```

## 🐛 Troubleshooting

### Connection Test Fails
**Error:** "Authentication failed. Check your API key."

**Solution:**
1. Verify credentials in stayflexi_config.py
2. Check if API key is still valid in StayFlexi account
3. Verify PMS ID and Hotel ID match your property

### No Bookings Found
**Error:** "No bookings found for the selected date range."

**Solution:**
1. Check if date range is correct
2. Verify bookings exist in StayFlexi for that period
3. Check hotel ID is correct

### Sync to Database Fails
**Error:** "Error syncing booking..."

**Solution:**
1. Check Supabase connection
2. Verify `reservations` table exists with correct columns
3. Check booking_id field is TEXT type

### Timeout Errors
**Error:** "Request timeout. Server may be unavailable."

**Solution:**
1. Check internet connection
2. Verify StayFlexi API is operational
3. Increase STAYFLEXI_TIMEOUT in config

## 📈 Data Flow

```
StayFlexi Channel Manager API
         ↓
API Client (stayflexi_integration.py)
         ↓
Data Transformation
         ↓
Supabase Database (reservations table)
         ↓
Streamlit UI (stayflexi_ui.py)
         ↓
User (view, export, manage bookings)
```

## 🔐 Security Notes

- ✅ API credentials are configured in code (can be moved to environment variables)
- ✅ Bearer token authentication with StayFlexi
- ✅ Retry logic prevents account lockout
- ✅ Error logging for audit trail
- ✅ User activity tracking via log_activity()

## 📞 Support

**For StayFlexi API Issues:**
- Check Postman collection in repo
- Review StayFlexi API documentation
- Contact StayFlexi support team

**For TIE System Integration:**
- Review stayflexi_integration.py code comments
- Check logs via "Log Report" page
- Verify database schema

## ✨ Next Steps

1. ✅ Deploy changes to production
2. ✅ Train team on "StayFlexi Sync" page
3. ✅ Schedule automated syncs (optional)
4. ✅ Monitor sync status daily
5. ✅ Set up email alerts for sync failures (optional)

---

**Setup Date:** 2026-06-06  
**Property:** Edenbeach Resort  
**Status:** ✅ Ready for Production
