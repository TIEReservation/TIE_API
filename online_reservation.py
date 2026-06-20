import streamlit as st
import pandas as pd
from datetime import datetime
import re
from supabase import create_client, Client
from utils import safe_int, safe_float, get_property_name
from stayflexi_sync_ui import show_stayflexi_quick_sync_button
from eden_beach_integration import EdenBeachAPIConfig, EdenBeachAPIClient

# Initialize Supabase client
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
except KeyError as e:
    st.error(f"Missing Supabase secret: {e}. Please check Streamlit Cloud secrets configuration.")
    st.stop()


# ──────────────────────────────────────────────────────────────────[...]
# Eden Beach API – credentials come ONLY from .streamlit/secrets.toml
# Add this block to your secrets file:
#
#   [eden_beach]
#   api_url = "https://api.stayflexi.com"
#   api_key = "your-x-sf-api-key-here"
#   pms_id = "20057"
#   hotel_id = "30357"
#
# ──────────────────────────────────────────────────────────────────[...]

def _get_eden_beach_client():
    """
    Build a configured EdenBeachAPIClient strictly from Streamlit secrets.
    Returns (client, error_message).  error_message is None on success.
    """
    try:
        api_url = st.secrets["eden_beach"]["api_url"]
        api_key = st.secrets["eden_beach"]["api_key"]
        pms_id = st.secrets["eden_beach"]["pms_id"]
        hotel_id = st.secrets["eden_beach"]["hotel_id"]
    except KeyError:
        return None, (
            "Eden Beach API credentials not found. "
            "Add [eden_beach] with api_url, api_key, pms_id, hotel_id to "
            ".streamlit/secrets.toml (local) or Streamlit Cloud Secrets (production)."
        )

    cfg = EdenBeachAPIConfig()
    try:
        cfg.set_api_url(api_url)
        cfg.set_api_key(api_key)
        cfg.set_pms_id(pms_id)
        cfg.set_hotel_id(hotel_id)
    except ValueError as e:
        return None, str(e)

    return EdenBeachAPIClient(cfg), None


# ──────────────────────────────────────────────────────────────────[...]
# Helpers
# ──────────────────────────────────────────────────────────────────[...]

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
    adults = children = infants = 0
    if not pax_str or pd.isna(pax_str):
        return adults, children, infants
    pax_str = re.sub(r'\s*,\s*', ',', pax_str)
    for part in pax_str.split(','):
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
        truncated = reservation.copy()
        string_fields_50 = [
            "property", "booking_id", "guest_name", "guest_phone", "room_no",
            "room_type", "rate_plans", "booking_source", "segment", "staflexi_status",
            "mode_of_booking", "booking_status", "payment_status", "submitted_by", "modified_by"
        ]
        for field in string_fields_50:
            if field in truncated:
                truncated[field] = truncate_string(truncated[field], 50)
        if "remarks" in truncated:
            truncated["remarks"] = truncate_string(truncated["remarks"], 500)
        response = supabase.table("online_reservations").insert(truncated).execute()
        return bool(response.data)
    except Exception as e:
        if '23505' in str(e) and 'duplicate key value' in str(e).lower():
            return False
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


def process_and_sync_excel(uploaded_file):
    """Process the uploaded Excel file and sync to DB."""
    try:
        df = pd.read_excel(uploaded_file, header=0)
        if df.empty:
            st.warning("Uploaded file is empty.")
            return 0, 0
        existing_reservations = load_online_reservations_from_supabase()
        existing_ids = {r["booking_id"] for r in existing_reservations}
        inserted = skipped = 0
        for _, row in df.iterrows():
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
                "submitted_by": "",
                "modified_by": "",
                "total_amount_with_services": total_amount_with_services,
                "ota_gross_amount": ota_gross_amount,
                "ota_commission": ota_commission,
                "ota_tax": ota_tax,
                "ota_net_amount": ota_net_amount,
                "room_revenue": room_revenue
            }
            if insert_online_reservation(reservation):
                inserted += 1
                st.session_state.online_reservations.append(reservation)
        return inserted, skipped
    except Exception as e:
        st.error(f"Error processing Excel file: {e}")
        return 0, 0


# ──────────────────────────────────────────────────────────────────[...]
# Eden Beach API sync logic
# ──────────────────────────────────────────────────────────────────[...]

