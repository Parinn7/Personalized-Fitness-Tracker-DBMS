from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import oracledb
import config

app = Flask(__name__)
CORS(app)

# ── ROOT ─────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_file('index.html')

DB_CONFIG = {"user": config.DB_USER, "password": config.DB_PASSWORD, "dsn": config.DB_DSN}

def get_conn():
    return oracledb.connect(**DB_CONFIG)

def rows_as_dicts(cur):
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── NEXT ID HELPER ───────────────────────────────────────────
# Returns MAX(pk)+1 so frontend can auto-assign IDs without sequences
NEXT_ID_MAP = {
    "users":    "SELECT NVL(MAX(user_id),0)+1    FROM USERS",
    "workouts": "SELECT NVL(MAX(workout_id),0)+1 FROM WORKOUTS",
    "meals":    "SELECT NVL(MAX(meal_id),0)+1    FROM MEALS",
    "sleep":    "SELECT NVL(MAX(sleep_id),0)+1   FROM SLEEP_LOG",
    "goals":    "SELECT NVL(MAX(goal_id),0)+1    FROM GOALS",
}

@app.route("/api/next-id/<table>")
def next_id(table):
    sql = NEXT_ID_MAP.get(table)
    if not sql:
        return jsonify({"error": "unknown table"}), 400
    conn = get_conn(); cur = conn.cursor()
    cur.execute(sql)
    nid = cur.fetchone()[0]
    cur.close(); conn.close()
    return jsonify({"next_id": int(nid)})


# ════════════════════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════════════════════
@app.route("/api/users")
def get_users():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.age, u.gender,
               u.fitness_level, u.location,
               NVL((SELECT SUM(calories_burned) FROM WORKOUTS w WHERE w.user_id=u.user_id),0) AS total_calories_burned,
               NVL((SELECT COUNT(*)             FROM WORKOUTS w WHERE w.user_id=u.user_id),0) AS total_workouts,
               NVL((SELECT ROUND(AVG(sleep_hours),1) FROM SLEEP_LOG s WHERE s.user_id=u.user_id),0) AS avg_sleep
        FROM USERS u ORDER BY u.user_id
    """)
    rows = rows_as_dicts(cur)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/users/<int:uid>")
def get_user(uid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.age, u.gender,
               u.fitness_level, u.location,
               NVL((SELECT SUM(calories_burned) FROM WORKOUTS w WHERE w.user_id=u.user_id),0) AS total_calories_burned,
               NVL((SELECT COUNT(*)             FROM WORKOUTS w WHERE w.user_id=u.user_id),0) AS total_workouts,
               NVL((SELECT ROUND(AVG(sleep_hours),1) FROM SLEEP_LOG s WHERE s.user_id=u.user_id),0) AS avg_sleep
        FROM USERS u WHERE u.user_id=:1
    """, (uid,))
    rows = rows_as_dicts(cur)
    cur.close(); conn.close()
    return jsonify(rows[0] if rows else {})

@app.route("/api/users", methods=["POST"])
def add_user():
    d = request.json
    for f in ["user_id","name"]:
        if not d.get(f): return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO USERS (user_id,name,age,gender,height,weight,fitness_level,join_date,location)
            VALUES (:1,:2,:3,:4,:5,:6,:7,SYSDATE,:8)
        """, (int(d["user_id"]), d["name"],
              int(d["age"]) if d.get("age") else None,
              d.get("gender"),
              float(d["height"]) if d.get("height") else None,
              float(d["weight"]) if d.get("weight") else None,
              d.get("fitness_level","Beginner"),
              d.get("location")))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": f"User '{d['name']}' added!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  WEATHER
# ════════════════════════════════════════════════════════════
@app.route("/api/weather")
def get_weather():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT location, temperature, condition_type, humidity, weather_date
        FROM WEATHER w1
        WHERE weather_date=(SELECT MAX(weather_date) FROM WEATHER w2 WHERE UPPER(w2.location)=UPPER(w1.location))
        ORDER BY location
    """)
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0].lower() for d in cur.description], row))
        if r.get("weather_date"): r["weather_date"] = r["weather_date"].strftime("%Y-%m-%d %H:%M")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/weather", methods=["POST"])
