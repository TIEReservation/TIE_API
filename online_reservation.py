import streamlit as st
import requests
from datetime import datetime, timedelta
import jwt

# Add these new functions for better token management

def decode_token_expiry(token):
    """Decode JWT token to check expiration without verification."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded.get('exp')
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            return exp_date
        return None
    except Exception as e:
        st.warning(f"Could not decode token: {e}")
        return None

def is_token_expired(token):
    """Check if token is expired or will expire soon."""
    exp_date = decode_token_expiry(token)
    if not exp_date:
        return True
    
    # Consider token expired if it expires within 1 hour
    return exp_date < datetime.now() + timedelta(hours=1)

def get_valid_token():
    """Get a valid token from session state or secrets, refresh if needed."""
    # Check session state first
    if 'stayflexi_api_token' in st.session_state:
        token = st.session_state.stayflexi_api_token
        if not is_token_expired(token):
            return token
    
    # Check secrets/config
    try:
        token = st.secrets.get("stayflexi", {}).get("api_token", STAYFLEXI_API_TOKEN)
        if not is_token_expired(token):
            st.session_state.stayflexi_api_token = token
            return token
    except:
        pass
    
    # Token is expired or missing
    return None

def get_fresh_api_token(email: str, password: str):
    """Get a fresh API token from Stayflexi login endpoint."""
    login_url = f"{STAYFLEXI_API_BASE_URL}/auth/login"
    
    if not password:
        return None, "Password is required"
    
    try:
        response = requests.post(
            login_url,
            json={"email": email, "password": password},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        token = data.get("token") or data.get("accessToken")
        
        if token:
            # Store in session state
            st.session_state.stayflexi_api_token = token
            
            # Show expiry info
            exp_date = decode_token_expiry(token)
            if exp_date:
                return token, f"Token valid until {exp_date.strftime('%Y-%m-%d %H:%M:%S')}"
            return token, "Token obtained successfully"
        else:
            return None, "No token in API response"
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return None, "Invalid credentials"
        return None, f"HTTP Error: {e.response.status_code}"
    except Exception as e:
        return None, f"Failed to get token: {str(e)}"

def fetch_stayflexi_bookings_with_retry(hotel_id: str, from_date, to_date, max_retries=1):
    """Fetch bookings with automatic token refresh on 401."""
    token = get_valid_token()
    
    if not token:
        return {"error": "unauthorized", "message": "No valid token available"}
    
    url = f"{STAYFLEXI_API_BASE_URL}/core/api/v1/reservation/navigationGetRoomBookings"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "hotelId": hotel_id,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d")
    }
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Check for 401 Unauthorized
            if response.status_code == 401:
                if attempt < max_retries:
                    # Try to refresh token automatically if credentials are in secrets
                    try:
                        email = st.secrets.get("stayflexi", {}).get("email", STAYFLEXI_EMAIL)
                        password = st.secrets.get("stayflexi", {}).get("password")
                        
                        if password:
                            new_token, message = get_fresh_api_token(email, password)
                            if new_token:
                                token = new_token
                                headers["Authorization"] = f"Bearer {token}"
                                continue  # Retry with new token
                    except:
                        pass
                
                return {"error": "unauthorized", "message": "API token expired or invalid"}
            
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and "bookings" in data:
                return data["bookings"]
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and attempt < max_retries:
                continue
            st.warning(f"API Request Failed for hotel {hotel_id}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            st.warning(f"API Request Failed for hotel {hotel_id}: {e}")
            return []
        except Exception as e:
            st.warning(f"Error fetching bookings for hotel {hotel_id}: {e}")
            return []
    
    return []


# Updated UI section for token management
def render_token_management_ui():
    """Render the token management UI with status checking."""
    with st.expander("🔑 API Token Configuration", expanded=False):
        current_token = get_valid_token()
        
        if current_token:
            exp_date = decode_token_expiry(current_token)
            if exp_date:
                time_remaining = exp_date - datetime.now()
                days_remaining = time_remaining.days
                
                if days_remaining > 30:
                    st.success(f"✅ Token is valid until {exp_date.strftime('%Y-%m-%d %H:%M:%S')} ({days_remaining} days remaining)")
                elif days_remaining > 7:
                    st.warning(f"⚠️ Token expires on {exp_date.strftime('%Y-%m-%d %H:%M:%S')} ({days_remaining} days remaining)")
                else:
                    st.error(f"⛔ Token expires soon: {exp_date.strftime('%Y-%m-%d %H:%M:%S')} ({days_remaining} days remaining)")
            else:
                st.info("Token status unknown")
        else:
            st.error("❌ No valid token available")
        
        st.markdown("---")
        st.markdown("**Get Fresh Token:**")
        
        col1, col2 = st.columns(2)
        with col1:
            fresh_email = st.text_input(
                "Stayflexi Email", 
                value=st.secrets.get("stayflexi", {}).get("email", STAYFLEXI_EMAIL), 
                key="fresh_email"
            )
        with col2:
            fresh_password = st.text_input("Stayflexi Password", type="password", key="fresh_password")
        
        if st.button("🔄 Get Fresh Token", key="get_fresh_token"):
            if fresh_email and fresh_password:
                with st.spinner("Getting fresh API token..."):
                    new_token, message = get_fresh_api_token(fresh_email, fresh_password)
                    if new_token:
                        st.success(f"✅ {message}")
                        st.info("💡 Token stored in session. Consider updating your Streamlit secrets for permanent use.")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            else:
                st.error("Please provide both email and password.")
        
        st.markdown("---")
        st.markdown("**💡 Tip:** Store your Stayflexi password in Streamlit secrets for automatic token refresh:")
        st.code("""
[stayflexi]
email = "your-email@example.com"
password = "your-password"
api_token = "your-current-token"
        """, language="toml")


# Update the sync_property_bookings function to use the new retry mechanism
def sync_property_bookings(hotel_id: str, property_name: str, from_date, to_date, existing_ids: set):
    """Sync bookings for a single property with automatic retry."""
    inserted = 0
    skipped = 0
    errors = 0
    
    api_bookings = fetch_stayflexi_bookings_with_retry(hotel_id, from_date, to_date)
    
    # Check for authorization error
    if isinstance(api_bookings, dict) and api_bookings.get("error") == "unauthorized":
        return inserted, skipped, errors, "unauthorized"
    
    if not api_bookings:
        return inserted, skipped, errors, None
    
    for booking in api_bookings:
        try:
            db_record = transform_stayflexi_to_db_format(booking, property_name)
            
            if db_record["booking_id"] in existing_ids:
                skipped += 1
                continue
            
            if insert_online_reservation(db_record):
                inserted += 1
                existing_ids.add(db_record["booking_id"])
            else:
                skipped += 1
                
        except Exception as e:
            st.warning(f"Error processing booking: {e}")
            errors += 1
    
    return inserted, skipped, errors, None
