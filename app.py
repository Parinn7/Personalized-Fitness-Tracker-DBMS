from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import oracledb
import config
from datetime import date

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

def is_missing_db_object(error):
    return "ORA-00942" in str(error)

def query_rows(cur, primary_sql, fallback_sql=None, params=()):
    try:
        cur.execute(primary_sql, params)
    except Exception as e:
        if not fallback_sql or not is_missing_db_object(e):
            raise
        cur.execute(fallback_sql, params)
    return rows_as_dicts(cur)

def row_as_dict(cur, row):
    if not row:
        return None
    cols = [d[0].lower() for d in cur.description]
    return dict(zip(cols, row))

def date_str(value, with_time=False):
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")

def as_date(value):
    if not value:
        return None
    return value.date() if hasattr(value, "date") else value

def safe_number(value, digits=1):
    if value is None:
        return 0
    return round(float(value), digits)

def build_goal_progress(goal):
    if not goal:
        return None
    start_date = goal.get("start_date")
    end_date = goal.get("end_date")
    if not start_date or not end_date:
        goal["progress_pct"] = 0
        goal["goal_status"] = "No Timeline"
        goal["days_remaining"] = None
        return goal

    today = date.today()
    start_only = as_date(start_date)
    end_only = as_date(end_date)
    total_days = max((end_only - start_only).days, 0)
    elapsed_days = (today - start_only).days
    days_remaining = (end_only - today).days

    if total_days == 0:
        progress_pct = 100.0 if today >= end_only else 0.0
    else:
        progress_pct = round(min(100, max(0, (elapsed_days / total_days) * 100)), 1)

    if today > end_only:
        status = "Expired"
    elif today < start_only:
        status = "Upcoming"
    elif days_remaining <= 7:
        status = "Deadline Near"
    else:
        status = "In Progress"

    goal["progress_pct"] = progress_pct
    goal["goal_status"] = status
    goal["days_remaining"] = days_remaining
    goal["start_date"] = date_str(start_date)
    goal["end_date"] = date_str(end_date)
    return goal

def get_latest_goal(cur, user_id):
    cur.execute("""
        SELECT goal_type, target_value, start_date, end_date
        FROM (
            SELECT goal_type, target_value, start_date, end_date,
                   CASE
                       WHEN TRUNC(SYSDATE) BETWEEN TRUNC(start_date) AND TRUNC(end_date) THEN 0
                       WHEN TRUNC(SYSDATE) < TRUNC(start_date) THEN 1
                       ELSE 2
                   END AS priority_rank,
                   goal_id
            FROM GOALS
            WHERE user_id=:1
            ORDER BY priority_rank, end_date, goal_id DESC
        )
        WHERE ROWNUM=1
    """, (user_id,))
    goal = row_as_dict(cur, cur.fetchone())
    return build_goal_progress(goal) if goal else None

