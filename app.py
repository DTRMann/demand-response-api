from flask import Flask, request, jsonify, abort
from datetime import datetime
import uuid
from typing import Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

# From python scripts
from tzHandlingHelpers import get_utc_now


app = Flask(__name__)

# Events database
events_db = []

@dataclass
class DemandResponseEvent:
    
    start_time: datetime
    end_time: datetime
    requesting_entity: str
    timezone: str = "UTC"  # Default timezone
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        
        # Validate requesting_entity
        if not self.requesting_entity:
            raise ValueError("requesting_entity is required")
            
        # Validate timezone
        try:
            ZoneInfo(self.timezone)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{self.timezone}': {str(e)}")
            
        # Ensure datetime objects are timezone-aware in UTC
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must include timezone information")
        if self.end_time.tzinfo is None:
            raise ValueError("end_time must include timezone information")
            
        # Convert to UTC for storage
        self.start_time = self.start_time.astimezone(ZoneInfo("UTC"))
        self.end_time = self.end_time.astimezone(ZoneInfo("UTC"))
    
    def to_dict(self):
        """Convert to dict, with timezone-aware ISO format strings"""
        result = asdict(self)
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat()
        return result
        
    def to_local_dict(self):
        """Convert to dict with times in the event's specified timezone"""
        result = asdict(self)
        try:
            # Convert to the timezone specified in the event
            tz = ZoneInfo(self.timezone)
            result['start_time'] = self.start_time.astimezone(tz).isoformat()
            result['end_time'] = self.end_time.astimezone(tz).isoformat()
        except:
            # Fallback to UTC if timezone is invalid
            result['start_time'] = self.start_time.isoformat()
            result['end_time'] = self.end_time.isoformat()
        return result

# Convert JSON to DemandResponseEvent
def parse_event_data(data):
    """Parse JSON input into a DemandResponseEvent with user-friendly date handling"""
    try:
        # Get the user's timezone from request
        user_timezone = data.get('timezone', 'UTC')
        
        # Validate timezone early
        try:
            tz = ZoneInfo(user_timezone)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{user_timezone}': {str(e)}")
        
        # Get the time strings from input
        start_time_str = data['start_time']
        end_time_str = data['end_time']
        
        # Try multiple formats for user convenience
        formats = [
            # ISO format
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            # Common date formats
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M"
        ]
        
        # Try to parse start_time with multiple formats
        start_time = None
        for fmt in formats:
            try:
                # Parse as naive datetime, then assign the specified timezone
                start_time = datetime.strptime(start_time_str, fmt).replace(tzinfo=tz)
                break
            except ValueError:
                continue
                
        if start_time is None:
            raise ValueError(f"Could not parse start_time: '{start_time_str}'. Please use a format like '2025/04/24 14:30'")
            
        # Try to parse end_time with multiple formats
        end_time = None
        for fmt in formats:
            try:
                # Parse as naive datetime, then assign the specified timezone
                end_time = datetime.strptime(end_time_str, fmt).replace(tzinfo=tz)
                break
            except ValueError:
                continue
                
        if end_time is None:
            raise ValueError(f"Could not parse end_time: '{end_time_str}'. Please use a format like '2025/04/24 14:30'")
            
        # Update the data dict with parsed datetime objects
        data['start_time'] = start_time
        data['end_time'] = end_time
        
    except KeyError as e:
        raise ValueError(f"Missing required field: {e.args[0]}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {str(e)}")
    
    return DemandResponseEvent(**data)

# Create a new demand response event
@app.route("/events/", methods=["POST"])
def create_event():
    
    data = request.get_json()
    
    if not data:
        abort(400, description="No input provided")
    
    try:
        event = parse_event_data(data)
    except ValueError as e:
        abort(400, description=str(e))
    
    events_db.append(event)
    
    return jsonify(event.to_dict()), 201

