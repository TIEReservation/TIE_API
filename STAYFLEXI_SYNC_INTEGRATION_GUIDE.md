# Stayflexi Sync Integration Guide for Eden Beach Resort

## 📋 Summary
This integration allows you to:
- ✅ Pull bookings from Stayflexi API for Eden Beach Resort
- ✅ Automatically import them into your local database
- ✅ Maintain local status independently (changes here won't affect Stayflexi)
- ✅ Prevent duplicate bookings using booking_id
- ✅ Add a quick sync button to Online Reservations page

---

## 🔧 Step-by-Step Integration Instructions

### **STEP 1: Update `online_reservation.py`**

**Location:** `online_reservation.py` (around line 209, before `show_online_reservations()` function)

**ACTION:** Add this import at the top of the file:
```python
from stayflexi_sync_ui import show_stayflexi_quick_sync_button
```

**LOCATION TO ADD:** After line 6 (after other imports)

---

### **STEP 2: Add Sync Button to Online Reservations Page**

**Location:** Inside `show_online_reservations()` function (after line 211)

**BEFORE:** (Current code)
```python
def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # Upload and Sync section
    st.subheader("Upload and Sync Excel File")
```

**AFTER:** (Updated code with Stayflexi button)
```python
def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # ✅ ADD STAYFLEXI SYNC BUTTON HERE
    st.subheader("🔄 Sync Bookings")
    show_stayflexi_quick_sync_button(supabase)
    st.markdown("---")

    # Upload and Sync section
    st.subheader("Upload and Sync Excel File")
```

---

### **STEP 3: Get Stayflexi Credentials**

**You need:**
1. **Stayflexi API Token** - Get from your Stayflexi account settings
2. **Stayflexi Email** - Your registered email in Stayflexi

**Where to find:**
- Log in to your Stayflexi account
- Go to Settings → API Keys
- Copy your API Token
- Use your registered email

---

### **STEP 4: Configuration in App**

1. Open your app in Streamlit
2. Navigate to **Online Reservations** page
3. Click **⚙️ Setup** button
4. Enter:
   - Stayflexi API Token
   - Stayflexi Email
5. Click **💾 Save & Connect**
6. System will test the connection

---

### **STEP 5: Sync Bookings**

**To sync bookings:**

1. Go to **Online Reservations** page
2. Click **🔄 Sync Now** button
3. System will:
   - Fetch bookings from Stayflexi (last 30 days + next 90 days)
   - Check for duplicates using booking_id
   - Import only NEW bookings
   - Skip existing bookings
   - Show results

**What you'll see:**
- ✅ Number of imported bookings
- ⏭️ Number of skipped duplicates
- ❌ Number of errors (if any)
- 📋 Detailed sync log

---

## 📁 Files Created/Modified

### **New Files:**
1. `stayflexi_sync.py` - Core sync logic
2. `stayflexi_sync_ui.py` - Streamlit UI components

### **Modified Files:**
1. `online_reservation.py` - Add import + button

---

## 🔑 How It Works

### **Sync Flow:**
```
Stayflexi API
     ↓
Fetch Bookings (date range)
     ↓
Check Local Database for duplicates
     ↓
Import NEW bookings only
     ↓
Update Online Reservations table
```

### **Duplicate Prevention:**
- Checks booking_id in local database
- If booking_id exists → SKIP
- If booking_id is new → IMPORT

### **Local Status Management:**
- Imported bookings get default status: **"Confirmed"**
- You can edit status in your system
- Changes are LOCAL only (not synced back to Stayflexi)

---

## 💾 Data Mapping

### Stayflexi → Local Database:

| Stayflexi Field | Local Field |
|---|---|
| id | booking_id |
| guestName | guest_name |
| guestPhone | mobile_no |
| guestEmail | email |
| checkInDate | check_in |
| checkOutDate | check_out |
| roomNumber | room_no |
| roomType | room_type |
| adults | no_of_adults |
| children | no_of_children |
| infants | no_of_infants |
| totalPrice | total_tariff |
| paidAmount | advance_amount |
| paymentMethod | advance_mop |

---

## ✨ Features

✅ **One-Way Sync** - Only pulls from Stayflexi, no push back  
✅ **Duplicate Prevention** - Booking ID checking  
✅ **Local Status** - Maintained independently  
✅ **Error Handling** - Retry logic + detailed logs  
✅ **Date Filtering** - Fetch specific date ranges  
✅ **User-Friendly** - Simple button interface  
✅ **Secure** - API token stored in session (not persistent)  

---

## 🚀 Quick Start Checklist

- [ ] Get Stayflexi API Token
- [ ] Get Stayflexi Email
- [ ] Update `online_reservation.py` with import
- [ ] Add sync button to online_reservations() function
- [ ] Deploy changes
- [ ] Test connection in app
- [ ] Perform first sync
- [ ] Verify bookings imported

---

## 🛠️ Troubleshooting

### **"Connection Failed" Error**
- ❌ Check API token is correct
- ❌ Check email is correct
- ❌ Verify internet connection
- ❌ Confirm Stayflexi API is accessible

### **"Authentication Failed" Error**
- ❌ Verify credentials with Stayflexi support
- ❌ Check if API token has expired
- ❌ Regenerate API token if needed

### **"Sync Failed" Error**
- ❌ Check booking_id format
- ❌ Verify database connection
- ❌ Check Stayflexi response format
- ❌ Review sync log for details

### **Bookings Not Importing**
- ❌ All bookings might be duplicates
- ❌ Check sync log for "Skipped" entries
- ❌ Try different date range
- ❌ Verify booking_id exists in response

---

## 📞 Support

For issues or questions:
1. Check sync log for error details
2. Verify API credentials
3. Test connection explicitly
4. Review this guide
5. Contact support with sync log

---

## 🔐 Security Notes

🔒 API tokens stored in Streamlit session (not persistent)  
🔒 Never commit credentials to version control  
🔒 Use environment variables in production  
🔒 Sync happens on-demand (no auto-sync enabled)  

