"""
Eden Beach Resort API Integration Module
Handles API connections, authentication, data fetching, and synchronization
"""

import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import logging
from functools import wraps
from urllib.parse import urlparse, urlunparse, urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdenBeachAPIConfig:
    """Configuration management for Eden Beach API"""
    
    def __init__(self):
        self.api_base_url = None
        self.api_key = None
        self.pms_id = None
        self.hotel_id = None
        self.property_id = "EDEN_BEACH_RESORT"
        self.timeout = 30
        self.max_retries = 3
    
    def set_api_key(self, api_key: str):
        """Set and validate API key"""
        if not api_key or len(api_key.strip()) == 0:
            raise ValueError("API key cannot be empty")
        self.api_key = api_key.strip()
        return True
    
    def set_api_url(self, url: str):
        """Set and validate API base URL"""
        if not url or len(url.strip()) == 0:
            raise ValueError("API URL cannot be empty")
        if not url.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")
        self.api_base_url = url.rstrip("/")
        return True
    
    def set_pms_id(self, pms_id: str):
        """Set PMS identifier"""
        if not pms_id or len(str(pms_id).strip()) == 0:
            raise ValueError("PMS ID cannot be empty")
        self.pms_id = str(pms_id).strip()
        return True
    
    def set_hotel_id(self, hotel_id: str):
        """Set hotel identifier"""
        if not hotel_id or len(str(hotel_id).strip()) == 0:
            raise ValueError("Hotel ID cannot be empty")
        self.hotel_id = str(hotel_id).strip()
        return True
    
    def is_configured(self) -> bool:
        """Check if API is properly configured"""
        return all([self.api_base_url, self.api_key, self.pms_id, self.hotel_id])
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TIE-Reservation-System/1.0"
        }


