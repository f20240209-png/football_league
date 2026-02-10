import mysql.connector
import requests
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
API_KEY = '85dc36138bfb466c805bdf36ca913349'
BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "PL"
SEASON = 2025

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER') or os.getenv('DB_USERNAME') or 'root',
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME') or os.getenv('DB_DATABASE'),
        port=int(os.getenv('DB_PORT', 3306))
    )

def sync_all():
    print(f"🚀 STARTING BULLETPROOF SYNC (Season {SEASON})...")
    headers = {'X-Auth-Token': API_KEY}

    # ==========================================
    # STEP 0: CLEAN SLATE
    # ==========================================
    print("\n0️⃣  Wiping old data...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ['top_assists', 'top_scorers', 'matches', 'players', 'teams']:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    conn.close() # Close immediately to stay safe
    print("   -> Data wiped.")

    # ==========================================
    # STEP 1: TEAMS & STANDINGS
    # ==========================================
    print("\n1️⃣  Syncing Teams & Standings...")
    conn = get_db_connection() # New Connection
    cursor = conn.cursor()
    
    url = f"{BASE_URL}/competitions/{COMPETITION}/standings?season={SEASON}"
    response = requests.get(url, headers=headers)
    
    local_team_map = {} 

    if response.status_code == 200:
        data = response.json()
        standings = data['standings'][0]['table']
        
        for team_data in standings:
            t = team_data['team']
            stats = team_data
            
            cursor.execute("""
            INSERT INTO teams (name, logo, points, played, won, drawn, lost, goals_for, goals_against, goal_diff)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (t['shortName'], t['crest'], stats['points'], stats['playedGames'], 
                  stats['won'], stats['draw'], stats['lost'], 
                  stats['goalsFor'], stats['goalsAgainst'], stats['goalDifference']))
            
            local_team_map[t['shortName']] = cursor.lastrowid
            
        conn.commit()
        conn.close() # Close after finishing teams
        print(f"✅ Added {len(local_team_map)} Teams!")
    else:
        print(f"❌ Failed to get Standings: {response.status_code}")
        return

    # ==========================================
    # STEP 2: PLAYERS & MANAGERS (The Crash Zone)
    # ==========================================
    print("\n2️⃣  Syncing Managers & Players...")
    
    # Get the list of teams first
    teams_url = f"{BASE_URL}/competitions/{COMPETITION}/teams?season={SEASON}"
    t_resp = requests.get(teams_url, headers=headers)
    
    if t_resp.status_code == 200:
        api_teams = t_resp.json()['teams']
        
        for api_team in api_teams:
            short_name = api_team['shortName']
            
            # CHECK: Do we have this team in our DB?
            if short_name in local_team_map:
                local_team_id = local_team_map[short_name]
                print(f"   -> Processing: {short_name}...")

                # --- CRITICAL FIX: NEW CONNECTION FOR EVERY TEAM ---
                # We open a connection JUST for this team, then close it.
                # This prevents the "Lost Connection" error during sleep.
                try:
                    team_conn = get_db_connection()
                    team_cursor = team_conn.cursor()

                    # 1. Update Manager/Venue
                    venue = api_team.get('venue', 'Unknown Stadium')
                    manager = api_team.get('coach', {}).get('name', 'Unknown')
                    
                    team_cursor.execute("UPDATE teams SET manager=%s, venue=%s WHERE id=%s", 
                                        (manager, venue, local_team_id))

                    # 2. Get Squad
                    squad_url = f"{BASE_URL}/teams/{api_team['id']}"
                    s_resp = requests.get(squad_url, headers=headers)
                    
                    if s_resp.status_code == 200:
                        squad = s_resp.json()['squad']
                        for p in squad:
                            team_cursor.execute("""
                                INSERT INTO players (name, position, shirt_number, nationality, team_id) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (p['name'], p.get('position'), p.get('shirtNumber'), 
                                  p.get('nationality'), local_team_id))
                    
                    team_conn.commit()
                    team_conn.close() # <--- DISCONNECT HERE SAFELY
                    
                except Exception as e:
                    print(f"⚠️ Error syncing {short_name}: {e}")
                    # Continue to next team even if one fails

                # NOW we sleep safely without holding a DB connection
                time.sleep(6.5) 

    # ==========================================
    # STEP 3: MATCHES
    # ==========================================
    print("\n3️⃣  Syncing Matches...")
    conn = get_db_connection() # New Connection
    cursor = conn.cursor()
    
    url = f"{BASE_URL}/competitions/{COMPETITION}/matches?season={SEASON}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        matches = response.json()['matches']
        count = 0
        for m in matches:
            home_id = local_team_map.get(m['homeTeam']['shortName'])
            away_id = local_team_map.get(m['awayTeam']['shortName'])
            
            if home_id and away_id:
                score = m['score']['fullTime']
                status = m['status']
                cursor.execute("""
                    INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, match_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (home_id, away_id, score['home'], score['away'], 
                      datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ"), status))
                count += 1
        conn.commit()
        conn.close()
        print(f"✅ Added {count} matches.")

    # ==========================================
    # STEP 4: TOP SCORERS
    # ==========================================
    print("\n4️⃣  Syncing Stats...")
    conn = get_db_connection() # New Connection
    cursor = conn.cursor()
    
    url = f"{BASE_URL}/competitions/{COMPETITION}/scorers?season={SEASON}&limit=50"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        scorers = response.json()['scorers']
        for s in scorers:
            p_name = s['player']['name']
            t_name = s['team']['shortName']
            goals = s.get('goals', 0)
            assists = s.get('assists'); 
            if assists is None: assists = 0

            cursor.execute("INSERT INTO top_scorers (player_name, team_name, goals, assists) VALUES (%s, %s, %s, %s)", 
                           (p_name, t_name, goals, assists))
            
            if assists > 0:
                cursor.execute("INSERT INTO top_assists (player_name, team_name, assists) VALUES (%s, %s, %s)", 
                               (p_name, t_name, assists))
        conn.commit()
        conn.close()
        print("✅ Stats synced.")

    print("\n🎉 SYNC COMPLETE! No timeouts allowed. 🚀")

if __name__ == "__main__":
    sync_all()