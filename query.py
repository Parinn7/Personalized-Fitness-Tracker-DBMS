import oracledb
import config

connection = oracledb.connect(
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    dsn=config.DB_DSN
)

cursor = connection.cursor()

cursor.execute("SELECT user_id, name, location FROM USERS ORDER BY user_id")
users = cursor.fetchall()
print("Users:")
for user in users:
    print(user)

cursor.execute("SELECT * FROM WEATHER")
weather = cursor.fetchall()
print("\nWeather:")
for w in weather:
    print(w)

cursor.close()
connection.close()