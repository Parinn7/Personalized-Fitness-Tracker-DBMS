SET SERVEROUTPUT ON;

DECLARE
    -- Main user cursor
    CURSOR user_cur IS
        SELECT user_id, name, fitness_level, location
        FROM USERS;

    -- Variables for user
    v_user_id       USERS.user_id%TYPE;
    v_name          USERS.name%TYPE;
    v_fitness_level USERS.fitness_level%TYPE;
    v_location      USERS.location%TYPE;

    -- Weather variables
    v_temp          WEATHER.temperature%TYPE;
    v_condition     WEATHER.condition_type%TYPE;
    v_humidity      WEATHER.humidity%TYPE;

    -- Workout variables
    v_workout_type  WORKOUTS.workout_type%TYPE;
    v_duration      WORKOUTS.duration_minutes%TYPE;
    v_calories_burned WORKOUTS.calories_burned%TYPE;

    -- Meal variables
    v_total_calories NUMBER;
    v_total_protein  NUMBER;
    v_total_carbs    NUMBER;

    -- Sleep variables
    v_sleep_hours   SLEEP_LOG.sleep_hours%TYPE;

    -- Goal variables
    v_goal_type     GOALS.goal_type%TYPE;

    -- Recommendation message
    v_message       VARCHAR2(500);
    v_rec_id        NUMBER;