class EdenBeachAPIClient:
    """Client for Eden Beach Resort API interactions"""
    STAYFLEXI_SERVICE_PATH = "/core/apiv1/cmservice"
    
    def __init__(self, config: EdenBeachAPIConfig):
        self.config = config
        self.session = requests.Session()
        self.last_error = None
        self.last_sync_time = None
    
    @classmethod
    def _build_stayflexi_base_url(cls, configured_url: str) -> str:
        """
        Normalize configured URL to StayFlexi CM service base URL.
        Handles both host-only and already-suffixed URLs safely.
        """
        parsed = urlparse(configured_url.strip())
        path = (parsed.path or "").rstrip("/")
        normalized_path = path.lower()
        service_path = cls.STAYFLEXI_SERVICE_PATH
        service_path_lower = service_path.lower()
        
        if service_path_lower in normalized_path:
            idx = normalized_path.index(service_path_lower) + len(service_path_lower)
            final_path = path[:idx]
        else:
            final_path = service_path
        
        return urlunparse((parsed.scheme, parsed.netloc, final_path, "", "", ""))
    
    @classmethod
    def _build_request_url(cls, configured_url: str, endpoint: str) -> str:
        base_url = cls._build_stayflexi_base_url(configured_url).rstrip("/") + "/"
        endpoint_path = endpoint.lstrip("/")
        return urljoin(base_url, endpoint_path)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Tuple[bool, Optional[Dict], str]:
        """
        Make HTTP request with error handling and retries
        
        Returns:
            Tuple of (success: bool, response_data: Dict or None, message: str)
        """
        if not self.config.is_configured():
            return False, None, "API not configured. Please set API key and URL."
        
        url = self._build_request_url(self.config.api_base_url, endpoint)
        headers = self.config.get_headers()
        
        request_params = dict(params or {})
        request_params["pmsId"] = self.config.pms_id
        request_params["hotelId"] = self.config.hotel_id
        
        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        params=request_params,
                        timeout=self.config.timeout
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        url, 
                        headers=headers, 
                        json=data,
                        params=request_params,
                        timeout=self.config.timeout
                    )
                elif method.upper() == "PUT":
                    response = self.session.put(
                        url, 
                        headers=headers, 
                        json=data,
                        params=request_params,
                        timeout=self.config.timeout
                    )
                else:
                    return False, None, f"Unsupported HTTP method: {method}"
                
                # Handle response
                if response.status_code == 401:
                    return False, None, f"Authentication failed [{method.upper()} {url}] (status=401)"
                elif response.status_code == 403:
                    return False, None, f"Access forbidden [{method.upper()} {url}] (status=403)"
                elif response.status_code == 404:
                    body_preview = response.text[:300]
                    return False, None, f"Endpoint not found [{method.upper()} {url}] (status=404, body={body_preview})"
                elif response.status_code >= 500:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"Server error (attempt {attempt + 1}) {method.upper()} {url}: {response.status_code}")
                        continue
                    body_preview = response.text[:300]
                    return False, None, f"Server error [{method.upper()} {url}] (status={response.status_code}, body={body_preview})"
                elif response.status_code >= 400:
                    try:
                        error_msg = response.json().get("message", response.text)
                    except:
                        error_msg = response.text
                    return False, None, f"Request failed [{method.upper()} {url}] (status={response.status_code}): {error_msg}"
                
                # Success
                if response.status_code == 204:  # No content
                    return True, {"status": "success"}, "Operation successful"
                
                try:
                    return True, response.json(), "Success"
                except:
                    return True, {"raw_response": response.text}, "Success"
                    
            except requests.Timeout:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Timeout (attempt {attempt + 1}/{self.config.max_retries}) {method.upper()} {url}")
                    continue
                return False, None, f"Request timeout [{method.upper()} {url}]. Server may be unavailable."
            except requests.ConnectionError as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Connection error (attempt {attempt + 1}) {method.upper()} {url}: {str(e)}")
                    continue
                return False, None, f"Connection error [{method.upper()} {url}]: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error {method.upper()} {url}: {str(e)}")
                return False, None, f"Unexpected error [{method.upper()} {url}]: {str(e)}"
        
        return False, None, "Failed after multiple retry attempts"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection and authentication"""
        success, response, message = self._make_request("GET", "/reservation/navigationGetRoomBookings")
        if success:
            return True, "✅ Connection successful!"
        else:
            self.last_error = message
            return False, f"❌ Connection failed: {message}"
    
    def fetch_bookings(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None) -> Tuple[bool, Optional[List], str]:
        """
        Fetch bookings from Eden Beach API
        
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
        
        success, response, message = self._make_request("GET", "/reservation/navigationGetRoomBookings", params=params)
        
        if success and response:
            bookings = []
            if isinstance(response, list):
                bookings = response
            elif isinstance(response, dict):
                for key in ["reservations", "bookings", "data", "rooms"]:
                    if key in response and isinstance(response[key], list):
                        bookings = response[key]
                        break
            self.last_sync_time = datetime.now()
            logger.info(f"Fetched {len(bookings)} bookings")
            return True, bookings, f"Successfully fetched {len(bookings)} bookings"
        else:
            return False, None, message
    
    def fetch_booking_details(self, booking_id: str) -> Tuple[bool, Optional[Dict], str]:
        """Fetch details for a specific booking"""
        success, response, message = self._make_request("GET", f"/api/bookings/{booking_id}")
        return success, response.get("booking") if success else None, message
    
    def fetch_availability(self, start_date: str, end_date: str) -> Tuple[bool, Optional[Dict], str]:
        """Fetch room availability for date range"""
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        success, response, message = self._make_request("GET", "/api/availability", params=params)
        return success, response.get("availability") if success else None, message
    
    def create_booking(self, booking_data: Dict) -> Tuple[bool, Optional[Dict], str]:
        """Create a new booking"""
        success, response, message = self._make_request("POST", "/api/bookings", data=booking_data)
        return success, response.get("booking") if success else None, message
    
    def update_booking(self, booking_id: str, update_data: Dict) -> Tuple[bool, Optional[Dict], str]:
        """Update an existing booking"""
        success, response, message = self._make_request("PUT", f"/api/bookings/{booking_id}", data=update_data)
        return success, response.get("booking") if success else None, message
    
    def fetch_guests(self) -> Tuple[bool, Optional[List], str]:
        """Fetch guest information"""
        success, response, message = self._make_request("GET", "/api/guests")
        if success and response:
            guests = response.get("guests", [])
            return True, guests, f"Successfully fetched {len(guests)} guests"
        return False, None, message
    
    def fetch_rooms(self) -> Tuple[bool, Optional[List], str]:
        """Fetch room inventory"""
        success, response, message = self._make_request("GET", "/api/rooms")
        if success and response:
            rooms = response.get("rooms", [])
            return True, rooms, f"Successfully fetched {len(rooms)} rooms"
        return False, None, message


