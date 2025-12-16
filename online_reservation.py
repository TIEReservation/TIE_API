import streamlit as st
import pandas as pd
from datetime import datetime
import re
from supabase import create_client, Client
from utils import safe_int, safe_float, get_property_name
import requests
from config import STAYFLEXI_API_TOKEN, STAYFLEXI_API_URL  # Import URL and token from config

# Initialize Supabase client
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
except KeyError as e:
    st.error(f"Missing Supabase secret: {e}. Please check Streamlit Cloud secrets configuration.")
    st.stop()

def parse_date(dt_str):
    """Parse date string with or without time."""
    if not dt_str or pd.isna(dt_str):
        return None
    try:
        return datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S").date()
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%d/%m/%Y").date()
        except ValueError:
            return None

def parse_pax(pax_str):
    """Parse pax string to get adults, children, infants."""
    adults = 0
    children = 0
    infants = 0
    if not pax_str or pd.isna(pax_str):
        return adults, children, infants
    # Normalize spaces
    pax_str = re.sub(r'\s*,\s*', ',', pax_str)
    parts = pax_str.split(',')
    for part in parts:
        part = part.strip()
        if 'Adults:' in part:
            try:
                adults += int(part.split('Adults:')[1].strip())
            except ValueError:
                pass
        elif 'Children:' in part:
            try:
                children += int(part.split('Children:')[1].strip())
            except ValueError:
                pass
        elif 'Infant:' in part:
            try:
                infants += int(part.split('Infant:')[1].strip())
            except ValueError:
                pass
    return adults, children, infants

def truncate_string(value, max_length=50):
    """Truncate string to specified length."""
    if not value:
        return value
    return str(value)[:max_length] if len(str(value)) > max_length else str(value)

def insert_online_reservation(reservation):
    """Insert a new online reservation into Supabase."""
    try:
        # Truncate string fields to prevent database errors
        truncated_reservation = reservation.copy()
        
        # List of fields that might have character limits
        string_fields_50 = [
            "property", "booking_id", "guest_name", "guest_phone", "room_no", 
            "room_type", "rate_plans", "booking_source", "segment", "staflexi_status",
            "mode_of_booking", "booking_status", "payment_status", "submitted_by", "modified_by"
        ]
        
        # Truncate to 50 characters for standard fields
        for field in string_fields_50:
            if field in truncated_reservation:
                truncated_reservation[field] = truncate_string(truncated_reservation[field], 50)
        
        # Remarks might have a longer limit, but let's be safe and truncate to 500
        if "remarks" in truncated_reservation:
            truncated_reservation["remarks"] = truncate_string(truncated_reservation["remarks"], 500)
        
        response = supabase.table("online_reservations").insert(truncated_reservation).execute()
        return bool(response.data)
    except Exception as e:
        if '23505' in str(e) and 'duplicate key value' in str(e).lower():
            return False  # Silently skip duplicate booking_id errors
        st.error(f"Error inserting online reservation: {e}")
        return False

