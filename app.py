from flask import Flask, render_template, request, redirect, url_for, jsonify

import mysql.connector

from google import genai as google_genai

import os

from dotenv import load_dotenv

from datetime import datetime





load_dotenv()



app = Flask(__name__)







api_key = os.getenv("GEMINI_API_KEY")

try:

    client = google_genai.Client(api_key=api_key)

    print("✅ SUCCESS: AI Client initialized successfully!")

except Exception as e:

    print(f"❌ ERROR initializing AI: {e}")



# ... (your existing routes for home, fixtures, etc.) ...



# --- DATABASE CONFIGURATION ---

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

@app.route('/ask-ai', methods=['POST'])

def ask_ai():

    data = request.get_json()

    user_query = data.get('message')

    

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    

    # 1. LEAGUE STANDINGS & MANAGERS

    cursor.execute("SELECT name, points, played, manager, goal_diff FROM teams ORDER BY points DESC")

    standings_data = cursor.fetchall()

    

    # 2. RECENT RESULTS (Last 10 finished matches)

    cursor.execute("""

        SELECT m.match_date, t1.name as home, t2.name as away, m.home_score, m.away_score 

        FROM matches m 

        JOIN teams t1 ON m.home_team_id = t1.team_id 

        JOIN teams t2 ON m.away_team_id = t2.team_id 

        WHERE m.status = 'FINISHED' 

        ORDER BY m.match_date DESC LIMIT 10

    """)

    recent_results = cursor.fetchall()

    

    # 3. UPCOMING FIXTURES (Next 5 matches)

    cursor.execute("""

        SELECT m.match_date, t1.name as home, t2.name as away 

        FROM matches m 

        JOIN teams t1 ON m.home_team_id = t1.team_id 

        JOIN teams t2 ON m.away_team_id = t2.team_id 

        WHERE m.status != 'FINISHED' 

        ORDER BY m.match_date ASC LIMIT 5

    """)

    fixtures_data = cursor.fetchall()



    # 4. TOP SCORERS (Top 10)

    cursor.execute("SELECT player_name, team_name, goals FROM top_scorers ORDER BY goals DESC LIMIT 10")

    scorers_data = cursor.fetchall()



    # 5. TOP ASSISTS (Top 10)

    cursor.execute("SELECT player_name, team_name, assists FROM top_scorers ORDER BY assists DESC LIMIT 10")

    assists_data = cursor.fetchall()

    

    cursor.close()

    conn.close()



    # Create a clean list of "Team: Manager" for the AI to reference

    manager_list = ", ".join([f"{t['name']}: {t['manager']}" for t in standings_data if t['manager']])

    

    # --- CONSTRUCT THE PROMPT ---

    prompt = f"""

    You are the official expert assistant  and Oddsmaker for this specific Football League.

    Answer the user's question using ONLY the real-time data provided below.

    Total Games in a Season=38 (Use this to calculate games remaining).

    === DATA CONTEXT ===

    

    1. 🏆 CURRENT STANDINGS (Ranked by Points):

    {standings_data}

    (Managers:{manager_list})

    

    2. ⚽ RECENT RESULTS (Last 10 Games):

    {recent_results}

    

    3. 📅 UPCOMING FIXTURES (Next 5 Games):

    {fixtures_data}

    

    4. 🥇 TOP SCORERS:

    {scorers_data}

    

    5. 👟 TOP ASSISTS:

    {assists_data}

    

    === END DATA ===

    

    User Question: {user_query}

    

    Instructions:

    GENERAL: Answer friendly and accurately using the data above.

    - If the user asks about a specific team's form, check the 'Recent Results'.

    - If asked about the next game, check 'Upcoming Fixtures'.

    - If asked about "Who is the best player?", use Goals and Assists data.

    - Be conversational but accurate.

    MANAGERS: If asked about a manager, always use the 'Managers' list provided above.

     SEASON PREDICTIONS (Title / Top 4 / Relegation):

       - Look at the "Points" and "Played" columns.

       - Calculate "Points Remaining" = (38 - Played) * 3.

       - If a team is 1st by 10 points with 5 games left, their chance is >95%.

       - If a team is 10 points from 4th place with 3 games left, their UCL chance is <5%.

       - **Provide a percentage estimate** (e.g., "Arsenal has a 65% chance of winning the league").

       - Explain the math simply (e.g., "They need 4 more wins to guarantee the title").

    GOLDEN BOOT CHANCES:

       - Compare the top player's goals to the chasers.

       - If Player A is 5 goals ahead with 3 games left, they are "Very Likely (90%)" to win.

       - If the gap is 1 goal, it is a "Tosss-up (50/50)".   

    ODDS & PREDICTIONS (IMPORTANT): 

       If the user asks for "Odds", "Prediction", or "Who will win?":

       - Compare the two teams' POINTS and RECENT FORM.

       - Estimate a % chance of winning for Home, Draw, and Away.

       - Convert that % into DECIMAL ODDS (Formula: 100 / probability).

       - FORMAT THE ANSWER LIKE THIS:

         "**Prediction: [Home Team] vs [Away Team]**

          - 🏠 Home Win: [Odds] (e.g. 1.50)

          - 🤝 Draw: [Odds] (e.g. 4.00)

          - 🚌 Away Win: [Odds] (e.g. 6.50)



    VISUAL GRAPHS (Crucial):

       - If the user asks about a team's "Form", "Progress", "Season History", or asks to "Visualize" or "Show a graph":

       - You must output a SPECIAL TAG at the very end of your message.

       - Format: [GRAPH: Team Name]

       - Example: "Manchester United have been inconsistent lately. [GRAPH: Manchester United]"

       - ONLY use the exact Team Name from the database.      



          *Analyst's Take: [Brief explanation based on form]*"



    """

    

    try:

        response = client.models.generate_content(

            model="gemini-flash-latest", 

            contents=prompt

        )

        return jsonify({"answer": response.text})

        

    except Exception as e:

        print(f"AI ERROR: {e}") 

        return jsonify({"answer": "Sorry, I'm having trouble analyzing the league data right now."})

    



