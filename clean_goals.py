import mysql.connector

conn = mysql.connector.connect(user='root', password='', host='localhost', database='football_league')
cursor = conn.cursor()

# DELETE all existing fake goals
cursor.execute("TRUNCATE TABLE goals") 
conn.commit()

print("GOALS")
conn.close()