import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        user='root',
        password='root123',     # <--- PUT YOUR PASSWORD HERE IF YOU HAVE ONE
        host='localhost',
        database='football_league'
    )

def reset_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("⚠️  WARNING: This will delete ALL current data (Teams, Players, Matches).")
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Operation cancelled.")
        return

    print("🧹 Cleaning database...")

    # We must delete in this specific order to avoid Foreign Key errors
    tables_to_clear = ['cards', 'matches', 'players', 'teams']

    for table in tables_to_clear:
        try:
            # DELETE FROM removes rows but keeps the table structure
            cursor.execute(f"DELETE FROM {table}")
            print(f"   ✅ Cleared table: {table}")
        except mysql.connector.Error as err:
            print(f"   ❌ Error clearing {table}: {err}")

    conn.commit()
    cursor.close()
    conn.close()
    print("✨ Database is now EMPTY and ready for fresh API data!")

if __name__ == "__main__":
    reset_database()