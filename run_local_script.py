# -*- coding: utf-8 -*-
"""
Created on Tue Jun 10 21:57:25 2025

@author: DTRManning
"""

import sqlite3
import os
from datetime import datetime, timedelta, timezone

# Ensure import works
os.chdir('C:\\Users\\DTRManning\\Desktop\\demand-response-api')
from demand_response_api import app, init_db

# Create in-memory database
mem_conn = sqlite3.connect(":memory:")
mem_conn.row_factory = sqlite3.Row
init_db(mem_conn)

# Inject in-memory DB into Flask app and set testing flag
app.config['DB_CONN'] = mem_conn
app.config['TESTING'] = True  # This prevents teardown from closing our connection

# Use fixed base time for determinism
now = datetime.now(timezone.utc)
now = now.replace(minute=0, second=0, microsecond=0) # Round down to beginning of current hour

def generate_payload(start_offset_minutes=0, duration_minutes=60):
    start = now + timedelta(minutes=start_offset_minutes)
    end = start + timedelta(minutes=duration_minutes)
    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "entity": "TestEntity",
        "message": "Test Message",
        "metadata": {"type": "test"}
    }

# Run simple tests locally - no need for app_context workaround
client = app.test_client()

# Create Event
payload = generate_payload()
resp = client.post('/events', json=payload)
print("Create:", resp.status_code, resp.get_json())
eid = resp.get_json()['id']

# Get Event
resp = client.get(f'/events/{eid}')
print("Read:", resp.status_code, resp.get_json())

# Update Event
payload['message'] = "Updated Message"
resp = client.put(f'/events/{eid}', json=payload)
print("Update:", resp.status_code, resp.get_json())

# Delete Event
resp = client.delete(f'/events/{eid}')
print("Delete:", resp.status_code, resp.get_json())

# Verify Deletion
resp = client.get(f'/events/{eid}')
print("Verify Deletion:", resp.status_code)

mem_conn.close()
