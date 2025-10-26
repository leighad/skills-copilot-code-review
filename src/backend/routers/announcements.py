"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from datetime import datetime
from bson import ObjectId
import pymongo

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def verify_authenticated_user(username: str) -> Dict[str, Any]:
    """Verify that the user is authenticated and return user info"""
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"]
    }


@router.get("/")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all currently active announcements (within date range)"""
    current_time = datetime.utcnow().isoformat() + "Z"
    
    # Find announcements that are currently active
    announcements = announcements_collection.find({
        "$or": [
            {"start_date": {"$exists": False}},
            {"start_date": None},
            {"start_date": {"$lte": current_time}}
        ],
        "end_date": {"$gte": current_time}
    }).sort("created_at", pymongo.DESCENDING)
    
    result = []
    for announcement in announcements:
        result.append({
            "id": str(announcement["_id"]),
            "message": announcement["message"],
            "start_date": announcement.get("start_date"),
            "end_date": announcement["end_date"],
            "created_by": announcement["created_by"],
            "created_at": announcement["created_at"]
        })
    
    return result


@router.get("/manage")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements for management (requires authentication)"""
    verify_authenticated_user(username)
    
    announcements = announcements_collection.find().sort("created_at", pymongo.DESCENDING)
    
    result = []
    for announcement in announcements:
        result.append({
            "id": str(announcement["_id"]),
            "message": announcement["message"],
            "start_date": announcement.get("start_date"),
            "end_date": announcement["end_date"],
            "created_by": announcement["created_by"],
            "created_at": announcement["created_at"]
        })
    
    return result


@router.post("/")
def create_announcement(
    message: str,
    end_date: str,
    username: str,
    start_date: str = None
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    user = verify_authenticated_user(username)
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if not end_date:
        raise HTTPException(status_code=400, detail="End date is required")
    
    # Validate date format
    try:
        datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if start_date:
            datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    announcement_data = {
        "message": message.strip(),
        "end_date": end_date,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if start_date:
        announcement_data["start_date"] = start_date
    
    result = announcements_collection.insert_one(announcement_data)
    
    return {
        "id": str(result.inserted_id),
        "message": "Announcement created successfully"
    }


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    end_date: str,
    username: str,
    start_date: str = None
) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    user = verify_authenticated_user(username)
    
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if not end_date:
        raise HTTPException(status_code=400, detail="End date is required")
    
    # Validate date format
    try:
        datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if start_date:
            datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    update_data = {
        "message": message.strip(),
        "end_date": end_date
    }
    
    if start_date:
        update_data["start_date"] = start_date
    else:
        # Remove start_date if not provided
        announcements_collection.update_one(
            {"_id": obj_id},
            {"$unset": {"start_date": ""}}
        )
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    return {"message": "Announcement updated successfully"}


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, Any]:
    """Delete an announcement (requires authentication)"""
    user = verify_authenticated_user(username)
    
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}