import streamlit as st
import os
from supabase import create_client, Client
from directreservation import show_new_reservation_form, show_reservations, show_edit_reservations, show_analytics, load_reservations_from_supabase
from online_reservation import show_online_reservations, load_online_reservations_from_supabase
from booking_date_report import show_booking_date_report
from booking_date_report import show_booking_date_report
from booking_date_report_datewise import show_datewise_booking_report  
from checkin_date_report_datewise import show_checkin_date_report  
try:
    from editOnline import show_edit_online_reservations
    edit_online_available = True
except Exception as e:
    st.error(f"Failed to import editOnline module: {e}. 'Edit Online Reservations' page will be disabled.")
    show_edit_online_reservations = None
    edit_online_available = False
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
# Try to import target achievement module
try:
    from target_achievement_report import show_target_achievement_report
    target_achievement_available = True
except Exception as e:
    st.warning(f"Target Achievement module not found: {e}")
    show_target_achievement_report = None
    target_achievement_available = False
# Page config
st.set_page_config(
    page_title="TIE Reservations",
    page_icon="https://github.com/TIEReservation/TIEReservation-System/raw/main/TIE_Logo_Icon.png",
    layout="wide"
)
# Display logo in top-left corner
st.image("https://github.com/TIEReservation/TIEReservation-System/raw/main/TIE_Logo_Icon.png", width=100)

# ✅ OPTIMIZED: Initialize Supabase client with caching
@st.cache_resource
def get_supabase_client():
    """Create a single Supabase client for the entire session."""
    try:
        os.environ["SUPABASE_URL"] = "https://oxbrezracnmazucnnqox.supabase.co"
        os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94YnJlenJhY25tYXp1Y25ucW94Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3NjUxMTgsImV4cCI6MjA2OTM0MTExOH0.nqBK2ZxntesLY9qYClpoFPVnXOW10KrzF-UI_DKjbKo"
        return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {e}")
        st.stop()

