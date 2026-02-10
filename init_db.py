import sqlite3

def init_db():
    try:
        # 1. Connect to the database file (creates it if missing)
        conn = sqlite3.connect('football.db')
        
        # 2. Read the schema.sql file to create the tables
        with open('schema.sql') as f:
            conn.executescript(f.read())
        
        print("✅ Tables created successfully.")

        # 3. Insert Sample Data (So the app doesn't look broken)
        cur = conn.cursor()
        
        print("📝 Inserting sample data...")

        # Add Teams
        cur.execute("INSERT INTO teams (name, points, logo) VALUES (?, ?, ?)",
                    ('Arsenal', 15, 'https://resources.premierleague.com/premierleague/badges/t3.svg'))
        
        cur.execute("INSERT INTO teams (name, points, logo) VALUES (?, ?, ?)",
                    ('Man City', 12, 'https://resources.premierleague.com/premierleague/badges/t43.svg'))

        cur.execute("INSERT INTO teams (name, points, logo) VALUES (?, ?, ?)",
                    ('Liverpool', 10, 'https://resources.premierleague.com/premierleague/badges/t14.svg'))

        # Add a Player (Saka)
        cur.execute("INSERT INTO players (team_id, name, position, number) VALUES (?, ?, ?, ?)",
                    (1, 'Bukayo Saka', 'Forward', 7))

        # Add a Finished Match (Arsenal 2 - 1 Man City)
        cur.execute("""
            INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, match_date, status) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (1, 2, 2, 1, '2023-10-08 16:30:00', 'FINISHED'))

        # Add an Upcoming Fixture
        cur.execute("""
            INSERT INTO matches (home_team_id, away_team_id, match_date, status) 
            VALUES (?, ?, ?, ?)
        """, (2, 3, '2025-05-01 20:00:00', 'SCHEDULED'))

        conn.commit()
        conn.close()
        print("🎉 Success! Database is ready.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    init_db()