from sqlalchemy import text
from app.database.connection import engine

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database(), current_user, version()")
    ).fetchone()

    print("Database connection successful!")
    print("Database:", result[0])
    print("User:", result[1])
    print("PostgreSQL:", result[2].split(",")[0])