"""Initialize the database schema. Run: python -m scripts.init_db"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import init_database


def main():
    print("Initializing database schema...")
    try:
        init_database()
        print("Database schema created successfully!")
    except Exception as e:
        print(f"ERROR creating database: {e}")
        print("Make sure MySQL is running and .env is configured correctly.")
        sys.exit(1)


if __name__ == "__main__":
    main()
