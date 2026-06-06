"""
StayFlexi Channel Manager API Integration Module
Handles API connections, authentication, data fetching, and booking synchronization with Edenbeach
"""

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from functools import wraps

import stayflexi_config as config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StayFlexiAPIConfig:
    """Configuration management for StayFlexi API"""
    
    def __init__(self):
        self.api_base_url = config.STAYFLEXI_API_BASE_URL
        self.pms_id = config.STAYFLEXI_PMS_ID
        self.hotel_id = config.STAYFLEXI_HOTEL_ID
        self.api_key = config.STAYFLEXI_API_KEY
        self.timeout = config.STAYFLEXI_TIMEOUT
        self.max_retries = config.STAYFLEXI_MAX_RETRIES
    
    def is_configured(self) -> bool:
        """Check if API is properly configured"""
        return all([self.api_base_url, self.pms_id, self.hotel_id, self.api_key])
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "X-SF-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TIE-Reservation-System/1.0"
        }


class StayFlexiAPIClient:
    """Client for StayFlexi Channel Manager API interactions"""
    
    def __init__(self, config: StayFlexiAPIConfig):
        self.config = config
        self.session = requests.Session()
        self.last_error = None
        self.last_sync_time = None
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                      params: Optional[Dict] = None) -> Tuple[bool, Optional[Dict], str]:
        """
        Make HTTP request with error handling and retries
        
        Returns:
            Tuple of (success: bool, response_data: Dict or None, message: str)
        """
        if not self.config.is_configured():
            return False, None, "API not configured. Check credentials."
        
        url = f"{self.config.api_base_url}{endpoint}"
        
        # Add standard query parameters
        if params is None:
            params = {}
        params["pmsId"] = self.config.pms_id
        params["hotelId"] = self.config.hotel_id
        
        headers = self.config.get_headers()
        
        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        params=params,
                        timeout=self.config.timeout
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        url, 
                        headers=headers, 
                        json=data,
                        params=params,
                        timeout=self.config.timeout
                    )
                elif method.upper() == "PUT":
                    response = self.session.put(
                        url, 
                        headers=headers, 
                        json=data,
                        params=params,
                        timeout=self.config.timeout
                    )
                else:
                    return False, None, f"Unsupported HTTP method: {method}"
                
                # Handle response status codes
                if response.status_code == 401:
                    return False, None, "Authentication failed. Check your API key."
                elif response.status_code == 403:
                    return False, None, "Access forbidden. Check your permissions."
                elif response.status_code == 404:
                    return False, None, "Endpoint not found."
                elif response.status_code >= 500:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"Server error (attempt {attempt + 1}): {response.status_code}")
                        continue
                    return False, None, "Server error. Please try again later."
                elif response.status_code >= 400:
                    try:
                        error_msg = response.json().get("message", response.text)
                    except:
                        error_msg = response.text
                    return False, None, f"Request failed: {error_msg}"
                
                # Success
                if response.status_code == 204:
                    return True, {"status": "success"}, "Operation successful"
                
                try:
                    return True, response.json(), "Success"
                except:
                    return True, {"raw_response": response.text}, "Success"
                    
            except requests.Timeout:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Timeout (attempt {attempt + 1}/{self.config.max_retries})")
                    continue
                return False, None, "Request timeout. Server may be unavailable."
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
        """Test API connection and authentication"""
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["health"]
        )
        if success:
            return True, "✅ Connection to StayFlexi API successful!"
        else:
            self.last_error = message
            return False, f"❌ Connection failed: {message}"
    
    def fetch_bookings(self, start_date: str, end_date: str) -> Tuple[bool, Optional[List], str]:
        """
        Fetch bookings by date range
        
        Args:
            start_date: Date string in format DD-MM-YYYY
            end_date: Date string in format DD-MM-YYYY
        
        Returns:
            Tuple of (success: bool, bookings: List or None, message: str)
        """
        params = {
            "startDate": start_date,
            "endDate": end_date
        }
        
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["get_bookings"],
            params=params
        )
        
        if success and response:
            bookings = response.get("data", []) if isinstance(response, dict) else response
            if isinstance(bookings, list):
                self.last_sync_time = datetime.now()
                logger.info(f"Fetched {len(bookings)} bookings")
                return True, bookings, f"Successfully fetched {len(bookings)} bookings"
            else:
                return True, [], "No bookings found"
        else:
            return False, None, message
    
    def fetch_booking_detail(self, booking_id: str) -> Tuple[bool, Optional[Dict], str]:
        """Fetch details for a specific booking"""
        params = {"bookingId": booking_id}
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["get_booking_detail"],
            params=params
        )
        return success, response.get("data") if success else None, message
    
    def fetch_channels(self) -> Tuple[bool, Optional[List], str]:
        """Fetch available channels"""
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["get_channels"]
        )
        if success and response:
            channels = response.get("data", []) if isinstance(response, dict) else response
            return True, channels, f"Successfully fetched channels"
        return False, None, message
    
    def fetch_room_count(self, room_type_id: str, start_date: str, end_date: str) -> Tuple[bool, Optional[Dict], str]:
        """Fetch room availability/count for date range"""
        params = {
            "roomTypeId": room_type_id,
            "fromDate": start_date,
            "toDate": end_date
        }
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["get_room_count"],
            params=params
        )
        return success, response.get("data") if success else None, message
    
    def fetch_room_rates(self, room_type_id: str, rate_plan_id: str, start_date: str, end_date: str) -> Tuple[bool, Optional[Dict], str]:
        """Fetch room rates for date range"""
        params = {
            "roomTypeId": room_type_id,
            "ratePlanId": rate_plan_id,
            "fromDate": start_date,
            "toDate": end_date
        }
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["get_room_rates"],
            params=params
        )
        return success, response.get("data") if success else None, message
    
    def create_booking(self, booking_data: Dict) -> Tuple[bool, Optional[Dict], str]:
        """Create a new booking"""
        success, response, message = self._make_request(
            "POST", 
            config.STAYFLEXI_ENDPOINTS["create_booking"],
            data=booking_data
        )
        return success, response.get("data") if success else None, message
    
    def checkin_booking(self, booking_id: str) -> Tuple[bool, Optional[Dict], str]:
        """Check-in a booking"""
        params = {"bookingId": booking_id}
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["checkin"],
            params=params
        )
        return success, response.get("data") if success else None, message
    
    def checkout_booking(self, booking_id: str) -> Tuple[bool, Optional[Dict], str]:
        """Check-out a booking"""
        params = {"bookingId": booking_id}
        success, response, message = self._make_request(
            "GET", 
            config.STAYFLEXI_ENDPOINTS["checkout"],
            params=params
        )
        return success, response.get("data") if success else None, message
    
    def cancel_booking(self, booking_id: str) -> Tuple[bool, Optional[Dict], str]:
        """Cancel a booking"""
        success, response, message = self._make_request(
            "POST", 
            config.STAYFLEXI_ENDPOINTS["cancel_booking"],
            data={"bookingId": booking_id}
        )
        return success, response.get("data") if success else None, message


