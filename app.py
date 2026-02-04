from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
db_config = {
    'user': 'root',
    'password': 'root123',  # <--- CHECK YOUR PASSWORD
    'host': 'localhost',
    'database': 'football_league'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)


# =========================================================
#  SECTION 1: PUBLIC PAGES
# =========================================================

# --- ROUTE 1: HOMEPAGE (Standings) ---
@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch the Standings
    cursor.execute("SELECT * FROM teams ORDER BY points DESC, goal_diff DESC")
    teams = cursor.fetchall()
    
    # 2. NEW: Calculate Form for every team
    for team in teams:
        team_id = team['team_id']
        
        # Get last 5 COMPLETED matches for this team (ordered by date, newest first)
        cursor.execute("""
            SELECT home_team_id, away_team_id, home_score, away_score
            FROM matches 
            WHERE (home_team_id = %s OR away_team_id = %s) 
            AND home_score IS NOT NULL
            ORDER BY match_date DESC 
            LIMIT 5
        """, (team_id, team_id))
        
        recent_matches = cursor.fetchall()
        
        form_guide = []
        
        for match in recent_matches:
            # Check if the current team was Home or Away
            if match['home_team_id'] == team_id:
                # We were Home
                if match['home_score'] > match['away_score']:
                    form_guide.append('W')
                elif match['home_score'] < match['away_score']:
                    form_guide.append('L')
                else:
                    form_guide.append('D')
            else:
                # We were Away
                if match['away_score'] > match['home_score']:
                    form_guide.append('W')
                elif match['away_score'] < match['home_score']:
                    form_guide.append('L')
                else:
                    form_guide.append('D')
        
        # Reverse the list so it reads: [Oldest Match] -> [Most Recent Match]
        team['form'] = form_guide[::-1]

    conn.close()
    return render_template('index.html', teams=teams)

# --- ROUTE 2: TEAMS LIST (Matches your teams.html) ---
@app.route('/teams')
def teams_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # This selects everything, including 'stadium' if it is in your DB
    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()
    conn.close()
    return render_template('teams.html', teams=teams)


# --- ROUTE 3: SQUAD DETAILS (Fixed URL to match your HTML) ---
# Your HTML asks for /team/ID, so we use that here.
@app.route('/team/<int:team_id>')
def squad(team_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get Team Info
    cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
    team = cursor.fetchone()
    
    # Get Players
    cursor.execute("SELECT * FROM players WHERE team_id = %s ORDER BY position", (team_id,))
    players = cursor.fetchall()
    
    conn.close()
    return render_template('squad.html', team=team, players=players)


# --- ROUTE 4: FIXTURES ---
# --- ROUTE: FIXTURES (Upcoming Matches) ---
@app.route('/fixtures')
def fixtures():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get matches that are NOT finished
    query = """
        SELECT m.match_date, m.status, 
               t1.name AS home_team, t1.logo_url AS home_logo, 
               t2.name AS away_team, t2.logo_url AS away_logo
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id 
        JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.status != 'FINISHED'
        ORDER BY m.match_date ASC
    """
    cursor.execute(query)
    matches = cursor.fetchall()
    conn.close()
    
    # We send 'matches' (not fixtures) to match standard naming
    return render_template('fixtures.html', matches=matches)


# --- ROUTE: RESULTS (With Filter Logic) ---
@app.route('/results')
def results():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get List of Teams for the Dropdown
    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()

    # 2. Check if user selected a team filter
    team_id_filter = request.args.get('team_id')

    # 3. Build Query
    base_query = """
        SELECT m.match_date, m.status, m.home_score, m.away_score,
               t1.name AS home_team, t1.logo_url AS home_logo, 
               t2.name AS away_team, t2.logo_url AS away_logo
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id 
        JOIN teams t2 ON m.away_team_id = t2.team_id
        WHERE m.status = 'FINISHED'
    """
    
    if team_id_filter:
        base_query += " AND (m.home_team_id = %s OR m.away_team_id = %s)"
        params = (team_id_filter, team_id_filter)
        cursor.execute(base_query + " ORDER BY m.match_date DESC", params)
    else:
        cursor.execute(base_query + " ORDER BY m.match_date DESC")

    matches = cursor.fetchall()
    conn.close()
    
    return render_template('results.html', matches=matches, teams=teams, selected_team=team_id_filter)


# --- ROUTE 5: TOP SCORERS ---
@app.route('/top-scorers')
def top_scorers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # We join top_scorers with teams to get the logo_url based on team_name
    query = """
        SELECT ts.player_name, ts.team_name, ts.goals, t.logo_url
        FROM top_scorers ts
        LEFT JOIN teams t ON ts.team_name = t.name
        ORDER BY ts.goals DESC 
        LIMIT 20
    """
    cursor.execute(query)
    scorers = cursor.fetchall()
    conn.close()
    return render_template('top_scorers.html', scorers=scorers)


# --- ROUTE: TOP ASSISTS ---
@app.route('/top-assists')
def top_assists():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Updated query to join teams and get the logo
    query = """
        SELECT ts.player_name as name, ts.team_name, ts.assists, t.logo_url
        FROM top_scorers ts
        JOIN teams t ON ts.team_name = t.name
        ORDER BY ts.assists DESC 
        LIMIT 20
    """
    cursor.execute(query)
    assists = cursor.fetchall()
    conn.close()
    return render_template('top_assists.html', assists=assists)

# =========================================================
#  SECTION 2: ADMIN PAGES
# =========================================================

@app.route('/add-goal', methods=['GET', 'POST'])
def add_goal():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        match_id = request.form['match_id']
        player_id = request.form['player_id']
        minute = request.form['minute']
        cursor.execute("INSERT INTO goals (match_id, player_id, minute_scored) VALUES (%s, %s, %s)", (match_id, player_id, minute))
        conn.commit()
        return redirect('/top-scorers')

    cursor.execute("SELECT m.match_id, m.match_date, t1.name as home_team, t2.name as away_team FROM matches m JOIN teams t1 ON m.home_team_id = t1.team_id JOIN teams t2 ON m.away_team_id = t2.team_id ORDER BY m.match_date DESC")
    matches = cursor.fetchall()
    
    filter_team_id = request.args.get('team_id')
    if filter_team_id:
        cursor.execute("SELECT player_id, name FROM players WHERE team_id = %s ORDER BY name", (filter_team_id,))
    else:
        cursor.execute("SELECT player_id, name FROM players ORDER BY name LIMIT 50")
    players = cursor.fetchall()

    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()

    conn.close()
    return render_template('add_goal.html', matches=matches, players=players, teams=teams, selected_team=filter_team_id)


@app.route('/admin/add-match', methods=['GET', 'POST'])
def add_match():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        home_team_id = request.form['home_team']
        away_team_id = request.form['away_team']
        home_score = request.form['home_score']
        away_score = request.form['away_score']
        match_date = request.form['match_date']

        cursor.execute("""
            INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, match_date, status) 
            VALUES (%s, %s, %s, %s, %s, 'FINISHED')
        """, (home_team_id, away_team_id, home_score, away_score, match_date))
        conn.commit()
        
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('add_match.html', teams=teams)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')