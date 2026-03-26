import oracledb
import config

connection = oracledb.connect(
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    dsn=config.DB_DSN
)

cursor = connection.cursor()

# Read the cursors.sql file
with open('SQL/cursors.sql', 'r') as f:
    sql_content = f.read()

# Split by '/' to get individual PL/SQL blocks
blocks = sql_content.split('/')

for i, block in enumerate(blocks):
    block = block.strip()
    if block and not block.startswith('--'):
        print(f"Executing block {i+1}...")
        try:
            cursor.execute(block)
            # For blocks with DBMS_OUTPUT, we need to get the output
            # But oracledb doesn't directly support DBMS_OUTPUT, so perhaps print the result
            print("Block executed successfully.")
        except Exception as e:
            print(f"Error in block {i+1}: {e}")

connection.commit()
cursor.close()
connection.close()

print("Cursors executed!")