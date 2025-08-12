# app/models.py
import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(__file__), "tv-calc.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        # -------- Channel groups & channels --------
        db.execute("""
        CREATE TABLE IF NOT EXISTS channel_groups (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            size TEXT NOT NULL CHECK(size IN ('big','small')),
            UNIQUE(channel_group_id, name),
            FOREIGN KEY(channel_group_id) REFERENCES channel_groups(id) ON DELETE CASCADE
        )""")

        # -------- TRP rates (legacy admin) --------
        db.execute("""
        CREATE TABLE IF NOT EXISTS trp_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            target_group TEXT NOT NULL,
            primary_label TEXT NOT NULL,
            secondary_label TEXT,
            share_primary REAL,
            share_secondary REAL,
            prime_share_primary REAL,
            prime_share_secondary REAL,
            price_per_sec_eur REAL NOT NULL,
            UNIQUE(owner, target_group)
        )""")

        # -------- Pricing lists (rate cards) --------
        db.execute("""
        CREATE TABLE IF NOT EXISTS pricing_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")
        # Check if we need to migrate the pricing_list_items table to remove unique constraint
        cursor = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pricing_list_items'")
        table_def = cursor.fetchone()
        
        if table_def and 'UNIQUE(pricing_list_id, owner, target_group)' in table_def['sql']:
            # Table has the old unique constraint, need to migrate
            db.execute("ALTER TABLE pricing_list_items RENAME TO pricing_list_items_old")
            
            # Create new table without unique constraint
            db.execute("""
            CREATE TABLE pricing_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pricing_list_id INTEGER NOT NULL,
                owner TEXT NOT NULL,
                target_group TEXT NOT NULL,
                primary_label TEXT NOT NULL,
                secondary_label TEXT,
                share_primary REAL,
                share_secondary REAL,
                prime_share_primary REAL,
                prime_share_secondary REAL,
                price_per_sec_eur REAL NOT NULL,
                FOREIGN KEY(pricing_list_id) REFERENCES pricing_lists(id) ON DELETE CASCADE
            )""")
            
            # Copy data from old table
            db.execute("""
            INSERT INTO pricing_list_items 
            SELECT * FROM pricing_list_items_old
            """)
            
            # Drop old table
            db.execute("DROP TABLE pricing_list_items_old")
        else:
            # Create table without unique constraint if it doesn't exist
            db.execute("""
            CREATE TABLE IF NOT EXISTS pricing_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pricing_list_id INTEGER NOT NULL,
                owner TEXT NOT NULL,
                target_group TEXT NOT NULL,
                primary_label TEXT NOT NULL,
                secondary_label TEXT,
                share_primary REAL,
                share_secondary REAL,
                prime_share_primary REAL,
                prime_share_secondary REAL,
                price_per_sec_eur REAL NOT NULL,
                FOREIGN KEY(pricing_list_id) REFERENCES pricing_lists(id) ON DELETE CASCADE
            )""")

        # -------- Campaigns / Waves --------
        db.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pricing_list_id INTEGER NOT NULL,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'draft',
            FOREIGN KEY(pricing_list_id) REFERENCES pricing_lists(id) ON DELETE RESTRICT
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS waves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS wave_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id INTEGER NOT NULL,
            owner TEXT NOT NULL,
            target_group TEXT NOT NULL,
            primary_label TEXT NOT NULL,
            secondary_label TEXT,
            share_primary REAL,
            share_secondary REAL,
            prime_share_primary REAL,
            prime_share_secondary REAL,
            price_per_sec_eur REAL NOT NULL,
            trps REAL NOT NULL,
            FOREIGN KEY(wave_id) REFERENCES waves(id) ON DELETE CASCADE
        )""")

        db.commit()
        
        # discount table
        
        db.execute("""
        CREATE TABLE IF NOT EXISTS discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            wave_id INTEGER,
            discount_type TEXT CHECK(discount_type IN ('client', 'agency')) NOT NULL,
            discount_percentage REAL NOT NULL,
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY(wave_id) REFERENCES waves(id) ON DELETE CASCADE
        )
        """)
        db.commit()

