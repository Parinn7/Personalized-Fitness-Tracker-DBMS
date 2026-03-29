-- ============================================
-- VIEW 1: Weekly Progress Report Per User
-- ============================================
CREATE OR REPLACE VIEW Weekly_Progress AS
SELECT 
    u.user_id,
    u.name,
    u.location,
    (SELECT COUNT(*) 
     FROM WORKOUTS w 
     WHERE w.user_id = u.user_id 
     AND w.workout_date >= SYSDATE - 7)          AS total_workouts,
    (SELECT NVL(SUM(w.duration_minutes), 0) 
     FROM WORKOUTS w 
     WHERE w.user_id = u.user_id 
     AND w.workout_date >= SYSDATE - 7)          AS total_workout_mins,
    (SELECT NVL(SUM(w.calories_burned), 0) 
     FROM WORKOUTS w 
     WHERE w.user_id = u.user_id 
     AND w.workout_date >= SYSDATE - 7)          AS total_calories_burned,
    (SELECT NVL(SUM(m.calories), 0) 
     FROM MEALS m 
     WHERE m.user_id = u.user_id 
     AND m.meal_date >= SYSDATE - 7)             AS total_calories_consumed,
    (SELECT ROUND(NVL(AVG(s.sleep_hours), 0), 2) 
     FROM SLEEP_LOG s 
     WHERE s.user_id = u.user_id 
     AND s.sleep_date >= SYSDATE - 7)            AS avg_sleep_hours
FROM USERS u;


-- ============================================
-- VIEW 2: Average Calories Burned Per Workout Type
-- ============================================
CREATE OR REPLACE VIEW Avg_Calories_Per_Workout AS
SELECT 
    workout_type,
    COUNT(*)                        AS total_sessions,
    ROUND(AVG(duration_minutes), 2) AS avg_duration_mins,
    ROUND(AVG(calories_burned), 2)  AS avg_calories_burned,
    SUM(calories_burned)            AS total_calories_burned
FROM WORKOUTS
GROUP BY workout_type;

-- ============================================
-- VIEW 3: Sleep Quality Summary
-- ============================================
CREATE OR REPLACE VIEW Sleep_Quality_Summary AS
SELECT 
    u.user_id,
    u.name,
    ROUND(AVG(s.sleep_hours), 2) AS avg_sleep_hours,
    MIN(s.sleep_hours)           AS min_sleep_hours,
    MAX(s.sleep_hours)           AS max_sleep_hours,
    SUM(CASE WHEN s.sleep_hours < 6   THEN 1 ELSE 0 END) AS poor_sleep_days,
    SUM(CASE WHEN s.sleep_hours >= 6 
             AND s.sleep_hours < 8    THEN 1 ELSE 0 END) AS average_sleep_days,
    SUM(CASE WHEN s.sleep_hours >= 8  THEN 1 ELSE 0 END) AS good_sleep_days
FROM USERS u
LEFT JOIN SLEEP_LOG s ON u.user_id = s.user_id
GROUP BY u.user_id, u.name;

-- ============================================
-- VIEW 4: User Nutrition Summary
-- ============================================
CREATE OR REPLACE VIEW Nutrition_Summary AS
SELECT 
    u.user_id,
    u.name,
    ROUND(NVL(n.avg_daily_calories, 0), 2) AS avg_daily_calories,
    ROUND(NVL(n.avg_protein, 0), 2)        AS avg_protein,
    ROUND(NVL(n.avg_carbs, 0), 2)          AS avg_carbs,
    ROUND(NVL(n.avg_fats, 0), 2)           AS avg_fats,
    NVL(n.total_calories, 0)               AS total_calories
FROM USERS u
LEFT JOIN (
    SELECT user_id,
           AVG(day_calories) AS avg_daily_calories,
           AVG(day_protein)  AS avg_protein,
           AVG(day_carbs)    AS avg_carbs,
           AVG(day_fats)     AS avg_fats,
           SUM(day_calories) AS total_calories
    FROM (
        SELECT user_id,
               TRUNC(meal_date) AS meal_day,
               SUM(calories)    AS day_calories,
               SUM(protein)     AS day_protein,
               SUM(carbs)       AS day_carbs,
               SUM(fats)        AS day_fats
        FROM MEALS
        GROUP BY user_id, TRUNC(meal_date)
    )
    GROUP BY user_id
) n ON u.user_id = n.user_id;

-- ============================================
-- VIEW 5: Latest Weather Per City
-- ============================================
CREATE OR REPLACE VIEW Latest_Weather AS
SELECT 
    location,
    temperature,
    condition_type,
    humidity,
    weather_date
FROM WEATHER w1
WHERE weather_date = (
    SELECT MAX(weather_date)
    FROM WEATHER w2
    WHERE w2.location = w1.location
);

SELECT * FROM Weekly_Progress;
SELECT * FROM Avg_Calories_Per_Workout;
SELECT * FROM Sleep_Quality_Summary;
SELECT * FROM Nutrition_Summary;
SELECT * FROM Latest_Weather;
