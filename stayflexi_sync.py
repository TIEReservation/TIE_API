"""
Stayflexi to Local Database Sync Module for Eden Beach Resort
One-way synchronization: Stayflexi → Local Database only
- Pulls new bookings from Stayflexi
- Maintains local status independently
- Prevents duplicates using booking_id
- No changes are sent back to Stayflexi
"""

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StayflexiSyncConfig:
    """Configuration for Stayflexi API connection"""
    
    def __init__(self):
        self.api_url = "https://api.stayflexi.com/core/api/v1"
        self.api_token = None
        self.email = None
        self.property_id = "EDEN_BEACH_RESORT"
        self.timeout = 30
        self.max_retries = 3
    
    def set_credentials(self, api_token: str, email: str):
        """Set API credentials"""
        if not api_token or not email:
            raise ValueError("API token and email are required")
        self.api_token = api_token.strip()
        self.email = email.strip()
        return True
    
    def is_configured(self) -> bool:
        """Check if credentials are configured"""
        return self.api_token is not None and self.email is not None
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Stayflexi API"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }


class StayflexiAPIClient:
    """Client to fetch bookings from Stayflexi API"""
    
    def __init__(self, config: StayflexiSyncConfig):
        self.config = config
        self.session = requests.Session()
        self.last_error = None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[bool, Optional[Dict], str]:
        """Make API request with error handling"""
        if not self.config.is_configured():
            return False, None, "Stayflexi credentials not configured"
        
        url = f"{self.config.api_url}{endpoint}"
        headers = self.config.get_headers()
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 401:
                    return False, None, "Authentication failed. Invalid API token or email."
                elif response.status_code == 403:
                    return False, None, "Access forbidden. Check permissions."
                elif response.status_code == 404:
                    return False, None, "Endpoint not found."
                elif response.status_code >= 500:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"Server error (attempt {attempt + 1}): {response.status_code}")
                        continue
                    return False, None, "Stayflexi server error. Try again later."
                elif response.status_code >= 400:
                    try:
                        error_msg = response.json().get("message", response.text)
                    except:
                        error_msg = response.text
                    return False, None, f"Request failed: {error_msg}"
                
                try:
                    return True, response.json(), "Success"
                except:
                    return True, {"raw_response": response.text}, "Success"
                    
            except requests.Timeout:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Timeout (attempt {attempt + 1})")
                    continue
                return False, None, "Request timeout. Stayflexi server may be unavailable."
            except requests.ConnectionError as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Connection error (attempt {attempt + 1}): {str(e)}")
                    continue
                return False, None, f"Connection error: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return False, None, f"Unexpected error: {str(e)}"
        
        return False, None, "Failed after multiple retry attempts"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test Stayflexi connection"""
        success, response, message = self._make_request("/reservation/navigationGetRoomBookings")
        if success:
            return True, "✅ Connected to Stayflexi API successfully!"
        return False, f"❌ Connection failed: {message}"
    
    def fetch_bookings(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None) -> Tuple[bool, Optional[List], str]:
        """
        Fetch bookings from Stayflexi API
        
        Args:
            start_date: ISO format date string (YYYY-MM-DD)
            end_date: ISO format date string (YYYY-MM-DD)
        
        Returns:
            Tuple of (success: bool, bookings: List or None, message: str)
        """
        params = {}
        if start_date:
            params["checkInFrom"] = start_date
        if end_date:
            params["checkInTo"] = end_date
        
        success, response, message = self._make_request("/reservation/navigationGetRoomBookings", params=params)
        
        if success and response:
            # Handle different response structures
            bookings = []
            
            if isinstance(response, list):
                bookings = response
            elif isinstance(response, dict):
                # Try different possible response keys
                for key in ["reservations", "bookings", "data", "rooms"]:
                    if key in response:
                        bookings = response[key] if isinstance(response[key], list) else []
                        break
            
            logger.info(f"Fetched {len(bookings)} bookings from Stayflexi")
            return True, bookings, f"Successfully fetched {len(bookings)} bookings"
        else:
            return False, None, message


class LocalDatabaseSync:
    """Handle syncing from Stayflexi to local database"""
    
    def __init__(self, api_client: StayflexiAPIClient, supabase_client):
        self.api_client = api_client
        self.supabase = supabase_client
        self.sync_log = []
    
    def get_existing_booking_ids(self) -> set:
        """Get all existing booking IDs from local database"""
        try:
            response = self.supabase.table("reservations").select("booking_id").execute()
            return {record["booking_id"] for record in response.data} if response.data else set()
        except Exception as e:
            logger.error(f"Error fetching existing booking IDs: {str(e)}")
            return set()
    
    def sync_bookings(self, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> Dict:
        """
        Sync bookings from Stayflexi to local database
        Only imports new bookings (not in local DB)
        """
        try:
            # Get existing booking IDs to avoid duplicates
            existing_ids = self.get_existing_booking_ids()
            logger.info(f"Found {len(existing_ids)} existing bookings in local database")
            
            # Fetch bookings from Stayflexi
            success, bookings, message = self.api_client.fetch_bookings(start_date, end_date)
            
            if not success:
                return {
                    "success": False,
                    "message": message,
                    "imported": 0,
                    "skipped": 0,
                    "errors": 0,
                    "log": []
                }
            
            imported = 0
            skipped = 0
            errors = 0
            sync_log = []
            
            for booking in bookings:
                try:
                    booking_id = booking.get("id") or booking.get("booking_id") or booking.get("referenceNumber")
                    
                    if not booking_id:
                        errors += 1
                        sync_log.append(f"⚠️ Skipped booking with no ID")
                        continue
                    
                    booking_id = str(booking_id)
                    
                    # Check if booking already exists
                    if booking_id in existing_ids:
                        skipped += 1
                        sync_log.append(f"⏭️ Skipped duplicate: {booking_id}")
                        continue
                    
                    # Transform booking data
                    transformed = self._transform_booking(booking)
                    
                    # Insert into local database
                    response = self.supabase.table("reservations").insert(transformed).execute()
                    
                    if response.data:
                        imported += 1
                        existing_ids.add(booking_id)
                        sync_log.append(f"✅ Imported: {booking_id}")
                    else:
                        errors += 1
                        sync_log.append(f"❌ Failed to import: {booking_id}")
                
                except Exception as e:
                    errors += 1
                    logger.error(f"Error syncing booking {booking.get('id')}: {str(e)}")
                    sync_log.append(f"❌ Error: {str(e)}")
            
            return {
                "success": True,
                "message": f"Sync completed. Imported: {imported}, Skipped (duplicates): {skipped}, Errors: {errors}",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "log": sync_log
            }
        
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            return {
                "success": False,
                "message": f"Sync error: {str(e)}",
                "imported": 0,
                "skipped": 0,
                "errors": 1,
                "log": [f"❌ Error: {str(e)}"]
            }
    
    def _transform_booking(self, stayflexi_booking: Dict) -> Dict:
        """
        Transform Stayflexi booking format to local database format
        Maps fields and maintains local control of status
        """
        # Extract dates
        check_in_str = stayflexi_booking.get("checkInDate") or stayflexi_booking.get("check_in")
        check_out_str = stayflexi_booking.get("checkOutDate") or stayflexi_booking.get("check_out")
        
        # Parse dates
        check_in = None
        check_out = None
        if check_in_str:
            try:
                check_in = pd.to_datetime(check_in_str).strftime("%Y-%m-%d")
            except:
                check_in = None
        if check_out_str:
            try:
                check_out = pd.to_datetime(check_out_str).strftime("%Y-%m-%d")
            except:
                check_out = None
        
        # Calculate days
        no_of_days = 0
        if check_in and check_out:
            try:
                delta = pd.to_datetime(check_out) - pd.to_datetime(check_in)
                no_of_days = max(1, delta.days)
            except:
                no_of_days = 0
        
        # Parse pax
        no_of_adults = int(stayflexi_booking.get("adults", 1) or 1)
        no_of_children = int(stayflexi_booking.get("children", 0) or 0)
        no_of_infants = int(stayflexi_booking.get("infants", 0) or 0)
        total_pax = no_of_adults + no_of_children + no_of_infants
        
        # Parse pricing
        total_tariff = float(stayflexi_booking.get("totalPrice", 0) or 0)
        tariff = total_tariff / max(1, no_of_days)
        advance_amount = float(stayflexi_booking.get("paidAmount", 0) or 0)
        balance_amount = max(0, total_tariff - advance_amount)
        
        return {
            "booking_id": str(stayflexi_booking.get("id", "")),
            "property_name": "Eden Beach Resort",  # Explicitly set for Eden Beach
            "guest_name": stayflexi_booking.get("guestName") or "",
            "mobile_no": stayflexi_booking.get("guestPhone") or "",
            "email": stayflexi_booking.get("guestEmail") or "",
            "room_no": stayflexi_booking.get("roomNumber") or "",
            "room_type": stayflexi_booking.get("roomType") or "",
            "no_of_adults": no_of_adults,
            "no_of_children": no_of_children,
            "no_of_infants": no_of_infants,
            "total_pax": total_pax,
            "check_in": check_in,
            "check_out": check_out,
            "no_of_days": no_of_days,
            "tariff": tariff,
            "total_tariff": total_tariff,
            "advance_amount": advance_amount,
            "balance_amount": balance_amount,
            "advance_mop": stayflexi_booking.get("paymentMethod") or "Not Paid",
            "balance_mop": "Pending",
            "mob": "Online",  # Bookings from Stayflexi are online
            "online_source": "Stayflexi",
            "breakfast": stayflexi_booking.get("breakfast") or "EP",
            # LOCAL STATUS - maintained independently in this system
            "plan_status": "Confirmed",  # Default status for new imports
            "payment_status": "Not Paid" if balance_amount > 0 else "Fully Paid",
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "enquiry_date": check_in,
            "invoice_no": "",
            "submitted_by": "Stayflexi Sync",
            "modified_by": "",
            "modified_comments": f"Imported from Stayflexi on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "remarks": f"Source: Stayflexi | Reference: {stayflexi_booking.get('referenceNumber', '')}"
        }
    
    def get_sync_status(self) -> Dict:
        """Get current sync status"""
        try:
            response = self.supabase.table("reservations").select("count", count="exact").eq("submitted_by", "Stayflexi Sync").execute()
            stayflexi_bookings = response.count if response.count else 0
            
            response = self.supabase.table("reservations").select("count", count="exact").execute()
            total_bookings = response.count if response.count else 0
            
            return {
                "total_bookings": total_bookings,
                "stayflexi_bookings": stayflexi_bookings,
                "other_bookings": total_bookings - stayflexi_bookings,
                "last_sync": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                "total_bookings": 0,
                "stayflexi_bookings": 0,
                "other_bookings": 0,
                "error": str(e)
            }


# Export classes
__all__ = [
    'StayflexiSyncConfig',
    'StayflexiAPIClient',
    'LocalDatabaseSync'
]
