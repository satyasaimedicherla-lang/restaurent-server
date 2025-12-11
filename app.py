import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import pandas as pd

app = Flask(__name__)
CORS(app)

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class CallLog(db.Model):
    __tablename__ = 'call_log'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, nullable=False)
    event = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)

# --- Global Analytics Logic ---
def calculate_analytics(logs_df):
    if logs_df.empty:
        return {
            'total': "0", 'open': "0", 'avg_resp': "0.0", 'avg_dlv': "0.0",
            'hourly': {i: 0 for i in range(24)}, 'closed': 0
        }

    # FIX: Create a copy to avoid SettingWithCopyWarning
    df = logs_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    total = 0
    closed_req = 0
    resp_times = []
    dlv_times = []
    hourly = {i: 0 for i in range(24)}
    
    tables = df.groupby('table_id')
    
    for tid, group in tables:
        events = group.sort_values('timestamp').to_dict('records')
        call_start = None
        
        for e in events:
            evt = e['event']
            ts = e['timestamp']
            
            if evt == "Customer_Called":
                total += 1
                call_start = ts
                h = ts.hour
                hourly[h] = hourly.get(h, 0) + 1
            elif evt == "Waiter_Responded" and call_start:
                diff = (ts - call_start).total_seconds() / 60
                resp_times.append(diff)
            elif (evt == "Food_Delivered" or "Bill" in evt) and call_start:
                diff = (ts - call_start).total_seconds() / 60
                dlv_times.append(diff)
                call_start = None
                closed_req += 1

    avg_resp = sum(resp_times)/len(resp_times) if resp_times else 0
    avg_dlv = sum(dlv_times)/len(dlv_times) if dlv_times else 0

    return {
        'total': str(total),
        'open': str(total - closed_req),
        'closed': closed_req,
        'avg_resp': f"{avg_resp:.1f}",
        'avg_dlv': f"{avg_dlv:.1f}",
        'hourly': hourly
    }

# --- Per-Table Analytics Logic ---
def get_table_analytics(logs_df, table_id):
    if logs_df.empty:
        return {"available": "Yes", "orders_received": "0", "orders_responded": "0", "orders_delivered": "0"}

    # FIX: Create a copy here too
    df = logs_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter for this specific table
    table_events = df[df['table_id'] == table_id].sort_values('timestamp')
    
    if table_events.empty:
        return {"available": "Yes", "orders_received": "0", "orders_responded": "0", "orders_delivered": "0"}

    orders_received = 0
    orders_responded = 0
    orders_delivered = 0
    
    for _, row in table_events.iterrows():
        evt = row['event']
        if evt == "Customer_Called":
            orders_received += 1
        elif evt == "Waiter_Responded":
            orders_responded += 1
        elif "Food_Delivered" in evt or "Bill" in evt:
            orders_delivered += 1

    # Check availability (based on last event)
    last_event = table_events.iloc[-1]['event']
    is_available = "Yes"
    if last_event in ["Customer_Called", "Waiter_Responded"]:
        is_available = "No"

    return {
        "available": is_available,
        "orders_received": str(orders_received),
        "orders_responded": str(orders_responded),
        "orders_delivered": str(orders_delivered)
    }

@app.route('/', methods=['GET'])
def home():
    return "SmartOps Server is Running!", 200

@app.route('/log', methods=['POST', 'GET'])
def log_data():
    data = request.get_json(silent=True) or request.args
    table_id = data.get('tableId') or data.get('table')
    event = data.get('event')

    if not table_id or not event:
        return jsonify({"status": "error"}), 400

    entry = CallLog(table_id=int(table_id), event=event)
    db.session.add(entry)
    db.session.commit()
    print(f"LOGGED: Table {table_id} - {event}")
    return jsonify({"status": "success"}), 200

@app.route('/data')
def get_data():
    try:
        logs_df = pd.read_sql_table('call_log', db.engine)
        analytics = calculate_analytics(logs_df)
    except Exception as e:
        print(f"Error: {e}")
        logs_df = pd.DataFrame()
        analytics = calculate_analytics(logs_df)

    live_status = []
    if not logs_df.empty:
        # FIX: Copy for live status calculation as well
        df = logs_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        latest = df.sort_values('timestamp').drop_duplicates(subset='table_id', keep='last')
        now = datetime.now()
        for _, r in latest.iterrows():
            last_event = r['event']
            status_display = last_event
            if last_event in ['Food_Delivered', 'Table_Closed 💰 Bill']:
                status_display = "Idle"
            
            last_time = r['timestamp'].to_pydatetime()
            minutes_ago = int((now - last_time).total_seconds() / 60)
            
            live_status.append({
                'table_id': int(r['table_id']),
                'status': status_display,
                'minutes_ago': minutes_ago
            })
            
    return jsonify({'analytics': analytics, 'live_status': live_status})

@app.route('/table/<int:table_id>/data')
def get_table_data(table_id):
    try:
        logs_df = pd.read_sql_table('call_log', db.engine)
        # We pass the raw df, the function inside will copy it
        stats = get_table_analytics(logs_df, table_id)
        return jsonify({'status': 'success', 'stats': stats}), 200
    except Exception as e:
        print(f"Error fetching table data: {e}")
        return jsonify({'status': 'error', 'stats': {}}), 500

# Initialize DB
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
