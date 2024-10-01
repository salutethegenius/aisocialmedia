from app import app, db
from models import Content, ScheduledPost

def update_database():
    with app.app_context():
        # Drop the existing tables
        db.drop_all()
        
        # Create the tables with the updated schema
        db.create_all()
        
        print("Database schema updated successfully.")

if __name__ == "__main__":
    update_database()
