import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        # Try 'DB_USER', if empty try 'DB_USERNAME', if both empty default to 'root'
        user=os.getenv('DB_USER') or os.getenv('DB_USERNAME') or 'root',
        password=os.getenv('DB_PASSWORD'),
        # Try 'DB_NAME', if empty try 'DB_DATABASE'
        database=os.getenv('DB_NAME') or os.getenv('DB_DATABASE'),
        port=int(os.getenv('DB_PORT', 3306))
    )

def create_tables():
    print("🚀 Connecting to Railway Database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Clean Slate (Deletes 'coaches' if it exists)
        tables = ['top_assists', 'top_scorers', 'coaches', 'goals', 'matches', 'players', 'teams']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print("🗑️  Old tables deleted.")

        # 2. Teams Table (With 'manager' column)
        cursor.execute("""
        CREATE TABLE teams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            logo VARCHAR(255),
            founded INT,
            venue VARCHAR(255),
            manager VARCHAR(255),
            points INT DEFAULT 0,
            played INT DEFAULT 0,
            won INT DEFAULT 0,
            drawn INT DEFAULT 0,
            lost INT DEFAULT 0,
            goals_for INT DEFAULT 0,
            goals_against INT DEFAULT 0,
            goal_diff INT DEFAULT 0
        )
        """)
        print("✅ Table 'teams' created.")

        # 3. Players Table
        cursor.execute("""
        CREATE TABLE players (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            position VARCHAR(50),
            shirt_number INT,
            team_id INT,
            nationality VARCHAR(100),
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
        )
        """)
        print("✅ Table 'players' created.")

        # 4. Matches Table
        cursor.execute("""
        CREATE TABLE matches (
            id INT AUTO_INCREMENT PRIMARY KEY,
            home_team_id INT,
            away_team_id INT,
            home_score INT,
            away_score INT,
            match_date DATETIME,
            status VARCHAR(50),
            FOREIGN KEY (home_team_id) REFERENCES teams(id) ON DELETE CASCADE,
            FOREIGN KEY (away_team_id) REFERENCES teams(id) ON DELETE CASCADE
        )
        """)
        print("✅ Table 'matches' created.")

        # 5. Top Scorers Table
        cursor.execute("""
        CREATE TABLE top_scorers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            player_name VARCHAR(255),
            team_name VARCHAR(255),
            goals INT,
            assists INT
        )
        """)
        print("✅ Table 'top_scorers' created.")

        # 6. Top Assists Table
        cursor.execute("""
        CREATE TABLE top_assists (
            id INT AUTO_INCREMENT PRIMARY KEY,
            player_name VARCHAR(255),
            team_name VARCHAR(255),
            assists INT
        )
        """)
        print("✅ Table 'top_assists' created.")

        conn.commit()
        conn.close()
        print("\n✨ DATABASE STRUCTURE FIXED! Ready for sync.")

    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")

if __name__ == "__main__":
    create_tables()