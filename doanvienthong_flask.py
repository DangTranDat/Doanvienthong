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
            SELECT recorded_at, acc_total, angle, gyro_total, alert_text
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
                'alert_text': row[4] or ''
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

        #Ghi vào cơ sở dữ liệu
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO doanvienthong_table (acc_total, angle, gyro_total, alert_text)
            VALUES (%s, %s, %s, %s)
        """, (acc_total, angle, gyro_total, alert_text))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print("Lỗi khi ghi dữ liệu:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
