from flask import Flask, jsonify, send_file
from flask_cors import CORS
import oracledb
import config

app = Flask(__name__)
CORS(app)

# ── ROOT ROUTE ───────────────────────────────────────────────
@app.route('/')
def index():
    return send_file('index.html')

# ── DB CONFIG ───────────────────────────────────────────────
# oracledb.init_oracle_client(lib_dir=config.INSTANT_CLIENT_PATH)

DB_CONFIG = {
    "user":     config.DB_USER,
    "password": config.DB_PASSWORD,
    "dsn":      config.DB_DSN
}

def get_conn():
    return oracledb.connect(**DB_CONFIG)


# ── USERS ───────────────────────────────────────────────────
@app.route("/api/users")
def get_users():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.age, u.gender,
               u.fitness_level, u.location,
               NVL((SELECT SUM(calories_burned)
                    FROM WORKOUTS w
                    WHERE w.user_id = u.user_id), 0) AS total_calories_burned,
               NVL((SELECT COUNT(*)
                    FROM WORKOUTS w
                    WHERE w.user_id = u.user_id), 0) AS total_workouts,
               NVL((SELECT ROUND(AVG(sleep_hours),1)
                    FROM SLEEP_LOG s
                    WHERE s.user_id = u.user_id), 0) AS avg_sleep
        FROM USERS u
        ORDER BY u.user_id
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)


# ── WEATHER ─────────────────────────────────────────────────
@app.route("/api/weather")
def get_weather():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT location, temperature, condition_type, humidity, weather_date
        FROM WEATHER w1
        WHERE weather_date = (
            SELECT MAX(weather_date) FROM WEATHER w2
            WHERE UPPER(w2.location) = UPPER(w1.location)
        )
        ORDER BY location
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if r.get("weather_date"):
            r["weather_date"] = r["weather_date"].strftime("%Y-%m-%d %H:%M")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)


