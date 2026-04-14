import sqlite3

def init_db():
    conn = sqlite3.connect('football.db')
    
    # Just create the table structure
    with open('schema.sql') as f:
        conn.executescript(f.read())
        
    print("✅ Database structure created (Empty). Run 'sync_api.py' next!")
    conn.close()

if __name__ == '__main__':
    init_db()