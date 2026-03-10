import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import engine, Base
from db.models import Asset, ValidationRun, ValidationResult


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")
    print("Tables in database:")
    for table in Base.metadata.tables:
        print(f"  {table}")


if __name__ == "__main__":
    create_tables()
