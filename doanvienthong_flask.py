from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME'),
        port=os.environ.get('DB_PORT', 5432)
    )

@app.route('/')
def index():
    return render_template('doanvienthong.html')

@app.route('/data')
def data():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, temperature, humidity, water_level, rain_level,
                   soil_moisture, pressure, vibration, gyro_x, gyro_y, gyro_z,canhbao
            FROM nckh2025
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        rows = rows[::-1]  # đảo ngược thời gian tăng dần
        return jsonify({
            'timestamps': [r[0].strftime("%H:%M:%S") for r in rows],
            'temperatures': [r[1] for r in rows],
            'humidities': [r[2] for r in rows],
            'water_levels': [r[3] for r in rows],
            'rains_level': [r[4] for r in rows],
            'soil_moistures': [r[5] for r in rows],
            'pressures': [r[6] for r in rows],
            'vibrations': [r[7] for r in rows],
            'gyro_xs': [r[8] for r in rows],
            'gyro_ys': [r[9] for r in rows],
            'gyro_zs': [r[10] for r in rows],
            'canhbao': [r[11] for r in rows],
        })

    except Exception as e:
        print("Lỗi trong /data:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json
        print("Dữ liệu nhận từ Gateway:", data)

        #Lấy dữ liệu từ JSON
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        water_level = data.get('water_level')
        rain_level= data.get('rain_level')
        soil_moisture = data.get('soil_moisture')
        pressure = data.get('pressure')
        vibration = data.get('vibration')
        gyro_x = data.get('gyro_x')
        gyro_y = data.get('gyro_y')
        gyro_z = data.get('gyro_z')
        canhbao = data.get("CANH BAO","")
        timestamp = datetime.now()

        #Ghi vào cơ sở dữ liệu
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO nckh2025 (
                timestamp, temperature, humidity,
                water_level, rain_level, soil_moisture,
                pressure, vibration, gyro_x, gyro_y, gyro_z, canhbao
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            timestamp, temperature, humidity,
            water_level, rain_level, soil_moisture,
            pressure, vibration, gyro_x, gyro_y, gyro_z,canhbao
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print("Lỗi khi ghi dữ liệu:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
