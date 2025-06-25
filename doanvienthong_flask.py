from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from datetime import datetime
import random
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# Danh sách các tọa độ mẫu
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

# Tính min/max của từng phần
latitudes = [coord[0] for coord in coordinates]
longitudes = [coord[1] for coord in coordinates]

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
    """
    Tính khoảng cách giữa hai điểm (lat1, lon1) và (lat2, lon2) theo km
    """
    R = 6371  # Bán kính Trái Đất tính theo km

    # Chuyển sang radian
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Hiệu giữa các kinh/vĩ độ
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Áp dụng công thức Haversine
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    return R * c  # khoảng cách theo km


@app.route('/')
def index():
    return render_template('doanvienthong.html')

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

        # Đảo ngược danh sách để hiển thị theo thời gian tăng dần
        rows = rows[::-1]

        # Chuyển đổi dữ liệu thành dạng JSON
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
        print("Lỗi trong /data:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json
        print("Dữ liệu nhận từ Gateway:", data)

        #Lấy dữ liệu từ JSON
        acc_total = data.get('acc_total')
        angle = data.get('angle')
        gyro_total = data.get('gyro_total')
        alert_text = data.get('alert_text')
         # Chọn ngẫu nhiên một tọa độ
        latitude = random.uniform(min_lat, max_lat)
        longitude = random.uniform(min_lng, max_lng)

        #Ghi vào cơ sở dữ liệu
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


@app.route('/enable_antitheft', methods=['POST'])
def enable_antitheft():
    try:
        # 1. Lấy dữ liệu mới nhất từ DB (tọa độ trước khi bật)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude
            FROM doanvienthong_table
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY recorded_at DESC
            LIMIT 1
        """)
        last_point = cursor.fetchone()
        cursor.close()
        conn.close()

        if not last_point:
            return jsonify({'error': 'Không có dữ liệu tọa độ trong DB'}), 404

        lat1, lon1 = last_point

        # 2. Tạo một tọa độ mới random trong vùng tọa độ
        latitude = random.uniform(min_lat, max_lat)
        longitude = random.uniform(min_lng, max_lng)

        # 3. Tính khoảng cách bằng Haversine
        distance_km = haversine(lat1, lon1, latitude, longitude)

        # 4. Trả về kết quả
        return jsonify({
            'original_location': {'lat': lat1, 'lng': lon1},
            'new_location': {'lat': latitude, 'lng': longitude},
            'distance_km': round(distance_km, 4)
        })

    except Exception as e:
        print("Lỗi trong enable_antitheft:", e)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