class EdenBeachDataSync:
    """Handle data synchronization between Eden Beach API and Supabase"""
    
    def __init__(self, api_client: EdenBeachAPIClient, supabase_client):
        self.api_client = api_client
        self.supabase = supabase_client
        self.sync_status = {
            "bookings": False,
            "guests": False,
            "rooms": False,
            "last_sync": None,
            "error_count": 0
        }
    
    def sync_bookings(self) -> Dict:
        """Sync bookings from Eden Beach to Supabase"""
        try:
            success, bookings, message = self.api_client.fetch_bookings()
            
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
                    self.supabase.table("reservations").upsert(
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
    
    def sync_guests(self) -> Dict:
        """Sync guest information"""
        try:
            success, guests, message = self.api_client.fetch_guests()
            
            if not success:
                self.sync_status["error_count"] += 1
                return {
                    "success": False,
                    "message": message,
                    "count": 0
                }
            
            synced_count = 0
            for guest in guests:
                try:
                    transformed = self._transform_guest(guest)
                    self.supabase.table("guests").upsert(
                        transformed,
                        on_conflict="guest_id"
                    ).execute()
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing guest {guest.get('id')}: {str(e)}")
                    self.sync_status["error_count"] += 1
            
            self.sync_status["guests"] = True
            return {
                "success": True,
                "message": f"Successfully synced {synced_count} guests",
                "count": synced_count
            }
        
        except Exception as e:
            logger.error(f"Guest sync error: {str(e)}")
            self.sync_status["error_count"] += 1
            return {
                "success": False,
                "message": f"Sync error: {str(e)}",
                "count": 0
            }
    
    def sync_rooms(self) -> Dict:
        """Sync room inventory"""
        try:
            success, rooms, message = self.api_client.fetch_rooms()
            
            if not success:
                self.sync_status["error_count"] += 1
                return {
                    "success": False,
                    "message": message,
                    "count": 0
                }
            
            synced_count = 0
            for room in rooms:
                try:
                    transformed = self._transform_room(room)
                    self.supabase.table("rooms").upsert(
                        transformed,
                        on_conflict="room_id"
                    ).execute()
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing room {room.get('id')}: {str(e)}")
                    self.sync_status["error_count"] += 1
            
            self.sync_status["rooms"] = True
            return {
                "success": True,
                "message": f"Successfully synced {synced_count} rooms",
                "count": synced_count
            }
        
        except Exception as e:
            logger.error(f"Room sync error: {str(e)}")
            self.sync_status["error_count"] += 1
            return {
                "success": False,
                "message": f"Sync error: {str(e)}",
                "count": 0
            }
    
    def sync_all(self) -> Dict:
        """Perform complete sync of all data"""
        results = {
            "bookings": self.sync_bookings(),
            "guests": self.sync_guests(),
            "rooms": self.sync_rooms(),
            "timestamp": datetime.now().isoformat()
        }
        return results
    
    @staticmethod
    def _transform_booking(api_booking: Dict) -> Dict:
        """Transform API booking format to Supabase format"""
        return {
            "booking_id": api_booking.get("id"),
            "property": "Eden Beach Resort",
            "guest_name": api_booking.get("guest_name"),
            "email": api_booking.get("email"),
            "phone": api_booking.get("phone"),
            "checkin_date": api_booking.get("check_in_date"),
            "checkout_date": api_booking.get("check_out_date"),
            "room_type": api_booking.get("room_type"),
            "number_of_guests": api_booking.get("number_of_guests"),
            "total_price": api_booking.get("total_price"),
            "status": api_booking.get("status", "confirmed"),
            "notes": api_booking.get("notes", ""),
            "source": "Eden Beach API",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def _transform_guest(api_guest: Dict) -> Dict:
        """Transform API guest format to Supabase format"""
        return {
            "guest_id": api_guest.get("id"),
            "name": api_guest.get("name"),
            "email": api_guest.get("email"),
            "phone": api_guest.get("phone"),
            "country": api_guest.get("country"),
            "city": api_guest.get("city"),
            "guest_type": api_guest.get("guest_type", "regular"),
            "created_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def _transform_room(api_room: Dict) -> Dict:
        """Transform API room format to Supabase format"""
        return {
            "room_id": api_room.get("id"),
            "room_number": api_room.get("room_number"),
            "room_type": api_room.get("type"),
            "capacity": api_room.get("capacity"),
            "price_per_night": api_room.get("price_per_night"),
            "amenities": json.dumps(api_room.get("amenities", [])),
            "status": api_room.get("status", "available"),
            "created_at": datetime.now().isoformat()
        }
    
    def get_sync_status(self) -> Dict:
        """Get current sync status"""
        return {
            **self.sync_status,
            "last_sync_formatted": self.sync_status["last_sync"].strftime("%Y-%m-%d %H:%M:%S") 
                                   if self.sync_status["last_sync"] else "Never"
        }