def sync_eden_beach_bookings_to_online_reservations(start_date=None, end_date=None):
    """
    Fetch bookings from the Eden Beach API and upsert them into online_reservations.
    Returns (inserted, updated, errors, error_message).
    """
    client, err = _get_eden_beach_client()
    if client is None:
        return 0, 0, 0, err

    success, bookings, message = client.fetch_bookings(
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date)   if end_date   else None,
    )

    if not success:
        return 0, 0, 0, message
    if not bookings:
        return 0, 0, 0, None

    existing_ids = {r["booking_id"] for r in load_online_reservations_from_supabase()}
    inserted = updated = errors = 0

    for booking in bookings:
        try:
            booking_id = str(booking.get("id") or booking.get("booking_id") or "")
            if not booking_id:
                errors += 1
                continue

            check_in_raw  = booking.get("check_in_date")  or booking.get("checkin")
            check_out_raw = booking.get("check_out_date") or booking.get("checkout")

            pax_str = booking.get("pax", "")
            if pax_str:
                no_of_adults, no_of_children, no_of_infant = parse_pax(str(pax_str))
            else:
                no_of_adults   = safe_int(booking.get("adults",   booking.get("number_of_guests", 0)))
                no_of_children = safe_int(booking.get("children", 0))
                no_of_infant   = safe_int(booking.get("infants",  0))

            total_pax          = no_of_adults + no_of_children + no_of_infant
            booking_amount     = safe_float(booking.get("total_price")        or booking.get("booking_amount"))
            total_payment_made = safe_float(booking.get("total_payment_made") or booking.get("amount_paid"))
            balance_due        = safe_float(booking.get("balance_due")        or max(0.0, booking_amount - total_payment_made))

            if total_payment_made >= booking_amount and booking_amount > 0:
                payment_status = "Fully Paid"
            elif total_payment_made > 0:
                payment_status = "Partially Paid"
            else:
                payment_status = "Not Paid"

            reservation = {
                "property":                   "Eden Beach Resort",
                "booking_id":                 truncate_string(booking_id, 50),
                "booking_made_on":            booking.get("booking_made_on") or booking.get("created_at"),
                "guest_name":                 truncate_string(booking.get("guest_name") or booking.get("customer_name", ""), 50),
                "guest_phone":                truncate_string(booking.get("phone")      or booking.get("customer_phone", ""), 50),
                "check_in":                   check_in_raw,
                "check_out":                  check_out_raw,
                "no_of_adults":               no_of_adults,
                "no_of_children":             no_of_children,
                "no_of_infant":               no_of_infant,
                "total_pax":                  total_pax,
                "room_no":                    truncate_string(booking.get("room_ids") or booking.get("room_no", ""), 50),
                "room_type":                  truncate_string(booking.get("room_type", ""), 50),
                "rate_plans":                 truncate_string(booking.get("rate_plan") or booking.get("rate_plans", ""), 50),
                "booking_source":             truncate_string(booking.get("source")    or booking.get("booking_source", "Eden Beach API"), 50),
                "segment":                    truncate_string(booking.get("segment", ""), 50),
                "staflexi_status":            truncate_string(booking.get("status", ""), 50),
                "booking_confirmed_on":       booking.get("booking_confirmed_on"),
                "booking_amount":             booking_amount,
                "total_payment_made":         total_payment_made,
                "balance_due":                balance_due,
                "mode_of_booking":            truncate_string(booking.get("mode_of_booking") or booking.get("source", "Eden Beach API"), 50),
                "booking_status":             truncate_string(booking.get("booking_status", "Pending"), 50),
                "payment_status":             payment_status,
                "remarks":                    truncate_string(booking.get("special_requests") or booking.get("notes", ""), 500),
                "submitted_by":               "",
                "modified_by":                "",
                "total_amount_with_services": safe_float(booking.get("total_amount_with_services")),
                "ota_gross_amount":           safe_float(booking.get("ota_gross_amount")),
                "ota_commission":             safe_float(booking.get("ota_commission")),
                "ota_tax":                    safe_float(booking.get("ota_tax")),
                "ota_net_amount":             safe_float(booking.get("ota_net_amount")),
                "room_revenue":               safe_float(booking.get("room_revenue")),
            }

            if booking_id in existing_ids:
                supabase.table("online_reservations") \
                    .update(reservation) \
                    .eq("booking_id", booking_id) \
                    .execute()
                updated += 1
            else:
                if insert_online_reservation(reservation):
                    inserted += 1
                    existing_ids.add(booking_id)

        except Exception as e:
            errors += 1
            st.warning(f"⚠️ Could not sync booking {booking.get('id', '?')}: {e}")

    return inserted, updated, errors, None


# ──────────────────────────────────────────────────────────────────[...]
# Eden Beach sync UI block
# ──────────────────────────────────────────────────────────────────[...]

