
import pytest
from datetime import datetime, timedelta, timezone

import app

@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    
    # Point DB_PATH to a fresh temporary file
    db_file = tmp_path / "test_events.db"
    monkeypatch.setattr(app, 'DB_PATH', str(db_file))
    # Initialize fresh database
    app.init_db()
    yield

@pytest.fixture
def client():
    return app.app.test_client()

# Helper to generate ISO8601 UTC timestamps
def utc_iso(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()

def test_create_and_get_event(client):
    
    start = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=-1))
    end = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=1))
    payload = {
        'start_time': start,
        'end_time': end,
        'entity': 'tester',
        'message': 'hello',
        'metadata': {'foo': 'bar'}
    }
    # Create
    resp = client.post('/events', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'id' in data
    eid = data['id']

    # Get list
    resp = client.get('/events')
    assert resp.status_code == 200
    all_events = resp.get_json()
    assert any(e['id'] == eid for e in all_events)

    # Get detail
    resp = client.get(f'/events/{eid}')
    assert resp.status_code == 200
    detail = resp.get_json()
    assert detail['entity'] == 'tester'
    assert detail['message'] == 'hello'
    assert detail['metadata']['foo'] == 'bar'

def test_update_event(client):
    # First create
    start = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=-2))
    end = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=2))
    resp = client.post('/events', json={
        'start_time': start,
        'end_time': end,
        'entity': 'uploader'
    })
    eid = resp.get_json()['id']

    # Update
    new_start = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=-5))
    new_end = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=5))
    update_data = {
        'start_time': new_start,
        'end_time': new_end,
        'entity': 'updater',
        'message': 'updated',
        'metadata': {'x': 1}
    }
    resp = client.put(f'/events/{eid}', json=update_data)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == eid

    # Verify
    resp = client.get(f'/events/{eid}')
    detail = resp.get_json()
    assert detail['entity'] == 'updater'
    assert detail['message'] == 'updated'
    assert detail['metadata'] == {'x': 1}

def test_delete_event(client):
    
    # Create
    start = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=-1))
    end = utc_iso(datetime.now(timezone.utc) + timedelta(minutes=1))
    eid = client.post('/events', json={
        'start_time': start,
        'end_time': end,
        'entity': 'deleter'
    }).get_json()['id']

    # Delete
    resp = client.delete(f'/events/{eid}')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == eid

    # Confirm gone
    resp = client.get(f'/events/{eid}')
    assert resp.status_code == 404

def test_status_filters(client):
    
    now = datetime.now(timezone.utc)
    # Past event
    p_start = utc_iso(now - timedelta(hours=2))
    p_end = utc_iso(now - timedelta(hours=1))
    past_id = client.post('/events', json={'start_time': p_start, 'end_time': p_end, 'entity': 'e'}).get_json()['id']
    # Active event
    a_start = utc_iso(now - timedelta(minutes=1))
    a_end = utc_iso(now + timedelta(minutes=1))
    active_id = client.post('/events', json={'start_time': a_start, 'end_time': a_end, 'entity': 'e'}).get_json()['id']
    # Future event
    f_start = utc_iso(now + timedelta(hours=1))
    f_end = utc_iso(now + timedelta(hours=2))
    future_id = client.post('/events', json={'start_time': f_start, 'end_time': f_end, 'entity': 'e'}).get_json()['id']

    # All
    all_resp = client.get('/events?status=all').get_json()
    assert {e['id'] for e in all_resp} == {past_id, active_id, future_id}

    # Past
    past_resp = client.get('/events?status=past').get_json()
    assert [e['id'] for e in past_resp] == [past_id]

    # Active
    act_resp = client.get('/events?status=active').get_json()
    assert [e['id'] for e in act_resp] == [active_id]

    # Future
    fut_resp = client.get('/events?status=future').get_json()
    assert [e['id'] for e in fut_resp] == [future_id]

    # Entity filter
    ent_resp = client.get('/events?status=all&entity=e').get_json()
    assert set(e['id'] for e in ent_resp) == {past_id, active_id, future_id}

def test_invalid_requests(client):
    
    # Missing JSON
    resp = client.post('/events', data='')
    assert resp.status_code == 400

    # Invalid timestamp format
    resp = client.post('/events', json={'start_time': 'bad', 'end_time': 'bad', 'entity': 'x'})
    assert resp.status_code == 400

    # Missing entity
    now_iso = utc_iso(datetime.now(timezone.utc))
    resp = client.post('/events', json={'start_time': now_iso, 'end_time': now_iso})
    assert resp.status_code == 400

    # Nonexistent GET/PUT/DELETE
    for method in ('get', 'put', 'delete'):
        resp = getattr(client, method)('/events/nonexistent')
        if method == 'get':
            assert resp.status_code == 404
        else:
            # PUT and DELETE return 400 or 404
            assert resp.status_code in (400, 404)