BEGIN
    OPEN user_cur;
    LOOP
        FETCH user_cur INTO v_user_id, v_name, v_fitness_level, v_location;
        EXIT WHEN user_cur%NOTFOUND;

        -- ----------------------------------------
        -- FETCH TODAY'S WEATHER FOR USER'S CITY
        -- ----------------------------------------
        BEGIN
            SELECT temperature, condition_type, humidity
            INTO v_temp, v_condition, v_humidity
            FROM WEATHER
            WHERE UPPER(location) = UPPER(v_location)
            AND TRUNC(weather_date) = TRUNC(SYSDATE)
            AND ROWNUM = 1;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_temp      := NULL;
                v_condition := 'Unknown';
                v_humidity  := NULL;
        END;

        -- ----------------------------------------
        -- FETCH YESTERDAY'S WORKOUT
        -- ----------------------------------------
        BEGIN
            SELECT workout_type, duration_minutes, calories_burned
            INTO v_workout_type, v_duration, v_calories_burned
            FROM WORKOUTS
            WHERE user_id = v_user_id
            AND TRUNC(workout_date) = TRUNC(SYSDATE - 1)
            AND ROWNUM = 1;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_workout_type    := NULL;
                v_duration        := 0;
                v_calories_burned := 0;
        END;

        -- ----------------------------------------
        -- FETCH YESTERDAY'S MEAL TOTALS
        -- ----------------------------------------
        BEGIN
            SELECT NVL(SUM(calories), 0),
                   NVL(SUM(protein), 0),
                   NVL(SUM(carbs), 0)
            INTO v_total_calories, v_total_protein, v_total_carbs
            FROM MEALS
            WHERE user_id = v_user_id
            AND TRUNC(meal_date) = TRUNC(SYSDATE - 1);
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_total_calories := 0;
                v_total_protein  := 0;
                v_total_carbs    := 0;
        END;

        -- ----------------------------------------
        -- FETCH LAST NIGHT'S SLEEP
        -- ----------------------------------------
        BEGIN
            SELECT sleep_hours
            INTO v_sleep_hours
            FROM SLEEP_LOG
            WHERE user_id = v_user_id
            AND TRUNC(sleep_date) = TRUNC(SYSDATE - 1);
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_sleep_hours := 0;
        END;

        -- ----------------------------------------
        -- FETCH CURRENT GOAL
        -- ----------------------------------------
        BEGIN
            SELECT goal_type
            INTO v_goal_type
            FROM GOALS
            WHERE user_id = v_user_id
            AND ROWNUM = 1;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_goal_type := 'General Fitness';
        END;

        -- ----------------------------------------
        -- GENERATE RECOMMENDATION MESSAGE
        -- ----------------------------------------
        v_message := 'Hey ' || v_name || '! ';

        -- Sleep based advice
        IF v_sleep_hours = 0 THEN
            v_message := v_message || 'No sleep data found for yesterday. ';
        ELSIF v_sleep_hours < 6 THEN
            v_message := v_message || 'You only slept ' || v_sleep_hours || ' hrs - rest is critical for recovery! Consider a light yoga or stretching session today. ';
        ELSIF v_sleep_hours >= 6 AND v_sleep_hours < 7.5 THEN
            v_message := v_message || 'You slept ' || v_sleep_hours || ' hrs - decent but aim for 8hrs. ';
        ELSE
            v_message := v_message || 'Great sleep of ' || v_sleep_hours || ' hrs! Your body is well recovered. ';
        END IF;

        -- Weather based advice
        IF v_condition = 'Rain' OR v_condition = 'Drizzle' OR v_condition = 'Thunderstorm' THEN
            v_message := v_message || 'It is ' || v_condition || ' in ' || v_location || ' today - skip outdoor workouts, focus on indoor training. ';
        ELSIF v_temp > 38 THEN
            v_message := v_message || 'It is very hot (' || v_temp || 'C) in ' || v_location || ' - avoid outdoor exercise, stay hydrated! ';
        ELSIF v_temp > 30 THEN
            v_message := v_message || 'Warm weather (' || v_temp || 'C) in ' || v_location || ' - workout early morning or evening. ';
        ELSIF v_temp >= 20 AND v_temp <= 30 THEN
            v_message := v_message || 'Perfect weather (' || v_temp || 'C) in ' || v_location || ' for an outdoor workout! ';
        ELSE
            v_message := v_message || 'Cool weather (' || v_temp || 'C) in ' || v_location || ' - great for a brisk run or cycling! ';
        END IF;

        -- Workout based advice
        IF v_workout_type IS NULL THEN
            v_message := v_message || 'No workout logged yesterday - try not to skip days! ';
        ELSIF v_duration >= 60 THEN
            v_message := v_message || 'Excellent ' || v_duration || ' min ' || v_workout_type || ' yesterday! Consider active recovery today. ';
        ELSIF v_duration >= 30 THEN
            v_message := v_message || 'Good ' || v_duration || ' min ' || v_workout_type || ' yesterday! Push a bit harder today. ';
        ELSE
            v_message := v_message || 'Only ' || v_duration || ' min workout yesterday - aim for at least 30 mins today! ';
        END IF;

        -- Nutrition based advice
        IF v_total_calories = 0 THEN
            v_message := v_message || 'No meals logged yesterday - track your food for better results! ';
        ELSIF v_total_calories > 2500 THEN
            v_message := v_message || 'High calorie intake (' || v_total_calories || ' kcal) yesterday - eat clean today. ';
        ELSIF v_total_calories < 1200 THEN
            v_message := v_message || 'Very low calories (' || v_total_calories || ' kcal) yesterday - fuel your body properly! ';
        ELSE
            v_message := v_message || 'Good calorie intake (' || v_total_calories || ' kcal) yesterday. ';
        END IF;

        -- Goal based advice
        IF v_goal_type = 'Weight Loss' THEN
            v_message := v_message || 'Focus on cardio + calorie deficit for your Weight Loss goal!';
        ELSIF v_goal_type = 'Muscle Gain' THEN
            v_message := v_message || 'Hit the weights and ensure high protein intake for Muscle Gain!';
        ELSIF v_goal_type = 'Run Distance' THEN
            v_message := v_message || 'Add 5-10 mins to your run today to build towards your distance goal!';
        ELSE
            v_message := v_message || 'Stay consistent and keep tracking for overall fitness!';
        END IF;

        -- ----------------------------------------
        -- INSERT INTO RECOMMENDATIONS TABLE
        -- ----------------------------------------
        INSERT INTO RECOMMENDATIONS
            (recommendation_id, user_id, message, recommendation_date)
        VALUES
            (rec_seq.NEXTVAL, v_user_id, v_message, SYSDATE);

        -- Print to console
        DBMS_OUTPUT.PUT_LINE('');
        DBMS_OUTPUT.PUT_LINE('--- Recommendation for ' || v_name || ' ---');
        DBMS_OUTPUT.PUT_LINE(v_message);

    END LOOP;
    CLOSE user_cur;

    COMMIT;
    DBMS_OUTPUT.PUT_LINE('');
    DBMS_OUTPUT.PUT_LINE('All recommendations generated and saved!');

EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Error: ' || SQLERRM);
        ROLLBACK;
END;
/
SELECT r.recommendation_id, u.name, r.message, r.recommendation_date
FROM RECOMMENDATIONS r
JOIN USERS u ON r.user_id = u.user_id
ORDER BY r.recommendation_id;