# ---------------- Channel groups / channels ----------------

def upsert_channel_group(name: str) -> int:
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO channel_groups(name) VALUES (?)", (name,))
        row = db.execute("SELECT id FROM channel_groups WHERE name=?", (name,)).fetchone()
        return row["id"]

def list_channel_groups():
    with get_db() as db:
        rows = db.execute("SELECT id, name FROM channel_groups ORDER BY name").fetchall()
        return [dict(r) for r in rows]

def create_channel(channel_group_id: int, name: str, size: str):
    size = size.lower()
    if size not in ("big","small"):
        raise ValueError("size must be 'big' or 'small'")
    with get_db() as db:
        db.execute("""
            INSERT INTO channels(channel_group_id, name, size)
            VALUES (?,?,?)
        """, (channel_group_id, name, size))

def list_channels(channel_group_id: int | None = None):
    with get_db() as db:
        if channel_group_id:
            rows = db.execute("""
                SELECT c.id, c.name, c.size, c.channel_group_id, g.name AS group_name
                FROM channels c
                JOIN channel_groups g ON g.id=c.channel_group_id
                WHERE c.channel_group_id=?
                ORDER BY (size='big') DESC, c.name
            """, (channel_group_id,)).fetchall()
        else:
            rows = db.execute("""
                SELECT c.id, c.name, c.size, c.channel_group_id, g.name AS group_name
                FROM channels c
                JOIN channel_groups g ON g.id=c.channel_group_id
                ORDER BY g.name, (size='big') DESC, c.name
            """).fetchall()
        return [dict(r) for r in rows]

def update_channel(channel_id: int, *, name: str | None = None, size: str | None = None):
    sets, args = [], []
    if name is not None:
        sets.append("name=?"); args.append(name)
    if size is not None:
        size = size.lower()
        if size not in ("big","small"):
            raise ValueError("size must be 'big' or 'small'")
        sets.append("size=?"); args.append(size)
    if not sets:
        return
    args.append(channel_id)
    with get_db() as db:
        db.execute(f"UPDATE channels SET {', '.join(sets)} WHERE id=?", args)

def delete_channel(channel_id: int):
    with get_db() as db:
        db.execute("DELETE FROM channels WHERE id=?", (channel_id,))

def seed_channel_groups():
    amb_id = upsert_channel_group("AMB Baltics")
    mg_id  = upsert_channel_group("MG grupė")
    existing = { (r["channel_group_id"], r["name"]) for r in list_channels() }
    def ensure(gid, name, size):
        if (gid, name) not in existing:
            create_channel(gid, name, size)
    ensure(amb_id, "TV3", "big")
    ensure(amb_id, "TV6", "small")
    ensure(amb_id, "TV8", "small")
    ensure(amb_id, "TV3 Plus", "small")
    ensure(mg_id, "LNK", "big")

def update_channel_group(group_id: int, name: str):
    if not name or not name.strip():
        raise ValueError("name required")
    with get_db() as db:
        db.execute("UPDATE channel_groups SET name=? WHERE id=?", (name.strip(), group_id))

def delete_channel_group(group_id: int):
    with get_db() as db:
        db.execute("DELETE FROM channel_groups WHERE id=?", (group_id,))

# ---------------- TRP rates (legacy) ----------------