def show_eden_beach_sync_section():
    """Render the Eden Beach API sync card inside the Online Reservations page."""
    st.subheader("🏖️ Eden Beach API Sync")

    # Guard: show a clear message if secrets are not set yet
    eb_secrets_ok = (
        "eden_beach" in st.secrets
        and st.secrets["eden_beach"].get("api_url")
        and st.secrets["eden_beach"].get("api_key")
        and st.secrets["eden_beach"].get("pms_id")
        and st.secrets["eden_beach"].get("hotel_id")
    )
    if not eb_secrets_ok:
        st.warning(
            "🔐 Eden Beach API credentials not configured.  \n"
            "Add the following to **`.streamlit/secrets.toml`** (local) or  \n"
            "**Streamlit Cloud → App Settings → Secrets** (production):\n\n"
            "```toml\n"
            "[eden_beach]\n"
            "api_url = \"https://api.stayflexi.com\"\n"
            "api_key = \"your-x-sf-api-key-here\"\n"
            "pms_id = \"20057\"\n"
            "hotel_id = \"30357\"\n"
            "```"
        )
        st.divider()
        return

    # Optional date-range filter
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        eb_start = st.date_input("Sync From (Check-In date)", value=None, key="eb_sync_start")
    with col_d2:
        eb_end = st.date_input("Sync To (Check-In date)",   value=None, key="eb_sync_end")

    col_test, col_sync = st.columns([1, 2])

    # Test connection
    with col_test:
        if st.button("🔌 Test Connection", key="eb_test_conn"):
            client, err = _get_eden_beach_client()
            if client is None:
                st.error(f"Configuration error: {err}")
            else:
                with st.spinner("Testing Eden Beach API connection…"):
                    ok, msg = client.test_connection()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    # THE SYNC BUTTON
    with col_sync:
        if st.button("🔄 Sync Eden Beach API → Database", key="eb_sync_btn", type="primary"):
            with st.spinner("Fetching & syncing Eden Beach bookings…"):
                inserted, updated, errors, err_msg = sync_eden_beach_bookings_to_online_reservations(
                    start_date=eb_start if eb_start else None,
                    end_date=eb_end   if eb_end   else None,
                )
            if err_msg:
                st.error(f"❌ Sync failed: {err_msg}")
            else:
                st.success(
                    f"✅ Eden Beach sync complete!  "
                    f"Inserted: **{inserted}** | Updated: **{updated}** | Errors: **{errors}**"
                )
                st.session_state.online_reservations = load_online_reservations_from_supabase()

    st.divider()


# ──────────────────────────────────────────────────────────────────[...]
# Main page
# ──────────────────────────────────────────────────────────────────[...]

def show_online_reservations():
    """Display online reservations page with upload and view."""
    st.title("🔥 Online Reservations")
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # ✅ STAYFLEXI SYNC SECTION (EXISTING)
    st.subheader("🔄 Sync from Stayflexi (Eden Beach Resort)")
    show_stayflexi_quick_sync_button(supabase)
    st.markdown("---")

    # 🏖️ EDEN BEACH API SYNC SECTION (NEW)
    show_eden_beach_sync_section()

    # Upload and Sync section (EXISTING)
    st.subheader("📤 Upload and Sync Excel File")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    if uploaded_file is not None:
        if st.button("🔄 Sync to Database"):
            with st.spinner("Processing and syncing..."):
                inserted, skipped = process_and_sync_excel(uploaded_file)
                st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                st.session_state.online_reservations = load_online_reservations_from_supabase()

    # View section
    st.subheader("View Online Reservations")
    if not st.session_state.online_reservations:
        st.info("No online reservations available.")
        return

    df = pd.DataFrame(st.session_state.online_reservations)

    # Pagination controls
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

    # Filters
    st.subheader("Filters")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_date = st.date_input("Start Date (Check-In)", value=None)
    with col2:
        end_date = st.date_input("End Date (Check-In)", value=None)
    with col3:
        filter_status = st.selectbox("Filter by Booking Status", ["All", "Pending", "Confirmed", "Cancelled", "Completed", "No Show"])
    with col4:
        properties = ["All"] + sorted(df["property"].dropna().unique().tolist())
        filter_property = st.selectbox("Filter by Property", properties)

    sort_order = st.radio("Sort by Check-In Date", ["Descending (Newest First)", "Ascending (Oldest First)"], index=0)

    filtered_df = df.copy()
    if start_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) <= pd.to_datetime(end_date)]
    if filter_status != "All":
        filtered_df = filtered_df[filtered_df["booking_status"] == filter_status]
    if filter_property != "All":
        filtered_df = filtered_df[filtered_df["property"] == filter_property]

    if sort_order == "Ascending (Oldest First)":
        filtered_df = filtered_df.sort_values(by="check_in", ascending=True)
    else:
        filtered_df = filtered_df.sort_values(by="check_in", ascending=False)

    if filtered_df.empty:
        st.warning("No reservations match the selected filters.")
    else:
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = filtered_df.iloc[start_idx:end_idx]
        st.info(f"Showing records {start_idx + 1} to {min(end_idx, len(filtered_df))} of {len(filtered_df)}")
        display_columns = [
            "property", "booking_id", "guest_name", "guest_phone", "check_in", "check_out", "room_no", "room_type",
            "booking_status", "payment_status", "booking_amount", "total_payment_made", "balance_due"
        ]
        st.dataframe(paginated_df[display_columns], use_container_width=True, height=600)
