from flask import Flask, request, jsonify
from enum import Enum
from datetime import datetime
import uuid
from typing import Dict, Any
from dataclasses import dataclass, field, asdict

app = Flask(__name__)

# In-memory storage for events
events_db = []

class EventLevel(str, Enum):
    HIGH = "High"
    CRITICAL = "Critical"

@dataclass
class DemandResponseEvent:
    level: EventLevel
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"  # Default timezone
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)  # Flexible metadata field
    id: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self):
        result = asdict(self)
        result['level'] = self.level.value
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat()
        return result

# Helper function to convert JSON to DemandResponseEvent
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
    event = parse_event_data(data)
    events_db.append(event)
    return jsonify(event.to_dict())

# Get current active event (if any)
@app.route("/events/active", methods=["GET"])
def get_active_event():
    now = datetime.now()
    active_events = [event for event in events_db if event.start_time <= now <= event.end_time]
    
    # Return the most severe active event if multiple exist
    if not active_events:
        return jsonify(None)
    
    # Prioritize Critical events over High events
    critical_events = [e for e in active_events if e.level == EventLevel.CRITICAL]
    if critical_events:
        return jsonify(critical_events[0].to_dict())
    
    return jsonify(active_events[0].to_dict())

# Get future events
@app.route("/events/future", methods=["GET"])
def get_future_events():
    now = datetime.now()
    future_events = [event.to_dict() for event in events_db if event.start_time > now]
    return jsonify(future_events)

# Get upcoming event (soonest future event)
@app.route("/events/upcoming", methods=["GET"])
def get_upcoming_event():
    now = datetime.now()
    future_events = [event for event in events_db if event.start_time > now]
    
    if not future_events:
        return jsonify(None)
    
    # Sort by start time and return the soonest event
    soonest_event = sorted(future_events, key=lambda e: e.start_time)[0]
    return jsonify(soonest_event.to_dict())

# Get all events (optionally filter by status)
@app.route("/events/", methods=["GET"])
def get_events():
    status = request.args.get('status', 'all').lower()
    now = datetime.now()
    
    if status == 'all':
        return jsonify([event.to_dict() for event in events_db])
    elif status == 'active':
        active_events = [event.to_dict() for event in events_db if event.start_time <= now <= event.end_time]
        return jsonify(active_events)
    elif status == 'future':
        future_events = [event.to_dict() for event in events_db if event.start_time > now]
        return jsonify(future_events)
    elif status == 'past':
        past_events = [event.to_dict() for event in events_db if event.end_time < now]
        return jsonify(past_events)
    else:
        return jsonify({"error": "Invalid status parameter. Use 'all', 'active', 'future', or 'past'"}), 400

if __name__ == "__main__":
    app.run(debug=True)



