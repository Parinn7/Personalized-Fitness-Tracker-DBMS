-- USERS TABLE
CREATE TABLE Users (
    user_id NUMBER PRIMARY KEY,
    name VARCHAR2(50) NOT NULL,
    age NUMBER,
    gender VARCHAR2(10),
    height NUMBER,
    weight NUMBER,
    fitness_level VARCHAR2(20),
    join_date DATE
);

-- WEATHER TABLE

CREATE TABLE Weather (
    weather_id NUMBER PRIMARY KEY,
    weather_date DATE,
    temperature NUMBER,
    condition_type VARCHAR2(50),
    humidity NUMBER
);

-- WORKOUTS TABLE
CREATE TABLE Workouts (
    workout_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    workout_type VARCHAR2(50),
    duration_minutes NUMBER,
    calories_burned NUMBER,
    workout_date DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- MEALS TABLE
CREATE TABLE Meals (
    meal_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    meal_type VARCHAR2(20),
    calories NUMBER,
    protein NUMBER,
    carbs NUMBER,
    fats NUMBER,
    meal_date DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- SLEEP LOG TABLE
CREATE TABLE Sleep_Log (
    sleep_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    sleep_hours NUMBER,
    sleep_date DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- GOALS TABLE
CREATE TABLE Goals (
    goal_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    goal_type VARCHAR2(50),
    target_value NUMBER,
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- RECOMMENDATIONS TABLE
CREATE TABLE Recommendations (
    recommendation_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    message VARCHAR2(500),
    recommendation_date DATE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

