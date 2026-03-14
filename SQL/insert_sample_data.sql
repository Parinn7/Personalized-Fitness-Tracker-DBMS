-----------------------------------
-- USERS DATA
-----------------------------------

INSERT INTO Users VALUES
(1, 'Rahul Patel', 22, 'Male', 175, 70, 'Intermediate', DATE '2026-01-10');

INSERT INTO Users VALUES
(2, 'Anita Shah', 24, 'Female', 165, 60, 'Beginner', DATE '2026-02-05');

INSERT INTO Users VALUES
(3, 'Karan Mehta', 28, 'Male', 180, 82, 'Advanced', DATE '2026-01-20');

INSERT INTO Users VALUES
(4, 'Neha Desai', 26, 'Female', 168, 58, 'Intermediate', DATE '2026-02-12');


-----------------------------------
-- WEATHER DATA
-----------------------------------



-----------------------------------
-- WORKOUT DATA
-----------------------------------

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


-----------------------------------
-- MEALS DATA
-----------------------------------

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


-----------------------------------
-- SLEEP DATA
-----------------------------------

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


-----------------------------------
-- GOALS DATA
-----------------------------------

INSERT INTO Goals VALUES
(1, 1, 'Weight Loss', 5, DATE '2026-01-01', DATE '2026-04-01');

INSERT INTO Goals VALUES
(2, 2, 'Run Distance', 20, DATE '2026-02-01', DATE '2026-05-01');

INSERT INTO Goals VALUES
(3, 3, 'Muscle Gain', 3, DATE '2026-01-15', DATE '2026-06-01');

INSERT INTO Goals VALUES
(4, 4, 'Weight Maintenance', 0, DATE '2026-02-10', DATE '2026-05-10');