def add_weather():
    d = request.json
    for f in ["location","temperature","condition_type","humidity"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO WEATHER (weather_id,weather_date,temperature,condition_type,humidity,location)
            VALUES (weather_seq.NEXTVAL,SYSDATE,:1,:2,:3,:4)
        """, (float(d["temperature"]), d["condition_type"], int(d["humidity"]), d["location"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": f"Weather for '{d['location']}' added!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  WORKOUTS  — optional ?user_id= filter
# ════════════════════════════════════════════════════════════
@app.route("/api/workouts")
def get_workouts():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    sql = """
        SELECT u.name, w.workout_type, w.duration_minutes, w.calories_burned, w.workout_date
        FROM WORKOUTS w JOIN USERS u ON w.user_id=u.user_id
    """
    params = ()
    if uid:
        sql += " WHERE w.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY w.workout_date DESC"
    cur.execute(sql, params)
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0].lower() for d in cur.description], row))
        if r.get("workout_date"): r["workout_date"] = r["workout_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/workouts", methods=["POST"])
def add_workout():
    d = request.json
    for f in ["workout_id","user_id","workout_type","duration_minutes","calories_burned","workout_date"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO WORKOUTS (workout_id,user_id,workout_type,duration_minutes,calories_burned,workout_date)
            VALUES (:1,:2,:3,:4,:5,TO_DATE(:6,'YYYY-MM-DD'))
        """, (int(d["workout_id"]), int(d["user_id"]), d["workout_type"],
              int(d["duration_minutes"]), int(d["calories_burned"]), d["workout_date"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": "Workout logged!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  MEALS  — optional ?user_id= filter
# ════════════════════════════════════════════════════════════
@app.route("/api/meals")
def get_meals():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    sql = """
        SELECT u.name, m.meal_type, m.calories, m.protein, m.carbs, m.fats, m.meal_date
        FROM MEALS m JOIN USERS u ON m.user_id=u.user_id
    """
    params = ()
    if uid:
        sql += " WHERE m.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY m.meal_date DESC"
    cur.execute(sql, params)
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0].lower() for d in cur.description], row))
        if r.get("meal_date"): r["meal_date"] = r["meal_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/meals", methods=["POST"])
