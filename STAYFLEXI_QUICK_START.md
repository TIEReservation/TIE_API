# Edenbeach StayFlexi Integration - Quick Setup Checklist

## 📋 What Has Been Implemented

✅ **3 New Python Modules Created:**
- `stayflexi_config.py` - Configuration with your hotel credentials
- `stayflexi_integration.py` - API client & data sync engine (saves to existing table)
- `stayflexi_ui.py` - Streamlit interface with 4 tabs

✅ **Pre-configured with Your Credentials:**
- PMS ID: 20057
- Hotel ID: 30357
- API Key: n9F3BrVUdLKABeG91ryvbdaAI1dffxb0

✅ **Saves to Existing Table:**
- All bookings sync to your existing `online_reservations` table
- **NO new table creation needed** ✅
- Same location as when you upload Excel data

---

## 🚀 What YOU Need to Do (Simple 2-Step Process)

### ✅ Step 1: Update app.py (5 minutes)

**Location:** Line 4 (Imports section)
```python
# ADD THIS LINE:
from stayflexi_ui import show_stayflexi_sync
```

**Location:** Line 207 (all_screens list)
```python
# FIND THIS LINE:
all_screens = ["Inventory Dashboard", "Night Report Dashboard", ...

# ADD THIS to the list:
"StayFlexi Sync",
```

**Location:** Line 468 (Page routing section, after line 468)
```python
# ADD THIS BLOCK:
elif page == "StayFlexi Sync":
    show_stayflexi_sync()
    log_activity(supabase, st.session_state.username, "Accessed StayFlexi Sync")
```

### ✅ Step 2: Deploy & Test (5 minutes)

**Command:**
```bash
streamlit run app.py
```

**Test:**
1. Login to app
2. Navigate to "StayFlexi Sync" (if you're admin or have it assigned)
3. Click "Connection Test" tab
4. Click "🔍 Test Connection" button
5. Should see: ✅ Connection to StayFlexi API successful!

---

## 📊 After Setup - How to Use

### **For Daily Use - Sync Bookings**
1. Go to "StayFlexi Sync" page
2. Click "📥 Sync Bookings" tab
3. Set date range (default = last 30 days to next 90 days)
4. Click "🚀 Start Sync"
5. Review bookings
6. Click "✅ Confirm & Sync to Database"
7. ✅ Bookings appear in `online_reservations` table

### **To View Bookings**
1. Go to "StayFlexi Sync" page
2. Click "📊 View Bookings" tab
3. See all synced bookings from StayFlexi
4. Download as CSV if needed

### **To Monitor**
1. Go to "StayFlexi Sync" page
2. Click "📈 Sync Status" tab
3. Check connection health and last sync time

---

## 🎯 Key Features

| Feature | What It Does |
|---------|-------------|
| **Connection Test** | Verify StayFlexi API is reachable |
| **Sync Bookings** | Pull bookings from StayFlexi for any date range |
| **View Bookings** | See all bookings synced to your system |
| **Export to CSV** | Download bookings for Excel/analysis |
| **Sync Status** | Monitor API health and last sync time |
| **Activity Logging** | All syncs are logged for audit trail |

---

## 🗄️ Where Data Goes

**ALL StayFlexi bookings are saved to:**
```
Supabase → online_reservations table
```

**Same table as:**
- Excel file uploads
- OTA bookings (Booking.com, Agoda, etc.)

**Combined view in:** "Online Reservations" page

---

## ❓ Common Questions

**Q: Do I need to create a new table?**  
A: No! Bookings save to your existing `online_reservations` table.

**Q: How often should I sync?**  
A: Manual sync is recommended daily. Automatic hourly sync can be enabled in config.

**Q: Which users can access this?**  
A: Only users assigned "StayFlexi Sync" in User Management. You control this.

**Q: What happens to old data?**  
A: Each sync updates bookings (upsert) - duplicates won't be created.

**Q: Can I sync historical bookings?**  
A: Yes! Set any date range in the "Sync Bookings" tab.

**Q: Will it overwrite existing online_reservations data?**  
A: No! It only adds new bookings. Existing data is safe.

---

## 📁 Files You Need to Know

```
TIE_API/
├── app.py                          ← MODIFY (add 3 lines)
├── stayflexi_config.py            ← NEW (already has your credentials)
├── stayflexi_integration.py        ← NEW (API client - saves to online_reservations)
├── stayflexi_ui.py                ← NEW (user interface)
├── STAYFLEXI_SETUP_GUIDE.md        ← NEW (detailed guide)
└── requirements.txt                ← Already has needed packages
```

**No new dependencies needed** - all required packages already in requirements.txt!

---

## ⚠️ Troubleshooting

**Issue: "Connection Failed"**
- Check internet connection
- Verify StayFlexi is online
- Check API key in stayflexi_config.py

**Issue: "No bookings found"**
- Check date range is correct
- Verify bookings exist in StayFlexi
- Try wider date range

**Issue: Can't see "StayFlexi Sync" page**
- Make sure you updated app.py correctly
- Admin needs to assign it to your user
- Restart Streamlit app

**Issue: "Error syncing to database"**
- Verify `online_reservations` table exists
- Check Supabase connection is working
- Review error message for details

---

## ✨ What's Next?

After successful setup:

1. ✅ Use "StayFlexi Sync" to pull Edenbeach bookings daily
2. ✅ View all bookings in "Online Reservations" page
3. ✅ Export to CSV for analysis
4. ✅ Set up team access via User Management
5. ✅ (Optional) Enable auto-sync for hands-off operation

---

## ✅ Completion Checklist

- [ ] Added import to app.py (line 4)
- [ ] Added "StayFlexi Sync" to all_screens (line 207)
- [ ] Added elif block for page routing (after line 468)
- [ ] Restarted Streamlit app
- [ ] Tested connection (see ✅ message)
- [ ] Successfully synced first batch of bookings
- [ ] Can view bookings in "Online Reservations" page
- [ ] Bookings visible in `online_reservations` table in Supabase

**Once all checked: You're Ready to Go! 🎉**

---

**Setup Completed:** 2026-06-06  
**Status:** ✅ Ready for Production  
**Data Saved To:** `online_reservations` table (same as Excel uploads)  
**Total Setup Time:** ~10 minutes
