import requests
import json
from datetime import datetime, timedelta

# Base URL for API
base_url = "http://localhost:5000"

# Helper function to print responses nicely
def print_response(response):
    print(f"Status Code: {response.status_code}")
    print("Response:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("-" * 50)

# Get current time
now = datetime.now()

# Create a past event (ended 2 hours ago)
past_event = {
    "level": "High",
    "start_time": (now - timedelta(hours=4)).isoformat(),
    "end_time": (now - timedelta(hours=2)).isoformat(),
    "requesting_entity": "GridOperator1",  # Added required field
    "message": "Past demand response event",
    "metadata": {"region": "West"}
}

# Create a current active event
active_event = {
    "level": "Critical",
    "start_time": (now - timedelta(hours=1)).isoformat(),
    "end_time": (now + timedelta(hours=3)).isoformat(),
    "requesting_entity": "GridOperator2",  # Added required field
    "message": "Current active demand response event",
    "metadata": {"region": "Central"}
}

# Create a future event
future_event = {
    "level": "High",
    "start_time": (now + timedelta(hours=5)).isoformat(),
    "end_time": (now + timedelta(hours=8)).isoformat(),
    "requesting_entity": "GridOperator1",  # Added required field
    "message": "Scheduled future demand response event",
    "metadata": {"region": "East"}
}

print("1. Creating a past event...")
response = requests.post(f"{base_url}/events/", json=past_event)
print_response(response)

print("2. Creating a current active event...")
response = requests.post(f"{base_url}/events/", json=active_event)
print_response(response)

print("3. Creating a future event...")
response = requests.post(f"{base_url}/events/", json=future_event)
print_response(response)

print("4. Getting all current active events...")
response = requests.get(f"{base_url}/events/active")
print_response(response)

print("5. Getting active events for a specific entity...")
response = requests.get(f"{base_url}/events/active?entity=GridOperator2")
print_response(response)

print("6. Getting all future events...")
response = requests.get(f"{base_url}/events/future")
print_response(response)

print("7. Getting future events for a specific entity...")
response = requests.get(f"{base_url}/events/future?entity=GridOperator1")
print_response(response)

print("8. Getting all events...")
response = requests.get(f"{base_url}/events/")
print_response(response)

print("9. Getting only active events using status parameter...")
response = requests.get(f"{base_url}/events/?status=active")
print_response(response)

print("10. Getting only past events...")
response = requests.get(f"{base_url}/events/?status=past")
print_response(response)

print("11. Getting events filtered by entity...")
response = requests.get(f"{base_url}/events/?entity=GridOperator1")
print_response(response)

print("12. Getting active events for a specific entity...")
response = requests.get(f"{base_url}/events/?status=active&entity=GridOperator2")
print_response(response)

print("13. Test invalid event (missing required field)...")
invalid_event = {
    "level": "High",
    "start_time": now.isoformat(),
    "end_time": (now + timedelta(hours=2)).isoformat(),
    # Missing requesting_entity field
    "message": "This should fail validation"
}
response = requests.post(f"{base_url}/events/", json=invalid_event)
print_response(response)

