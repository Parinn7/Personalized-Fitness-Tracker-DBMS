-- user
-- user data
INSERT INTO Users (name, age, gender, height, weight, fitness_level, join_date)
VALUES ('Rahul Patel', 22, 'Male', 175, 70, 'Intermediate', DATE '2026-01-10');

INSERT INTO Users (name, age, gender, height, weight, fitness_level, join_date)
VALUES ('Anita Shah', 24, 'Female', 165, 60, 'Beginner', DATE '2026-02-05');

INSERT INTO Users (name, age, gender, height, weight, fitness_level, join_date)
VALUES ('Karan Mehta', 28, 'Male', 180, 82, 'Advanced', DATE '2026-01-20');

INSERT INTO Users (name, age, gender, height, weight, fitness_level, join_date)
VALUES ('Neha Desai', 26, 'Female', 168, 58, 'Intermediate', DATE '2026-02-12');


--weather data
INSERT INTO Weather (weather_date, temperature, condition_type, humidity)
VALUES (DATE '2026-03-10', 34, 'Sunny', 40);

INSERT INTO Weather (weather_date, temperature, condition_type, humidity)
VALUES (DATE '2026-03-11', 29, 'Rainy', 70);

INSERT INTO Weather (weather_date, temperature, condition_type, humidity)
VALUES (DATE '2026-03-12', 30, 'Cloudy', 55);

INSERT INTO Weather (weather_date, temperature, condition_type, humidity)
VALUES (DATE '2026-03-13', 36, 'Hot', 35);

INSERT INTO Weather (weather_date, temperature, condition_type, humidity)
VALUES (DATE '2026-03-14', 28, 'Pleasant', 45);



-- workout data
INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (1, 'Running', 45, 350, DATE '2026-03-10');

INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (1, 'Cycling', 30, 220, DATE '2026-03-11');

INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (2, 'Yoga', 60, 180, DATE '2026-03-10');

INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (3, 'Weight Training', 50, 300, DATE '2026-03-12');

INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (4, 'Swimming', 40, 280, DATE '2026-03-13');

INSERT INTO Workouts (user_id, workout_type, duration_minutes, calories_burned, workout_date)
VALUES (2, 'Running', 35, 260, DATE '2026-03-14');



-- Meals Data
INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (1, 'Breakfast', 400, 20, 50, 10, DATE '2026-03-10');

INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (1, 'Lunch', 650, 35, 70, 20, DATE '2026-03-10');

INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (2, 'Breakfast', 350, 18, 45, 8, DATE '2026-03-11');

INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (3, 'Dinner', 700, 40, 60, 25, DATE '2026-03-12');

INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (4, 'Lunch', 600, 30, 65, 18, DATE '2026-03-13');

INSERT INTO Meals (user_id, meal_type, calories, protein, carbs, fats, meal_date)
VALUES (2, 'Dinner', 550, 28, 55, 15, DATE '2026-03-14');



-- Sleep data
INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (1, 7, DATE '2026-03-10');

INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (1, 6, DATE '2026-03-11');

INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (2, 8, DATE '2026-03-11');

INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (3, 7.5, DATE '2026-03-12');

INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (4, 6.5, DATE '2026-03-13');

INSERT INTO Sleep_Log (user_id, sleep_hours, sleep_date)
VALUES (2, 7, DATE '2026-03-14');


-- Goal data
INSERT INTO Goals (user_id, goal_type, target_value, start_date, end_date)
VALUES (1, 'Weight Loss', 5, DATE '2026-01-01', DATE '2026-04-01');

INSERT INTO Goals (user_id, goal_type, target_value, start_date, end_date)
VALUES (2, 'Run Distance', 20, DATE '2026-02-01', DATE '2026-05-01');

INSERT INTO Goals (user_id, goal_type, target_value, start_date, end_date)
VALUES (3, 'Muscle Gain', 3, DATE '2026-01-15', DATE '2026-06-01');

INSERT INTO Goals (user_id, goal_type, target_value, start_date, end_date)
VALUES (4, 'Weight Maintenance', 0, DATE '2026-02-10', DATE '2026-05-10');




-- Recommendation

