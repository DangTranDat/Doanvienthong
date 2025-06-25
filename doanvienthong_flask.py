from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from datetime import datetime
import random
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# ========= CẤU HÌNH =========
coordinates = [
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

# ========= TRẠNG THÁI CHỐNG TRỘM =========
anti_theft_enabled = False
reference_position = None

# ========= HÀM TIỆN ÍCH =========
def get_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME'),
        port=os.environ.get('DB_PORT', 5432)
    )

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

# ========= ROUTE HTML =========
@app.route('/')
def index():
    return render_template('doanvienthong.html')

# ========= ROUTE LẤY DỮ LIỆU =========
@app.route('/data')
def data():
    global anti_theft_enabled, reference_position
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

        rows = rows[::-1]  # tăng dần thời gian

        data = []
        for row in rows:
            record = {
                'recorded_at': row[0].strftime('%Y-%m-%d %H:%M:%S'),
                'acc_total': row[1],
                'angle': row[2],
                'gyro_total': row[3],
                'alert_text': row[4] or '',
                'latitude': row[5],
                'longitude': row[6]
            }

            if anti_theft_enabled and reference_position:
                lat0, lon0 = reference_position
                lat1, lon1 = row[5], row[6]
                distance = haversine(lat0, lon0, lat1, lon1)
                record['distance_from_ref'] = round(distance, 4)
            else:
                record['distance_from_ref'] = None

            data.append(record)

        return jsonify({'records': data})

    except Exception as e:
        print("Lỗi trong /data:", e)
        return jsonify({'error': str(e)}), 500

# ========= ROUTE NHẬN DỮ LIỆU =========
@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json
        acc_total = data.get('acc_total')
        angle = data.get('angle')
        gyro_total = data.get('gyro_total')
        alert_text = data.get('alert_text')

        latitude = random.uniform(min_lat, max_lat)
        longitude = random.uniform(min_lng, max_lng)

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
        print("Lỗi khi ghi dữ liệu:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ========= BẬT CHỐNG TRỘM =========
@app.route('/enable_antitheft', methods=['POST'])
def enable_antitheft():
    global anti_theft_enabled, reference_position
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude
            FROM doanvienthong_table
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY recorded_at DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return jsonify({'error': 'Không tìm thấy tọa độ để làm mốc'}), 404

        reference_position = result
        anti_theft_enabled = True

        return jsonify({'status': 'started', 'reference': {
            'lat': reference_position[0],
            'lng': reference_position[1]
        }})

    except Exception as e:
        print("Lỗi trong enable_antitheft:", e)
        return jsonify({'error': str(e)}), 500

# ========= TẮT CHỐNG TRỘM =========
@app.route('/disable_antitheft', methods=['POST'])
def disable_antitheft():
    global anti_theft_enabled, reference_position
    anti_theft_enabled = False
    reference_position = None
    return jsonify({'status': 'stopped'})

# ========= KHỞI CHẠY =========
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
