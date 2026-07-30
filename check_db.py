import sqlite3
conn = sqlite3.connect("instance/data.db")
print("Tables:", conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
print("Alembic version:", conn.execute("SELECT * FROM alembic_version").fetchall())
conn.close()