SELECT 
u.name,
w.condition_type,
wo.duration_minutes,
CASE
    WHEN w.condition_type = 'Rainy' THEN 'Indoor workout recommended'
    WHEN w.temperature > 35 THEN 'Light workout recommended'
    WHEN wo.duration_minutes > 60 THEN 'Rest day suggested'
    ELSE 'Outdoor workout recommended'
END AS recommendation
FROM Users u
JOIN Workouts wo 
ON u.user_id = wo.user_id
JOIN Weather w 
ON wo.workout_date = w.weather_date;

--weather
INSERT INTO Weather VALUES
(1, DATE '2026-03-10', 34, 'Sunny', 40);

INSERT INTO Weather VALUES
(2, DATE '2026-03-11', 29, 'Rainy', 70);

INSERT INTO Weather VALUES
(3, DATE '2026-03-12', 30, 'Cloudy', 55);

INSERT INTO Weather VALUES
(4, DATE '2026-03-13', 36, 'Hot', 35);

INSERT INTO Weather VALUES
(5, DATE '2026-03-14', 28, 'Pleasant', 45);


--workout
INSERT INTO Workouts VALUES
(1, 1, 'Running', 45, 350, DATE '2026-03-10');

INSERT INTO Workouts VALUES
(2, 1, 'Cycling', 30, 220, DATE '2026-03-11');

INSERT INTO Workouts VALUES
(3, 2, 'Yoga', 60, 180, DATE '2026-03-10');

INSERT INTO Workouts VALUES
(4, 3, 'Weight Training', 50, 300, DATE '2026-03-12');

INSERT INTO Workouts VALUES
(5, 4, 'Swimming', 40, 280, DATE '2026-03-13');

INSERT INTO Workouts VALUES
(6, 2, 'Running', 35, 260, DATE '2026-03-14');


--Meals
INSERT INTO Meals VALUES
(1, 1, 'Breakfast', 400, 20, 50, 10, DATE '2026-03-10');

INSERT INTO Meals VALUES
(2, 1, 'Lunch', 650, 35, 70, 20, DATE '2026-03-10');

INSERT INTO Meals VALUES
(3, 2, 'Breakfast', 350, 18, 45, 8, DATE '2026-03-11');

INSERT INTO Meals VALUES
(4, 3, 'Dinner', 700, 40, 60, 25, DATE '2026-03-12');

INSERT INTO Meals VALUES
(5, 4, 'Lunch', 600, 30, 65, 18, DATE '2026-03-13');

INSERT INTO Meals VALUES
(6, 2, 'Dinner', 550, 28, 55, 15, DATE '2026-03-14');

-- sleep
INSERT INTO Sleep_Log VALUES
(1, 1, 7, DATE '2026-03-10');

INSERT INTO Sleep_Log VALUES
(2, 1, 6, DATE '2026-03-11');

INSERT INTO Sleep_Log VALUES
(3, 2, 8, DATE '2026-03-11');

INSERT INTO Sleep_Log VALUES
(4, 3, 7.5, DATE '2026-03-12');

INSERT INTO Sleep_Log VALUES
(5, 4, 6.5, DATE '2026-03-13');

INSERT INTO Sleep_Log VALUES
(6, 2, 7, DATE '2026-03-14');

--Goals
INSERT INTO Goals VALUES
(1, 1, 'Weight Loss', 5, DATE '2026-01-01', DATE '2026-04-01');

INSERT INTO Goals VALUES
(2, 2, 'Run Distance', 20, DATE '2026-02-01', DATE '2026-05-01');

INSERT INTO Goals VALUES
(3, 3, 'Muscle Gain', 3, DATE '2026-01-15', DATE '2026-06-01');

INSERT INTO Goals VALUES
(4, 4, 'Weight Maintenance', 0, DATE '2026-02-10', DATE '2026-05-10');

--
SELECT 
u.name,
w.condition_type,
wo.duration_minutes,
CASE
    WHEN w.condition_type = 'Rainy' THEN 'Indoor workout recommended'
    WHEN w.temperature > 35 THEN 'Light workout recommended'
    WHEN wo.duration_minutes > 60 THEN 'Rest day suggested'
    ELSE 'Outdoor workout recommended'
END AS recommendation
FROM Users u
JOIN Workouts wo ON u.user_id = wo.user_id
JOIN Weather w ON wo.workout_date = w.weather_date;