-- ============================================
-- CURSOR 2: Goal Progress Tracker
-- ============================================
SET SERVEROUTPUT ON;

DECLARE
    CURSOR goal_cur IS
        SELECT u.name, g.goal_type, g.target_value,
               g.start_date, g.end_date
        FROM USERS u
        JOIN GOALS g ON u.user_id = g.user_id;

    v_name         USERS.name%TYPE;
    v_goal_type    GOALS.goal_type%TYPE;
    v_target       GOALS.target_value%TYPE;
    v_start        GOALS.start_date%TYPE;
    v_end          GOALS.end_date%TYPE;
    v_days_total   NUMBER;
    v_days_done    NUMBER;
    v_progress_pct NUMBER;
    v_status       VARCHAR2(100);

BEGIN
    OPEN goal_cur;
    LOOP
        FETCH goal_cur INTO v_name, v_goal_type, v_target, v_start, v_end;
        EXIT WHEN goal_cur%NOTFOUND;

        v_days_total   := TRUNC(v_end - v_start);
        v_days_done    := TRUNC(SYSDATE - v_start);
        v_progress_pct := ROUND((v_days_done / NULLIF(v_days_total, 0)) * 100, 2);

        IF SYSDATE > v_end THEN
            v_status := 'EXPIRED - Goal deadline passed!';
        ELSIF v_progress_pct >= 75 THEN
            v_status := 'ALMOST THERE - Final push!';
        ELSIF v_progress_pct >= 50 THEN
            v_status := 'HALFWAY - Keep going!';
        ELSIF v_progress_pct >= 25 THEN
            v_status := 'GOOD START - Stay consistent!';
        ELSE
            v_status := 'JUST STARTED - Build the habit!';
        END IF;

        DBMS_OUTPUT.PUT_LINE('');
        DBMS_OUTPUT.PUT_LINE('--- Goal Tracker: ' || v_name || ' ---');
        DBMS_OUTPUT.PUT_LINE('Goal       : ' || v_goal_type);
        DBMS_OUTPUT.PUT_LINE('Target     : ' || v_target);
        DBMS_OUTPUT.PUT_LINE('Progress   : ' || v_progress_pct || '% of timeline completed');
        DBMS_OUTPUT.PUT_LINE('Status     : ' || v_status);

    END LOOP;
    CLOSE goal_cur;
END;
/

-- ============================================
-- CURSOR 3: Weekly Workout Streak Counter
-- ============================================
SET SERVEROUTPUT ON;

DECLARE
    CURSOR streak_cur IS
        SELECT user_id, name FROM USERS;

    v_user_id   USERS.user_id%TYPE;
    v_name      USERS.name%TYPE;
    v_streak    NUMBER := 0;
    v_check_date DATE;
    v_count     NUMBER;

BEGIN
    OPEN streak_cur;
    LOOP
        FETCH streak_cur INTO v_user_id, v_name;
        EXIT WHEN streak_cur%NOTFOUND;

        v_streak     := 0;
        v_check_date := TRUNC(SYSDATE - 1);

        -- Check last 7 days for consecutive workouts
        FOR i IN 1..7 LOOP
            SELECT COUNT(*)
            INTO v_count
            FROM WORKOUTS
            WHERE user_id = v_user_id
            AND TRUNC(workout_date) = v_check_date;

            IF v_count > 0 THEN
                v_streak     := v_streak + 1;
                v_check_date := v_check_date - 1;
            ELSE
                EXIT;
            END IF;
        END LOOP;

        DBMS_OUTPUT.PUT_LINE('');
        DBMS_OUTPUT.PUT_LINE('--- Workout Streak: ' || v_name || ' ---');
        DBMS_OUTPUT.PUT_LINE('Current Streak : ' || v_streak || ' consecutive day(s)');
        IF v_streak = 0 THEN
            DBMS_OUTPUT.PUT_LINE('Message        : No recent workouts - start today!');
        ELSIF v_streak >= 5 THEN
            DBMS_OUTPUT.PUT_LINE('Message        : Outstanding streak! Keep it up!');
        ELSIF v_streak >= 3 THEN
            DBMS_OUTPUT.PUT_LINE('Message        : Great consistency! Push for 5 days!');
        ELSE
            DBMS_OUTPUT.PUT_LINE('Message        : Good start! Aim for 3 days in a row!');
        END IF;

    END LOOP;
    CLOSE streak_cur;
END;
/