# ── RECOMMENDATIONS ─────────────────────────────────────────
@app.route("/api/recommendations")
def get_recommendations():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, r.message, r.recommendation_date
        FROM RECOMMENDATIONS r
        JOIN USERS u ON r.user_id = u.user_id
        ORDER BY r.recommendation_date DESC, r.recommendation_id DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if r.get("recommendation_date"):
            r["recommendation_date"] = r["recommendation_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)


# ── WORKOUTS ─────────────────────────────────────────────────
@app.route("/api/workouts")
def get_workouts():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, w.workout_type, w.duration_minutes,
               w.calories_burned, w.workout_date
        FROM WORKOUTS w
        JOIN USERS u ON w.user_id = u.user_id
        ORDER BY w.workout_date DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if r.get("workout_date"):
            r["workout_date"] = r["workout_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)


# ── MEALS ────────────────────────────────────────────────────
@app.route("/api/meals")
def get_meals():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, m.meal_type, m.calories,
               m.protein, m.carbs, m.fats, m.meal_date
        FROM MEALS m
        JOIN USERS u ON m.user_id = u.user_id
        ORDER BY m.meal_date DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if r.get("meal_date"):
            r["meal_date"] = r["meal_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)


# ── SLEEP ────────────────────────────────────────────────────
@app.route("/api/sleep")
def get_sleep():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, s.sleep_hours, s.sleep_date
        FROM SLEEP_LOG s
        JOIN USERS u ON s.user_id = u.user_id
        ORDER BY s.sleep_date DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if r.get("sleep_date"):
            r["sleep_date"] = r["sleep_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)


# ── GOALS ────────────────────────────────────────────────────
@app.route("/api/goals")
def get_goals():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, g.goal_type, g.target_value,
               TRUNC(g.end_date - SYSDATE) AS days_remaining,
               ROUND((TRUNC(SYSDATE - g.start_date) /
                      NULLIF(TRUNC(g.end_date - g.start_date),0)) * 100, 1) AS progress_pct
        FROM GOALS g
        JOIN USERS u ON g.user_id = u.user_id
        ORDER BY g.end_date
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)


# ── WEEKLY PROGRESS VIEW ─────────────────────────────────────
@app.route("/api/weekly")
def get_weekly():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Weekly_Progress ORDER BY user_id")
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)


# ── VIEW: WEEKLY PROGRESS ────────────────────────────────────
@app.route("/api/view/weekly")
def view_weekly():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Weekly_Progress ORDER BY user_id")
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── VIEW: AVG CALORIES PER WORKOUT ───────────────────────────
@app.route("/api/view/calories")
def view_calories():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Avg_Calories_Per_Workout")
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── VIEW: SLEEP QUALITY ───────────────────────────────────────
@app.route("/api/view/sleep")
def view_sleep():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Sleep_Quality_Summary ORDER BY avg_sleep_hours DESC")
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── VIEW: NUTRITION SUMMARY ───────────────────────────────────
@app.route("/api/view/nutrition")
def view_nutrition():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Nutrition_Summary ORDER BY avg_daily_calories DESC")
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: TOP PERFORMERS ─────────────────────────────────────
@app.route("/api/query/top")
def query_top():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, u.fitness_level,
               SUM(w.calories_burned) AS total_calories_burned,
               COUNT(w.workout_id)    AS total_workouts
        FROM USERS u JOIN WORKOUTS w ON u.user_id = w.user_id
        GROUP BY u.name, u.fitness_level
        ORDER BY total_calories_burned DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: MISSED WORKOUTS ────────────────────────────────────
@app.route("/api/query/missed")
def query_missed():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, u.fitness_level, u.location,
               TO_CHAR(MAX(w.workout_date),'YYYY-MM-DD') AS last_workout_date,
               TRUNC(SYSDATE) - TRUNC(MAX(w.workout_date)) AS days_since
        FROM USERS u LEFT JOIN WORKOUTS w ON u.user_id = w.user_id
        GROUP BY u.user_id, u.name, u.fitness_level, u.location
        HAVING TRUNC(SYSDATE) - TRUNC(MAX(w.workout_date)) > 2
            OR MAX(w.workout_date) IS NULL
        ORDER BY days_since DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: NUTRITION STATUS ───────────────────────────────────
@app.route("/api/query/nutrition")
def query_nutrition():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name,
               ROUND(AVG(m.calories),2) AS avg_daily_calories,
               2000 - ROUND(AVG(m.calories),2) AS calorie_deficit,
               CASE WHEN AVG(m.calories) < 1500 THEN 'Under Eating'
                    WHEN AVG(m.calories) > 2500 THEN 'Over Eating'
                    ELSE 'On Track' END AS nutrition_status
        FROM USERS u JOIN MEALS m ON u.user_id = m.user_id
        GROUP BY u.name ORDER BY avg_daily_calories DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: POPULAR WORKOUTS ───────────────────────────────────
@app.route("/api/query/popular")
def query_popular():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT workout_type, COUNT(*) AS frequency,
               ROUND(AVG(duration_minutes),2) AS avg_duration,
               ROUND(AVG(calories_burned),2)  AS avg_calories
        FROM WORKOUTS
        GROUP BY workout_type ORDER BY frequency DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: SLEEP RANKING ──────────────────────────────────────
@app.route("/api/query/sleep")
def query_sleep():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name, ROUND(AVG(s.sleep_hours),2) AS avg_sleep,
               CASE WHEN AVG(s.sleep_hours) >= 8 THEN 'Excellent'
                    WHEN AVG(s.sleep_hours) >= 6 THEN 'Adequate'
                    ELSE 'Poor' END AS sleep_status
        FROM USERS u JOIN SLEEP_LOG s ON u.user_id = s.user_id
        GROUP BY u.name ORDER BY avg_sleep DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

# ── QUERY: CALORIE BALANCE ────────────────────────────────────
@app.route("/api/query/balance")
def query_balance():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.name,
               NVL(SUM(w.calories_burned),0) AS total_burned,
               NVL(SUM(m.calories),0)        AS total_consumed,
               NVL(SUM(m.calories),0) - NVL(SUM(w.calories_burned),0) AS net_balance
        FROM USERS u
        LEFT JOIN WORKOUTS w ON u.user_id = w.user_id
        LEFT JOIN MEALS m    ON u.user_id = m.user_id
        GROUP BY u.name ORDER BY net_balance DESC
    """)
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)