# --- NEW ROUTE: CALCULATE TEAM PROGRESS FOR GRAPHS ---

@app.route('/team-progress/<team_name>')

def team_progress(team_name):

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    

    # 1. Get the Team ID

    cursor.execute("SELECT team_id FROM teams WHERE name = %s", (team_name,))

    team = cursor.fetchone()

    

    if not team:

        return jsonify({"error": "Team not found"}), 404

    

    team_id = team['team_id']

    

    # 2. Get all finished matches for this team, ordered by date

    cursor.execute("""

        SELECT match_date, home_team_id, away_team_id, home_score, away_score

        FROM matches 

        WHERE (home_team_id = %s OR away_team_id = %s) AND status = 'FINISHED'

        ORDER BY match_date ASC

    """, (team_id, team_id))

    

    matches = cursor.fetchall()

    

    # 3. Calculate Cumulative Points

    points_history = []

    current_points = 0

    match_labels = [] # To store "Matchday 1", "Matchday 2", etc.

    

    for i, m in enumerate(matches):

        points_gained = 0

        

        # Logic: Did they win, draw, or lose?

        if m['home_team_id'] == team_id: # Playing Home

            if m['home_score'] > m['away_score']: points_gained = 3

            elif m['home_score'] == m['away_score']: points_gained = 1

        else: # Playing Away

            if m['away_score'] > m['home_score']: points_gained = 3

            elif m['away_score'] == m['home_score']: points_gained = 1

            

        current_points += points_gained

        

        # Format date for the graph (e.g., "Oct 12")

        # Ensure match_date is a datetime object

        if isinstance(m['match_date'], str):

             date_obj = datetime.strptime(m['match_date'], '%Y-%m-%d') # Adjust format if needed

             date_str = date_obj.strftime("%b %d")

        else:

             date_str = m['match_date'].strftime("%b %d")

             

        points_history.append(current_points)

        match_labels.append(date_str)



    cursor.close()

    conn.close()

    

    return jsonify({

        "labels": match_labels,

        "data": points_history,

        "team": team_name

    })    

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