def get_recommendation_snapshot(cur, user_id):
    cur.execute("""
        SELECT user_id, name, fitness_level, location
        FROM USERS
        WHERE user_id=:1
    """, (user_id,))
    user = row_as_dict(cur, cur.fetchone())
    if not user:
        return None

    cur.execute("""
        SELECT temperature, condition_type, humidity, weather_date
        FROM (
            SELECT temperature, condition_type, humidity, weather_date, weather_id
            FROM WEATHER
            WHERE UPPER(location)=UPPER(:1)
            ORDER BY weather_date DESC, weather_id DESC
        )
        WHERE ROWNUM=1
    """, (user["location"],))
    weather = row_as_dict(cur, cur.fetchone()) or {}

    cur.execute("""
        SELECT workout_type, duration_minutes, calories_burned, workout_date
        FROM (
            SELECT workout_type, duration_minutes, calories_burned, workout_date, workout_id
            FROM WORKOUTS
            WHERE user_id=:1
            ORDER BY workout_date DESC, workout_id DESC
        )
        WHERE ROWNUM=1
    """, (user_id,))
    workout = row_as_dict(cur, cur.fetchone()) or {}

    cur.execute("""
        SELECT sleep_hours, sleep_date
        FROM (
            SELECT sleep_hours, sleep_date, sleep_id
            FROM SLEEP_LOG
            WHERE user_id=:1
            ORDER BY sleep_date DESC, sleep_id DESC
        )
        WHERE ROWNUM=1
    """, (user_id,))
    sleep = row_as_dict(cur, cur.fetchone()) or {}

    cur.execute("""
        SELECT NVL(SUM(calories),0) AS yesterday_calories,
               NVL(SUM(protein),0) AS yesterday_protein
        FROM MEALS
        WHERE user_id=:1
          AND TRUNC(meal_date)=TRUNC(SYSDATE-1)
    """, (user_id,))
    nutrition_yesterday = row_as_dict(cur, cur.fetchone()) or {}

    cur.execute("""
        SELECT ROUND(NVL(AVG(day_calories),0),1) AS avg_daily_calories_7d,
               ROUND(NVL(AVG(day_protein),0),1) AS avg_daily_protein_7d
        FROM (
            SELECT TRUNC(meal_date) AS meal_day,
                   SUM(calories) AS day_calories,
                   SUM(protein) AS day_protein
            FROM MEALS
            WHERE user_id=:1
              AND meal_date >= TRUNC(SYSDATE)-6
            GROUP BY TRUNC(meal_date)
        )
    """, (user_id,))
    nutrition_week = row_as_dict(cur, cur.fetchone()) or {}

    cur.execute("""
        SELECT COUNT(*) AS workouts_7d,
               NVL(SUM(duration_minutes),0) AS workout_minutes_7d,
               NVL(SUM(calories_burned),0) AS calories_burned_7d
        FROM WORKOUTS
        WHERE user_id=:1
          AND workout_date >= TRUNC(SYSDATE)-6
    """, (user_id,))
    week_stats = row_as_dict(cur, cur.fetchone()) or {}

    goal = get_latest_goal(cur, user_id) or {}

    last_workout_date = workout.get("workout_date")
    days_since_workout = (date.today() - as_date(last_workout_date)).days if last_workout_date else None

    snapshot = {
        **user,
        "temperature": weather.get("temperature"),
        "condition_type": weather.get("condition_type"),
        "humidity": weather.get("humidity"),
        "weather_date": date_str(weather.get("weather_date"), with_time=True),
        "last_workout_type": workout.get("workout_type"),
        "last_workout_duration": workout.get("duration_minutes"),
        "last_workout_calories": workout.get("calories_burned"),
        "last_workout_date": date_str(last_workout_date),
        "days_since_workout": days_since_workout,
        "latest_sleep_hours": sleep.get("sleep_hours"),
        "latest_sleep_date": date_str(sleep.get("sleep_date")),
        "yesterday_calories": nutrition_yesterday.get("yesterday_calories", 0),
        "yesterday_protein": nutrition_yesterday.get("yesterday_protein", 0),
        "avg_daily_calories_7d": nutrition_week.get("avg_daily_calories_7d", 0),
        "avg_daily_protein_7d": nutrition_week.get("avg_daily_protein_7d", 0),
        "workouts_7d": week_stats.get("workouts_7d", 0),
        "workout_minutes_7d": week_stats.get("workout_minutes_7d", 0),
        "calories_burned_7d": week_stats.get("calories_burned_7d", 0),
        "goal_type": goal.get("goal_type"),
        "goal_target": goal.get("target_value"),
        "goal_progress_pct": goal.get("progress_pct", 0),
        "goal_status": goal.get("goal_status"),
        "goal_end_date": goal.get("end_date"),
    }
    return snapshot