def load_online_reservations_from_supabase():
    """Load online reservations from Supabase."""
    try:
        response = supabase.table("online_reservations").select("*").order("check_in", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading online reservations: {e}")
        return []

def fetch_stayflexi_bookings(pms_id=None):
    """Fetch bookings from Stayflexi API with corrected auth."""
    try:
        # Use the URL from config; append pmsId if provided
        url = STAYFLEXI_API_URL
        if pms_id:
            url += f"?pmsId={pms_id}"
        headers = {
            "X-SF-API-KEY": STAYFLEXI_API_TOKEN  # Corrected header per API doc
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Assuming the response is a list of booking dicts or has a key like 'bookings' or 'data'
            # Adjust based on actual response structure; for now, assume it's a list
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                st.warning(f"Unexpected API response format: {data}")
                return []
        else:
            st.error(f"API request failed with status {response.status_code}: {response.text}")
            if response.status_code == 401:
                st.error("401 Unauthorized: Check your API token and pmsId. Contact admin@stayflexi.com for credentials.")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching from Stayflexi API: {e}")
        return []

# ... (process_and_sync_api, process_and_sync_excel, and show_online_reservations remain the same as before)

def process_and_sync_api(bookings_data):
    """Process the API data and sync to DB. Assumes similar structure to Excel columns."""
    try:
        existing_reservations = load_online_reservations_from_supabase()
        existing_ids = {r["booking_id"] for r in existing_reservations}
        inserted = 0
        skipped = 0
        for booking in bookings_data:
            # Map API fields to Excel-like keys; adjust keys based on actual API response
            # (Add st.write(booking) temporarily to inspect structure if needed)
            row = {
                "hotel id": booking.get("hotel_id") or booking.get("hotelId"),
                "hotel name": booking.get("hotel_name") or booking.get("hotelName"),
                "booking id": booking.get("booking_id") or booking.get("bookingId"),
                "booking_made_on": booking.get("booking_made_on") or booking.get("bookingMadeOn"),
                "customer_name": booking.get("customer_name") or booking.get("guest_name") or booking.get("guestName"),
                "customer_phone": booking.get("customer_phone") or booking.get("guest_phone") or booking.get("guestPhone"),
                "checkin": booking.get("check_in") or booking.get("checkIn"),
                "checkout": booking.get("check_out") or booking.get("checkOut"),
                "pax": booking.get("pax") or f"Adults:{booking.get('adults', 0)},Children:{booking.get('children', 0)},Infant:{booking.get('infants', 0)}",
                "room ids": booking.get("room_ids") or booking.get("roomId") or booking.get("room_no") or booking.get("roomNo"),
                "room types": booking.get("room_types") or booking.get("roomType"),
                "rate_plans": booking.get("rate_plans") or booking.get("ratePlan"),
                "booking_source": booking.get("booking_source") or booking.get("channel") or "Stayflexi",
                "segment": booking.get("segment"),
                "status": booking.get("status") or "Confirmed",
                "booking_amount": booking.get("booking_amount") or booking.get("total_amount"),
                "Total Payment Made": booking.get("total_payment_made") or booking.get("payment_made"),
                "balance_due": booking.get("balance_due"),
                "special_requests": booking.get("special_requests") or booking.get("remarks"),
                "total_amount_with_services": booking.get("total_amount_with_services"),
                "ota_gross_amount": booking.get("ota_gross_amount"),
                "ota_commission": booking.get("ota_commission"),
                "ota_tax": booking.get("ota_tax"),
                "ota_net_amount": booking.get("ota_net_amount"),
                "room_revenue": booking.get("room_revenue"),
            }
            
            # ... (rest of the function is identical to previous version)
            hotel_id = str(safe_int(row.get("hotel id", "")))
            property_name = get_property_name(hotel_id)
            if property_name == "Unknown Property":
                property_name = str(row.get("hotel name", "")).split("-")[0].strip() if row.get("hotel name") else ""
            booking_id = str(row.get("booking id", ""))
            if not booking_id:
                continue
            if booking_id in existing_ids:
                skipped += 1
                continue
            # (All the parsing and reservation dict creation remains the same)
            booking_made_on = parse_date(row.get("booking_made_on"))
            guest_name = truncate_string(row.get("customer_name", ""), 50)
            guest_phone = truncate_string(row.get("customer_phone", ""), 50)
            check_in = parse_date(row.get("checkin"))
            check_out = parse_date(row.get("checkout"))
            pax_str = str(row.get("pax", ""))
            no_of_adults, no_of_children, no_of_infant = parse_pax(pax_str)
            total_pax = no_of_adults + no_of_children + no_of_infant
            room_no = truncate_string(row.get("room ids", ""), 50)
            room_type = truncate_string(row.get("room types", ""), 50)
            rate_plans = truncate_string(row.get("rate_plans", ""), 50)
            booking_source = truncate_string(row.get("booking_source", ""), 50)
            segment = truncate_string(row.get("segment", ""), 50)
            staflexi_status = truncate_string(row.get("status", ""), 50)
            booking_confirmed_on = None
            booking_amount = safe_float(row.get("booking_amount"))
            total_payment_made = safe_float(row.get("Total Payment Made"))
            balance_due = safe_float(row.get("balance_due"))
            mode_of_booking = truncate_string(booking_source, 50)
            booking_status = "Pending"
            if total_payment_made >= booking_amount:
                payment_status = "Fully Paid"
            elif total_payment_made > 0:
                payment_status = "Partially Paid"
            else:
                payment_status = "Not Paid"
            remarks = truncate_string(row.get("special_requests", ""), 500)
            submitted_by = ""
            modified_by = ""
            total_amount_with_services = safe_float(row.get("total_amount_with_services"))
            ota_gross_amount = safe_float(row.get("ota_gross_amount"))
            ota_commission = safe_float(row.get("ota_commission"))
            ota_tax = safe_float(row.get("ota_tax"))
            ota_net_amount = safe_float(row.get("ota_net_amount"))
            room_revenue = safe_float(row.get("room_revenue"))
            reservation = {
                "property": property_name,
                "booking_id": booking_id,
                "booking_made_on": str(booking_made_on) if booking_made_on else None,
                "guest_name": guest_name,
                "guest_phone": guest_phone,
                "check_in": str(check_in) if check_in else None,
                "check_out": str(check_out) if check_out else None,
                "no_of_adults": no_of_adults,
                "no_of_children": no_of_children,
                "no_of_infant": no_of_infant,
                "total_pax": total_pax,
                "room_no": room_no,
                "room_type": room_type,
                "rate_plans": rate_plans,
                "booking_source": booking_source,
                "segment": segment,
                "staflexi_status": staflexi_status,
                "booking_confirmed_on": booking_confirmed_on,
                "booking_amount": booking_amount,
                "total_payment_made": total_payment_made,
                "balance_due": balance_due,
                "mode_of_booking": mode_of_booking,
                "booking_status": booking_status,
                "payment_status": payment_status,
                "remarks": remarks,
                "submitted_by": submitted_by,
                "modified_by": modified_by,
                "total_amount_with_services": total_amount_with_services,
                "ota_gross_amount": ota_gross_amount,
                "ota_commission": ota_commission,
                "ota_tax": ota_tax,
                "ota_net_amount": ota_net_amount,
                "room_revenue": room_revenue
            }
            if insert_online_reservation(reservation):
                inserted += 1
                if 'online_reservations' in st.session_state:
                    st.session_state.online_reservations.append(reservation)
            else:
                skipped += 1
        return inserted, skipped
    except Exception as e:
        st.error(f"Error processing API data: {e}")
        return 0, 0

def process_and_sync_excel(uploaded_file):
    # (Identical to previous version - omitted for brevity)
    pass  # Replace with the full function from before

def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # API Sync section
    st.subheader("🔄 Sync from Stayflexi API")
    col1, col2 = st.columns(2)
    with col1:
        pms_id_input = st.text_input("PMS ID (optional, from Stayflexi)", placeholder="Enter your pmsId if required")
    with col2:
        if st.button("Sync Bookings from Stayflexi API", use_container_width=True):
            with st.spinner("Fetching bookings from Stayflexi API and syncing..."):
                pms_id = pms_id_input.strip() if pms_id_input else None
                bookings_data = fetch_stayflexi_bookings(pms_id)
                if bookings_data:
                    inserted, skipped = process_and_sync_api(bookings_data)
                    st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                    # Reload to reflect changes
                    st.session_state.online_reservations = load_online_reservations_from_supabase()
                else:
                    st.warning("No new bookings fetched from API.")

    # (Rest of the function - Excel upload and view table - identical to previous)
    st.subheader("Upload and Sync Excel File")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file is not None:
        if st.button("🔄 Sync to Database"):
            with st.spinner("Processing and syncing..."):
                inserted, skipped = process_and_sync_excel(uploaded_file)
                st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                st.session_state.online_reservations = load_online_reservations_from_supabase()

    st.subheader("View Online Reservations")
    if not st.session_state.online_reservations:
        st.info("No online reservations available.")
        return

    df = pd.DataFrame(st.session_state.online_reservations)
    # Filters and table display (identical - omitted for brevity)
    # ... (add the full filters and dataframe code from previous version)
