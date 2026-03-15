import requests
import oracledb
import config

# Thick mode
oracledb.init_oracle_client(lib_dir=r"C:\Users\Admin\Downloads\instantclient-basic-windows.x64-23.26.1.0.0\instantclient_23_0")

API_KEY = config.API_KEY

# Connect as SYSTEM to XEPDB1
connection = oracledb.connect(
    user="SYSTEM",
    password=config.DB_PASSWORD,
    dsn=config.DB_DSN
)

cursor = connection.cursor()

# Get all user locations
cursor.execute("SELECT user_id, location FROM USERS")
users = cursor.fetchall()

for user_id, city in users:
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    print(f"\nAPI Response for {city}:", data.get("cod"))

    temperature = data.get("main", {}).get("temp")
    humidity = data.get("main", {}).get("humidity")
    condition = data.get("weather", [{}])[0].get("main")

    print(f"City: {city} | Temp: {temperature}°C | Humidity: {humidity}% | Condition: {condition}")

    cursor.execute("""
        INSERT INTO WEATHER
        (weather_id, weather_date, temperature, condition_type, humidity, location)
        VALUES (weather_seq.NEXTVAL, SYSDATE, :1, :2, :3, :4)
    """, (temperature, condition, humidity, city))

connection.commit()
print("\nWeather inserted successfully for all users!")

cursor.close()
connection.close()