def build_ai_recommendation(snapshot):
    if not snapshot:
        return None

    parts = [f"Hey {snapshot['name']}!"]
    reasons = []
    focus_area = "Performance"
    priority = "Low"

    sleep_hours = float(snapshot.get("latest_sleep_hours") or 0)
    if not sleep_hours:
        parts.append("Log your sleep tonight so recovery stays measurable.")
        reasons.append("No recent sleep data")
    elif sleep_hours < 6:
        parts.append(f"Recovery comes first after only {sleep_hours:.1f} hrs of sleep, so keep today's training light.")
        reasons.append("Sleep is below 6 hours")
        focus_area = "Recovery"
        priority = "High"
    elif sleep_hours < 7.5:
        parts.append(f"You slept {sleep_hours:.1f} hrs, so a solid bedtime tonight will help tomorrow's session.")
        reasons.append("Sleep is decent but below optimal")
        if priority == "Low":
            priority = "Medium"
            focus_area = "Recovery"
    else:
        parts.append(f"You banked {sleep_hours:.1f} hrs of sleep, which gives you a strong recovery base.")

    days_since_workout = snapshot.get("days_since_workout")
    workouts_7d = int(snapshot.get("workouts_7d") or 0)
    last_workout_type = snapshot.get("last_workout_type")
    last_workout_duration = snapshot.get("last_workout_duration") or 0
    if days_since_workout is None:
        parts.append("No workouts are logged yet, so start with a manageable 20-30 minute session today.")
        reasons.append("No workout history found")
        focus_area = "Consistency"
        priority = "High"
    elif days_since_workout >= 3:
        parts.append(f"It's been {days_since_workout} days since your last workout, so restart with a short confidence-building session today.")
        reasons.append("Workout streak has cooled off")
        focus_area = "Consistency"
        priority = "High"
    elif last_workout_duration >= 60:
        parts.append(f"Your last {last_workout_type} session ran {int(last_workout_duration)} minutes, so mobility or light cardio would balance the load well.")
        reasons.append("Recent training load is high")
        if priority == "Low":
            priority = "Medium"
    elif workouts_7d >= 5:
        parts.append(f"You already have {workouts_7d} workouts this week, so keep today's intensity controlled if fatigue shows up.")
    else:
        parts.append(f"Build on your recent {last_workout_type} work with another focused session and keep the weekly rhythm going.")

    avg_daily_calories = float(snapshot.get("avg_daily_calories_7d") or 0)
    avg_daily_protein = float(snapshot.get("avg_daily_protein_7d") or 0)
    if avg_daily_calories == 0:
        parts.append("Meal logs are missing this week, so tracking food will make your progress much easier to coach.")
        reasons.append("Meal tracking is missing")
        if priority == "Low":
            priority = "Medium"
            focus_area = "Nutrition"
    elif avg_daily_calories < 1500:
        parts.append(f"Your recent intake averages about {avg_daily_calories:.0f} kcal, so add a balanced meal and don't under-fuel training.")
        reasons.append("Calories are trending low")
        priority = "High"
        focus_area = "Nutrition"
    elif avg_daily_calories > 2600:
        parts.append(f"Your recent intake averages about {avg_daily_calories:.0f} kcal, so tighten portions and keep food quality high today.")
        reasons.append("Calories are trending high")
        if priority != "High":
            priority = "Medium"
            focus_area = "Nutrition"
    elif avg_daily_protein and avg_daily_protein < 75:
        parts.append(f"Calories look stable, but protein is only around {avg_daily_protein:.0f}g per day, so add a protein-rich meal.")
        reasons.append("Protein intake is low")
        if priority == "Low":
            priority = "Medium"
            focus_area = "Nutrition"
    else:
        parts.append("Nutrition looks steady, so keep protein consistent and hydrate well.")

    weather_cond = (snapshot.get("condition_type") or "").lower()
    temp = snapshot.get("temperature")
    location = snapshot.get("location") or "your city"
    if weather_cond:
        if any(x in weather_cond for x in ["rain", "drizzle", "thunderstorm"]):
            parts.append(f"{location} weather looks wet today, so indoor training is the smarter choice.")
        elif temp is not None and float(temp) >= 38:
            parts.append(f"It's very hot in {location} at {float(temp):.1f}C, so avoid peak heat and focus on hydration.")
        elif temp is not None and float(temp) >= 30:
            parts.append(f"{location} is warm at {float(temp):.1f}C, so train early or later in the evening.")
        elif temp is not None and float(temp) >= 20:
            parts.append(f"Weather in {location} is ideal for an outdoor session if that fits your plan.")
        elif temp is not None:
            parts.append(f"Cool weather in {location} makes this a good day for a brisk run or ride.")

    goal_type = snapshot.get("goal_type")
    goal_status = snapshot.get("goal_status")
    goal_progress = snapshot.get("goal_progress_pct") or 0
    if goal_type:
        if goal_status == "Deadline Near":
            parts.append(f"Your {goal_type} goal is entering the final stretch, so make today's session count.")
        elif goal_status == "Expired":
            parts.append(f"Your {goal_type} goal timeline has ended, so it may be time to reset the target.")
        else:
            parts.append(f"You're about {goal_progress:.0f}% through the {goal_type} timeline, so consistency matters more than intensity spikes.")

    message = " ".join(parts)
    if len(message) > 280:
        message = message[:277].rstrip() + "..."

    return {
        "user_id": snapshot["user_id"],
        "name": snapshot["name"],
        "message": message,
        "priority": priority,
        "focus_area": focus_area,
        "reasons": reasons[:3],
        "snapshot": snapshot,
    }

