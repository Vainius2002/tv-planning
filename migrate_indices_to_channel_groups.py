#!/usr/bin/env python3
"""
Migration script to change indices from target_group to channel_group basis
This will significantly reduce duplication and make management easier
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app/tv-calc.db")

def migrate_indices_to_channel_groups():
    """Migrate indices tables to use channel_group instead of target_group"""
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # 1. Create new tables with channel_group structure
        print("Creating new indices tables with channel_group...")
        
        # Duration indices by channel group
        conn.execute("""
        CREATE TABLE IF NOT EXISTS duration_indices_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_group_id INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(channel_group_id, duration_seconds),
            FOREIGN KEY(channel_group_id) REFERENCES channel_groups(id) ON DELETE CASCADE
        )""")
        
        # Seasonal indices by channel group  
        conn.execute("""
        CREATE TABLE IF NOT EXISTS seasonal_indices_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_group_id INTEGER NOT NULL,
            month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(channel_group_id, month),
            FOREIGN KEY(channel_group_id) REFERENCES channel_groups(id) ON DELETE CASCADE
        )""")
        
        # Position indices by channel group
        conn.execute("""
        CREATE TABLE IF NOT EXISTS position_indices_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_group_id INTEGER NOT NULL,
            position_type TEXT NOT NULL,
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(channel_group_id, position_type),
            FOREIGN KEY(channel_group_id) REFERENCES channel_groups(id) ON DELETE CASCADE
        )""")
        
        # 2. Get channel groups
        channel_groups = conn.execute("SELECT id, name FROM channel_groups").fetchall()
        
        if not channel_groups:
            print("No channel groups found. Creating default groups...")
            conn.execute("INSERT INTO channel_groups (name) VALUES ('AMB Baltics')")
            conn.execute("INSERT INTO channel_groups (name) VALUES ('MG grupė')")
            channel_groups = conn.execute("SELECT id, name FROM channel_groups").fetchall()
        
        # 3. Migrate duration indices (use most common values)
        print("Migrating duration indices...")
        
        # Get distinct duration ranges with their most common index values
        duration_data = conn.execute("""
            SELECT duration_seconds, index_value, COUNT(*) as count
            FROM duration_indices
            GROUP BY duration_seconds, index_value
            ORDER BY duration_seconds, count DESC
        """).fetchall()
        
        # Group by duration and take most common index
        duration_map = {}
        for row in duration_data:
            if row['duration_seconds'] not in duration_map:
                duration_map[row['duration_seconds']] = row['index_value']
        
        # Insert for each channel group
        for cg in channel_groups:
            for duration, index_val in duration_map.items():
                # Determine description based on duration
                if duration <= 9:
                    desc = "5\"-9\""
                elif duration <= 14:
                    desc = "10\"-14\""
                elif duration <= 19:
                    desc = "15\"-19\""
                elif duration <= 24:
                    desc = "20\"-24\""
                elif duration <= 29:
                    desc = "25\"-29\""
                elif duration <= 44:
                    desc = "30\"-44\""
                else:
                    desc = "≥45\""
                    
                conn.execute("""
                    INSERT OR IGNORE INTO duration_indices_new 
                    (channel_group_id, duration_seconds, index_value, description)
                    VALUES (?, ?, ?, ?)
                """, (cg['id'], duration, index_val, f"{desc} ({cg['name']})"))
        
        # 4. Migrate seasonal indices
        print("Migrating seasonal indices...")
        
        # AMB Baltics pattern (from image data)
        amb_seasonal = [
            (1, 0.9, "Sausis"), (2, 0.95, "Vasaris"), (3, 1.5, "Kovas"),
            (4, 1.55, "Balandis"), (5, 1.6, "Gegužė"), (6, 1.55, "Birželis"),
            (7, 1.1, "Liepa"), (8, 1.1, "Rugpjūtis"), (9, 1.65, "Rugsėjis"),
            (10, 1.65, "Spalis"), (11, 1.65, "Lapkritis"), (12, 1.5, "Gruodis")
        ]
        
        # MG grupė pattern (slightly different)
        mg_seasonal = [
            (1, 0.9, "Sausis"), (2, 1.0, "Vasaris"), (3, 1.4, "Kovas"),
            (4, 1.45, "Balandis"), (5, 1.45, "Gegužė"), (6, 1.4, "Birželis"),
            (7, 0.95, "Liepa"), (8, 1.0, "Rugpjūtis"), (9, 1.60, "Rugsėjis"),
            (10, 1.65, "Spalis"), (11, 1.65, "Lapkritis"), (12, 1.5, "Gruodis")
        ]
        
        for cg in channel_groups:
            # Use different patterns for different channel groups
            if 'AMB' in cg['name']:
                pattern = amb_seasonal
            else:
                pattern = mg_seasonal
                
            for month, index_val, desc in pattern:
                conn.execute("""
                    INSERT OR IGNORE INTO seasonal_indices_new 
                    (channel_group_id, month, index_value, description)
                    VALUES (?, ?, ?, ?)
                """, (cg['id'], month, index_val, f"{desc} ({cg['name']})"))
        
        # 5. Migrate position indices
        print("Migrating position indices...")
        
        # AMB Baltics pattern
        amb_position = [
            ("first", 1.45, "Pirma pozicija"),
            ("second", 1.3, "Antra pozicija"),
            ("last", 1.3, "Paskutinė"),
            ("other", 1.2, "Kita spec.")
        ]
        
        # MG grupė pattern
        mg_position = [
            ("first", 1.5, "Pirma pozicija"),
            ("second", 1.4, "Antra pozicija"),
            ("last", 1.4, "Paskutinė"),
            ("other", 1.3, "Kita spec.")
        ]
        
        for cg in channel_groups:
            if 'AMB' in cg['name']:
                pattern = amb_position
            else:
                pattern = mg_position
                
            for pos_type, index_val, desc in pattern:
                conn.execute("""
                    INSERT OR IGNORE INTO position_indices_new 
                    (channel_group_id, position_type, index_value, description)
                    VALUES (?, ?, ?, ?)
                """, (cg['id'], pos_type, index_val, f"{desc} ({cg['name']})"))
        
        # 6. Rename old tables and replace with new ones
        print("Replacing old tables with new ones...")
        
        conn.execute("DROP TABLE IF EXISTS duration_indices_old")
        conn.execute("DROP TABLE IF EXISTS seasonal_indices_old")
        conn.execute("DROP TABLE IF EXISTS position_indices_old")
        
        conn.execute("ALTER TABLE duration_indices RENAME TO duration_indices_old")
        conn.execute("ALTER TABLE seasonal_indices RENAME TO seasonal_indices_old")
        conn.execute("ALTER TABLE position_indices RENAME TO position_indices_old")
        
        conn.execute("ALTER TABLE duration_indices_new RENAME TO duration_indices")
        conn.execute("ALTER TABLE seasonal_indices_new RENAME TO seasonal_indices")
        conn.execute("ALTER TABLE position_indices_new RENAME TO position_indices")
        
        # Commit transaction
        conn.commit()
        print("Migration completed successfully!")
        
        # Show statistics
        stats = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM duration_indices) as duration_count,
                (SELECT COUNT(*) FROM seasonal_indices) as seasonal_count,
                (SELECT COUNT(*) FROM position_indices) as position_count,
                (SELECT COUNT(*) FROM duration_indices_old) as old_duration_count,
                (SELECT COUNT(*) FROM seasonal_indices_old) as old_seasonal_count,
                (SELECT COUNT(*) FROM position_indices_old) as old_position_count
        """).fetchone()
        
        print(f"\nMigration statistics:")
        print(f"Duration indices: {stats['old_duration_count']} -> {stats['duration_count']} records")
        print(f"Seasonal indices: {stats['old_seasonal_count']} -> {stats['seasonal_count']} records")
        print(f"Position indices: {stats['old_position_count']} -> {stats['position_count']} records")
        
        total_old = stats['old_duration_count'] + stats['old_seasonal_count'] + stats['old_position_count']
        total_new = stats['duration_count'] + stats['seasonal_count'] + stats['position_count']
        print(f"Total reduction: {total_old} -> {total_new} records ({100*(1-total_new/total_old):.1f}% reduction)")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_indices_to_channel_groups()