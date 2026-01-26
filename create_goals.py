import mysql.connector

# --- CONFIGURATION (Match this to your app.py) ---
db_config = {
    'user': 'root',
    'password': 'root123',     # <--- Add your password if you set one!
    'host': 'localhost',
    'database': 'football_league'
}

# --- THE SQL CODE IS HERE ---
sql_commands = [
    # 1. Create the Goals table
    """
    CREATE TABLE IF NOT EXISTS goals (
        goal_id INT AUTO_INCREMENT PRIMARY KEY,
        match_id INT,
        player_id INT,
        team_id INT,
        minute_scored INT,
        FOREIGN KEY (match_id) REFERENCES matches(match_id),
        FOREIGN KEY (player_id) REFERENCES players(player_id),
        FOREIGN KEY (team_id) REFERENCES teams(team_id)
    );
    """,
    # 2. Add some dummy data so we can see it working
    "INSERT INTO goals (match_id, player_id, team_id, minute_scored) VALUES (1, 1, 1, 12)",
    "INSERT INTO goals (match_id, player_id, team_id, minute_scored) VALUES (1, 1, 1, 45)",
    "INSERT INTO goals (match_id, player_id, team_id, minute_scored) VALUES (1, 2, 1, 88)"
]

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    print("Connecting to database...")

    for sql in sql_commands:
        try:
            cursor.execute(sql)
        except Exception as e:
            print(f"Note: {e}") # specific error if data exists

    conn.commit()
    print("✅ SUCCESS! Table 'goals' created.")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")