def get_recommendation_overview(cur, user_id=None):
    params = ()
    sql = "SELECT user_id FROM USERS"
    if user_id:
        sql += " WHERE user_id=:1"
        params = (int(user_id),)
    sql += " ORDER BY user_id"
    cur.execute(sql, params)
    user_ids = [row[0] for row in cur.fetchall()]

    generated = []
    for uid in user_ids:
        snapshot = get_recommendation_snapshot(cur, uid)
        generated_item = build_ai_recommendation(snapshot)
        if generated_item:
            generated.append(generated_item)

    generated.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item["priority"], 3),
            -(item["snapshot"].get("days_since_workout") or 0),
            item["name"].lower(),
        )
    )

    latest_sql = """
        SELECT * FROM (
            SELECT u.user_id, u.name, r.message, r.recommendation_date
            FROM RECOMMENDATIONS r
            JOIN USERS u ON r.user_id=u.user_id
    """
    latest_params = ()
    if user_id:
        latest_sql += " WHERE u.user_id=:1"
        latest_params = (int(user_id),)
    latest_sql += """
            ORDER BY r.recommendation_date DESC, r.recommendation_id DESC
        )
        WHERE ROWNUM <= 5
    """
    cur.execute(latest_sql, latest_params)
    latest_saved = []
    for row in cur.fetchall():
        item = row_as_dict(cur, row)
        item["recommendation_date"] = date_str(item.get("recommendation_date"), with_time=True)
        latest_saved.append(item)

    total_saved_sql = "SELECT COUNT(*) FROM RECOMMENDATIONS"
    today_saved_sql = "SELECT COUNT(*) FROM RECOMMENDATIONS WHERE TRUNC(recommendation_date)=TRUNC(SYSDATE)"
    saved_params = ()
    if user_id:
        total_saved_sql += " WHERE user_id=:1"
        today_saved_sql += " AND user_id=:1"
        saved_params = (int(user_id),)

    cur.execute(total_saved_sql, saved_params)
    total_saved = cur.fetchone()[0]
    cur.execute(today_saved_sql, saved_params)
    saved_today = cur.fetchone()[0]

    focus_counts = {}
    for item in generated:
        focus_counts[item["focus_area"]] = focus_counts.get(item["focus_area"], 0) + 1

    attention_users = []
    for item in generated[:5]:
        snap = item["snapshot"]
        attention_users.append({
            "user_id": item["user_id"],
            "name": item["name"],
            "priority": item["priority"],
            "focus_area": item["focus_area"],
            "reasons": item["reasons"],
            "days_since_workout": snap.get("days_since_workout"),
            "latest_sleep_hours": snap.get("latest_sleep_hours"),
            "avg_daily_calories_7d": snap.get("avg_daily_calories_7d"),
            "goal_type": snap.get("goal_type"),
        })

    avg_weekly_workouts = round(
        sum(int(item["snapshot"].get("workouts_7d") or 0) for item in generated) / len(generated), 1
    ) if generated else 0

    return {
        "summary": {
            "tracked_users": len(generated),
            "saved_recommendations": total_saved,
            "saved_today": saved_today,
            "high_priority_users": sum(1 for item in generated if item["priority"] == "High"),
            "avg_weekly_workouts": avg_weekly_workouts,
        },
        "focus_breakdown": [
            {"focus_area": key, "count": value}
            for key, value in sorted(focus_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "generated_preview": [
            {
                "user_id": item["user_id"],
                "name": item["name"],
                "message": item["message"],
                "priority": item["priority"],
                "focus_area": item["focus_area"],
                "reasons": item["reasons"],
                "snapshot": item["snapshot"],
            }
            for item in generated
        ],
        "attention_users": attention_users,
        "latest_recommendations": latest_saved,
    }


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
        SELECT g.goal_id, g.user_id, u.name, g.goal_type, g.target_value,
               g.start_date, g.end_date
        FROM GOALS g JOIN USERS u ON g.user_id=u.user_id
    """
    params = ()
    if uid:
        sql += " WHERE g.user_id=:1"
        params = (int(uid),)
    sql += " ORDER BY g.end_date"
    cur.execute(sql, params)
    rows = [build_goal_progress(row) for row in rows_as_dicts(cur)]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/goals", methods=["POST"])
def add_goal():
    d = request.json
    for f in ["goal_id","user_id","goal_type","target_value","start_date","end_date"]:
        if d.get(f) is None or d.get(f)=="": return jsonify({"error": f"'{f}' is required"}), 400
    if d["end_date"] < d["start_date"]:
        return jsonify({"error": "'end_date' must be on or after 'start_date'"}), 400
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

@app.route("/api/recommendations/overview")
def recommendation_overview():
    uid = request.args.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    data = get_recommendation_overview(cur, uid)
    cur.close(); conn.close()
    return jsonify(data)

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

@app.route("/api/recommendations/generate", methods=["POST"])
def generate_recommendations():
    d = request.json or {}
    uid = d.get("user_id")
    conn = get_conn(); cur = conn.cursor()
    try:
        params = ()
        sql = "SELECT user_id FROM USERS"
        if uid:
            sql += " WHERE user_id=:1"
            params = (int(uid),)
        sql += " ORDER BY user_id"
        cur.execute(sql, params)
        user_ids = [row[0] for row in cur.fetchall()]
        if not user_ids:
            return jsonify({"error": "No matching users found"}), 404

        generated = []
        for target_uid in user_ids:
            snapshot = get_recommendation_snapshot(cur, target_uid)
            item = build_ai_recommendation(snapshot)
            if not item:
                continue
            cur.execute("""
                SELECT COUNT(*)
                FROM RECOMMENDATIONS
                WHERE user_id=:1
                  AND message=:2
                  AND TRUNC(recommendation_date)=TRUNC(SYSDATE)
            """, (item["user_id"], item["message"]))
            if cur.fetchone()[0]:
                item["recommendation_date"] = date.today().strftime("%Y-%m-%d")
                generated.append(item)
                continue
            cur.execute("""
                INSERT INTO RECOMMENDATIONS (recommendation_id,user_id,message,recommendation_date)
                VALUES (rec_seq.NEXTVAL,:1,:2,SYSDATE)
            """, (item["user_id"], item["message"]))
            item["recommendation_date"] = date.today().strftime("%Y-%m-%d")
            generated.append(item)

        conn.commit()
        return jsonify({
            "success": True,
            "generated": len(generated),
            "recommendations": generated,
            "message": f"{len(generated)} AI recommendation(s) generated."
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close(); conn.close()


# ════════════════════════════════════════════════════════════
#  ANALYTICS (read-only, coach only)
# ════════════════════════════════════════════════════════════
@app.route("/api/view/weekly")
def view_weekly():
    conn = get_conn(); cur = conn.cursor()
    rows = query_rows(cur,
        "SELECT * FROM Weekly_Progress ORDER BY user_id",
        """
        SELECT
            u.user_id,
            u.name,
            u.location,
            (SELECT COUNT(*)
             FROM WORKOUTS w
             WHERE w.user_id = u.user_id
               AND w.workout_date >= TRUNC(SYSDATE) - 6) AS total_workouts,
            (SELECT NVL(SUM(w.duration_minutes), 0)
             FROM WORKOUTS w
             WHERE w.user_id = u.user_id
               AND w.workout_date >= TRUNC(SYSDATE) - 6) AS total_workout_mins,
            (SELECT NVL(SUM(w.calories_burned), 0)
             FROM WORKOUTS w
             WHERE w.user_id = u.user_id
               AND w.workout_date >= TRUNC(SYSDATE) - 6) AS total_calories_burned,
            (SELECT NVL(SUM(m.calories), 0)
             FROM MEALS m
             WHERE m.user_id = u.user_id
               AND m.meal_date >= TRUNC(SYSDATE) - 6) AS total_calories_consumed,
            (SELECT ROUND(NVL(AVG(s.sleep_hours), 0), 2)
             FROM SLEEP_LOG s
             WHERE s.user_id = u.user_id
               AND s.sleep_date >= TRUNC(SYSDATE) - 6) AS avg_sleep_hours
        FROM USERS u
        ORDER BY u.user_id
        """
    )
    cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/calories")
def view_calories():
    conn = get_conn(); cur = conn.cursor()
    rows = query_rows(cur,
        "SELECT * FROM Avg_Calories_Per_Workout",
        """
        SELECT
            workout_type,
            COUNT(*) AS total_sessions,
            ROUND(AVG(duration_minutes), 2) AS avg_duration_mins,
            ROUND(AVG(calories_burned), 2) AS avg_calories_burned,
            SUM(calories_burned) AS total_calories_burned
        FROM WORKOUTS
        GROUP BY workout_type
        ORDER BY avg_calories_burned DESC, workout_type
        """
    )
    cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/sleep")
def view_sleep():
    conn = get_conn(); cur = conn.cursor()
    rows = query_rows(cur,
        "SELECT * FROM Sleep_Quality_Summary ORDER BY avg_sleep_hours DESC",
        """
        SELECT
            u.user_id,
            u.name,
            ROUND(AVG(s.sleep_hours), 2) AS avg_sleep_hours,
            MIN(s.sleep_hours) AS min_sleep_hours,
            MAX(s.sleep_hours) AS max_sleep_hours,
            SUM(CASE WHEN s.sleep_hours < 6 THEN 1 ELSE 0 END) AS poor_sleep_days,
            SUM(CASE WHEN s.sleep_hours >= 6 AND s.sleep_hours < 8 THEN 1 ELSE 0 END) AS average_sleep_days,
            SUM(CASE WHEN s.sleep_hours >= 8 THEN 1 ELSE 0 END) AS good_sleep_days
        FROM USERS u
        LEFT JOIN SLEEP_LOG s ON u.user_id = s.user_id
        GROUP BY u.user_id, u.name
        ORDER BY avg_sleep_hours DESC NULLS LAST, u.user_id
        """
    )
    cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/view/nutrition")
def view_nutrition():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name,
               ROUND(NVL(n.avg_daily_calories,0),2) AS avg_daily_calories,
               ROUND(NVL(n.avg_protein,0),2) AS avg_protein,
               ROUND(NVL(n.avg_carbs,0),2) AS avg_carbs,
               ROUND(NVL(n.avg_fats,0),2) AS avg_fats,
               NVL(n.total_calories,0) AS total_calories
        FROM USERS u
        LEFT JOIN (
            SELECT user_id,
                   AVG(day_calories) AS avg_daily_calories,
                   AVG(day_protein) AS avg_protein,
                   AVG(day_carbs) AS avg_carbs,
                   AVG(day_fats) AS avg_fats,
                   SUM(day_calories) AS total_calories
            FROM (
                SELECT user_id,
                       TRUNC(meal_date) AS meal_day,
                       SUM(calories) AS day_calories,
                       SUM(protein) AS day_protein,
                       SUM(carbs) AS day_carbs,
                       SUM(fats) AS day_fats
                FROM MEALS
                GROUP BY user_id, TRUNC(meal_date)
            )
            GROUP BY user_id
        ) n ON n.user_id=u.user_id
        ORDER BY avg_daily_calories DESC, u.user_id
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)

@app.route("/api/analytics/overview")
def analytics_overview():
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM USERS) AS total_users,
                (SELECT COUNT(*) FROM WORKOUTS WHERE workout_date >= TRUNC(SYSDATE)-6) AS workouts_7d,
                (SELECT NVL(SUM(calories_burned),0) FROM WORKOUTS WHERE workout_date >= TRUNC(SYSDATE)-6) AS calories_burned_7d,
                (SELECT ROUND(NVL(AVG(sleep_hours),0),1) FROM SLEEP_LOG WHERE sleep_date >= TRUNC(SYSDATE)-6) AS avg_sleep_7d,
                (SELECT ROUND(NVL(AVG(day_calories),0),1)
                   FROM (
                       SELECT SUM(calories) AS day_calories
                       FROM MEALS
                       WHERE meal_date >= TRUNC(SYSDATE)-6
                       GROUP BY user_id, TRUNC(meal_date)
                   )
                ) AS avg_daily_calories_7d,
                (SELECT COUNT(*) FROM GOALS WHERE TRUNC(SYSDATE) <= TRUNC(end_date)) AS active_goals,
                (SELECT COUNT(*) FROM RECOMMENDATIONS WHERE TRUNC(recommendation_date)=TRUNC(SYSDATE)) AS recommendations_today
            FROM dual
        """)
        summary = row_as_dict(cur, cur.fetchone())

        cur.execute("""
            SELECT u.name,
                   NVL((SELECT COUNT(*) FROM WORKOUTS w WHERE w.user_id=u.user_id AND w.workout_date >= TRUNC(SYSDATE)-6),0) AS workouts_7d,
                   NVL((SELECT SUM(w.duration_minutes) FROM WORKOUTS w WHERE w.user_id=u.user_id AND w.workout_date >= TRUNC(SYSDATE)-6),0) AS minutes_7d,
                   NVL((SELECT SUM(w.calories_burned) FROM WORKOUTS w WHERE w.user_id=u.user_id AND w.workout_date >= TRUNC(SYSDATE)-6),0) AS calories_7d,
                   ROUND(NVL((SELECT AVG(s.sleep_hours) FROM SLEEP_LOG s WHERE s.user_id=u.user_id AND s.sleep_date >= TRUNC(SYSDATE)-6),0),1) AS avg_sleep_7d
            FROM USERS u
            ORDER BY calories_7d DESC, workouts_7d DESC, u.name
        """)
        weekly_leaders = rows_as_dicts(cur)

        cur.execute("""
            SELECT workout_type,
                   COUNT(*) AS session_count,
                   ROUND(AVG(duration_minutes),1) AS avg_duration,
                   ROUND(AVG(calories_burned),1) AS avg_calories
            FROM WORKOUTS
            WHERE workout_date >= TRUNC(SYSDATE)-29
            GROUP BY workout_type
            ORDER BY session_count DESC, avg_calories DESC
        """)
        workout_mix = rows_as_dicts(cur)

        cur.execute("""
            SELECT u.name,
                   ROUND(NVL(n.avg_daily_calories,0),1) AS avg_daily_calories,
                   ROUND(NVL(s.avg_sleep_hours,0),1) AS avg_sleep_hours,
                   NVL(w.days_since_workout,999) AS days_since_workout
            FROM USERS u
            LEFT JOIN (
                SELECT user_id, AVG(day_calories) AS avg_daily_calories
                FROM (
                    SELECT user_id, TRUNC(meal_date) AS meal_day, SUM(calories) AS day_calories
                    FROM MEALS
                    GROUP BY user_id, TRUNC(meal_date)
                )
                GROUP BY user_id
            ) n ON n.user_id=u.user_id
            LEFT JOIN (
                SELECT user_id, AVG(sleep_hours) AS avg_sleep_hours
                FROM SLEEP_LOG
                GROUP BY user_id
            ) s ON s.user_id=u.user_id
            LEFT JOIN (
                SELECT user_id, TRUNC(SYSDATE)-TRUNC(MAX(workout_date)) AS days_since_workout
                FROM WORKOUTS
                GROUP BY user_id
            ) w ON w.user_id=u.user_id
            ORDER BY days_since_workout DESC, avg_sleep_hours ASC, avg_daily_calories ASC
        """)
        risk_rows = rows_as_dicts(cur)
        alerts = []
        for row in risk_rows:
            reasons = []
            if (row.get("days_since_workout") or 999) >= 3:
                reasons.append("Consistency risk")
            if (row.get("avg_sleep_hours") or 0) and row["avg_sleep_hours"] < 6:
                reasons.append("Sleep risk")
            calories = row.get("avg_daily_calories") or 0
            if calories and (calories < 1500 or calories > 2600):
                reasons.append("Nutrition risk")
            if reasons:
                row["reasons"] = reasons
                alerts.append(row)

        return jsonify({
            "summary": summary,
            "weekly_leaders": weekly_leaders[:6],
            "workout_mix": workout_mix,
            "alerts": alerts[:6],
        })
    finally:
        cur.close(); conn.close()

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
        SELECT u.name,
               ROUND(NVL(n.avg_daily_calories,0),2) AS avg_daily_calories,
               ROUND(2000-NVL(n.avg_daily_calories,0),2) AS calorie_deficit,
               CASE WHEN NVL(n.avg_daily_calories,0)<1500 THEN 'Under Eating'
                    WHEN NVL(n.avg_daily_calories,0)>2500 THEN 'Over Eating'
                    ELSE 'On Track' END AS nutrition_status
        FROM USERS u
        LEFT JOIN (
            SELECT user_id, AVG(day_calories) AS avg_daily_calories
            FROM (
                SELECT user_id, TRUNC(meal_date) AS meal_day, SUM(calories) AS day_calories
                FROM MEALS
                GROUP BY user_id, TRUNC(meal_date)
            )
            GROUP BY user_id
        ) n ON n.user_id=u.user_id
        ORDER BY avg_daily_calories DESC, u.name
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
        WITH burned AS (
            SELECT user_id, SUM(calories_burned) AS total_burned
            FROM WORKOUTS
            GROUP BY user_id
        ),
        consumed AS (
            SELECT user_id, SUM(calories) AS total_consumed
            FROM MEALS
            GROUP BY user_id
        )
        SELECT u.name,
               NVL(b.total_burned,0) AS total_burned,
               NVL(c.total_consumed,0) AS total_consumed,
               NVL(c.total_consumed,0)-NVL(b.total_burned,0) AS net_balance,
               CASE
                   WHEN NVL(c.total_consumed,0)-NVL(b.total_burned,0) > 0 THEN 'Calorie Surplus'
                   WHEN NVL(c.total_consumed,0)-NVL(b.total_burned,0) < 0 THEN 'Calorie Deficit'
                   ELSE 'Balanced'
               END AS balance_status
        FROM USERS u
        LEFT JOIN burned b ON u.user_id=b.user_id
        LEFT JOIN consumed c ON u.user_id=c.user_id
        ORDER BY net_balance DESC, u.name
    """)
    rows = rows_as_dicts(cur); cur.close(); conn.close(); return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
