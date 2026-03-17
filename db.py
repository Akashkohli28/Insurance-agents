import aiosqlite
import sqlite3
import json
import logging
from typing import Dict, Any, List
from logging_config import get_logger

DB_PATH = "insurance.db"
logger = get_logger(__name__)

async def init_db():
    """Initialize the SQLite database with table and initial data."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
        CREATE TABLE IF NOT EXISTS policyholders (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            policy_id TEXT,
            renewal_date TEXT,
            days_remaining INTEGER,
            renewal_status TEXT,
            preferred_channel TEXT,
            history TEXT
        )
        '''):
            pass
        
        async with db.execute("SELECT COUNT(*) FROM policyholders") as cursor:
            row = await cursor.fetchone()
            if row[0] == 0:
                # Initial seed data
                initial_data = [
                    ("PH_EMAIL", "John 30-Day", "sahalshrestha02@gmail.com", "+919718556121", "POL030", "2025-04-01", 30, "PENDING", "EMAIL", "[]"),
                    ("PH_WHATSAPP", "Bob 15-Day", "sahalshrestha02@gmail.com", "+919718556121", "POL015", "2025-03-17", 15, "PENDING", "WHATSAPP", "[]"),
                    ("PH_VOICE", "Jane 7-Day", "jane7@example.com", "+919718556121", "POL007", "2025-03-09", 7, "PENDING", "VOICE", "[]"),
                    ("PH_HITL", "Alice 2-Day", "alice2@example.com", "+919718556121", "POL002", "2025-03-04", 2, "PENDING", "EMAIL", "[]")
                ]
                await db.executemany("INSERT INTO policyholders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", initial_data)
                await db.commit()
                logger.info("Database initialized with seed data.")

async def get_policyholder(ph_id: str) -> Dict[str, Any]:
    """Retrieve policyholder data from SQLite asynchronously."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM policyholders WHERE id = ?", (ph_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['history'] = json.loads(data['history'])
                return data
            return None

async def update_policyholder(ph_id: str, updates: Dict[str, Any]):
    """Update policyholder data in SQLite asynchronously."""
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in updates.items():
            if key == 'history':
                value = json.dumps(value)
            # Use valid columns only
            allowed = ["renewal_status", "history", "days_remaining", "preferred_channel"]
            if key in allowed:
                query = f"UPDATE policyholders SET {key} = ? WHERE id = ?"
                await db.execute(query, (value, ph_id))
        await db.commit()
        logger.info(f"Updated policyholder {ph_id}: {updates}")

async def list_policyholders_async() -> List[Dict[str, Any]]:
    """List all policyholders asynchronously."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM policyholders") as cursor:
            rows = await cursor.fetchall()
            ph_list = []
            for row in rows:
                ph = dict(row)
                ph['history'] = json.loads(ph['history'])
                ph_list.append(ph)
            return ph_list

# Note: We can't easily keep DBProxy for async without changing call sites.
# We will transition call sites in api.py.
