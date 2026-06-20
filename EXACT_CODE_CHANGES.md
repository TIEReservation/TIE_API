# Exact Code Changes for online_reservation.py

## 🎯 STEP 1: ADD IMPORT AT TOP

**Location:** Line 6 (after existing imports)

**Add this line:**
```python
from stayflexi_sync_ui import show_stayflexi_quick_sync_button
```

**Full imports section should look like:**
```python
import streamlit as st
import pandas as pd
from datetime import datetime
import re
from supabase import create_client, Client
from utils import safe_int, safe_float, get_property_name
from stayflexi_sync_ui import show_stayflexi_quick_sync_button  # ✅ ADD THIS LINE
```

---

## 🎯 STEP 2: MODIFY show_online_reservations() FUNCTION

**Location:** Around line 209-227

**CURRENT CODE (BEFORE):**
```python
def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # Upload and Sync section
    st.subheader("Upload and Sync Excel File")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file is not None:
        if st.button("🔄 Sync to Database"):
            with st.spinner("Processing and syncing..."):
                inserted, skipped = process_and_sync_excel(uploaded_file)
                st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                # Reload to reflect changes
                st.session_state.online_reservations = load_online_reservations_from_supabase()

     # View section
    st.subheader("View Online Reservations")
```

**UPDATED CODE (AFTER):**
```python
def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # ✅ ADD STAYFLEXI SYNC SECTION
    st.subheader("🔄 Sync from Stayflexi (Eden Beach Resort)")
    show_stayflexi_quick_sync_button(supabase)
    st.markdown("---")

    # Upload and Sync section
    st.subheader("Upload and Sync Excel File")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file is not None:
        if st.button("🔄 Sync to Database"):
            with st.spinner("Processing and syncing..."):
                inserted, skipped = process_and_sync_excel(uploaded_file)
                st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                # Reload to reflect changes
                st.session_state.online_reservations = load_online_reservations_from_supabase()

     # View section
    st.subheader("View Online Reservations")
```

---

## 📝 COMPLETE UPDATED FUNCTION

Here's the complete `show_online_reservations()` function with both features:

```python
def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # ✅ STAYFLEXI SYNC SECTION (NEW)
    st.subheader("🔄 Sync from Stayflexi (Eden Beach Resort)")
    show_stayflexi_quick_sync_button(supabase)
    st.markdown("---")

    # Upload and Sync section (EXISTING)
    st.subheader("Upload and Sync Excel File")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file is not None:
        if st.button("🔄 Sync to Database"):
            with st.spinner("Processing and syncing..."):
                inserted, skipped = process_and_sync_excel(uploaded_file)
                st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                # Reload to reflect changes
                st.session_state.online_reservations = load_online_reservations_from_supabase()

     # View section
    st.subheader("View Online Reservations")
    if not st.session_state.online_reservations:
        st.info("No online reservations available.")
        return

    df = pd.DataFrame(st.session_state.online_reservations)
    
    # ✅ OPTIMIZED: Add pagination controls
    col_page1, col_page2, col_page3 = st.columns([1, 2, 1])
    with col_page1:
        page_size = st.selectbox("Records per page", [50, 100, 200, 500], index=1, key="page_size_online")
    with col_page2:
        total_records = len(df)
        total_pages = (total_records + page_size - 1) // page_size
        page_number = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, step=1, key="page_num_online")
    with col_page3:
        st.metric("Total Records", total_records)
        st.metric("Total Pages", total_pages)
    # Enhanced filters
    st.subheader("Filters")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_date = st.date_input("Start Date (Check-In)", value=None)
    with col2:
        end_date = st.date_input("End Date (Check-In)", value=None)
    with col3:
        filter_status = st.selectbox("Filter by Booking Status", ["All", "Pending", "Confirmed", "Cancelled", "Completed", "No Show"])
    with col4:
        # Get unique properties for filter
        properties = ["All"] + sorted(df["property"].dropna().unique().tolist())
        filter_property = st.selectbox("Filter by Property", properties)

    # Sorting option
    sort_order = st.radio("Sort by Check-In Date", ["Descending (Newest First)", "Ascending (Oldest First)"], index=0)

    filtered_df = df.copy()
    # Apply filters
    if start_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) <= pd.to_datetime(end_date)]
    if filter_status != "All":
        filtered_df = filtered_df[filtered_df["booking_status"] == filter_status]
    if filter_property != "All":
        filtered_df = filtered_df[filtered_df["property"] == filter_property]

    # Apply sorting
    if sort_order == "Ascending (Oldest First)":
        filtered_df = filtered_df.sort_values(by="check_in", ascending=True)
    else:
        filtered_df = filtered_df.sort_values(by="check_in", ascending=False)

    if filtered_df.empty:
        st.warning("No reservations match the selected filters.")
    else:
        # ✅ OPTIMIZED: Apply pagination
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = filtered_df.iloc[start_idx:end_idx]
        
        st.info(f"Showing records {start_idx + 1} to {min(end_idx, len(filtered_df))} of {len(filtered_df)}")
        
        # Display selected columns
        display_columns = [
            "property", "booking_id", "guest_name", "guest_phone", "check_in", "check_out", "room_no", "room_type",
            "booking_status", "payment_status", "booking_amount", "total_payment_made", "balance_due"
        ]
        st.dataframe(paginated_df[display_columns], use_container_width=True, height=600)
```

---

## ✅ SUMMARY OF CHANGES

**Files to Modify:** 1 file
- `online_reservation.py`

**Changes:**
1. ✅ Add 1 import line at top
2. ✅ Add 3 lines in `show_online_reservations()` function

**Lines Added:**
- Line 6: `from stayflexi_sync_ui import show_stayflexi_quick_sync_button`
- Lines 217-219 (in function):
  ```python
  st.subheader("🔄 Sync from Stayflexi (Eden Beach Resort)")
  show_stayflexi_quick_sync_button(supabase)
  st.markdown("---")
  ```

---

## 🎬 RESULT

After making these changes, your Online Reservations page will have:

1. **Original Excel Upload Section** ✅
   - Upload Excel file button
   - "Sync to Database" button

2. **NEW Stayflexi Sync Section** ✨
   - "⚙️ Setup" button - Configure API credentials
   - "🔄 Sync Now" button - Fetch and import bookings
   - Shows import stats (Imported/Skipped/Errors)
   - Displays sync log details

---

## 🚀 DEPLOYMENT

1. Copy the import line
2. Add to top of `online_reservation.py` (line 7)
3. Find `show_online_reservations()` function
4. Add 3 lines after line 216 (before Excel upload section)
5. Save file
6. Deploy to Streamlit
7. Test the new button!

