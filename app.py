import json
import logging
import sqlite3
from flask import Flask, request, jsonify, abort
from datetime import datetime, timezone
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)
DB_PATH = 'events.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            entity TEXT NOT NULL,
            message TEXT,
            metadata TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_start ON events(start_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_end ON events(end_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_entity ON events(entity)')
    conn.commit()
    conn.close()

# DB helper
def db_execute(query, params=(), fetch=False, many=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        if many:
            c.executemany(query, params)
        else:
            c.execute(query, params)
        conn.commit()
        return c.fetchall() if fetch else None
    finally:
        conn.close()

# Utility: require ISO8601 UTC timestamps
def parse_iso8601(ts):
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            abort(400, description='Timestamp must include timezone')
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        abort(400, description=f'Invalid ISO8601 timestamp: {ts}')

# CRUD operations
@app.route('/events', methods=['POST'])
def create_event():
    data = request.get_json() or abort(400, description='Invalid JSON')
    eid = data.get('id') or str(uuid.uuid4())
    st = parse_iso8601(data.get('start_time', ''))
    et = parse_iso8601(data.get('end_time', ''))
    ent = data.get('entity') or abort(400, description='"entity" required')
    msg = data.get('message', '')
    meta = json.dumps(data.get('metadata', {}))
    db_execute(
        'INSERT OR REPLACE INTO events(id,start_time,end_time,entity,message,metadata) VALUES (?,?,?,?,?,?)',
        (eid, st, et, ent, msg, meta)
    )
    return jsonify({'id': eid}), 201

@app.route('/events', methods=['GET'])
def list_events():
    status = request.args.get('status', 'all')
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    params = []
    q = 'SELECT * FROM events'
    conds = []
    if status == 'active':
        conds.append('start_time <= ? AND end_time >= ?')
        params += [now, now]
    elif status == 'future':
        conds.append('start_time > ?')
        params.append(now)
    elif status == 'past':
        conds.append('end_time < ?')
        params.append(now)
    if status != 'all':
        q += ' WHERE ' + ' AND '.join(conds)
    ent = request.args.get('entity')
    if ent:
        q += (' WHERE ' if 'WHERE' not in q else ' AND ') + 'entity = ?'
        params.append(ent)
    rows = db_execute(q, tuple(params), fetch=True)
    events = []
    for r in rows:
        events.append({
            'id': r['id'],
            'start_time': r['start_time'],
            'end_time': r['end_time'],
            'entity': r['entity'],
            'message': r['message'],
            'metadata': json.loads(r['metadata'] or '{}')
        })
    return jsonify(events)

# TODO add details to error messages when returning 400 error.
@app.route('/events/<eid>', methods=['GET','PUT','DELETE'])
def event_detail(eid):
    if request.method == 'GET':
        rows = db_execute('SELECT * FROM events WHERE id = ?', (eid,), fetch=True)
        if not rows: abort(404) 
        r = rows[0]
        return jsonify({
            'id': r['id'], 'start_time': r['start_time'], 'end_time': r['end_time'],
            'entity': r['entity'], 'message': r['message'], 'metadata': json.loads(r['metadata'] or '{}')
        })

    if request.method == 'PUT':
        data = request.get_json() or abort(400)
        st = parse_iso8601(data.get('start_time', ''))
        et = parse_iso8601(data.get('end_time', ''))
        ent = data.get('entity') or abort(400)
        msg = data.get('message', '')
        meta = json.dumps(data.get('metadata', {}))
        db_execute(
            'UPDATE events SET start_time=?,end_time=?,entity=?,message=?,metadata=? WHERE id=?',
            (st, et, ent, msg, meta, eid)
        )
        return jsonify({'id': eid})

    if request.method == 'DELETE':
        db_execute('DELETE FROM events WHERE id=?', (eid,))
        return jsonify({'id': eid}), 200

if __name__ == '__main__':
    init_db()
    app.run()


