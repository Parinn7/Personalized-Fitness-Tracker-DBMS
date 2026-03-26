import oracledb
import config

connection = oracledb.connect(
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    dsn=config.DB_DSN
)

cursor = connection.cursor()

cursor.execute("INSERT INTO USERS VALUES (1, 'Dev', 21, 'Male', 172, 68, 'Beginner', SYSDATE - 60, 'Ahmedabad')")
connection.commit()

cursor.execute("SELECT user_id, name, location FROM USERS ORDER BY user_id")
users = cursor.fetchall()
print("Users:")
for user in users:
    print(user)

cursor.close()
connection.close()