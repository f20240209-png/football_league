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
    'password': 'root123',  # <--- Put your Workbench password here
    'host': 'localhost',
    'database': 'football_league'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def sync_all():
    print(f"🚀 STARTING FULL DATABASE SYNC (Season {SEASON}-{SEASON+1})...")
    conn = get_db_connection()
    cursor = conn.cursor()
    headers = {'X-Auth-Token': API_KEY}

    # ==========================================
    # STEP 1: SYNC TEAMS & STANDINGS
    # ==========================================
    print("\n1️⃣  Syncing Teams & Standings...")
    url = f"{BASE_URL}/competitions/{COMPETITION}/standings?season={SEASON}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        standings = data['standings'][0]['table']
        
        for team_data in standings:
            t = team_data['team']
            stats = team_data
            
            # Triple quotes for cleaner code
            query = """
            INSERT INTO teams (name, logo_url, points, played, won, drawn, lost, goals_for, goals_against, goal_diff)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            points=%s, played=%s, won=%s, drawn=%s, lost=%s, goals_for=%s, goals_against=%s, goal_diff=%s, logo_url=%s
            """
            cursor.execute(query, (
                t['shortName'], t['crest'], stats['points'], stats['playedGames'], stats['won'], stats['draw'], stats['lost'], 
                stats['goalsFor'], stats['goalsAgainst'], stats['goalDifference'],
                stats['points'], stats['playedGames'], stats['won'], stats['draw'], stats['lost'], 
                stats['goalsFor'], stats['goalsAgainst'], stats['goalDifference'], t['crest']
            ))
        conn.commit()
        print("✅ Teams & Points Updated!")
    else:
        print(f"❌ Failed to get Standings: {response.status_code}")

    # ==========================================
    # STEP 2: SYNC PLAYERS
    # ==========================================
    print("\n2️⃣  Syncing Players (This will take ~2 minutes to avoid API limits)...")
    
    cursor.execute("SELECT team_id, name FROM teams")
    teams = cursor.fetchall()
    team_map = {row[1]: row[0] for row in teams} 

    url = f"{BASE_URL}/competitions/{COMPETITION}/teams?season={SEASON}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        api_teams = response.json()['teams']
        for api_team in api_teams:
            short_name = api_team['shortName']
            api_team_id = api_team['id']
            
            if short_name in team_map:
                local_team_id = team_map[short_name]
                squad_url = f"{BASE_URL}/teams/{api_team_id}"
                s_response = requests.get(squad_url, headers=headers)
                
                if s_response.status_code == 200:
                    squad = s_response.json()['squad']
                    for player in squad:
                        p_name = player['name']
                        p_pos = player.get('position', 'Unknown')
                        p_num = player.get('shirtNumber', 0)
                        
                        # Use 'shirt_number' as agreed
                        p_query = """
                            INSERT INTO players (name, position, shirt_number, team_id) 
                            VALUES (%s, %s, %s, %s) 
                            ON DUPLICATE KEY UPDATE position=%s, shirt_number=%s
                        """
                        cursor.execute(p_query, (p_name, p_pos, p_num, local_team_id, p_pos, p_num))
                    
                    print(f"   -> Updated squad for {short_name}")
                    conn.commit()
                else:
                    print(f"   ⚠️ Failed {short_name}: API Error {s_response.status_code}")

                # --- IMPORTANT: WAIT 7 SECONDS TO RESPECT API LIMIT ---
                time.sleep(7) 
    else:
        print(f"❌ Failed to get Team List: {response.status_code}")
        
    print("✅ Players Updated!")

    # ==========================================
    # STEP 3: SYNC MATCH RESULTS
    # ==========================================
    print("\n3️⃣  Syncing Match Results...")
    url = f"{BASE_URL}/competitions/{COMPETITION}/matches?season={SEASON}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        matches = response.json()['matches']
        count = 0
        for m in matches:
            if m['status'] == 'FINISHED':
                home_name = m['homeTeam']['shortName']
                away_name = m['awayTeam']['shortName']
                
                home_id = team_map.get(home_name)
                away_id = team_map.get(away_name)

                if home_id and away_id:
                    match_date = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                    
                    m_query = """
                    INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, match_date, status)
                    SELECT %s, %s, %s, %s, %s, 'FINISHED'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM matches WHERE home_team_id=%s AND away_team_id=%s AND match_date=%s
                    )
                    """
                    cursor.execute(m_query, (
                        home_id, away_id, m['score']['fullTime']['home'], m['score']['fullTime']['away'], match_date,
                        home_id, away_id, match_date
                    ))
                    if cursor.rowcount > 0:
                        count += 1
        conn.commit()
        print(f"✅ Added {count} new matches!")
    else:
        print(f"❌ Failed to get Matches: {response.status_code}")

    print("\n🎉 DONE! Database is fully synced.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    sync_all()