from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from datetime import datetime
import random
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# Trạng thái chống trộm
anti_theft_enabled = False
reference_location = None

coordinates = [  # Tọa độ mẫu (như cũ)
    (21.006304796620064, 105.82409382625556),
    (21.00618460687564, 105.82404018207737),
    (21.006011833948428, 105.82439423365345),
    (21.00653265607812, 105.8246839122157),
    (21.006602766610587, 105.82449883980094),
    (21.006409962567016, 105.82439423365345),
    (21.00637741121041, 105.8245980815306),
    (21.006242197806916, 105.82439423365345)
]
latitudes = [c[0] for c in coordinates]
longitudes = [c[1] for c in coordinates]
min_lat, max_lat = min(latitudes), max(latitudes)
min_lng, max_lng = min(longitudes), max(longitudes)

def get_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME'),
        port=os.environ.get('DB_PORT', 5432)
    )

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Bán kính Trái Đất tính theo km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

@app.route('/')
def index():
    return render_template('doanvienthong.html')

@app.route('/toggle-anti-theft', methods=['POST'])
def toggle_anti_theft():
    global anti_theft_enabled, reference_location
    req_data = request.json
    anti_theft_enabled = req_data.get('enabled', False)

    if anti_theft_enabled:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT latitude, longitude
                FROM doanvienthong_table
                ORDER BY recorded_at DESC LIMIT 1
            """)
            result = cursor.fetchone()
            reference_location = result if result else None
            cursor.close()
            conn.close()
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        reference_location = None

    return jsonify({'status': 'ok', 'enabled': anti_theft_enabled})

@app.route('/status')
def status():
    return jsonify({
        'anti_theft_enabled': anti_theft_enabled,
        'reference_location': reference_location
    })

@app.route('/upload', methods=['POST'])
def upload_data():
    global anti_theft_enabled, reference_location

    try:
        data = request.json
        acc_total = data.get('acc_total')
        angle = data.get('angle')
        gyro_total = data.get('gyro_total')
        alert_text = data.get('alert_text')

        latitude = random.uniform(min_lat, max_lat)
        longitude = random.uniform(min_lng, max_lng)

        if anti_theft_enabled and reference_location:
            ref_lat, ref_lng = reference_location
            distance = haversine(ref_lat, ref_lng, latitude, longitude)
            print(f"Khoảng cách từ mốc: {distance:.2f} km")
            if distance > 0.02:  # ví dụ: nếu đi xa hơn 20m
                alert_text = "Phát hiện di chuyển bất thường"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO doanvienthong_table (acc_total, angle, gyro_total, alert_text, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (acc_total, angle, gyro_total, alert_text, latitude, longitude))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/data')
def data():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recorded_at, acc_total, angle, gyro_total, alert_text, latitude, longitude
            FROM doanvienthong_table
            ORDER BY recorded_at DESC
            LIMIT 20
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        rows = rows[::-1]

        data = []
        for row in rows:
            data.append({
                'recorded_at': row[0].strftime('%Y-%m-%d %H:%M:%S'),
                'acc_total': row[1],
                'angle': row[2],
                'gyro_total': row[3],
                'alert_text': row[4] or '',
                'latitude': row[5],
                'longitude': row[6]
            })

        return jsonify({'records': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
