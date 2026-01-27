from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
app = Flask(__name__)
# --- DATABASE CONFIGURATION ---
# This is how Python finds your database
db_config = {
    'user': 'root',
    'password': 'root123',  # <--- CHANGE THIS!
    'host': 'localhost',
    'database': 'football_league'
}
def get_db_connection():
    return mysql.connector.connect(**db_config)
# --- ROUTE 1: HOMEPAGE (League Table) ---
# --- ROUTE 1: HOMEPAGE (League Table) ---
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 

    # --- NEW SIMPLE QUERY ---
    # We already have the points in the 'teams' table, so just grab them!
    query = """
    SELECT *, 
           name AS team_name  
    FROM teams 
    ORDER BY points DESC, goal_diff DESC
    """
    
    cursor.execute(query)
    standings = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', standings=standings)
# --- ROUTE 2: TEAM DETAILS ---
@app.route('/teams')
def teams_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('teams.html', teams=teams)
# --- ROUTE 3: ADMIN - ADD MATCH RESULT (The "Updater") ---
@app.route('/admin/add-match', methods=['GET', 'POST'])
def add_match():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. Get data from the HTML form
        home_team_id = request.form['home_team']
        away_team_id = request.form['away_team']
        home_score = request.form['home_score']
        away_score = request.form['away_score']
        match_date = request.form['match_date']

        # 2. Insert into MySQL Database
        query = """
            INSERT INTO matches 
            (home_team_id, away_team_id, home_score, away_score, match_date, status) 
            VALUES (%s, %s, %s, %s, %s, 'FINISHED')
        """
        cursor.execute(query, (home_team_id, away_team_id, home_score, away_score, match_date))
        conn.commit()
        
        cursor.close()
        conn.close()
        # 3. Go back to homepage to see the update!
        return redirect(url_for('index'))

    # If it's just a normal visit (GET), show the form with the list of teams
    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('add_match.html', teams=teams)
# --- ROUTE 4: VIEW SQUAD (The "Team Manager") ---
@app.route('/team/<int:team_id>')
def team_squad(team_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Get the Team Name (so we can put it in the title)
    cursor.execute("SELECT * FROM teams WHERE team_id = %s", (team_id,))
    team = cursor.fetchone()

    # 2. Get all players for this team
    cursor.execute("SELECT * FROM players WHERE team_id = %s", (team_id,))
    players = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('squad.html', team=team, players=players)
# --- ROUTE 5: MATCH RESULTS & FILTERING ---
@app.route('/results')
def match_results():
    team_id_filter = request.args.get('team_id') # Get the filter from URL
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Get all teams for the dropdown filter
    cursor.execute("SELECT * FROM teams ORDER BY name")
    teams = cursor.fetchall()

    # 2. Base SQL Query
    query = """
        SELECT m.match_date, m.home_score, m.away_score,
               t1.name as home_team, t2.name as away_team
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
    """
    
    # 3. Apply Filter if selected
    params = ()
    if team_id_filter:
        query += " WHERE m.home_team_id = %s OR m.away_team_id = %s"
        params = (team_id_filter, team_id_filter)
    
    query += " ORDER BY m.match_date DESC"

    cursor.execute(query, params)
    matches = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('results.html', matches=matches, teams=teams)

# --- ROUTE 6: TOP SCORERS ---
@app.route('/top-scorers')
def top_scorers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Count goals per player and sort by highest
    # Count goals per player and sort by highest
    query = """
        SELECT p.name AS player_name, t.name AS team_name, COUNT(g.goal_id) AS goals
        FROM goals g
        JOIN players p ON g.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        GROUP BY p.player_id, p.name, t.name
        ORDER BY goals DESC
        LIMIT 20
    """
    
    cursor.execute(query)
    scorers = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('top_scorers.html', scorers=scorers)

# --- ROUTE 7: ADD REAL GOALS ---
# --- ROUTE 7: ADD REAL GOALS ---
# --- ROUTE 7: ADD REAL GOALS ---
@app.route('/add-goal', methods=['GET', 'POST'])
def add_goal():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. HANDLE SAVING DATA (If button clicked)
    if request.method == 'POST':
        match_id = request.form['match_id']
        player_id = request.form['player_id']
        minute = request.form['minute']

        cursor.execute("INSERT INTO goals (match_id, player_id, minute_scored) VALUES (%s, %s, %s)", 
                       (match_id, player_id, minute))
        conn.commit()
        return redirect('/top-scorers')

    # 2. HANDLE LOADING THE PAGE
    
    # Get Matches for the dropdown
    cursor.execute("""
        SELECT m.match_id, m.match_date, t1.name as home_team, t2.name as away_team 
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        ORDER BY m.match_date DESC
    """)
    matches = cursor.fetchall()

    # Get ALL Teams (for the Filter dropdown)
    cursor.execute("SELECT * FROM teams ORDER BY name ASC")
    teams = cursor.fetchall()

    # Get Players (Check if we need to filter!)
    filter_team_id = request.args.get('team_id') # <--- Check if user selected a team

    if filter_team_id:
        # Show ONLY players from the selected team
        query = """
            SELECT p.player_id, p.name, t.name as team_name 
            FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            WHERE p.team_id = %s 
            ORDER BY p.name ASC
        """
        cursor.execute(query, (filter_team_id,))
    else:
        # Show ALL players (but group them by team name so it looks nicer)
        query = """
            SELECT p.player_id, p.name, t.name as team_name 
            FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            ORDER BY t.name ASC, p.name ASC
        """
        cursor.execute(query)
    
    players = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('add_goal.html', matches=matches, players=players, teams=teams, selected_team=filter_team_id)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')