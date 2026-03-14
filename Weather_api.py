import requests
from config import API_KEY

CITY = "London"

url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"

response = requests.get(url)
data = response.json()

print("API RESPONSE:", data)

temperature = data.get("main", {}).get("temp")
humidity = data.get("main", {}).get("humidity")
condition = data.get("weather", [{}])[0].get("main")

print("Temperature:", temperature)
print("Humidity:", humidity)
print("Condition:", condition)

