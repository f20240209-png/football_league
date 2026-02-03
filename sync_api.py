import mysql.connector
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
API_KEY = '85dc36138bfb466c805bdf36ca913349'
BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "PL"
SEASON = 2025

# Database Settings
db_config = {
    'user': 'root',
    'password': 'root123',  # <--- CHECK THIS
    'host': 'localhost',
    'database': 'football_league'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def sync_all():
    print(f"🚀 STARTING ULTIMATE FIX (Season {SEASON})...")
    conn = get_db_connection()
    cursor = conn.cursor()
    headers = {'X-Auth-Token': API_KEY}

    # ==========================================
    # STEP 0: FIX DATABASE & CLEAN UP
    # ==========================================
    print("\n0️⃣  Preparing Database...")
    
    # 1. Enable deletion
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # 2. Add Stadium Column if missing
    try:
        cursor.execute("ALTER TABLE teams ADD COLUMN stadium VARCHAR(255)")
        print("   -> Added 'stadium' column.")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            print("   -> 'stadium' column already exists (Good).")
    
    # 3. Wipe old data to ensure clean sync
    tables = ['goals', 'matches', 'players', 'top_scorers', 'teams']
    for table in tables:
        cursor.execute(f"TRUNCATE TABLE {table}")
    print("   -> Old data wiped. Starting fresh.")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

    # ==========================================
    # STEP 1: SYNC TEAMS & STANDINGS
    # ==========================================
    print("\n1️⃣  Syncing Teams & Standings...")
    url = f"{BASE_URL}/competitions/{COMPETITION}/standings?season={SEASON}"
    response = requests.get(url, headers=headers)
    
    local_team_map = {} # Maps ShortName -> DB_ID

    if response.status_code == 200:
        data = response.json()
        standings = data['standings'][0]['table']
        
        for team_data in standings:
            t = team_data['team']
            stats = team_data
            
            # Insert Team
            query = """
            INSERT INTO teams (name, logo_url, points, played, won, drawn, lost, goals_for, goals_against, goal_diff)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                t['shortName'], t['crest'], stats['points'], stats['playedGames'], stats['won'], stats['draw'], stats['lost'], 
                stats['goalsFor'], stats['goalsAgainst'], stats['goalDifference']
            ))
            
            # Get the new ID
            new_team_id = cursor.lastrowid
            local_team_map[t['shortName']] = new_team_id
            
        conn.commit()
        print(f"✅ Added {len(local_team_map)} Teams!")
    else:
        print(f"❌ Failed to get Standings: {response.status_code}")
        return # Stop if this fails

    # ==========================================
    # STEP 2: DETAILS (Stadiums, Managers, Players)
    # ==========================================
    print("\n2️⃣  Syncing Stadiums & Players (This takes 2 mins)...")
    
    url = f"{BASE_URL}/competitions/{COMPETITION}/teams?season={SEASON}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        api_teams = response.json()['teams']
        for api_team in api_teams:
            short_name = api_team['shortName']
            api_team_id = api_team['id']
            
            # Capture Details
            venue = api_team.get('venue', 'Unknown Stadium')
            coach = api_team.get('coach', {})
            manager_name = coach.get('name', 'Unknown')
            
            if short_name in local_team_map:
                local_team_id = local_team_map[short_name]
                
                # Update DB
                cursor.execute("UPDATE teams SET manager = %s, stadium = %s WHERE team_id = %s", (manager_name, venue, local_team_id))
                
                # Get Squad
                print(f"   -> Downloading squad for {short_name}...")
                squad_url = f"{BASE_URL}/teams/{api_team_id}"
                s_response = requests.get(squad_url, headers=headers)
                
                if s_response.status_code == 200:
                    squad = s_response.json()['squad']
                    for player in squad:
                        p_name = player['name']
                        p_pos = player.get('position', 'Unknown')
                        p_num = player.get('shirtNumber')
                        
                        cursor.execute("""
                            INSERT INTO players (name, position, shirt_number, team_id) 
                            VALUES (%s, %s, %s, %s)
                        """, (p_name, p_pos, p_num, local_team_id))
                    conn.commit()
                    
                    # 🔴 CRITICAL PAUSE: Prevents API Ban
                    time.sleep(6.5) 

    # ==========================================
    # STEP 3: SYNC MATCHES (FIXTURES)
    # ==========================================
    print("\n3️⃣  Syncing Matches (Fixtures)...")
    url = f"{BASE_URL}/competitions/{COMPETITION}/matches?season={SEASON}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        matches = response.json()['matches']
        count = 0
        skipped = 0
        
        for m in matches:
            home_name = m['homeTeam']['shortName']
            away_name = m['awayTeam']['shortName']
            
            # Find IDs using our map
            home_id = local_team_map.get(home_name)
            away_id = local_team_map.get(away_name)

            if home_id and away_id:
                match_date = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                status = m['status']
                
                home_score = None
                away_score = None
                
                if status == 'FINISHED':
                    home_score = m['score']['fullTime']['home']
                    away_score = m['score']['fullTime']['away']
                
                cursor.execute("""
                INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, match_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (home_id, away_id, home_score, away_score, match_date, status))
                count += 1
            else:
                skipped += 1
                
        conn.commit()
        print(f"✅ Successfully added {count} matches!")
        if skipped > 0:
            print(f"⚠️ Skipped {skipped} matches (Teams not found).")
    else:
        print(f"❌ Failed to get Matches: {response.status_code}")

    # ==========================================
    # STEP 4: SYNC TOP SCORERS
    # ==========================================
    print("\n4️⃣  Syncing Top Scorers...")
    url = f"{BASE_URL}/competitions/{COMPETITION}/scorers?season={SEASON}&limit=20"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        scorers = response.json()['scorers']
        for s in scorers:
            cursor.execute("""
                INSERT INTO top_scorers (player_name, team_name, goals, assists)
                VALUES (%s, %s, %s, %s)
            """, (s['player']['name'], s['team']['shortName'], s['goals'], s.get('assists', 0)))
        conn.commit()
        print("✅ Top Scorers Updated!")

    print("\n🎉 DONE! Refresh your website now.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    sync_all()