from flask import Flask, request, jsonify
from enum import Enum
from datetime import datetime
import uuid
from typing import Dict, Any
from dataclasses import dataclass, field, asdict

app = Flask(__name__)

# Events database
events_db = []

class EventLevel(str, Enum):
    HIGH = "High"
    CRITICAL = "Critical"

@dataclass
class DemandResponseEvent:
    level: EventLevel
    start_time: datetime
    end_time: datetime
    requesting_entity: str  # Required field for requesting entity
    timezone: str = "UTC"  # Default timezone
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)  # Flexible metadata field
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        
        # Validate required requesting_entity field
        if not self.requesting_entity:
            raise ValueError("requesting_entity is required")
    
    def to_dict(self):
        result = asdict(self)
        result['level'] = self.level.value
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat()
        return result

# Convert JSON to DemandResponseEvent
def parse_event_data(data):
    
    # Handle datetime strings
    if isinstance(data['start_time'], str):
        data['start_time'] = datetime.fromisoformat(data['start_time'])
    if isinstance(data['end_time'], str):
        data['end_time'] = datetime.fromisoformat(data['end_time'])
    
    # Handle event level
    if isinstance(data['level'], str):
        data['level'] = EventLevel(data['level'])
    
    return DemandResponseEvent(**data)

# Create a new demand response event
@app.route("/events/", methods=["POST"])
def create_event():
    
    data = request.get_json()
    
    try:
        event = parse_event_data(data)
        events_db.append(event)
        return jsonify(event.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid event data: {str(e)}"}), 400

# Get current active events
@app.route("/events/active", methods=["GET"])
def get_active_events():
    
    now = datetime.now()
    entity = request.args.get('entity')
    
    active_events = [event for event in events_db if event.start_time <= now <= event.end_time]
    
    # Filter by requesting entity if provided
    if entity:
        active_events = [event for event in active_events if event.requesting_entity == entity]
    
    # Return all active events as a list of dictionaries
    return jsonify([event.to_dict() for event in active_events])

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
    
    return jsonify([event.to_dict() for event in filtered_events])

if __name__ == "__main__":
    app.run(debug=True)



