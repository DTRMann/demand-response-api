import pytest
import sqlite3
from datetime import datetime, timedelta, timezone

from demand_response_api import app, init_db

@pytest.fixture
def db_conn():
    # New in-memory db created for each test
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()

@pytest.fixture
def client(db_conn):
    app.config['DB_CONN'] = db_conn
    app.config['TESTING'] = True # Prevent teardown from using local memory
    with app.test_client() as c:
        yield c

def generate_event_payload(start_offset=0, duration_minutes=60):
    now = datetime.now(timezone.utc)
    now = now.replace(minute=0, second=0, microsecond=0) # Round down to beginning of current hour
    start = now + timedelta(minutes=start_offset)
    end = start + timedelta(minutes=duration_minutes)
    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "entity": "TestEntity",
        "message": "Test Message",
        "metadata": {"type": "test"}
    }

# Test crud
def test_create_event(client):
    payload = generate_event_payload()
    resp = client.post('/events', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'id' in data

def test_get_event(client):
    payload = generate_event_payload()
    create_resp = client.post('/events', json=payload)
    eid = create_resp.get_json()['id']

    get_resp = client.get(f'/events/{eid}')
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert data['entity'] == payload['entity']

def test_update_event(client):
    payload = generate_event_payload()
    create_resp = client.post('/events', json=payload)
    eid = create_resp.get_json()['id']

    updated_payload = payload.copy()
    updated_payload['message'] = "Updated Message"
    update_resp = client.put(f'/events/{eid}', json=updated_payload)
    assert update_resp.status_code == 200

    get_resp = client.get(f'/events/{eid}')
    assert get_resp.get_json()['message'] == "Updated Message"

def test_delete_event(client):
    payload = generate_event_payload()
    create_resp = client.post('/events', json=payload)
    eid = create_resp.get_json()['id']

    del_resp = client.delete(f'/events/{eid}')
    assert del_resp.status_code == 200

    get_resp = client.get(f'/events/{eid}')
    assert get_resp.status_code == 404

def test_list_events(client):
    client.post('/events', json=generate_event_payload(start_offset=-90, duration_minutes=30))  # past
    client.post('/events', json=generate_event_payload(start_offset=0, duration_minutes=90))  # active
    client.post('/events', json=generate_event_payload(start_offset=90, duration_minutes=30))   # future

    resp_all = client.get('/events')
    assert resp_all.status_code == 200
    assert len(resp_all.get_json()) == 3

    resp_active = client.get('/events?status=active')
    assert resp_active.status_code == 200
    assert len(resp_active.get_json()) == 1

    resp_future = client.get('/events?status=future')
    assert resp_future.status_code == 200
    assert len(resp_future.get_json()) == 1

    resp_past = client.get('/events?status=past')
    assert resp_past.status_code == 200
    assert len(resp_past.get_json()) == 1
