import sqlite3
import os

# Get the absolute path to your db.sqlite3 file
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table info
cursor.execute("PRAGMA table_info(bazaar_bazaarlisting)")
columns = cursor.fetchall()
print("Columns in bazaar_bazaarlisting table:")
for column in columns:
    print(column[1])  # column name is the second item in the tuple

# Count records
cursor.execute("SELECT COUNT(*) FROM bazaar_bazaarlisting")
count = cursor.fetchone()[0]
print(f"Total records: {count}")

# Check for 'N/A' in id field
cursor.execute("SELECT COUNT(*) FROM bazaar_bazaarlisting WHERE id='N/A'")
na_count = cursor.fetchone()[0]
print(f"Records with 'N/A' as id: {na_count}")

conn.close()

print("Database inspection completed!")