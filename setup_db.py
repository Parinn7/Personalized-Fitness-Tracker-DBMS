import oracledb
import config

# Connect to Oracle DB
connection = oracledb.connect(
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    dsn=config.DB_DSN
)

cursor = connection.cursor()

# Read and execute create_tables.sql
with open('SQL/create_tables.sql', 'r') as f:
    sql_script = f.read()

# Split by semicolon and execute each statement
statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

for stmt in statements:
    if stmt:
        try:
            cursor.execute(stmt)
            print(f"Executed: {stmt[:50]}...")
        except Exception as e:
            print(f"Error executing: {stmt[:50]}... Error: {e}")

connection.commit()
cursor.close()
connection.close()

print("Tables created successfully!")