def _norm_number(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    s = s.replace("€", "").replace("%", "").replace(" ", "").replace(",", ".")
    return float(s)

def upsert_trp_rate(**k):
    if not k.get("owner") or not k.get("target_group") or not k.get("primary_label"):
        raise ValueError("owner, target_group, primary_label are required")
    if k.get("price_per_sec_eur") in (None, ""):
        raise ValueError("price_per_sec_eur is required")
    for f in ["share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"]:
        if f in k:
            k[f] = _norm_number(k[f])
    with get_db() as db:
        db.execute("""
            INSERT INTO trp_rates (
                owner, target_group, primary_label, secondary_label,
                share_primary, share_secondary, prime_share_primary, prime_share_secondary,
                price_per_sec_eur
            ) VALUES (
                :owner, :target_group, :primary_label, :secondary_label,
                :share_primary, :share_secondary, :prime_share_primary, :prime_share_secondary,
                :price_per_sec_eur
            )
            ON CONFLICT(owner, target_group) DO UPDATE SET
                primary_label=excluded.primary_label,
                secondary_label=excluded.secondary_label,
                share_primary=excluded.share_primary,
                share_secondary=excluded.share_secondary,
                prime_share_primary=excluded.prime_share_primary,
                prime_share_secondary=excluded.prime_share_secondary,
                price_per_sec_eur=excluded.price_per_sec_eur
        """, k)

def list_trp_rates(owner=None):
    with get_db() as db:
        if owner:
            rows = db.execute("SELECT * FROM trp_rates WHERE owner=? ORDER BY target_group", (owner,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM trp_rates ORDER BY owner, target_group").fetchall()
    return [dict(r) for r in rows]

def update_trp_rate_by_id(row_id, data: dict):
    if not data:
        return
    to_update = {}
    for key in ["owner","target_group","primary_label","secondary_label",
                "share_primary","share_secondary","prime_share_primary","prime_share_secondary",
                "price_per_sec_eur"]:
        if key in data:
            val = data[key]
            if key in {"share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"}:
                val = _norm_number(val)
            to_update[key] = val
    if not to_update:
        return
    sets = ", ".join([f"{k}=?" for k in to_update.keys()])
    args = list(to_update.values()) + [row_id]
    with get_db() as db:
        db.execute(f"UPDATE trp_rates SET {sets} WHERE id=?", args)

def delete_trp_rate(row_id: int):
    with get_db() as db:
        db.execute("DELETE FROM trp_rates WHERE id=?", (row_id,))

# ---------------- Pricing lists (rate cards) ----------------

def create_pricing_list(name: str) -> int:
    with get_db() as db:
        db.execute("INSERT INTO pricing_lists(name) VALUES (?)", (name,))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def list_pricing_lists():
    with get_db() as db:
        rows = db.execute("SELECT id, name FROM pricing_lists ORDER BY name").fetchall()
        return [dict(r) for r in rows]

def update_pricing_list(pl_id: int, name: str):
    with get_db() as db:
        db.execute("UPDATE pricing_lists SET name=? WHERE id=?", (name, pl_id))

def delete_pricing_list(pl_id: int):
    with get_db() as db:
        db.execute("DELETE FROM pricing_lists WHERE id=?", (pl_id,))

def upsert_pricing_list_item(**k):
    # expects: pricing_list_id, owner, target_group, primary_label, secondary_label,
    # shares, primes, price_per_sec_eur
    for f in ["share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"]:
        if f in k:
            k[f] = _norm_number(k[f])
    with get_db() as db:
        db.execute("""
        INSERT INTO pricing_list_items (
            pricing_list_id, owner, target_group, primary_label, secondary_label,
            share_primary, share_secondary, prime_share_primary, prime_share_secondary, price_per_sec_eur
        ) VALUES (
            :pricing_list_id, :owner, :target_group, :primary_label, :secondary_label,
            :share_primary, :share_secondary, :prime_share_primary, :prime_share_secondary, :price_per_sec_eur
        )
        ON CONFLICT(pricing_list_id, owner, target_group) DO UPDATE SET
            primary_label=excluded.primary_label,
            secondary_label=excluded.secondary_label,
            share_primary=excluded.share_primary,
            share_secondary=excluded.share_secondary,
            prime_share_primary=excluded.prime_share_primary,
            prime_share_secondary=excluded.prime_share_secondary,
            price_per_sec_eur=excluded.price_per_sec_eur
        """, k)

def list_pricing_list_items(pl_id: int):
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM pricing_list_items
            WHERE pricing_list_id=?
            ORDER BY owner, target_group
        """, (pl_id,)).fetchall()
        return [dict(r) for r in rows]

def create_pricing_list_item(**k):
    # Create a new pricing list item (always INSERT, never UPDATE)
    for f in ["share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"]:
        if f in k:
            k[f] = _norm_number(k[f])
    with get_db() as db:
        cursor = db.execute("""
        INSERT INTO pricing_list_items (
            pricing_list_id, owner, target_group, primary_label, secondary_label,
            share_primary, share_secondary, prime_share_primary, prime_share_secondary, price_per_sec_eur
        ) VALUES (
            :pricing_list_id, :owner, :target_group, :primary_label, :secondary_label,
            :share_primary, :share_secondary, :prime_share_primary, :prime_share_secondary, :price_per_sec_eur
        )
        """, k)
        return cursor.lastrowid

def delete_pricing_list_item(item_id: int):
    with get_db() as db:
        db.execute("DELETE FROM pricing_list_items WHERE id=?", (item_id,))

def update_pricing_list_item(item_id: int, data: dict):
    # Convert channel_group_id to owner if present
    if 'channel_group_id' in data:
        data['owner'] = str(data['channel_group_id'])
        del data['channel_group_id']
    
    # Normalize numeric fields
    for f in ["share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"]:
        if f in data:
            data[f] = _norm_number(data[f])
    
    # Build UPDATE statement dynamically
    fields = []
    values = []
    for key, value in data.items():
        if key not in ['id', 'pricing_list_id']:  # Don't update these fields
            fields.append(f"{key}=?")
            values.append(value)
    
    if not fields:
        return  # Nothing to update
    
    values.append(item_id)  # Add item_id for WHERE clause
    
    with get_db() as db:
        db.execute(f"UPDATE pricing_list_items SET {','.join(fields)} WHERE id=?", values)

def get_pricing_item(pl_id: int, owner: str, target_group: str):
    with get_db() as db:
        row = db.execute("""
            SELECT * FROM pricing_list_items
            WHERE pricing_list_id=? AND owner=? AND target_group=?
        """, (pl_id, owner, target_group)).fetchone()
        return dict(row) if row else None

def list_pricing_owners(pl_id: int):
    with get_db() as db:
        rows = db.execute("""
            SELECT DISTINCT owner FROM pricing_list_items
            WHERE pricing_list_id=? ORDER BY owner
        """, (pl_id,)).fetchall()
        return [r["owner"] for r in rows]

def list_pricing_targets(pl_id: int, owner: str):
    with get_db() as db:
        rows = db.execute("""
            SELECT target_group FROM pricing_list_items
            WHERE pricing_list_id=? AND owner=? ORDER BY target_group
        """, (pl_id, owner)).fetchall()
        return [r["target_group"] for r in rows]

# ---------------- Campaigns / Waves ----------------

def create_campaign(name: str, pricing_list_id: int, start_date: str | None, end_date: str | None, status: str = "draft") -> int:
    with get_db() as db:
        db.execute("""
            INSERT INTO campaigns(name, pricing_list_id, start_date, end_date, status)
            VALUES (?,?,?,?,?)
        """, (name, pricing_list_id, start_date, end_date, status))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def list_campaigns():
    with get_db() as db:
        rows = db.execute("""
            SELECT c.*, p.name AS pricing_list_name
            FROM campaigns c
            JOIN pricing_lists p ON p.id=c.pricing_list_id
            ORDER BY c.id DESC
        """).fetchall()
        return [dict(r) for r in rows]

def update_campaign(cid: int, data: dict):
    sets, args = [], []
    for k in ["name","pricing_list_id","start_date","end_date","status"]:
        if k in data:
            sets.append(f"{k}=?"); args.append(data[k])
    if not sets:
        return
    args.append(cid)
    with get_db() as db:
        db.execute(f"UPDATE campaigns SET {', '.join(sets)} WHERE id=?", args)

def delete_campaign(cid: int):
    with get_db() as db:
        db.execute("DELETE FROM campaigns WHERE id=?", (cid,))

def create_wave(campaign_id: int, name: str | None, start_date: str | None, end_date: str | None) -> int:
    with get_db() as db:
        db.execute("""
            INSERT INTO waves(campaign_id, name, start_date, end_date)
            VALUES (?,?,?,?)
        """, (campaign_id, name, start_date, end_date))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def list_waves(campaign_id: int):
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM waves WHERE campaign_id=? ORDER BY id
        """, (campaign_id,)).fetchall()
        return [dict(r) for r in rows]

def update_wave(wid: int, data: dict):
    sets, args = [], []
    for k in ["name","start_date","end_date"]:
        if k in data:
            sets.append(f"{k}=?"); args.append(data[k])
    if not sets:
        return
    args.append(wid)
    with get_db() as db:
        db.execute(f"UPDATE waves SET {', '.join(sets)} WHERE id=?", args)

def delete_wave(wid: int):
    with get_db() as db:
        db.execute("DELETE FROM waves WHERE id=?", (wid,))

def _pricing_list_id_for_wave(wave_id: int) -> int | None:
    with get_db() as db:
        row = db.execute("""
            SELECT c.pricing_list_id
            FROM waves w
            JOIN campaigns c ON c.id=w.campaign_id
            WHERE w.id=?
        """, (wave_id,)).fetchone()
        return row["pricing_list_id"] if row else None

def list_wave_items(wave_id: int):
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM wave_items WHERE wave_id=? ORDER BY id
        """, (wave_id,)).fetchall()
        return [dict(r) for r in rows]

def create_wave_item_prefill(wave_id: int, owner: str, target_group: str, trps: float) -> int:
    pl_id = _pricing_list_id_for_wave(wave_id)
    if not pl_id:
        raise ValueError("Pricing list not found for wave")
    rate = get_pricing_item(pl_id, owner, target_group)
    if not rate:
        raise ValueError("Rate not found in pricing list for given owner/target_group")
    with get_db() as db:
        db.execute("""
            INSERT INTO wave_items(
                wave_id, owner, target_group, primary_label, secondary_label,
                share_primary, share_secondary, prime_share_primary, prime_share_secondary,
                price_per_sec_eur, trps
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            wave_id, owner, target_group, rate["primary_label"], rate["secondary_label"],
            rate["share_primary"], rate["share_secondary"], rate["prime_share_primary"], rate["prime_share_secondary"],
            rate["price_per_sec_eur"], _norm_number(trps)
        ))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def update_wave_item(item_id: int, data: dict):
    # allow overriding any snapped values
    numeric = {"share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur","trps"}
    sets, args = [], []
    for k in ["owner","target_group","primary_label","secondary_label",
              "share_primary","share_secondary","prime_share_primary","prime_share_secondary",
              "price_per_sec_eur","trps"]:
        if k in data:
            v = _norm_number(data[k]) if k in numeric else data[k]
            sets.append(f"{k}=?"); args.append(v)
    if not sets:
        return
    args.append(item_id)
    with get_db() as db:
        db.execute(f"UPDATE wave_items SET {', '.join(sets)} WHERE id=?", args)

def delete_wave_item(item_id: int):
    with get_db() as db:
        db.execute("DELETE FROM wave_items WHERE id=?", (item_id,))

# ---------------- Discounts ----------------

def create_discount(campaign_id: int = None, wave_id: int = None, discount_type: str = "client", discount_percentage: float = 0.0):
    """Create a discount for a campaign or wave"""
    if not campaign_id and not wave_id:
        raise ValueError("Either campaign_id or wave_id must be provided")
    if discount_type not in ['client', 'agency']:
        raise ValueError("discount_type must be 'client' or 'agency'")
    
    with get_db() as db:
        cursor = db.execute("""
        INSERT INTO discounts (campaign_id, wave_id, discount_type, discount_percentage)
        VALUES (?, ?, ?, ?)
        """, (campaign_id, wave_id, discount_type, discount_percentage))
        return cursor.lastrowid

def get_discounts_for_campaign(campaign_id: int):
    """Get all discounts for a campaign (both campaign-level and wave-level)"""
    with get_db() as db:
        rows = db.execute("""
        SELECT d.*, w.name as wave_name 
        FROM discounts d
        LEFT JOIN waves w ON d.wave_id = w.id
        WHERE d.campaign_id = ? OR d.wave_id IN (
            SELECT id FROM waves WHERE campaign_id = ?
        )
        ORDER BY d.discount_type, d.wave_id
        """, (campaign_id, campaign_id)).fetchall()
        return [dict(r) for r in rows]

def get_discounts_for_wave(wave_id: int):
    """Get all discounts for a specific wave"""
    with get_db() as db:
        rows = db.execute("""
        SELECT * FROM discounts WHERE wave_id = ?
        ORDER BY discount_type
        """, (wave_id,)).fetchall()
        return [dict(r) for r in rows]

def update_discount(discount_id: int, discount_percentage: float):
    """Update discount percentage"""
    with get_db() as db:
        db.execute("UPDATE discounts SET discount_percentage = ? WHERE id = ?", 
                  (discount_percentage, discount_id))

def delete_discount(discount_id: int):
    """Delete a discount"""
    with get_db() as db:
        db.execute("DELETE FROM discounts WHERE id = ?", (discount_id,))

def calculate_wave_total_with_discounts(wave_id: int):
    """Calculate wave total cost with discounts applied"""
    with get_db() as db:
        # Get base cost from wave items
        items = db.execute("""
        SELECT price_per_sec_eur, trps FROM wave_items WHERE wave_id = ?
        """, (wave_id,)).fetchall()
        
        base_cost = sum(item['price_per_sec_eur'] * item['trps'] for item in items)
        
        # Get discounts for this wave
        discounts = get_discounts_for_wave(wave_id)
        
        client_discount = 0
        agency_discount = 0
        
        for discount in discounts:
            if discount['discount_type'] == 'client':
                client_discount = max(client_discount, discount['discount_percentage'])
            elif discount['discount_type'] == 'agency':
                agency_discount = max(agency_discount, discount['discount_percentage'])
        
        # Apply discounts sequentially
        client_cost = base_cost * (1 - client_discount / 100)
        agency_cost = client_cost * (1 - agency_discount / 100)
        
        return {
            'base_cost': base_cost,
            'client_cost': client_cost,
            'agency_cost': agency_cost,
            'client_discount_percent': client_discount,
            'agency_discount_percent': agency_discount
        }

# ---------------- Campaign Status ----------------

def update_campaign_status(campaign_id: int, status: str):
    """Update campaign status"""
    valid_statuses = ['draft', 'confirmed', 'orders_sent', 'active', 'completed']
    if status not in valid_statuses:
        raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
    
    with get_db() as db:
        db.execute("UPDATE campaigns SET status = ? WHERE id = ?", (status, campaign_id))

def get_campaign_status(campaign_id: int):
    """Get campaign status"""
    with get_db() as db:
        row = db.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        return row['status'] if row else None

# ---------------- Report Generation ----------------

def get_campaign_report_data(campaign_id: int):
    """Get all data needed for campaign reports"""
    with get_db() as db:
        # Get campaign info
        campaign = db.execute("""
        SELECT c.*, pl.name as pricing_list_name 
        FROM campaigns c
        JOIN pricing_lists pl ON c.pricing_list_id = pl.id
        WHERE c.id = ?
        """, (campaign_id,)).fetchone()
        
        if not campaign:
            return None
        
        # Get waves with items and costs
        waves_data = []
        waves = db.execute("SELECT * FROM waves WHERE campaign_id = ? ORDER BY start_date, name", (campaign_id,)).fetchall()
        
        for wave in waves:
            wave_dict = dict(wave)
            
            # Get wave items
            items = db.execute("""
            SELECT * FROM wave_items WHERE wave_id = ? ORDER BY owner, target_group
            """, (wave['id'],)).fetchall()
            wave_dict['items'] = [dict(item) for item in items]
            
            # Get wave costs with discounts
            wave_dict['costs'] = calculate_wave_total_with_discounts(wave['id'])
            
            # Get discounts
            discounts = get_discounts_for_wave(wave['id'])
            wave_dict['discounts'] = discounts
            
            waves_data.append(wave_dict)
        
        return {
            'campaign': dict(campaign),
            'waves': waves_data
        }

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
import csv
import io

def generate_client_excel_report(campaign_id: int):
    """Generate Excel report for client (with client discounts applied)"""
    data = get_campaign_report_data(campaign_id)
    if not data:
        return None
    
    campaign = data['campaign']
    waves = data['waves']
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Campaign_{campaign['name']}_Client"
    
    # Styles
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    wave_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    wave_font = Font(bold=True)
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                   top=Side(style='thin'), bottom=Side(style='thin'))
    
    current_row = 1
    
    # Campaign header
    ws.merge_cells(f'A{current_row}:H{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = f"TV PLANAS - {campaign['name']}"
    cell.font = Font(size=16, bold=True)
    cell.alignment = Alignment(horizontal='center')
    current_row += 2
    
    # Campaign details
    ws[f'A{current_row}'] = "Laikotarpis:"
    ws[f'B{current_row}'] = f"{campaign.get('start_date', '')} - {campaign.get('end_date', '')}"
    current_row += 1
    
    ws[f'A{current_row}'] = "Kainoraštis:"
    ws[f'B{current_row}'] = campaign.get('pricing_list_name', '')
    current_row += 1
    
    ws[f'A{current_row}'] = "Statusas:"
    ws[f'B{current_row}'] = campaign.get('status', 'draft').replace('_', ' ').title()
    current_row += 2
    
    # Table headers
    headers = ['Banga', 'Laikotarpis', 'Savininkas', 'Tikslinė grupė', 'Kanalas', 'TRP', '€/sek', 'Viso €']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=current_row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border
    
    current_row += 1
    
    # Data rows
    total_cost = 0
    for wave in waves:
        wave_start_row = current_row
        
        for item in wave['items']:
            item_cost = item['trps'] * item['price_per_sec_eur']
            
            ws.cell(row=current_row, column=1).value = wave['name'] or f"Banga {wave['id']}"
            ws.cell(row=current_row, column=2).value = f"{wave.get('start_date', '')} - {wave.get('end_date', '')}"
            ws.cell(row=current_row, column=3).value = item['owner']
            ws.cell(row=current_row, column=4).value = item['target_group']
            ws.cell(row=current_row, column=5).value = f"{item['primary_label']}{' + ' + item['secondary_label'] if item['secondary_label'] else ''}"
            ws.cell(row=current_row, column=6).value = item['trps']
            ws.cell(row=current_row, column=7).value = round(item['price_per_sec_eur'], 2)
            ws.cell(row=current_row, column=8).value = round(item_cost, 2)
            
            # Apply borders
            for col in range(1, 9):
                ws.cell(row=current_row, column=col).border = border
            
            current_row += 1
        
        # Wave summary with client discount
        if wave['items']:
            costs = wave['costs']
            client_cost = costs['client_cost']
            total_cost += client_cost
            
            ws.merge_cells(f'A{current_row}:G{current_row}')
            cell = ws[f'A{current_row}']
            discount_text = f" (-{costs['client_discount_percent']}%)" if costs['client_discount_percent'] > 0 else ""
            cell.value = f"Bangos suma{discount_text}:"
            cell.font = wave_font
            cell.fill = wave_fill
            cell.alignment = Alignment(horizontal='right')
            
            ws.cell(row=current_row, column=8).value = round(client_cost, 2)
            ws.cell(row=current_row, column=8).font = wave_font
            ws.cell(row=current_row, column=8).fill = wave_fill
            
            for col in range(1, 9):
                ws.cell(row=current_row, column=col).border = border
            
            current_row += 2
    
    # Grand total
    ws.merge_cells(f'A{current_row}:G{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = "BENDRA SUMA:"
    cell.font = Font(bold=True, size=14)
    cell.alignment = Alignment(horizontal='right')
    
    ws.cell(row=current_row, column=8).value = round(total_cost, 2)
    ws.cell(row=current_row, column=8).font = Font(bold=True, size=14)
    
    # Adjust column widths
    column_widths = [15, 20, 15, 20, 30, 10, 10, 12]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_agency_csv_order(campaign_id: int):
    """Generate CSV order file for agency (with both client and agency discounts)"""
    data = get_campaign_report_data(campaign_id)
    if not data:
        return None
    
    campaign = data['campaign']
    waves = data['waves']
    
    csv_content = []
    csv_content.append(['# TV UŽSAKYMAS'])
    csv_content.append(['Kampanija', campaign['name']])
    csv_content.append(['Laikotarpis', f"{campaign.get('start_date', '')} - {campaign.get('end_date', '')}"])
    csv_content.append(['Kainoraštis', campaign.get('pricing_list_name', '')])
    csv_content.append(['Statusas', campaign.get('status', 'draft')])
    csv_content.append([])  # Empty row
    
    # Headers
    csv_content.append([
        'Banga', 'Laikotarpis', 'Savininkas', 'Tikslinė grupė', 'Kanalas', 
        'TRP', 'Bazinė kaina €/sek', 'Kliento kaina €/sek', 'Agentūros kaina €/sek', 
        'Kliento nuolaida %', 'Agentūros nuolaida %', 'Galutinė suma €'
    ])
    
    total_agency_cost = 0
    
    for wave in waves:
        costs = wave['costs']
        
        for item in wave['items']:
            base_price = item['price_per_sec_eur']
            trps = item['trps']
            
            # Calculate discounted prices per second
            client_discount_percent = costs['client_discount_percent']
            agency_discount_percent = costs['agency_discount_percent']
            
            client_price_per_sec = base_price * (1 - client_discount_percent / 100)
            agency_price_per_sec = client_price_per_sec * (1 - agency_discount_percent / 100)
            
            final_cost = agency_price_per_sec * trps
            total_agency_cost += final_cost
            
            csv_content.append([
                wave['name'] or f"Banga {wave['id']}",
                f"{wave.get('start_date', '')} - {wave.get('end_date', '')}",
                item['owner'],
                item['target_group'],
                f"{item['primary_label']}{' + ' + item['secondary_label'] if item['secondary_label'] else ''}",
                trps,
                round(base_price, 4),
                round(client_price_per_sec, 4),
                round(agency_price_per_sec, 4),
                client_discount_percent,
                agency_discount_percent,
                round(final_cost, 2)
            ])
    
    # Total
    csv_content.append([])
    csv_content.append(['BENDRA AGENTŪROS SUMA €', '', '', '', '', '', '', '', '', '', '', round(total_agency_cost, 2)])
    
    # Write CSV
    import csv as csv_module
    from io import StringIO
    
    # First write to string
    string_buffer = StringIO()
    writer = csv_module.writer(string_buffer, delimiter=';', lineterminator='\n')
    
    for row in csv_content:
        writer.writerow(row)
    
    # Convert to bytes with UTF-8 BOM
    csv_string = string_buffer.getvalue()
    output = BytesIO()
    output.write('\ufeff'.encode('utf-8'))  # BOM
    output.write(csv_string.encode('utf-8'))
    output.seek(0)
    
    return output