# Get current active events
@app.route("/events/active", methods=["GET"])
def get_active_events():
    # Get current time in UTC with timezone info
    now = get_utc_now()
    
    entity = request.args.get('entity')
    output_timezone = request.args.get('output_timezone')
    
    active_events = [event for event in events_db if event.start_time <= now <= event.end_time]
    
    # Filter by requesting entity if provided
    if entity:
        active_events = [event for event in active_events if event.requesting_entity == entity]
    
    # Process each event for output
    result = []
    for event in active_events:
        event_dict = event.to_dict()
        
        # If output_timezone is specified, convert the times
        if output_timezone:
            try:
                output_tz = ZoneInfo(output_timezone)
                event_dict['start_time'] = event.start_time.astimezone(output_tz).isoformat()
                event_dict['end_time'] = event.end_time.astimezone(output_tz).isoformat()
            except:
                
                print('Timezone invalid')
                
                pass
        
        result.append(event_dict)
    
    return jsonify(result)

# Get future events
@app.route("/events/future", methods=["GET"])
def get_future_events():
    
    now = datetime.now()
    entity = request.args.get('entity')
    
    future_events = [event for event in events_db if event.start_time > now]
    
    # Filter by requesting entity if provided
    if entity:
        future_events = [event for event in future_events if event.requesting_entity == entity]
        
    return jsonify([event.to_dict() for event in future_events])

# Get all events (optionally filter by status and/or entity)
@app.route("/events/", methods=["GET"])
def get_events():
    
    status = request.args.get('status', 'all').lower()
    entity = request.args.get('entity')
    metadata_key = request.args.get('metadata_key')
    metadata_value = request.args.get('metadata_value')
    now = datetime.now()
    
    # First filter by status
    if status == 'all':
        filtered_events = events_db
    elif status == 'active':
        filtered_events = [event for event in events_db if event.start_time <= now <= event.end_time]
    elif status == 'future':
        filtered_events = [event for event in events_db if event.start_time > now]
    elif status == 'past':
        filtered_events = [event for event in events_db if event.end_time < now]
    else:
        return jsonify({"error": "Invalid status parameter. Use 'all', 'active', 'future', or 'past'"}), 400
    
    # Then filter by entity if provided
    if entity:
        filtered_events = [event for event in filtered_events if event.requesting_entity == entity]
    
    # Filter by metadata if both key and value are provided
    if metadata_key and metadata_value:
        filtered_events = [
            event for event in filtered_events 
            if metadata_key in event.metadata and event.metadata[metadata_key] == metadata_value
        ]
    # Filter by metadata key only
    elif metadata_key:
        filtered_events = [
            event for event in filtered_events 
            if metadata_key in event.metadata
        ]
    
    return jsonify([event.to_dict() for event in filtered_events])

# Get a specific event by ID
@app.route("/events/<event_id>", methods=["GET"])
def get_event(event_id):
    
    event = next((e for e in events_db if e.id == event_id), None)
    
    if not event:
        abort(404, description=f"Event with ID {event_id} not found")
    
    return jsonify(event.to_dict())

# Update an existing event
@app.route("/events/<event_id>", methods=["PUT"])
def update_event(event_id):
    
    event = next((e for e in events_db if e.id == event_id), None)
    
    if not event:
        abort(404, description=f"Event with ID {event_id} not found")
    
    data = request.get_json()
    
    if not data:
        abort(400, description="No input provided")
    
    # Preserve the ID
    data['id'] = event_id
    
    try:
        # Remove the old event
        events_db.remove(event)
        # Create updated event
        updated_event = parse_event_data(data)
        # Add to database
        events_db.append(updated_event)
    except ValueError as e:
        # If there was an error, add the original event back
        events_db.append(event)
        abort(400, description=str(e))
    
    return jsonify(updated_event.to_dict())

# Delete an event
@app.route("/events/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    
    event = next((e for e in events_db if e.id == event_id), None)
    
    if not event:
        abort(404, description=f"Event with ID {event_id} not found")
    
    events_db.remove(event)
    
    return jsonify({
        "id": event_id,
        "message": "Event deleted successfully"
    })

if __name__ == "__main__":
    app.run(debug=True)


