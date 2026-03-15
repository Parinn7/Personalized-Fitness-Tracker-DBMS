-- ============================================
-- QUERY 1: Top Performing Users by Calories Burned
-- ============================================
SELECT 
    u.name,
    u.fitness_level,
    SUM(w.calories_burned)  AS total_calories_burned,
    COUNT(w.workout_id)     AS total_workouts
FROM USERS u
JOIN WORKOUTS w ON u.user_id = w.user_id
GROUP BY u.name, u.fitness_level
ORDER BY total_calories_burned DESC;

-- ============================================
-- QUERY 2: Users Who Missed Workouts in Last 7 Days
-- ============================================
SELECT 
    u.name,
    u.fitness_level,
    u.location,
    MAX(w.workout_date) AS last_workout_date,
    TRUNC(SYSDATE) - TRUNC(MAX(w.workout_date)) AS days_since_last_workout
FROM USERS u
LEFT JOIN WORKOUTS w ON u.user_id = w.user_id
GROUP BY u.user_id, u.name, u.fitness_level, u.location
HAVING TRUNC(SYSDATE) - TRUNC(MAX(w.workout_date)) > 2
    OR MAX(w.workout_date) IS NULL
ORDER BY days_since_last_workout DESC;

-- ============================================
-- QUERY 3: Nutrition Deficit or Surplus Per User
-- (Based on 2000 kcal standard daily requirement)
-- ============================================
SELECT 
    u.name,
    ROUND(AVG(m.calories), 2)        AS avg_daily_calories,
    2000 - ROUND(AVG(m.calories), 2) AS calorie_deficit_surplus,
    CASE 
        WHEN AVG(m.calories) < 1500 THEN 'Under Eating'
        WHEN AVG(m.calories) > 2500 THEN 'Over Eating'
        ELSE 'On Track'
    END AS nutrition_status
FROM USERS u
JOIN MEALS m ON u.user_id = m.user_id
GROUP BY u.name
ORDER BY avg_daily_calories DESC;

-- ============================================
-- QUERY 4: Most Popular Workout Types
-- ============================================
SELECT 
    workout_type,
    COUNT(*)                        AS frequency,
    ROUND(AVG(duration_minutes), 2) AS avg_duration,
    ROUND(AVG(calories_burned), 2)  AS avg_calories
FROM WORKOUTS
GROUP BY workout_type
ORDER BY frequency DESC;

-- ============================================
-- QUERY 5: User Goal Progress Overview
-- ============================================
SELECT 
    u.name,
    g.goal_type,
    g.target_value,
    g.start_date,
    g.end_date,
    TRUNC(g.end_date - SYSDATE) AS days_remaining,
    CASE 
        WHEN SYSDATE > g.end_date THEN 'Expired'
        WHEN TRUNC(g.end_date - SYSDATE) <= 7 THEN 'Deadline Near'
        ELSE 'In Progress'
    END AS goal_status
FROM USERS u
JOIN GOALS g ON u.user_id = g.user_id
ORDER BY days_remaining;

-- ============================================
-- QUERY 6: Average Sleep Per User With Status
-- ============================================
SELECT 
    u.name,
    ROUND(AVG(s.sleep_hours), 2) AS avg_sleep,
    CASE 
        WHEN AVG(s.sleep_hours) >= 8  THEN 'Excellent'
        WHEN AVG(s.sleep_hours) >= 6  THEN 'Adequate'
        ELSE 'Poor - Needs Improvement'
    END AS sleep_status
FROM USERS u
JOIN SLEEP_LOG s ON u.user_id = s.user_id
GROUP BY u.name
ORDER BY avg_sleep DESC;

-- ============================================
-- QUERY 7: Calories Burned vs Consumed Per User
-- ============================================
SELECT 
    u.name,
    NVL(SUM(w.calories_burned), 0)  AS total_burned,
    NVL(SUM(m.calories), 0)         AS total_consumed,
    NVL(SUM(m.calories), 0) - 
    NVL(SUM(w.calories_burned), 0)  AS net_calorie_balance,
    CASE 
        WHEN NVL(SUM(m.calories), 0) - NVL(SUM(w.calories_burned), 0) > 0 
            THEN 'Calorie Surplus'
        ELSE 'Calorie Deficit'
    END AS balance_status
FROM USERS u
LEFT JOIN WORKOUTS w ON u.user_id = w.user_id
LEFT JOIN MEALS m    ON u.user_id = m.user_id
GROUP BY u.name
ORDER BY net_calorie_balance DESC;

