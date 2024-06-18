import os
import time
import schedule
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import threading
from fastapi import FastAPI, HTTPException

DATABASE_URL = os.getenv("DATABASE_URL")
BACKUP_DIR = 'backups'
EXTERNAL_DIR = 'F:/backups'  # Use forward slashes for Windows path

def get_engine():
    return create_engine(DATABASE_URL)

def backup_table(engine, table_name):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"{table_name}_backup.sql")

    with sqlite3.connect(engine.url.database) as conn:
        with open(backup_file, 'w') as f:
            for line in conn.iterdump():
                if line.startswith(f'INSERT INTO "{table_name}"'):
                    f.write(f'{line}\n')

    backup_file_external = os.path.join(EXTERNAL_DIR, f"{table_name}_backup.sql")
    with sqlite3.connect(engine.url.database) as conn:
        with open(backup_file_external, 'w') as f:
            for line in conn.iterdump():
                if line.startswith(f'INSERT INTO "{table_name}"'):
                    f.write(f'{line}\n')

    print(f"Backup for table {table_name} created at {backup_file} and {backup_file_external}")

def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    engine = get_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine)

    for table_name in metadata.tables.keys():
        backup_table(engine, table_name)

schedule.every(1).minutes.do(backup_database)

def restore_table(engine, table_name, backup_file):
    with sqlite3.connect(engine.url.database) as conn:
        cursor = conn.cursor()
        
        # Remove existing data from the table
        cursor.execute(f'DELETE FROM "{table_name}";')
        
        # Restore data from the backup file
        with open(backup_file, 'r') as f:
            sql_script = f.read()
            conn.executescript(sql_script)

    print(f"Data for table {table_name} restored from {backup_file}")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    backup_thread = threading.Thread(target=run_scheduler)
    backup_thread.start()

@app.post("/restore-table/")
async def restore_table_endpoint(table_name: str, backup_file: str):
    engine = get_engine()
    external_backup_file = os.path.join(EXTERNAL_DIR, backup_file)
    if not os.path.exists(external_backup_file):
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    try:
        restore_table(engine, table_name, external_backup_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"message": f"Table {table_name} restored successfully from {backup_file}"}

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
