from flask import Flask, request, jsonify, abort
from datetime import datetime
import uuid
from typing import Dict, Any
from dataclasses import dataclass, field, asdict

app = Flask(__name__)

# Events database
events_db = []

@dataclass
class DemandResponseEvent:
    
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
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat()
        return result

# Convert JSON to DemandResponseEvent
def parse_event_data(data):
    
    try:
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
    except KeyError as e:
        raise ValueError(f"Missing required field: {e.args[0]}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid input: {str(e)}")
    
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


