import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
DB_NAME = 'ips.db'

# Initialize DB
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Create a table for server data
        cur.execute('''
            CREATE TABLE IF NOT EXISTS server_data(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_port TEXT,
                server_local_ip TEXT,
                server_public_ip TEXT,
                timestamp TEXT
            )
        ''')
        # Create a table for client data
        cur.execute('''
            CREATE TABLE IF NOT EXISTS client_data(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_local_ip TEXT,
                client_public_ip TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()

@app.route('/server', methods=['POST'])
def server_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON received'}), 400

    server_port = data.get('server_port')
    server_local_ip = data.get('server_local_ip')
    server_public_ip = data.get('server_public_ip')
    timestamp = datetime.now().isoformat()

    if not (server_port and server_local_ip and server_public_ip):
        return jsonify({'error': 'Missing server_port/server_local_ip/server_public_ip'}), 400
    
    print(f"Received server data: {server_port}, {server_local_ip}, {server_public_ip}")

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO server_data(server_port, server_local_ip, server_public_ip, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (server_port, server_local_ip, server_public_ip, timestamp))
        conn.commit()

    return jsonify({'status': 'Server info stored', 'timestamp': timestamp}), 200

@app.route('/client', methods=['POST'])
def client_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON received'}), 400

    client_local_ip = data.get('client_local_ip')
    client_public_ip = data.get('client_public_ip')
    timestamp = datetime.now().isoformat()

    if not (client_local_ip and client_public_ip):
        return jsonify({'error': 'Missing client_local_ip/client_public_ip'}), 400

    print(f"Received client data: {client_local_ip}, {client_public_ip}")

    # Store client info
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO client_data(client_local_ip, client_public_ip, timestamp)
            VALUES (?, ?, ?)
        ''', (client_local_ip, client_public_ip, timestamp))
        conn.commit()

    # Fetch the latest server data
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT server_port, server_local_ip, server_public_ip
            FROM server_data
            ORDER BY id DESC
            LIMIT 1
        ''')
        server_row = cur.fetchone()

    if not server_row:
        # No server data found
        return jsonify({'error': 'No server data available'}), 500

    server_port, server_local_ip, server_public_ip = server_row

    # Compare client public IP to latest server public IP
    if client_public_ip == server_public_ip:
        server_ip = server_local_ip
    else:
        server_ip = server_public_ip

    print(f"Suggested server IP: {server_ip} ({'Same' if client_public_ip == server_public_ip else 'Different'} public IP)")

    return jsonify({
        'server_ip': server_ip,
        'server_port': server_port,
        'stored_at': timestamp
    }), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=4337)