class StayFlexiDataSync:
    """Handle data synchronization between StayFlexi and Supabase"""
    
    def __init__(self, api_client: StayFlexiAPIClient, supabase_client):
        self.api_client = api_client
        self.supabase = supabase_client
        self.sync_status = {
            "bookings": False,
            "last_sync": None,
            "error_count": 0
        }
    
    def sync_bookings(self, start_date: str, end_date: str) -> Dict:
        """Sync bookings from StayFlexi to Supabase"""
        try:
            success, bookings, message = self.api_client.fetch_bookings(start_date, end_date)
            
            if not success:
                self.sync_status["error_count"] += 1
                return {
                    "success": False,
                    "message": message,
                    "count": 0
                }
            
            # Transform and insert bookings
            synced_count = 0
            for booking in bookings:
                try:
                    # Transform API format to Supabase format
                    transformed = self._transform_booking(booking)
                    
                    # Upsert to Supabase
                    self.supabase.table(config.STAYFLEXI_TABLES["bookings"]).upsert(
                        transformed,
                        on_conflict="booking_id"
                    ).execute()
                    
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing booking {booking.get('id')}: {str(e)}")
                    self.sync_status["error_count"] += 1
            
            self.sync_status["bookings"] = True
            self.sync_status["last_sync"] = datetime.now()
            
            return {
                "success": True,
                "message": f"Successfully synced {synced_count} bookings",
                "count": synced_count
            }
        
        except Exception as e:
            logger.error(f"Booking sync error: {str(e)}")
            self.sync_status["error_count"] += 1
            return {
                "success": False,
                "message": f"Sync error: {str(e)}",
                "count": 0
            }
    
    @staticmethod
    def _transform_booking(api_booking: Dict) -> Dict:
        """Transform StayFlexi booking format to Supabase format"""
        return {
            "booking_id": api_booking.get("bookingId") or api_booking.get("id"),
            "property": config.PROPERTY_NAME,
            "guest_name": api_booking.get("guestName") or api_booking.get("guest_name"),
            "email": api_booking.get("email"),
            "phone": api_booking.get("phone"),
            "checkin_date": api_booking.get("checkInDate") or api_booking.get("check_in_date"),
            "checkout_date": api_booking.get("checkOutDate") or api_booking.get("check_out_date"),
            "room_type": api_booking.get("roomType") or api_booking.get("room_type"),
            "number_of_guests": api_booking.get("numberOfGuests") or api_booking.get("number_of_guests"),
            "total_price": api_booking.get("totalPrice") or api_booking.get("total_price"),
            "status": api_booking.get("status", "confirmed"),
            "notes": api_booking.get("notes", ""),
            "source": "StayFlexi API",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def get_sync_status(self) -> Dict:
        """Get current sync status"""
        return {
            **self.sync_status,
            "last_sync_formatted": self.sync_status["last_sync"].strftime("%Y-%m-%d %H:%M:%S") 
                                   if self.sync_status["last_sync"] else "Never"
        }
