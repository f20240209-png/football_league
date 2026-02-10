import mysql.connector

db_config = {
    'user': 'root',
    'password': 'root123', 
    'host': 'localhost',
    'database': 'football_league'
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

print("--- COLUMNS IN TEAMS TABLE ---")
cursor.execute("DESCRIBE teams")
for col in cursor.fetchall():
    print(col)

conn.close()