# server.py
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime
import pandas as pd
import os

# Get the directory of the script
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder="templates")
CORS(app)

# Use a path relative to the script directory for the database
db_path = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class CallLog(db.Model):
    __tablename__ = 'call_log'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, nullable=False)
    event = db.Column(db.String(50), nullable=False)
    # Use server timestamp as the primary source of truth
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)
    # Store client time if provided
    client_time_str = db.Column(db.String(20), nullable=True)

@app.route('/log', methods=['POST', 'GET'])
def log_data():
    # Accept JSON POST first
    data = request.get_json(silent=True)
    if data:
        table_id = data.get('tableId') or data.get('table')
        event = data.get('event')
        time_str = data.get('time') # This is the client time
    else:
        # fallback to GET query params
        table_id = request.args.get('table') or request.args.get('tableId')
        event = request.args.get('event')
        time_str = request.args.get('time')

    if not table_id or not event:
        return jsonify({"status": "error", "message": "Missing table or event"}), 400

    try:
        table_id = int(table_id)
    except:
        return jsonify({"status":"error", "message":"table must be int"}), 400

    # We use the server's time for the database timestamp
    # but store the client's reported time for reference
    entry = CallLog(table_id=table_id, event=event, client_time_str=time_str)

    db.session.add(entry)
    db.session.commit()

    # also append to events.csv
    csv_path = os.path.join(basedir, 'events.csv')
    try:
        with open(csv_path, "a") as f:
            f.write(f"{entry.table_id},{entry.event},{entry.timestamp.isoformat()}\n")
    except Exception as e:
        print(f"Error writing to CSV: {e}")


    print(f"Data logged: Table {entry.table_id}, Event: {entry.event}, Time: {entry.timestamp}")
    return jsonify({"status": "success", "message": "Data logged"}), 200

@app.route('/data')
def get_all_data():
    try:
        # Query the database
        logs = CallLog.query.all()
        # Convert to list of dictionaries
        records = [
            {
                'id': log.id,
                'table_id': log.table_id,
                'event': log.event,
                'timestamp': log.timestamp.isoformat() # Use ISO format for JS
            } for log in logs
        ]
        
        if not records:
            return jsonify({'records': [], 'live_status': []})

        # --- Calculate Live Status ---
        # Group by table_id and find the latest event for each
        latest_events = {}
        for r in records:
            tbl_id = r['table_id']
            if tbl_id not in latest_events or r['timestamp'] > latest_events[tbl_id]['timestamp']:
                latest_events[tbl_id] = r

        live_status = []
        now = datetime.datetime.now()
        
        for table_id, r in latest_events.items():
            event_time = datetime.datetime.fromisoformat(r['timestamp'])
            minutes_ago = int((now - event_time).total_seconds() / 60)
            live_status.append({
                'table_id': int(r['table_id']),
                'event': r['event'],
                'minutes_ago': minutes_ago
            })
            
        return jsonify({'records': records, 'live_status': live_status})
        
    except Exception as e:
        print(f"Error in /data: {e}")
        # Fallback in case db is locked or table doesn't exist yet
        return jsonify({'records': [], 'live_status': []})


@app.route('/')
def index():
    # FIX: Render main.html instead of dashboard.html
    return render_template('main.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
