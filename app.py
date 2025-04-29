import json
import logging
import sqlite3
import uuid
from flask import Flask, request, jsonify, abort, g
from datetime import datetime, timezone
from pydantic import BaseModel, ValidationError, validator
from typing import Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)
DB_PATH = 'events.db'

# Request validation
class EventSchema(BaseModel):
    start_time: datetime
    end_time: datetime
    entity: str
    message: Optional[str] = ''
    metadata: Dict = {}

    @validator('start_time', 'end_time')
    def must_be_utc(cls, v):
        if v.tzinfo is None:
            raise ValueError('timestamp must include timezone')
        # normalize to UTC
        return v.astimezone(timezone.utc)

# per-request DB connection
def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # enforce WAL for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop('db', None)
    if db:
        db.close()

def db_execute(query, params=(), fetch=False, many=False):
    """
    Returns:
      - If fetch: list of rows
      - Else: int of affected rows
    """
    conn = get_db()
    c = conn.cursor()
    if many:
        c.executemany(query, params)
    else:
        c.execute(query, params)
    conn.commit()
    if fetch:
        return c.fetchall()
    return c.rowcount

# Initialize database with integer times
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            start_time INTEGER NOT NULL,
            end_time INTEGER NOT NULL,
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

def epoch_to_iso(ts_int: int) -> str:
    return datetime.fromtimestamp(ts_int, tz=timezone.utc).isoformat()

# --- CRUD operations ---

@app.route('/events', methods=['POST'])
def create_event():
    
    raw = request.get_json() or abort(400, description='Invalid JSON body')
    try:
        ev = EventSchema(**raw)
    except ValidationError as e:
        abort(400, description=e.json())
    eid = str(uuid.uuid4())
    st_i = int(ev.start_time.timestamp())
    et_i = int(ev.end_time.timestamp())
    meta_json = json.dumps(ev.metadata)

    try:
        db_execute(
            'INSERT INTO events(id, start_time, end_time, entity, message, metadata) VALUES (?,?,?,?,?,?)',
            (eid, st_i, et_i, ev.entity, ev.message, meta_json)
        )
    except sqlite3.IntegrityError as e:
        logging.error("DB insert failed: %s", e)
        abort(500, description='Could not create event')
    return jsonify({'id': eid}), 201

@app.route('/events', methods=['GET'])
def list_events():
    
    status = request.args.get('status', 'all')
    now_i = int(datetime.utcnow().replace(tzinfo=timezone.utc).timestamp())
    params = []
    filters = []

    if status == 'active':
        filters.append('start_time <= ? AND end_time >= ?')
        params += [now_i, now_i]
    elif status == 'future':
        filters.append('start_time > ?')
        params.append(now_i)
    elif status == 'past':
        filters.append('end_time < ?')
        params.append(now_i)

    ent = request.args.get('entity')
    if ent:
        filters.append('entity = ?')
        params.append(ent)

    q = 'SELECT * FROM events'
    if filters:
        q += ' WHERE ' + ' AND '.join(filters)

    rows = db_execute(q, tuple(params), fetch=True)
    out = []
    for r in rows:
        out.append({
            'id': r['id'],
            'start_time': epoch_to_iso(r['start_time']),
            'end_time':   epoch_to_iso(r['end_time']),
            'entity':     r['entity'],
            'message':    r['message'],
            'metadata':   json.loads(r['metadata'] or '{}')
        })
    return jsonify(out)

@app.route('/events/<eid>', methods=['GET','PUT','DELETE'])
def event_detail(eid):
    
    if request.method == 'GET':
        rows = db_execute('SELECT * FROM events WHERE id = ?', (eid,), fetch=True)
        if not rows:
            abort(404, description='Event not found')
        r = rows[0]
        return jsonify({
            'id': r['id'],
            'start_time': epoch_to_iso(r['start_time']),
            'end_time':   epoch_to_iso(r['end_time']),
            'entity':     r['entity'],
            'message':    r['message'],
            'metadata':   json.loads(r['metadata'] or '{}')
        })

    if request.method == 'PUT':
        raw = request.get_json() or abort(400, description='Invalid JSON body')
        try:
            ev = EventSchema(**raw)
        except ValidationError as e:
            abort(400, description=e.json())
        st_i = int(ev.start_time.timestamp())
        et_i = int(ev.end_time.timestamp())
        meta_json = json.dumps(ev.metadata)

        rowcount = db_execute(
            'UPDATE events SET start_time=?, end_time=?, entity=?, message=?, metadata=? WHERE id=?',
            (st_i, et_i, ev.entity, ev.message, meta_json, eid)
        )
        if rowcount == 0:
            abort(404, description='Event not found')
        return jsonify({'id': eid})

    rowcount = db_execute('DELETE FROM events WHERE id=?', (eid,))
    if rowcount == 0:
        abort(404, description='Event not found')
    return jsonify({'id': eid}), 200

if __name__ == '__main__':
    init_db()
    app.run()


