from main import create_admin_user, SessionLocal

def main():
    db = SessionLocal()
    admin = create_admin_user(db, "abbas", "2701")
    if admin:
        print("Admin user created successfully")
    else:
        print("Failed to create admin user")

if __name__ == "__main__":
    main() 