supabase: Client = get_supabase_client()
def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.reservations = []
        st.session_state.online_reservations = []
        st.session_state.edit_mode = False
        st.session_state.edit_index = None
        st.session_state.online_edit_mode = False
        st.session_state.online_edit_index = None
        st.session_state.current_page = "Direct Reservations"
        st.session_state.selected_booking_id = None
        st.session_state.user_data = None
        st.session_state.permissions = None
    if not st.session_state.authenticated:
        st.title("TIE Reservations Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            authenticated = False
           
            # Check if Admin hardcoded credential (bootstrap account)
            if username == "Admin" and password == "TieAdmin2024":
                st.session_state.authenticated = True
                st.session_state.username = "Admin"
                st.session_state.role = "Admin"
                st.session_state.current_page = "User Management"
                st.session_state.permissions = {"add": True, "edit": True, "delete": True}
                st.session_state.user_data = None
                authenticated = True
            else:
                # All users (including Admin if in DB) authenticate through database with plain text password
                try:
                    user_data = validate_user(supabase, username, password)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = user_data["role"]
                        st.session_state.user_data = user_data
                        st.session_state.permissions = user_data.get("permissions", {"add": False, "edit": False, "delete": False})
                       
                        # Get user's allowed screens
                        user_screens = user_data.get("screens", ["Direct Reservations"])
                        st.session_state.current_page = user_screens[0] if user_screens else "Direct Reservations"
                        authenticated = True
                    else:
                        st.error("Invalid username or password.")
                except Exception as e:
                    st.error(f"Database authentication failed: {e}")
                    st.error("Invalid username or password.")
           
            if authenticated:
                query_params = st.query_params
                query_booking_id = query_params.get("booking_id", [None])[0]
                if query_booking_id:
                    st.session_state.selected_booking_id = query_booking_id
                try:
                    if st.session_state.role != "Admin" or st.session_state.user_data is not None:
                        st.session_state.reservations = load_reservations_from_supabase()
                        st.session_state.online_reservations = load_online_reservations_from_supabase()
                    st.success(f"{username} login successful!")
                except Exception as e:
                    st.session_state.reservations = []
                    st.session_state.online_reservations = []
                    st.warning(f"{username} login successful, but failed to fetch data: {e}")
                st.rerun()
        st.stop()
    else:
        query_params = st.query_params
        query_page = query_params.get("page", [st.session_state.current_page])[0]
       
        # Define valid screens based on role
        if st.session_state.role == "Admin" and st.session_state.user_data is None:
            # Hardcoded Admin
            valid_screens = ["User Management", "Log Report"]
        elif st.session_state.role == "Admin" and st.session_state.user_data is not None:
            # Admin from database
            valid_screens = st.session_state.user_data.get("screens", ["User Management", "Log Report"])
        else:
            valid_screens = ["Inventory Dashboard",  "Booking Date Report", "Direct Reservations", "Night Report Dashboard", "View Reservations", "Edit Direct Reservation", "Online Reservations", "Edit Online Reservations", "Daily Status", "Daily Management Status", "Analytics", "Monthly Consolidation", "Summary Report", "Target Achievement"]
       
        # Apply screen filtering for users with configured screens
        if st.session_state.user_data:
            user_screens = st.session_state.user_data.get("screens", [])
            if query_page not in user_screens and query_page not in ["User Management", "Log Report"]:
                st.error(f"Access Denied: You do not have permission to view {query_page}.")
                st.session_state.current_page = user_screens[0] if user_screens else "Direct Reservations"
            else:
                st.session_state.current_page = query_page
        else:
            # For hardcoded Admin without user_data
            if query_page in valid_screens:
                st.session_state.current_page = query_page
       
        query_booking_id = query_params.get("booking_id", [None])[0]
        if query_booking_id:
            st.session_state.selected_booking_id = query_booking_id
def show_user_management():
    if st.session_state.role != "Admin":
        st.error("Access Denied: User Management is available only for Admin.")
        return
   
    st.header("User Management")
    users = load_users(supabase)
    if not users:
        st.info("No users found in database.")
    else:
        st.subheader("Existing Users")
        df = pd.DataFrame(users)
       
        # Convert JSONB columns to strings BEFORE filtering columns
        if 'properties' in df.columns:
            df['properties'] = df['properties'].apply(lambda x: json.dumps(x) if x is not None else '[]')
       
        if 'screens' in df.columns:
            df['screens'] = df['screens'].apply(lambda x: json.dumps(x) if x is not None else '[]')
       
        if 'permissions' in df.columns:
            df['permissions'] = df['permissions'].apply(lambda x: json.dumps(x) if x is not None else '{}')
       
        # Now filter columns for display (exclude password)
        display_columns = ["username", "role"]
        if "properties" in df.columns:
            display_columns.append("properties")
        if "screens" in df.columns:
            display_columns.append("screens")
        if "permissions" in df.columns:
            display_columns.append("permissions")
       
        # Display dataframe without password column for security
        display_df = df[display_columns].copy()
        st.dataframe(display_df)
    st.markdown("---")
    # Create new user
    st.subheader("Create New User")
    with st.form("create_user_form", clear_on_submit=False):
        new_username = st.text_input("Username", key="create_username")
        new_password = st.text_input("Password", type="password", key="create_password")
        new_role = st.selectbox("Role", ["Management", "ReservationTeam", "ReservationHead", "Accounts Team", "Admin"], key="create_role")
       
        all_properties = [
            "Le Poshe Beachview", "La Millionaire Resort", "Le Poshe Luxury", "Le Poshe Suite",
            "La Paradise Residency", "La Paradise Luxury", "La Villa Heritage", "Le Pondy Beach Side",
            "Le Royce Villa", "La Tamara Luxury", "La Antilia Luxury", "Date-wise Check-in Report", "La Tamara Suite",
            "Le Park Resort", "Villa Shakti", "Eden Beach Resort", "La Coromandel Luxury",
            "Le Terra", "Happymates Forest Retreat"
        ]
        new_properties = st.multiselect("Visible Properties", all_properties, default=all_properties, key="create_properties")
       
        all_screens = ["Inventory Dashboard", "Night Report Dashboard", "Accounts Report", "Date-wise Booking Report", "Date-wise Check-in Report", "Booking Date Report","Direct Reservations", "View Reservations", "Edit Direct Reservation", "Online Reservations", "Edit Online Reservations", "Daily Status", "Daily Management Status", "Analytics", "Monthly Consolidation", "Summary Report", "Target Achievement", "User Management", "Log Report"]
       
        # Default screens based on role
        if new_role == "Admin":
            default_screens = ["User Management", "Log Report"]
        elif new_role == "Management":
            default_screens = [s for s in all_screens if s not in ["User Management", "Log Report"]]
        elif new_role == "ReservationHead":
            default_screens = ["Direct Reservations", "Night Report Dashboard", "View Reservations", "Date-wise Booking Report", "Date-wise Check-in Report", "Edit Direct Reservation", "Online Reservations", "Edit Online Reservations", "Daily Status", "Monthly Consolidation", "Summary Report", "Target Achievement"]
        elif new_role == "Accounts Team":
            default_screens = ["Daily Status", "Night Report Dashboard", "Monthly Consolidation", "Accounts Report"]
        else:
            default_screens = [s for s in all_screens if s not in ["Daily Management Status", "Night Report Dashboard", "Date-wise Booking Report","Date-wise Check-in Report", "Analytics", "Inventory Dashboard", "Summary Report", "Target Achievement", "User Management", "Log Report"]]
       
        new_screens = st.multiselect("Visible Screens", all_screens, default=default_screens, key="create_screens")
       
        add_perm = st.checkbox("Add Permission", value=True, key="create_add_perm")
        edit_perm = st.checkbox("Edit Permission", value=True, key="create_edit_perm")
        delete_perm = st.checkbox("Delete Permission", value=False, key="create_delete_perm")
       
        submit_create = st.form_submit_button("Create User")
       
        if submit_create:
            if not new_username or not new_password:
                st.error("Username and Password are required!")
            else:
                # Check if user already exists
                existing = supabase.table("users").select("*").eq("username", new_username).execute().data
                if existing:
                    st.error(f"Username '{new_username}' already exists.")
                else:
                    new_permissions = {"add": add_perm, "edit": edit_perm, "delete": delete_perm}
                    # Password is stored as plain text by create_user function
                    success = create_user(supabase, new_username, new_password, new_role, new_properties, new_screens, new_permissions)
                    if success:
                        log_activity(supabase, st.session_state.username, f"Created user {new_username}")
                        st.rerun()
    st.markdown("---")
    # Modify existing user
    st.subheader("Modify Existing User")
    if users:
        modifiable_users = [u["username"] for u in users]
       
        if not modifiable_users:
            st.info("No modifiable users found.")
        else:
            modify_username = st.selectbox("Select User to Modify", modifiable_users, key="modify_username_select")
           
            if modify_username:
                user_to_modify = next((u for u in users if u["username"] == modify_username), None)
               
                if user_to_modify:
                    # Parse JSON fields if they are strings or None (fix for AttributeError)
                    current_properties_raw = user_to_modify.get("properties", [])
                    current_properties = current_properties_raw
                    if current_properties is None:
                        current_properties = []
                    elif isinstance(current_properties, str):
                        try:
                            current_properties = json.loads(current_properties_raw)
                        except (json.JSONDecodeError, TypeError):
                            current_properties = []
                    if not isinstance(current_properties, list):
                        current_properties = []

                    current_screens_raw = user_to_modify.get("screens", [])
                    current_screens = current_screens_raw
                    if current_screens is None:
                        current_screens = []
                    elif isinstance(current_screens, str):
                        try:
                            current_screens = json.loads(current_screens_raw)
                        except (json.JSONDecodeError, TypeError):
                            current_screens = []
                    if not isinstance(current_screens, list):
                        current_screens = []

                    current_perms_raw = user_to_modify.get("permissions", {"add": False, "edit": False, "delete": False})
                    current_perms = current_perms_raw
                    if current_perms is None:
                        current_perms = {"add": False, "edit": False, "delete": False}
                    elif isinstance(current_perms, str):
                        try:
                            current_perms = json.loads(current_perms_raw)
                        except (json.JSONDecodeError, TypeError):
                            current_perms = {"add": False, "edit": False, "delete": False}
                    if not isinstance(current_perms, dict):
                        current_perms = {"add": False, "edit": False, "delete": False}
                   
                    with st.form("modify_user_form", clear_on_submit=False):
                        st.write(f"**Modifying User: {modify_username}**")
                       
                        mod_password = st.text_input("New Password (leave blank to keep current)", type="password", key="modify_password")
                        st.caption("Password will be stored as plain text")
                       
                        current_role = user_to_modify.get("role", "ReservationTeam")
                        mod_role = st.selectbox("Role", ["Management", "ReservationTeam", "ReservationHead", "Accounts Team", "Admin"],
                                                index=["Management", "ReservationTeam", "ReservationHead", "Accounts Team", "Admin"].index(current_role) if current_role in ["Management", "ReservationTeam", "ReservationHead", "Accounts Team", "Admin"] else 1,
                                                key="modify_role")
                       
                        all_properties = [
                            "Le Poshe Beachview", "La Millionaire Resort", "Le Poshe Luxury", "Le Poshe Suite",
                            "La Paradise Residency", "La Paradise Luxury", "La Villa Heritage", "Le Pondy Beach Side",
                            "Le Royce Villa", "La Tamara Luxury", "La Antilia Luxury", "La Tamara Suite",
                            "Le Park Resort", "Villa Shakti", "Eden Beach Resort", "La Coromandel Luxury",
                            "Le Terra", "Happymates Forest Retreat"
                        ]
                        default_properties = [prop for prop in current_properties if prop in all_properties]
                        if not default_properties:
                            default_properties = all_properties
                        mod_properties = st.multiselect("Visible Properties", all_properties, default=default_properties, key="modify_properties")
                       
                        all_screens = ["Inventory Dashboard", "Booking Date Report", "Date-wise Booking Report", "Date-wise Check-in Report", "Accounts Report", "Direct Reservations", "Night Report Dashboard", "View Reservations", "Edit Direct Reservation", "Online Reservations", "Edit Online Reservations", "Daily Status", "Daily Management Status", "Analytics", "Monthly Consolidation", "Summary Report", "Target Achievement", "User Management", "Log Report"]
                        # Filter out any screens that don't exist in all_screens to avoid the error
                        valid_current_screens = [screen for screen in current_screens if screen in all_screens]
                        mod_screens = st.multiselect("Visible Screens", all_screens, default=valid_current_screens, key="modify_screens")
                       
                        mod_add = st.checkbox("Add Permission", value=current_perms.get("add", False), key="modify_add_perm")
                        mod_edit = st.checkbox("Edit Permission", value=current_perms.get("edit", False), key="modify_edit_perm")
                        mod_delete = st.checkbox("Delete Permission", value=current_perms.get("delete", False), key="modify_delete_perm")
                       
                        submit_modify = st.form_submit_button("Update User")
                       
                        if submit_modify:
                            mod_permissions = {"add": mod_add, "edit": mod_edit, "delete": mod_delete}
                            # Password is stored as plain text by update_user function
                            success = update_user(
                                supabase,
                                modify_username,
                                password=mod_password if mod_password else None,
                                role=mod_role,
                                properties=mod_properties,
                                screens=mod_screens,
                                permissions=mod_permissions
                            )
                            if success:
                                log_activity(supabase, st.session_state.username, f"Modified user {modify_username}")
                                st.rerun()
    st.markdown("---")
    # Delete user
    st.subheader("Delete User")
    if users:
        deletable_users = [u["username"] for u in users]
       
        if not deletable_users:
            st.info("No deletable users found.")
        else:
            delete_username = st.selectbox("Select User to Delete", deletable_users, key="delete_username_select")
           
            if delete_username:
                st.warning(f"⚠️ You are about to delete user: **{delete_username}**")
                st.write("This action cannot be undone!")
               
                if st.button("🗑️ Confirm Delete User", key="delete_user_button"):
                    success = delete_user(supabase, delete_username)
                    if success:
                        log_activity(supabase, st.session_state.username, f"Deleted user {delete_username}")
                        st.rerun()
def main():
    check_authentication()
    st.title("TIE Reservations")
    st.markdown("---")
    st.sidebar.title("Navigation")
    # === Build page options based on user configuration ===
    # Admin gets special pages
    if st.session_state.role == "Admin" and st.session_state.user_data is None:
        # Hardcoded Admin
        page_options = ["User Management", "Log Report"]
    elif st.session_state.user_data:
        # All database users (including Admin if in DB)
        allowed_screens = st.session_state.user_data.get("screens", [])
        page_options = allowed_screens if allowed_screens else ["Direct Reservations"]
    else:
        # Fallback (should not happen)
        page_options = ["Direct Reservations"]
    # === Backward compatibility for old URLs ===
    query_params = st.query_params
    query_page = query_params.get("page", [st.session_state.current_page])[0]
    url_mapping = {
        "Dashboard": "Inventory Dashboard",
        "Edit Reservations": "Edit Direct Reservation"
    }
    if query_page in url_mapping:
        st.session_state.current_page = url_mapping[query_page]
        st.query_params["page"] = st.session_state.current_page
    # === Sidebar Navigation ===
    default_index = page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0
    page = st.sidebar.selectbox("Choose a page", page_options, index=default_index, key="page_select")
    st.session_state.current_page = page
    # === Refresh Button (not for hardcoded Admin) ===
    if not (st.session_state.role == "Admin" and st.session_state.user_data is None):
        if st.sidebar.button("Refresh All Data"):
            st.cache_data.clear()
            try:
                st.session_state.reservations = load_reservations_from_supabase()
                st.session_state.online_reservations = load_online_reservations_from_supabase()
                log_activity(supabase, st.session_state.username, "Refreshed all data")
                st.success("Data refreshed from database!")
            except Exception as e:
                st.warning(f"Data refresh partially failed: {e}")
            st.rerun()
    # === Page Routing ===
    if page == "User Management":
        show_user_management()
        log_activity(supabase, st.session_state.username, "Accessed User Management")
    elif page == "Log Report":
        show_log_report(supabase)
        log_activity(supabase, st.session_state.username, "Accessed Log Report")
    elif page == "Inventory Dashboard":
        show_dashboard()
        log_activity(supabase, st.session_state.username, "Accessed Inventory Dashboard")
    elif page == "Direct Reservations":
        show_new_reservation_form()
        log_activity(supabase, st.session_state.username, "Accessed Direct Reservations")
    elif page == "View Reservations":
        show_reservations()
        log_activity(supabase, st.session_state.username, "Accessed View Reservations")
    elif page == "Edit Direct Reservation":
        show_edit_reservations()
        log_activity(supabase, st.session_state.username, "Accessed Edit Direct Reservation")
    elif page == "Online Reservations":
        show_online_reservations()
        log_activity(supabase, st.session_state.username, "Accessed Online Reservations")
    elif page == "Edit Online Reservations" and edit_online_available:
        show_edit_online_reservations(st.session_state.selected_booking_id)
        if st.session_state.selected_booking_id:
            st.session_state.selected_booking_id = None
            st.query_params.clear()
        log_activity(supabase, st.session_state.username, "Accessed Edit Online Reservations")
    elif page == "Daily Status":
        show_daily_status()
        log_activity(supabase, st.session_state.username, "Accessed Daily Status")
    elif page == "Daily Management Status":
        show_dms()
        log_activity(supabase, st.session_state.username, "Accessed Daily Management Status")
    elif page == "Analytics":
        show_analytics()
        log_activity(supabase, st.session_state.username, "Accessed Analytics")
    elif page == "Monthly Consolidation":
        show_monthly_consolidation()
        log_activity(supabase, st.session_state.username, "Accessed Monthly Consolidation")
    elif page == "Summary Report":
        show_summary_report()
        log_activity(supabase, st.session_state.username, "Accessed Summary Report")
    elif page == "Target Achievement" and target_achievement_available:
        show_target_achievement_report()
        log_activity(supabase, st.session_state.username, "Accessed Target Achievement")
    elif page == "Accounts Report":
        show_accounts_report()
        log_activity(supabase, st.session_state.username, "Accessed Accounts Report")
    elif page == "Night Report Dashboard":
        show_nrd_report()
        log_activity(supabase, st.session_state.username, "Accessed Night Report Dashboard")
    elif page == "Booking Date Report":
        show_booking_date_report()
        log_activity(supabase, st.session_state.username, "Accessed Booking Date Report")
    elif page == "Date-wise Booking Report":  # ADD THIS BLOCK
        show_datewise_booking_report()
        log_activity(supabase, st.session_state.username, "Accessed Date-wise Booking Report")
    elif page == "Date-wise Check-in Report":  # ADD THIS BLOCK
        show_checkin_date_report()
        log_activity(supabase, st.session_state.username, "Accessed Date-wise Check-in Report")
    
    # === Footer: User Info & Logout ===
    if st.session_state.authenticated:
        st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
        st.sidebar.write(f"Role: **{st.session_state.role}**")
    if st.sidebar.button("Log Out"):
        log_activity(supabase, st.session_state.username, "Logged out")
        st.cache_data.clear()
        st.cache_resource.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.reservations = []
        st.session_state.online_reservations = []
        st.session_state.current_page = "Direct Reservations"
        st.session_state.selected_booking_id = None
        st.query_params.clear()
        st.rerun()
if __name__ == "__main__":
    main()