def add_meal():
    d = request.json
    for f in ["meal_id","user_id","meal_type","calories","meal_date"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO MEALS (meal_id,user_id,meal_type,calories,protein,carbs,fats,meal_date)
            VALUES (:1,:2,:3,:4,:5,:6,:7,TO_DATE(:8,'YYYY-MM-DD'))
        """, (int(d["meal_id"]), int(d["user_id"]), d["meal_type"], int(d["calories"]),
              float(d.get("protein") or 0), float(d.get("carbs") or 0),
              float(d.get("fats") or 0), d["meal_date"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": "Meal logged!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  SLEEP  — optional ?user_id= filter
# ════════════════════════════════════════════════════════════
@app.route("/api/sleep")
def get_sleep():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    sql = "SELECT u.name, s.sleep_hours, s.sleep_date FROM SLEEP_LOG s JOIN USERS u ON s.user_id=u.user_id"
    params = ()
    if uid:
        sql += " WHERE s.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY s.sleep_date DESC"
    cur.execute(sql, params)
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0].lower() for d in cur.description], row))
        if r.get("sleep_date"): r["sleep_date"] = r["sleep_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/sleep", methods=["POST"])
def add_sleep():
    d = request.json
    for f in ["sleep_id","user_id","sleep_hours","sleep_date"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO SLEEP_LOG (sleep_id,user_id,sleep_hours,sleep_date)
            VALUES (:1,:2,:3,TO_DATE(:4,'YYYY-MM-DD'))
        """, (int(d["sleep_id"]), int(d["user_id"]), float(d["sleep_hours"]), d["sleep_date"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": "Sleep logged!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  GOALS  — optional ?user_id= filter
# ════════════════════════════════════════════════════════════
@app.route("/api/goals")
def get_goals():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    sql = """
        SELECT u.name, g.goal_type, g.target_value,
               TRUNC(g.end_date-SYSDATE) AS days_remaining,
               ROUND((TRUNC(SYSDATE-g.start_date)/NULLIF(TRUNC(g.end_date-g.start_date),0))*100,1) AS progress_pct
        FROM GOALS g JOIN USERS u ON g.user_id=u.user_id
    """
    params = ()
    if uid:
        sql += " WHERE g.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY g.end_date"
    cur.execute(sql, params)
    rows = rows_as_dicts(cur)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/goals", methods=["POST"])
def add_goal():
    d = request.json
    for f in ["goal_id","user_id","goal_type","target_value","start_date","end_date"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO GOALS (goal_id,user_id,goal_type,target_value,start_date,end_date)
            VALUES (:1,:2,:3,:4,TO_DATE(:5,'YYYY-MM-DD'),TO_DATE(:6,'YYYY-MM-DD'))
        """, (int(d["goal_id"]), int(d["user_id"]), d["goal_type"],
              float(d["target_value"]), d["start_date"], d["end_date"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": "Goal set!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  RECOMMENDATIONS  — optional ?user_id= filter
# ════════════════════════════════════════════════════════════
@app.route("/api/recommendations")
def get_recommendations():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    sql = """
        SELECT u.name, r.message, r.recommendation_date
        FROM RECOMMENDATIONS r JOIN USERS u ON r.user_id=u.user_id
    """
    params = ()
    if uid:
        sql += " WHERE r.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY r.recommendation_date DESC, r.recommendation_id DESC"
    cur.execute(sql, params)
    rows = []
    for row in cur.fetchall():
        r = dict(zip([d[0].lower() for d in cur.description], row))
        if r.get("recommendation_date"): r["recommendation_date"] = r["recommendation_date"].strftime("%Y-%m-%d")
        rows.append(r)
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/recommendations", methods=["POST"])
def add_recommendation():
    d = request.json
    for f in ["user_id","message"]:
        if not d.get(f): return jsonify({"error": f"'{f}' is required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO RECOMMENDATIONS (recommendation_id,user_id,message,recommendation_date)
            VALUES (rec_seq.NEXTVAL,:1,:2,SYSDATE)
        """, (int(d["user_id"]), d["message"]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "message": "Recommendation added!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ANALYTICS (read-only, coach only)
# ════════════════════════════════════════════════════════════
@app.route("/api/view/weekly")
def view_weekly():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM Weekly_Progress ORDER BY user_id")
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/calories")
def view_calories():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM Avg_Calories_Per_Workout")
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/sleep")
def view_sleep():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM Sleep_Quality_Summary ORDER BY avg_sleep_hours DESC")
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/nutrition")
def view_nutrition():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM Nutrition_Summary ORDER BY avg_daily_calories DESC")
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/top")
def query_top():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.name, u.fitness_level,
               SUM(w.calories_burned) AS total_calories_burned,
               COUNT(w.workout_id) AS total_workouts
        FROM USERS u JOIN WORKOUTS w ON u.user_id=w.user_id
        GROUP BY u.name,u.fitness_level ORDER BY total_calories_burned DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/missed")
def query_missed():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.name, u.fitness_level, u.location,
               TO_CHAR(MAX(w.workout_date),'YYYY-MM-DD') AS last_workout_date,
               TRUNC(SYSDATE)-TRUNC(MAX(w.workout_date)) AS days_since
        FROM USERS u LEFT JOIN WORKOUTS w ON u.user_id=w.user_id
        GROUP BY u.user_id,u.name,u.fitness_level,u.location
        HAVING TRUNC(SYSDATE)-TRUNC(MAX(w.workout_date))>2 OR MAX(w.workout_date) IS NULL
        ORDER BY days_since DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/nutrition")
def query_nutrition():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.name, ROUND(AVG(m.calories),2) AS avg_daily_calories,
               2000-ROUND(AVG(m.calories),2) AS calorie_deficit,
               CASE WHEN AVG(m.calories)<1500 THEN 'Under Eating'
                    WHEN AVG(m.calories)>2500 THEN 'Over Eating'
                    ELSE 'On Track' END AS nutrition_status
        FROM USERS u JOIN MEALS m ON u.user_id=m.user_id
        GROUP BY u.name ORDER BY avg_daily_calories DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/popular")
def query_popular():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT workout_type, COUNT(*) AS frequency,
               ROUND(AVG(duration_minutes),2) AS avg_duration,
               ROUND(AVG(calories_burned),2) AS avg_calories
        FROM WORKOUTS GROUP BY workout_type ORDER BY frequency DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/sleep")
def query_sleep():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.name, ROUND(AVG(s.sleep_hours),2) AS avg_sleep,
               CASE WHEN AVG(s.sleep_hours)>=8 THEN 'Excellent'
                    WHEN AVG(s.sleep_hours)>=6 THEN 'Adequate'
                    ELSE 'Poor' END AS sleep_status
        FROM USERS u JOIN SLEEP_LOG s ON u.user_id=s.user_id
        GROUP BY u.name ORDER BY avg_sleep DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/query/balance")
def query_balance():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.name,
               NVL(SUM(w.calories_burned),0) AS total_burned,
               NVL(SUM(m.calories),0) AS total_consumed,
               NVL(SUM(m.calories),0)-NVL(SUM(w.calories_burned),0) AS net_balance
        FROM USERS u
        LEFT JOIN WORKOUTS w ON u.user_id=w.user_id
        LEFT JOIN MEALS m ON u.user_id=m.user_id
        GROUP BY u.name ORDER BY net_balance DESC
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)