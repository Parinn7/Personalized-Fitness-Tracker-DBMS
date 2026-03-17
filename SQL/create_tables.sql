-- ============================================
-- PERSONALIZED FITNESS TRACKER DATABASE
-- All tables under SYSTEM on XEPDB1
-- ============================================

-- USERS TABLE
CREATE TABLE USERS (
    user_id       NUMBER PRIMARY KEY,
    name          VARCHAR2(50) NOT NULL,
    age           NUMBER,
    gender        VARCHAR2(10),
    height        NUMBER,
    weight        NUMBER,
    fitness_level VARCHAR2(20),
    join_date     DATE,
    location      VARCHAR2(100)
);

-- WEATHER TABLE
CREATE TABLE WEATHER (
    weather_id     NUMBER PRIMARY KEY,
    weather_date   DATE,
    temperature    NUMBER,
    condition_type VARCHAR2(50),
    humidity       NUMBER,
    location       VARCHAR2(100)
);

-- WORKOUTS TABLE
CREATE TABLE WORKOUTS (
    workout_id       NUMBER PRIMARY KEY,
    user_id          NUMBER,
    workout_type     VARCHAR2(50),
    duration_minutes NUMBER,
    calories_burned  NUMBER,
    workout_date     DATE,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- MEALS TABLE
CREATE TABLE MEALS (
    meal_id   NUMBER PRIMARY KEY,
    user_id   NUMBER,
    meal_type VARCHAR2(20),
    calories  NUMBER,
    protein   NUMBER,
    carbs     NUMBER,
    fats      NUMBER,
    meal_date DATE,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- SLEEP LOG TABLE
CREATE TABLE SLEEP_LOG (
    sleep_id    NUMBER PRIMARY KEY,
    user_id     NUMBER,
    sleep_hours NUMBER,
    sleep_date  DATE,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- GOALS TABLE
CREATE TABLE GOALS (
    goal_id      NUMBER PRIMARY KEY,
    user_id      NUMBER,
    goal_type    VARCHAR2(50),
    target_value NUMBER,
    start_date   DATE,
    end_date     DATE,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- RECOMMENDATIONS TABLE
CREATE TABLE RECOMMENDATIONS (
    recommendation_id   NUMBER PRIMARY KEY,
    user_id             NUMBER,
    message             VARCHAR2(500),
    recommendation_date DATE,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

-- ============================================
-- SEQUENCES
-- ============================================

CREATE SEQUENCE weather_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE rec_seq     START WITH 1 INCREMENT BY 1;

select * from users;