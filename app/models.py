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
        
        # TVC (TV Commercials) table
        db.execute("""
        CREATE TABLE IF NOT EXISTS tvcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            duration INTEGER NOT NULL, -- duration in seconds
            FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
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
            tvc_id INTEGER,
            FOREIGN KEY(wave_id) REFERENCES waves(id) ON DELETE CASCADE,
            FOREIGN KEY(tvc_id) REFERENCES tvcs(id) ON DELETE SET NULL
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

def migrate_add_tvc_id_to_wave_items():
    """Add tvc_id column to wave_items table if it doesn't exist"""
    with get_db() as db:
        # Check if tvc_id column already exists
        cursor = db.execute("PRAGMA table_info(wave_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'tvc_id' not in columns:
            # Add the tvc_id column
            db.execute("ALTER TABLE wave_items ADD COLUMN tvc_id INTEGER")
            db.commit()
            print("Added tvc_id column to wave_items table")

def migrate_add_campaign_fields():
    """Add missing fields to campaigns table"""
    with get_db() as db:
        cursor = db.execute("PRAGMA table_info(campaigns)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            ("agency", "TEXT"),
            ("client", "TEXT"),
            ("product", "TEXT"),
            ("country", "TEXT DEFAULT 'Lietuva'")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                db.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} column to campaigns table")
        
        db.commit()

def migrate_add_wave_item_fields():
    """Add all missing fields from Excel to wave_items table"""
    with get_db() as db:
        cursor = db.execute("PRAGMA table_info(wave_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            ("channel_id", "INTEGER"),
            ("channel_share", "REAL DEFAULT 0.75"),
            ("pt_zone_share", "REAL DEFAULT 0.55"),
            ("clip_duration", "INTEGER DEFAULT 10"),
            ("grp_planned", "REAL"),
            ("affinity1", "REAL"),
            ("affinity2", "REAL"),
            ("affinity3", "REAL"),
            ("gross_cpp_eur", "REAL"),
            ("duration_index", "REAL DEFAULT 1.0"),
            ("seasonal_index", "REAL DEFAULT 1.0"),
            ("trp_purchase_index", "REAL DEFAULT 0.95"),
            ("advance_purchase_index", "REAL DEFAULT 0.95"),
            ("position_index", "REAL DEFAULT 1.0"),
            ("gross_price_eur", "REAL"),
            ("client_discount", "REAL DEFAULT 0"),
            ("net_price_eur", "REAL"),
            ("agency_discount", "REAL DEFAULT 0"),
            ("net_net_price_eur", "REAL"),
            ("tg_size_thousands", "REAL DEFAULT 0"),
            ("tg_share_percent", "REAL DEFAULT 0"),
            ("tg_sample_size", "INTEGER DEFAULT 0"),
            ("daily_trp_distribution", "TEXT")  # JSON string for daily TRP values
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                db.execute(f"ALTER TABLE wave_items ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} column to wave_items table")
        
        db.commit()

def migrate_add_pricing_indices():
    """Add duration and seasonal indices to pricing_list_items"""
    with get_db() as db:
        cursor = db.execute("PRAGMA table_info(pricing_list_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            ("duration_index", "REAL DEFAULT 1.0"),
            ("seasonal_index", "REAL DEFAULT 1.0"),
            ("tg_size_thousands", "REAL DEFAULT 0"),  # TG dydis tūkstančiais
            ("tg_share_percent", "REAL DEFAULT 0"),   # TG dalis procentais 
            ("tg_sample_size", "INTEGER DEFAULT 0")   # TG imties dydis
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                db.execute(f"ALTER TABLE pricing_list_items ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} column to pricing_list_items table")
        
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

def list_all_channels():
    """Get all channels from all groups for campaign forms"""
    return list_channels()

def get_trp_rate_item(owner: str, target_group: str):
    """Get TRP rate item for specific owner and target group"""
    with get_db() as db:
        row = db.execute("""
            SELECT * FROM trp_rates 
            WHERE owner = ? AND target_group = ?
        """, (owner, target_group)).fetchone()
        if row:
            rate = dict(row)
            # Add default TG data since TRP rates don't have these fields
            rate["tg_size_thousands"] = 100.0  # Default TG size
            rate["tg_share_percent"] = 15.0    # Default TG share
            rate["tg_sample_size"] = 500       # Default sample size
            return rate
        return None

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

def create_pricing_list(name: str, auto_import: bool = True) -> int:
    """Create a new pricing list and optionally import TRP rates"""
    with get_db() as db:
        db.execute("INSERT INTO pricing_lists(name) VALUES (?)", (name,))
        list_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        
        if auto_import:
            # Automatically import all TRP rates to the new pricing list
            # Get all TRP rates
            trp_rates = db.execute("SELECT * FROM trp_rates").fetchall()
            
            # Get channel groups mapping (name to ID)
            channel_groups = db.execute("SELECT id, name FROM channel_groups").fetchall()
            group_map = {g["name"]: g["id"] for g in channel_groups}
            
            for rate in trp_rates:
                # Convert owner name to group ID
                owner_id = group_map.get(rate["owner"], rate["owner"])
                
                # Import each TRP rate as pricing list item
                db.execute("""
                    INSERT OR REPLACE INTO pricing_list_items (
                        pricing_list_id, owner, target_group, 
                        primary_label, secondary_label,
                        share_primary, share_secondary, 
                        prime_share_primary, prime_share_secondary,
                        price_per_sec_eur
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    list_id,
                    str(owner_id),  # Store as string for compatibility
                    rate["target_group"],
                    rate["primary_label"],
                    rate["secondary_label"],
                    rate["share_primary"],
                    rate["share_secondary"],
                    rate["prime_share_primary"],
                    rate["prime_share_secondary"],
                    rate["price_per_sec_eur"]
                ))
        
        return list_id

def import_trp_rates_to_pricing_list(pricing_list_id: int):
    """Import all TRP rates into a pricing list"""
    with get_db() as db:
        # Get all TRP rates
        trp_rates = db.execute("SELECT * FROM trp_rates").fetchall()
        
        # Get channel groups mapping (name to ID)
        channel_groups = db.execute("SELECT id, name FROM channel_groups").fetchall()
        group_map = {g["name"]: g["id"] for g in channel_groups}
        
        for rate in trp_rates:
            # Convert owner name to group ID
            owner_id = group_map.get(rate["owner"], rate["owner"])
            
            # Import each TRP rate as pricing list item
            db.execute("""
                INSERT OR REPLACE INTO pricing_list_items (
                    pricing_list_id, owner, target_group, 
                    primary_label, secondary_label,
                    share_primary, share_secondary, 
                    prime_share_primary, prime_share_secondary,
                    price_per_sec_eur
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pricing_list_id,
                str(owner_id),  # Store as string for compatibility
                rate["target_group"],
                rate["primary_label"],
                rate["secondary_label"],
                rate["share_primary"],
                rate["share_secondary"],
                rate["prime_share_primary"],
                rate["prime_share_secondary"],
                rate["price_per_sec_eur"]
            ))

def migrate_trp_rates_to_pricing_list(name: str) -> int:
    """Create a new pricing list and migrate all TRP rates to it"""
    return create_pricing_list(name, auto_import=True)

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

def create_campaign(name: str, start_date: str | None, end_date: str | None, 
                   agency: str = "", client: str = "", product: str = "", 
                   country: str = "Lietuva", status: str = "draft") -> int:
    with get_db() as db:
        db.execute("""
            INSERT INTO campaigns(name, start_date, end_date, 
                                agency, client, product, country, status)
            VALUES (?,?,?,?,?,?,?,?)
        """, (name, start_date, end_date, agency, client, product, country, status))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def list_campaigns():
    with get_db() as db:
        rows = db.execute("""
            SELECT c.*, NULL AS pricing_list_name
            FROM campaigns c
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
        # Delete TRP distribution data first
        delete_trp_distribution(cid)
        # Delete campaign (waves and wave_items will cascade)
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

def create_wave_item_prefill(wave_id: int, owner: str, target_group: str, trps: float, tvc_id: int = None) -> int:
    pl_id = _pricing_list_id_for_wave(wave_id)
    if not pl_id:
        raise ValueError("Pricing list not found for wave")
    rate = get_pricing_item(pl_id, owner, target_group)
    if not rate:
        raise ValueError("Rate not found in pricing list for given owner/target_group")
    
    # Validate TVC belongs to this wave's campaign if provided
    if tvc_id is not None:
        with get_db() as db:
            tvc_check = db.execute("""
            SELECT t.campaign_id, w.campaign_id as wave_campaign_id 
            FROM tvcs t, waves w 
            WHERE t.id = ? AND w.id = ?
            """, (tvc_id, wave_id)).fetchone()
            
            if not tvc_check or tvc_check['campaign_id'] != tvc_check['wave_campaign_id']:
                raise ValueError("TVC doesn't belong to this campaign")
    
    with get_db() as db:
        db.execute("""
            INSERT INTO wave_items(
                wave_id, owner, target_group, primary_label, secondary_label,
                share_primary, share_secondary, prime_share_primary, prime_share_secondary,
                price_per_sec_eur, trps, tvc_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            wave_id, owner, target_group, rate["primary_label"], rate["secondary_label"],
            rate["share_primary"], rate["share_secondary"], rate["prime_share_primary"], rate["prime_share_secondary"],
            rate["price_per_sec_eur"], _norm_number(trps), tvc_id
        ))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def create_wave_item_excel(wave_id: int, excel_data: dict) -> int:
    """Create a wave item with Excel-style data structure"""
        
    # Get pricing info from TRP rates based on channel_group (which is the owner) and target_group
    rate = get_trp_rate_item(excel_data["channel_group"], excel_data["target_group"])
    
    # Calculate derived values
    # GRP Planned = TRP × 100 / affinity1 (correct Excel formula)
    affinity1 = excel_data.get("affinity1")
    if affinity1 and affinity1 != 0:
        grp_planned = excel_data["trps"] * 100 / affinity1
    else:
        grp_planned = 0  # Cannot calculate without valid affinity1
    # CPP = price per second (from rate list, no clip duration multiplication)
    gross_cpp_eur = rate["price_per_sec_eur"] if rate else 1.0
    
    # Get indices from database if available, otherwise use form values
    # Get wave dates for seasonal index calculation
    with get_db() as db:
        wave_data = db.execute("SELECT start_date, end_date FROM waves WHERE id = ?", (wave_id,)).fetchone()
        wave_start_date = wave_data["start_date"] if wave_data else None
        wave_end_date = wave_data["end_date"] if wave_data else None
    
    # Get indices from database using channel group and wave date range
    db_indices = get_indices_for_wave_item(excel_data["channel_group"], excel_data["clip_duration"], wave_start_date, wave_end_date)
    
    # Use database indices if available, otherwise fall back to form values
    duration_index = db_indices.get("duration_index", excel_data.get("duration_index", 1.25))
    seasonal_index = db_indices.get("seasonal_index", excel_data.get("seasonal_index", 0.9))
    
    # Calculate gross price with all indices and clip duration
    gross_price_eur = (excel_data["trps"] * gross_cpp_eur * excel_data["clip_duration"] *
                      duration_index * seasonal_index * 
                      excel_data["trp_purchase_index"] * excel_data["advance_purchase_index"] * 
                      excel_data["position_index"])
    
    # Calculate net prices
    net_price_eur = gross_price_eur * (1 - excel_data["client_discount"] / 100)
    net_net_price_eur = net_price_eur * (1 - excel_data["agency_discount"] / 100)
    
    with get_db() as db:
        db.execute("""
            INSERT INTO wave_items(
                wave_id, target_group, trps, channel_id, channel_share, pt_zone_share, clip_duration, tvc_id,
                grp_planned, affinity1, affinity2, affinity3, gross_cpp_eur, duration_index,
                seasonal_index, trp_purchase_index, advance_purchase_index, position_index,
                gross_price_eur, client_discount, net_price_eur, agency_discount, net_net_price_eur,
                tg_size_thousands, tg_share_percent, tg_sample_size,
                owner, primary_label, secondary_label, share_primary, share_secondary,
                prime_share_primary, prime_share_secondary, price_per_sec_eur
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            wave_id, excel_data["target_group"], _norm_number(excel_data["trps"]), None,  # channel_id set to None since we use channel_group
            excel_data["channel_share"], excel_data["pt_zone_share"], excel_data["clip_duration"], 
            excel_data.get("tvc_id"),  # TVC ID from form
            grp_planned, excel_data.get("affinity1"), excel_data.get("affinity2"), excel_data.get("affinity3"),
            gross_cpp_eur, duration_index, seasonal_index,
            excel_data["trp_purchase_index"], excel_data["advance_purchase_index"], excel_data["position_index"],
            gross_price_eur, excel_data["client_discount"], net_price_eur, 
            excel_data["agency_discount"], net_net_price_eur,
            # TG data from Excel/form, fallback to TRP rates, then defaults
            excel_data.get("tg_size_thousands") or (rate.get("tg_size_thousands", 0) if rate else 0),
            excel_data.get("tg_share_percent") or (rate.get("tg_share_percent", 0) if rate else 0), 
            excel_data.get("tg_sample_size") or (rate.get("tg_sample_size", 0) if rate else 0),
            # Use channel_group as owner
            excel_data["channel_group"], 
            rate["primary_label"] if rate else "N/A",
            rate["secondary_label"] if rate else None,
            rate["share_primary"] if rate else 0,
            rate["share_secondary"] if rate else 0,
            rate["prime_share_primary"] if rate else 0,
            rate["prime_share_secondary"] if rate else 0,
            rate["price_per_sec_eur"] if rate else gross_cpp_eur
        ))
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

def update_wave_item(item_id: int, data: dict):
    print(f"DEBUG: update_wave_item called with item_id={item_id}, data={data}")
    # allow overriding any snapped values including discounts and Excel structure fields
    numeric = {"share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur","trps","client_discount","agency_discount",
               "channel_share","pt_zone_share","clip_duration","affinity1","affinity2","affinity3",
               "duration_index","seasonal_index","trp_purchase_index","advance_purchase_index","position_index"}
    sets, args = [], []
    for k in ["owner","target_group","primary_label","secondary_label",
              "share_primary","share_secondary","prime_share_primary","prime_share_secondary",
              "price_per_sec_eur","trps","client_discount","agency_discount",
              "channel_share","pt_zone_share","clip_duration","affinity1","affinity2","affinity3",
              "duration_index","seasonal_index","trp_purchase_index","advance_purchase_index","position_index"]:
        if k in data:
            v = _norm_number(data[k]) if k in numeric else data[k]
            sets.append(f"{k}=?"); args.append(v)
    
    # Recalculate prices and GRP if relevant fields were updated
    need_price_recalc = any(field in data for field in ["client_discount", "agency_discount", "trps", "clip_duration", "trp_purchase_index", "advance_purchase_index", "position_index", "duration_index", "seasonal_index"])
    need_grp_recalc = any(field in data for field in ["trps", "affinity1"])
    
    if need_price_recalc or need_grp_recalc:
        with get_db() as db:
            # Get current item data
            item = db.execute("SELECT * FROM wave_items WHERE id = ?", (item_id,)).fetchone()
            if item:
                # Get updated values or use existing ones (SQLite Row uses [] not .get())
                trps = data.get("trps", item["trps"] or 0)
                gross_cpp = item["gross_cpp_eur"] or 0
                
                # Get updated indices or use existing ones
                duration_index = data.get("duration_index", item["duration_index"] or 1.0)
                seasonal_index = data.get("seasonal_index", item["seasonal_index"] or 1.0)
                trp_purchase_index = data.get("trp_purchase_index", item["trp_purchase_index"] or 0.95)
                advance_purchase_index = data.get("advance_purchase_index", item["advance_purchase_index"] or 0.95)
                position_index = data.get("position_index", item["position_index"] or 1.0)
                
                # Recalculate gross price with all indices and clip duration
                clip_duration = data.get("clip_duration", item["clip_duration"] or 10)
                gross_price = (trps * gross_cpp * clip_duration * duration_index * seasonal_index * 
                             trp_purchase_index * advance_purchase_index * position_index)
                
                # Get discounts
                client_discount = data.get("client_discount", item["client_discount"] or 0)
                agency_discount = data.get("agency_discount", item["agency_discount"] or 0)
                
                # Calculate net prices
                net_price = gross_price * (1 - client_discount / 100)
                net_net_price = net_price * (1 - agency_discount / 100)
                
                # Recalculate GRP if needed
                if need_grp_recalc:
                    updated_trps = data.get("trps", item["trps"] or 0)
                    updated_affinity1 = data.get("affinity1", item["affinity1"])
                    
                    if updated_affinity1 and updated_affinity1 != 0:
                        grp_planned = updated_trps * 100 / updated_affinity1
                    else:
                        grp_planned = 0
                    
                    sets.append("grp_planned=?"); args.append(grp_planned)
                
                # Add price updates to sets
                sets.append("gross_price_eur=?"); args.append(gross_price)
                sets.append("net_price_eur=?"); args.append(net_price)
                sets.append("net_net_price_eur=?"); args.append(net_net_price)
    
    if not sets:
        print(f"DEBUG: No fields to update for item_id={item_id}")
        return
        
    args.append(item_id)
    sql = f"UPDATE wave_items SET {', '.join(sets)} WHERE id=?"
    print(f"DEBUG: Executing SQL: {sql} with args: {args}")
    
    with get_db() as db:
        db.execute(sql, args)
        print(f"DEBUG: Update completed for item_id={item_id}")

def delete_wave_item(item_id: int):
    with get_db() as db:
        db.execute("DELETE FROM wave_items WHERE id=?", (item_id,))

def recalculate_wave_item_prices_with_discounts(wave_id: int):
    """Recalculate all wave item prices using wave-level discounts"""
    with get_db() as db:
        # Get wave-level discounts
        discounts = db.execute("""
            SELECT discount_type, discount_percentage 
            FROM discounts 
            WHERE wave_id = ?
        """, (wave_id,)).fetchall()
        
        client_discount = 0
        agency_discount = 0
        
        for discount in discounts:
            if discount["discount_type"] == "client":
                client_discount = discount["discount_percentage"]
            elif discount["discount_type"] == "agency":
                agency_discount = discount["discount_percentage"]
        
        # Get all wave items for this wave
        items = db.execute("SELECT * FROM wave_items WHERE wave_id = ?", (wave_id,)).fetchall()
        
        for item in items:
            # Recalculate prices with wave-level discounts
            gross_price = item["gross_price_eur"] or 0
            net_price = gross_price * (1 - client_discount / 100)
            net_net_price = net_price * (1 - agency_discount / 100)
            
            # Update the item with new calculated prices and discounts
            db.execute("""
                UPDATE wave_items 
                SET client_discount = ?, agency_discount = ?, 
                    net_price_eur = ?, net_net_price_eur = ?
                WHERE id = ?
            """, (client_discount, agency_discount, net_price, net_net_price, item["id"]))
        
        db.commit()

# ---------------- TVCs (TV Commercials) ----------------

def create_tvc(campaign_id: int, name: str, duration: int):
    """Create a new TVC for a campaign"""
    if not name.strip():
        raise ValueError("TVC name is required")
    if duration <= 0:
        raise ValueError("Duration must be positive")
    
    with get_db() as db:
        cursor = db.execute("""
        INSERT INTO tvcs (campaign_id, name, duration)
        VALUES (?, ?, ?)
        """, (campaign_id, name.strip(), duration))
        return cursor.lastrowid

def list_campaign_tvcs(campaign_id: int):
    """Get all TVCs for a campaign"""
    with get_db() as db:
        rows = db.execute("""
        SELECT * FROM tvcs WHERE campaign_id = ? ORDER BY name
        """, (campaign_id,)).fetchall()
        return [dict(r) for r in rows]

def update_tvc(tvc_id: int, name: str = None, duration: int = None):
    """Update TVC name and/or duration"""
    updates = []
    values = []
    
    if name is not None:
        if not name.strip():
            raise ValueError("TVC name cannot be empty")
        updates.append("name = ?")
        values.append(name.strip())
    
    if duration is not None:
        if duration <= 0:
            raise ValueError("Duration must be positive")
        updates.append("duration = ?")
        values.append(duration)
    
    if not updates:
        return
    
    values.append(tvc_id)
    
    with get_db() as db:
        db.execute(f"UPDATE tvcs SET {', '.join(updates)} WHERE id = ?", values)

def delete_tvc(tvc_id: int):
    """Delete a TVC"""
    with get_db() as db:
        db.execute("DELETE FROM tvcs WHERE id = ?", (tvc_id,))

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
        # Get campaign info (pricing_list_id might be NULL, so use LEFT JOIN)
        campaign = db.execute("""
        SELECT c.*, COALESCE(pl.name, 'Default') as pricing_list_name 
        FROM campaigns c
        LEFT JOIN pricing_lists pl ON c.pricing_list_id = pl.id
        WHERE c.id = ?
        """, (campaign_id,)).fetchone()
        
        if not campaign:
            return None
        
        # Get waves with items and costs
        waves_data = []
        waves = db.execute("SELECT * FROM waves WHERE campaign_id = ? ORDER BY start_date, name", (campaign_id,)).fetchall()
        
        for wave in waves:
            wave_dict = dict(wave)
            
            # Get wave items with TVC info
            items = db.execute("""
            SELECT wi.*, t.name as tvc_name, t.duration as tvc_duration
            FROM wave_items wi
            LEFT JOIN tvcs t ON wi.tvc_id = t.id
            WHERE wi.wave_id = ? 
            ORDER BY wi.owner, wi.target_group
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

# ---------------- TRP Calendar ----------------

def save_trp_distribution(campaign_id: int, trp_data: dict):
    """Save TRP distribution for a campaign"""
    with get_db() as db:
        for date_str, trp_value in trp_data.items():
            db.execute("""
                INSERT INTO trp_distribution (campaign_id, date, trp_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(campaign_id, date) DO UPDATE SET
                    trp_value = excluded.trp_value,
                    updated_at = CURRENT_TIMESTAMP
            """, (campaign_id, date_str, float(trp_value) if trp_value else 0.0))

def load_trp_distribution(campaign_id: int):
    """Load TRP distribution for a campaign"""
    with get_db() as db:
        rows = db.execute("""
            SELECT date, trp_value FROM trp_distribution 
            WHERE campaign_id = ? AND trp_value > 0
            ORDER BY date
        """, (campaign_id,)).fetchall()
        
        return {row['date']: row['trp_value'] for row in rows}

def delete_trp_distribution(campaign_id: int):
    """Delete all TRP distribution data for a campaign"""
    with get_db() as db:
        db.execute("DELETE FROM trp_distribution WHERE campaign_id = ?", (campaign_id,))

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
    
    # Load TRP calendar data
    trp_data = load_trp_distribution(campaign_id)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TV Planas"
    
    # Professional styles
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")  # Dark blue
    header_font = Font(color="FFFFFF", bold=True, size=11)
    wave_fill = PatternFill(start_color="E7F3FF", end_color="E7F3FF", fill_type="solid")  # Light blue
    wave_font = Font(bold=True, color="1F4E79", size=10)
    total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # Light yellow for totals
    border = Border(left=Side(style='thin', color='D0D0D0'), right=Side(style='thin', color='D0D0D0'), 
                   top=Side(style='thin', color='D0D0D0'), bottom=Side(style='thin', color='D0D0D0'))
    thick_border = Border(left=Side(style='medium'), right=Side(style='medium'), 
                         top=Side(style='medium'), bottom=Side(style='medium'))
    
    current_row = 1
    
    # Campaign header
    ws.merge_cells(f'A{current_row}:Y{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = f"TV KOMUNIKACIJOS PLANAS"
    cell.font = Font(size=18, bold=True, color="1F4E79")
    cell.alignment = Alignment(horizontal='center')
    cell.fill = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
    current_row += 1
    
    # Campaign name
    ws.merge_cells(f'A{current_row}:Y{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = f"KAMPANIJA: {campaign['name'].upper()}"
    cell.font = Font(size=14, bold=True, color="1F4E79")
    cell.alignment = Alignment(horizontal='center')
    current_row += 3
    
    # Campaign info section
    info_font = Font(bold=True, size=10, color="1F4E79")
    value_font = Font(size=10)
    
    # Create a bordered info section
    info_cells = [
        ("Kampanijos laikotarpis:", f"{campaign.get('start_date', '')} - {campaign.get('end_date', '')}"),
        ("Klientas:", campaign.get('client', '')),
        ("Agentūra:", campaign.get('agency', '')),
        ("Produktas:", campaign.get('product', '')),
        ("Kainoraštis:", campaign.get('pricing_list_name', '')),
        ("Statusas:", campaign.get('status', 'draft').replace('_', ' ').title())
    ]
    
    for label, value in info_cells:
        ws[f'A{current_row}'] = label
        ws[f'A{current_row}'].font = info_font
        ws[f'B{current_row}'] = value
        ws[f'B{current_row}'].font = value_font
        current_row += 1
    
    # Calculate where to start main table (after calendar if it exists)
    if trp_data:
        current_row = 50  # Leave space for calendar above
    else:
        current_row += 1
    
    # Table headers
    headers = [
        'Banga', 'Laikotarpis', 'Kanalų grupė', 'Perkama tikslinė grupė', 'TVC', 'Trukmė', 
        'TG dydis (*000)', 'TG dalis (%)', 'TG imtis', 'Kanalo dalis (%)', 'PT zonos dalis (%)', 
        'TRP perkama', 'Affinity1', 'GRP planuojamas', 'Gross CPP', 'Trukmės koeficientas', 'Sezoninis koeficientas', 
        'TRP pirkimo koeficientas', 'Išankstinis koeficientas', 'Pozicijos indeksas', 'Gross kaina', 'Kliento nuolaida %', 'Net kaina', 
        'Agentūros nuolaida %', 'Net net kaina'
    ]
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
    row_count = 0
    light_fill = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")  # Zebra striping
    
    for wave in waves:
        wave_start_row = current_row
        
        for item in wave['items']:
            item_cost = item['trps'] * item['price_per_sec_eur']
            
            # Calculate values
            tg_size = item.get('tg_size_thousands', 0)
            tg_share = item.get('tg_share_percent', 0)
            tg_sample = item.get('tg_sample_size', 0)
            channel_share = item.get('channel_share', 0.75)
            if channel_share < 1:  # If it's a decimal (0.75), convert to percentage
                channel_share = channel_share * 100
            pt_zone_share = item.get('pt_zone_share', 0.55)
            if pt_zone_share < 1:  # If it's a decimal (0.55), convert to percentage
                pt_zone_share = pt_zone_share * 100
            affinity1 = item.get('affinity1', 0)
            grp_planned = (item['trps'] * 100 / affinity1) if affinity1 > 0 else 0
            gross_cpp = item.get('gross_cpp_eur', item.get('price_per_sec_no_discount', item['price_per_sec_eur']))
            
            # Indices
            duration_idx = item.get('duration_index', 1.0)
            seasonal_idx = item.get('seasonal_index', 1.0)
            trp_purchase_idx = item.get('trp_purchase_index', 1.0)
            advance_idx = item.get('advance_purchase_index', 1.0)
            position_idx = item.get('position_index', 1.0)
            
            # Prices
            gross_price = item.get('gross_price_eur', item_cost)
            client_discount = item.get('client_discount', 0)
            net_price = gross_price * (1 - client_discount / 100)
            agency_discount = item.get('agency_discount', 0)
            net_net_price = net_price * (1 - agency_discount / 100)
            
            ws.cell(row=current_row, column=1).value = wave['name'] or f"Banga {wave['id']}"
            ws.cell(row=current_row, column=2).value = f"{wave.get('start_date', '')} - {wave.get('end_date', '')}"
            ws.cell(row=current_row, column=3).value = item['owner']  # Kanalų grupė
            ws.cell(row=current_row, column=4).value = item['target_group']  # Perkama TG
            ws.cell(row=current_row, column=5).value = item.get('tvc_name', '-')  # TVC
            ws.cell(row=current_row, column=6).value = item.get('tvc_duration', item.get('clip_duration', 0))  # Trukmė
            ws.cell(row=current_row, column=7).value = tg_size  # TG dydis (*000)
            ws.cell(row=current_row, column=8).value = f"{tg_share}%" if tg_share > 0 else ""  # TG dalis (%)
            ws.cell(row=current_row, column=9).value = tg_sample if tg_sample > 0 else ""  # TG imtis
            ws.cell(row=current_row, column=10).value = f"{channel_share:.1f}%"  # Kanalo dalis
            ws.cell(row=current_row, column=11).value = f"{pt_zone_share:.1f}%"  # PT zonos dalis
            ws.cell(row=current_row, column=12).value = item['trps']  # TRP perk.
            ws.cell(row=current_row, column=13).value = affinity1 if affinity1 > 0 else ""  # Affinity1
            ws.cell(row=current_row, column=14).value = round(grp_planned, 2) if grp_planned > 0 else ""  # GRP plan.
            ws.cell(row=current_row, column=15).value = f"€{gross_cpp:.2f}"  # Gross CPP
            ws.cell(row=current_row, column=16).value = duration_idx  # Trukm.koef
            ws.cell(row=current_row, column=17).value = seasonal_idx  # Sez.koef
            ws.cell(row=current_row, column=18).value = trp_purchase_idx  # TRP pirk.
            ws.cell(row=current_row, column=19).value = advance_idx  # Išank.
            ws.cell(row=current_row, column=20).value = position_idx  # Pozic.
            ws.cell(row=current_row, column=21).value = f"€{gross_price:.2f}"  # Gross kaina
            ws.cell(row=current_row, column=22).value = f"{client_discount}%" if client_discount > 0 else "0%"  # Kl. nuol. %
            ws.cell(row=current_row, column=23).value = f"€{net_price:.2f}"  # Net kaina
            ws.cell(row=current_row, column=24).value = f"{agency_discount}%" if agency_discount > 0 else "0%"  # Ag. nuol. %
            ws.cell(row=current_row, column=25).value = f"€{net_net_price:.2f}"  # Net net kaina
            
            # Apply zebra striping and borders
            row_fill = light_fill if row_count % 2 == 1 else None
            for col in range(1, 26):
                cell = ws.cell(row=current_row, column=col)
                cell.border = border
                if row_fill:
                    cell.fill = row_fill
                cell.font = Font(size=9)  # Smaller font for data
                cell.alignment = Alignment(horizontal='center', vertical='center')  # Center alignment
            
            current_row += 1
            row_count += 1
        
        # Wave summary with client discount
        if wave['items']:
            costs = wave['costs']
            client_cost = costs['client_cost']
            total_cost += client_cost
            
            ws.merge_cells(f'A{current_row}:X{current_row}')
            cell = ws[f'A{current_row}']
            discount_text = f" (-{costs['client_discount_percent']}%)" if costs['client_discount_percent'] > 0 else ""
            cell.value = f"Bangos suma{discount_text}:"
            cell.font = wave_font
            cell.fill = wave_fill
            cell.alignment = Alignment(horizontal='right')
            
            ws.cell(row=current_row, column=25).value = f"€{client_cost:.2f}"
            ws.cell(row=current_row, column=25).font = wave_font
            ws.cell(row=current_row, column=25).fill = wave_fill
            
            for col in range(1, 26):
                cell = ws.cell(row=current_row, column=col)
                cell.border = border
                cell.fill = wave_fill
            
            current_row += 2
    
    # Grand total
    ws.merge_cells(f'A{current_row}:X{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = "BENDRA KAMPANIJOS SUMA:"
    cell.font = Font(bold=True, size=12, color="1F4E79")
    cell.alignment = Alignment(horizontal='right')
    cell.fill = total_fill
    cell.border = thick_border
    
    total_cell = ws.cell(row=current_row, column=25)
    total_cell.value = f"€{total_cost:.2f}"
    total_cell.font = Font(bold=True, size=12, color="1F4E79")
    total_cell.fill = total_fill
    total_cell.border = thick_border
    
    # Add TRP Calendar below campaign info
    if trp_data:
        # Position calendar after campaign info, before main table
        cal_start_row = 15  # After campaign info section
        
        # Calendar title
        ws.merge_cells(f'A{cal_start_row}:F{cal_start_row}')
        cal_title = ws[f'A{cal_start_row}']
        cal_title.value = "TRP KALENDORIUS"
        cal_title.font = Font(bold=True, size=12, color="1F4E79")
        cal_title.alignment = Alignment(horizontal='center')
        cal_title.fill = PatternFill(start_color="F0F8FF", end_color="F0F8FF", fill_type="solid")
        cal_start_row += 2
        
        import json
        from datetime import datetime, timedelta
        if isinstance(trp_data, str):
            trp_data = json.loads(trp_data)
        
        if trp_data:
            # Get date range from campaign or from TRP data
            start_date_str = campaign.get('start_date', '')
            end_date_str = campaign.get('end_date', '')
            
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    
                    # Calculate weeks
                    current_date = start_date
                    week_num = 0
                    max_weeks = 8  # Limit to 8 weeks for space
                    
                    while current_date <= end_date and week_num < max_weeks:
                        week_start = current_date
                        week_end = min(current_date + timedelta(days=6), end_date)
                        
                        # Week header
                        week_label = f"Savaitė {week_num + 1}"
                        ws.cell(row=cal_start_row, column=1).value = week_label
                        ws.cell(row=cal_start_row, column=1).font = Font(bold=True, size=9, color="1F4E79")
                        ws.cell(row=cal_start_row, column=1).alignment = Alignment(horizontal='center')
                        
                        # Days of week
                        day_names = ['Pr', 'An', 'Tr', 'Kt', 'Pn', 'Št', 'Sk']
                        for i, day_name in enumerate(day_names):
                            col_idx = i + 2
                            if col_idx <= 8:  # Don't exceed reasonable width
                                day_date = week_start + timedelta(days=i)
                                if day_date <= week_end:
                                    # Day header
                                    ws.cell(row=cal_start_row, column=col_idx).value = day_name
                                    ws.cell(row=cal_start_row, column=col_idx).font = Font(bold=True, size=8)
                                    ws.cell(row=cal_start_row, column=col_idx).alignment = Alignment(horizontal='center')
                                    ws.cell(row=cal_start_row, column=col_idx).fill = header_fill
                                    
                                    # Date
                                    ws.cell(row=cal_start_row + 1, column=col_idx).value = day_date.strftime('%d')
                                    ws.cell(row=cal_start_row + 1, column=col_idx).font = Font(size=8)
                                    ws.cell(row=cal_start_row + 1, column=col_idx).alignment = Alignment(horizontal='center')
                                    
                                    # TRP value
                                    date_key = day_date.strftime('%Y-%m-%d')
                                    trp_value = trp_data.get(date_key, 0)
                                    if trp_value > 0:
                                        ws.cell(row=cal_start_row + 2, column=col_idx).value = f"{trp_value:.1f}"
                                        ws.cell(row=cal_start_row + 2, column=col_idx).font = Font(size=8, bold=True, color="FF6B35")
                                    else:
                                        ws.cell(row=cal_start_row + 2, column=col_idx).value = ""
                                    ws.cell(row=cal_start_row + 2, column=col_idx).alignment = Alignment(horizontal='center')
                                    
                                    # Borders for calendar
                                    for row_offset in range(3):
                                        cell = ws.cell(row=cal_start_row + row_offset, column=col_idx)
                                        cell.border = border
                        
                        # Week total
                        week_total = sum(float(trp_data.get((week_start + timedelta(days=i)).strftime('%Y-%m-%d'), 0)) 
                                       for i in range(7) if week_start + timedelta(days=i) <= week_end)
                        if week_total > 0:
                            ws.cell(row=cal_start_row + 2, column=9).value = f"Σ {week_total:.1f}"
                            ws.cell(row=cal_start_row + 2, column=9).font = Font(size=8, bold=True, color="1F4E79")
                            ws.cell(row=cal_start_row + 2, column=9).alignment = Alignment(horizontal='center')
                        
                        cal_start_row += 4
                        current_date = week_end + timedelta(days=1)
                        week_num += 1
                    
                    # Total TRP summary
                    total_trp = sum(float(v) for v in trp_data.values())
                    if total_trp > 0:
                        ws.cell(row=cal_start_row, column=1).value = "BENDRAS TRP:"
                        ws.cell(row=cal_start_row, column=1).font = Font(bold=True, size=10, color="1F4E79")
                        ws.cell(row=cal_start_row, column=2).value = f"{total_trp:.1f}"
                        ws.cell(row=cal_start_row, column=2).font = Font(bold=True, size=10, color="1F4E79")
                        ws.cell(row=cal_start_row, column=2).fill = total_fill
                    
                except Exception as e:
                    # Fallback to simple table if date parsing fails
                    ws.cell(row=cal_start_row, column=1).value = "Data"
                    ws.cell(row=cal_start_row, column=2).value = "TRP"
                    for col in [1, 2]:
                        ws.cell(row=cal_start_row, column=col).font = header_font
                        ws.cell(row=cal_start_row, column=col).fill = header_fill
                    cal_start_row += 1
                    
                    for date_str, trp_value in sorted(trp_data.items()):
                        ws.cell(row=cal_start_row, column=1).value = date_str
                        ws.cell(row=cal_start_row, column=2).value = float(trp_value)
                        cal_start_row += 1
    
    # Professional footer
    current_row += 3
    ws.merge_cells(f'A{current_row}:Y{current_row}')
    footer_cell = ws[f'A{current_row}']
    from datetime import datetime
    footer_cell.value = f"Ataskaita sugeneruota: {datetime.now().strftime('%Y-%m-%d %H:%M')} | TV Planner Sistema"
    footer_cell.font = Font(size=8, italic=True, color="808080")
    footer_cell.alignment = Alignment(horizontal='center')
    
    # Adjust column widths
    column_widths = [
        12, 18, 15, 25, 12, 8,  # Banga, Laikotarpis, Kanalų grupė, Perkama tikslinė grupė, TVC, Trukmė
        12, 10, 8, 15, 15,      # TG dydis, TG dalis, TG imtis, Kanalo dalis, PT zonos dalis
        12, 10, 15, 12, 20,     # TRP perkama, Affinity1, GRP planuojamas, Gross CPP, Trukmės koeficientas
        20, 22, 20, 18, 12,     # Sezoninis koeficientas, TRP pirkimo koeficientas, Išankstinis koeficientas, Pozicijos indeksas, Gross kaina
        15, 12, 15, 15          # Kliento nuolaida %, Net kaina, Agentūros nuolaida %, Net net kaina
    ]
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
    
    # Load TRP calendar data
    trp_data = load_trp_distribution(campaign_id)
    
    csv_content = []
    csv_content.append(['# TV UŽSAKYMAS'])
    csv_content.append(['Kampanija', campaign['name']])
    csv_content.append(['Laikotarpis', f"{campaign.get('start_date', '')} - {campaign.get('end_date', '')}"])
    csv_content.append(['Kainoraštis', campaign.get('pricing_list_name', '')])
    csv_content.append(['Statusas', campaign.get('status', 'draft')])
    csv_content.append([])  # Empty row
    
    # Headers
    csv_content.append([
        'Banga', 'Laikotarpis', 'TVC', 'Trukmė', 'Savininkas', 'Tikslinė grupė', 'Kanalas', 
        'TRP', 'CPP €', 'TG dydis', 'Bazinė kaina €/sek', 'Kliento kaina €/sek', 'Agentūros kaina €/sek', 
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
                item.get('tvc_name', '-'),
                f"{item.get('tvc_duration', item.get('clip_duration', 0))}s",
                item['owner'],
                item['target_group'],
                f"{item['primary_label']}{' + ' + item['secondary_label'] if item['secondary_label'] else ''}",
                trps,
                round(item.get('price_per_sec_no_discount', base_price), 2),
                f"{item.get('tg_size_thousands', 0)}k",
                round(base_price, 4),
                round(client_price_per_sec, 4),
                round(agency_price_per_sec, 4),
                client_discount_percent,
                agency_discount_percent,
                round(final_cost, 2)
            ])
    
    # Total
    csv_content.append([])
    csv_content.append(['BENDRA AGENTŪROS SUMA €', '', '', '', '', '', '', '', '', '', '', '', '', '', '', round(total_agency_cost, 2)])
    
    # Add TRP Calendar if exists
    if trp_data:
        csv_content.append([])
        csv_content.append(['# TRP KALENDORIUS'])
        csv_content.append(['Data', 'TRP'])
        
        import json
        if isinstance(trp_data, str):
            trp_data = json.loads(trp_data)
            
        for date_str, trp_value in sorted(trp_data.items()):
            csv_content.append([date_str, float(trp_value)])
    
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

# ---------- INDICES MANAGEMENT ----------

def migrate_add_indices_tables():
    """Create tables for duration and seasonal indices management - LEGACY FUNCTION
    
    This function is now deprecated. Indices have been migrated to use channel_group_id
    instead of target_group. The new structure is already created by the migration script.
    """
    # This function is now a no-op since the migration has already been run
    # and the new channel_group-based structure is in place
    print("migrate_add_indices_tables: Indices tables already migrated to channel group structure")
    pass

def list_duration_indices():
    """Get all duration indices grouped by channel group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            """SELECT di.*, cg.name as channel_group_name 
               FROM duration_indices di 
               JOIN channel_groups cg ON di.channel_group_id = cg.id 
               ORDER BY cg.name, di.duration_seconds"""
        ).fetchall()]

def list_seasonal_indices():
    """Get all seasonal indices grouped by channel group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            """SELECT si.*, cg.name as channel_group_name 
               FROM seasonal_indices si 
               JOIN channel_groups cg ON si.channel_group_id = cg.id 
               ORDER BY cg.name, si.month"""
        ).fetchall()]

def list_position_indices():
    """Get all position indices grouped by channel group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            """SELECT pi.*, cg.name as channel_group_name 
               FROM position_indices pi 
               JOIN channel_groups cg ON pi.channel_group_id = cg.id 
               ORDER BY cg.name, pi.position_type"""
        ).fetchall()]

def get_duration_index(channel_group, duration_seconds):
    """Get duration index for specific channel group and duration"""
    with get_db() as db:
        # First try to find by channel_group_id
        if isinstance(channel_group, int):
            channel_group_id = channel_group
        else:
            # Look up channel group ID by name
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
            
        if channel_group_id:
            row = db.execute(
                "SELECT index_value FROM duration_indices WHERE channel_group_id = ? AND duration_seconds = ?",
                (channel_group_id, duration_seconds)
            ).fetchone()
            return float(row["index_value"]) if row else 1.0
        
        return 1.0  # Default if no channel group found

def get_seasonal_index(channel_group, month):
    """Get seasonal index for specific channel group and month (1-12)"""
    with get_db() as db:
        # First try to find by channel_group_id
        if isinstance(channel_group, int):
            channel_group_id = channel_group
        else:
            # Look up channel group ID by name
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
            
        if channel_group_id:
            row = db.execute(
                "SELECT index_value FROM seasonal_indices WHERE channel_group_id = ? AND month = ?",
                (channel_group_id, month)
            ).fetchone()
            return float(row["index_value"]) if row else 1.0
        
        return 1.0  # Default if no channel group found

def get_position_index(channel_group, position_type):
    """Get position index for specific channel group and position type"""
    with get_db() as db:
        # First try to find by channel_group_id
        if isinstance(channel_group, int):
            channel_group_id = channel_group
        else:
            # Look up channel group ID by name
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
            
        if channel_group_id:
            row = db.execute(
                "SELECT index_value FROM position_indices WHERE channel_group_id = ? AND position_type = ?",
                (channel_group_id, position_type)
            ).fetchone()
            return float(row["index_value"]) if row else 1.0
        
        return 1.0  # Default if no channel group found

def update_duration_index(channel_group, duration_seconds, index_value, description=None):
    """Update or create duration index"""
    with get_db() as db:
        # Look up channel group ID by name if needed
        if isinstance(channel_group, str):
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
        else:
            channel_group_id = channel_group
            
        if channel_group_id:
            db.execute("""
                INSERT OR REPLACE INTO duration_indices (channel_group_id, duration_seconds, index_value, description)
                VALUES (?, ?, ?, ?)
            """, (channel_group_id, duration_seconds, index_value, description))
            db.commit()

def update_seasonal_index(channel_group, month, index_value, description=None):
    """Update seasonal index for specific channel group and month"""
    with get_db() as db:
        # Look up channel group ID by name if needed
        if isinstance(channel_group, str):
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
        else:
            channel_group_id = channel_group
            
        if channel_group_id:
            db.execute("""
                INSERT OR REPLACE INTO seasonal_indices (channel_group_id, month, index_value, description)
                VALUES (?, ?, ?, ?)
            """, (channel_group_id, month, index_value, description))
            db.commit()

def delete_duration_index(channel_group, duration_seconds):
    """Delete duration index"""
    with get_db() as db:
        # Look up channel group ID by name if needed
        if isinstance(channel_group, str):
            cg_row = db.execute(
                "SELECT id FROM channel_groups WHERE name = ?", 
                (channel_group,)
            ).fetchone()
            channel_group_id = cg_row["id"] if cg_row else None
        else:
            channel_group_id = channel_group
            
        if channel_group_id:
            db.execute("DELETE FROM duration_indices WHERE channel_group_id = ? AND duration_seconds = ?", 
                       (channel_group_id, duration_seconds))
            db.commit()

def get_target_groups_list():
    """Get all available target groups from TRP rates (indices are now by channel group)"""
    with get_db() as db:
        trp_tgs = db.execute("SELECT DISTINCT target_group FROM trp_rates").fetchall()
        
        # Get target groups from TRP rates only (indices are now channel group based)
        all_tgs = set()
        for row in trp_tgs:
            all_tgs.add(row["target_group"])
            
        return sorted(list(all_tgs))

def get_indices_for_wave_item(channel_group, duration_seconds, start_date, end_date=None):
    """Get appropriate duration and seasonal indices for wave item based on channel group"""
    duration_index = get_duration_index(channel_group, duration_seconds)
    
    # Calculate seasonal index based on wave date range
    seasonal_index = 1.0
    if start_date:
        try:
            from datetime import datetime
            start_obj = datetime.strptime(start_date, '%Y-%m-%d')
            
            # If end_date is provided and spans multiple months, calculate average
            if end_date:
                try:
                    end_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    seasonal_index = calculate_average_seasonal_index(channel_group, start_obj, end_obj)
                    print(f"DEBUG: Multi-month wave {start_date} to {end_date}, average seasonal_index={seasonal_index}")
                except Exception as e:
                    print(f"DEBUG: Error parsing end_date {end_date}, using start_date only: {e}")
                    seasonal_index = get_seasonal_index(channel_group, start_obj.month)
            else:
                # Single month or no end date provided
                seasonal_index = get_seasonal_index(channel_group, start_obj.month)
                print(f"DEBUG: Single month wave {start_date}, seasonal_index={seasonal_index}")
                
        except Exception as e:
            print(f"DEBUG: Error parsing start_date {start_date}: {e}")
    else:
        print(f"DEBUG: No start_date provided for channel_group={channel_group}")
    
    return {
        'duration_index': duration_index,
        'seasonal_index': seasonal_index
    }

def calculate_average_seasonal_index(channel_group, start_date, end_date):
    """Calculate average seasonal index for a date range spanning multiple months"""
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    if start_date.year != end_date.year or start_date.month == end_date.month:
        # Same month or different years, use simple approach
        return get_seasonal_index(channel_group, start_date.month)
    
    total_weighted_index = 0
    total_days = 0
    
    current_date = start_date
    while current_date <= end_date:
        # Calculate days in current month for this wave
        if current_date.month == start_date.month:
            # First month: from start_date to end of month
            _, days_in_month = monthrange(current_date.year, current_date.month)
            days_in_current_month = days_in_month - current_date.day + 1
        elif current_date.month == end_date.month:
            # Last month: from beginning of month to end_date
            days_in_current_month = end_date.day
        else:
            # Full middle months
            _, days_in_current_month = monthrange(current_date.year, current_date.month)
        
        # Get seasonal index for this month
        month_index = get_seasonal_index(channel_group, current_date.month)
        
        # Add to weighted total
        total_weighted_index += month_index * days_in_current_month
        total_days += days_in_current_month
        
        print(f"DEBUG: Month {current_date.month}, days={days_in_current_month}, index={month_index}")
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)
    
    average_index = total_weighted_index / total_days if total_days > 0 else 1.0
    print(f"DEBUG: Average seasonal index calculation: total_weighted={total_weighted_index}, total_days={total_days}, average={average_index}")
    
    return average_index

def migrate_remove_pricing_list_requirement():
    """Remove pricing_list_id requirement from campaigns table"""
    with get_db() as db:
        # Check if pricing_list_id column exists and is NOT NULL
        cursor = db.execute("PRAGMA table_info(campaigns)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'pricing_list_id' in columns:
            col_info = columns['pricing_list_id']
            is_not_null = col_info[3] == 1  # notnull flag
            
            if is_not_null:
                print("Removing NOT NULL constraint from campaigns.pricing_list_id...")
                
                # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
                # First, get all existing data
                existing_campaigns = db.execute("SELECT * FROM campaigns").fetchall()
                
                # Drop the old table (after backing up foreign key constraints)
                db.execute("PRAGMA foreign_keys=OFF")
                db.execute("DROP TABLE campaigns")
                
                # Recreate campaigns table without NOT NULL on pricing_list_id
                db.execute("""
                CREATE TABLE campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pricing_list_id INTEGER,  -- Removed NOT NULL
                    start_date TEXT,
                    end_date TEXT,
                    agency TEXT,
                    client TEXT, 
                    product TEXT,
                    country TEXT,
                    status TEXT
                )
                """)
                
                # Restore data, setting pricing_list_id to NULL where needed
                for row in existing_campaigns:
                    values = list(row)
                    # If pricing_list_id references non-existent pricing list, set to NULL
                    if len(values) > 2 and values[2]:  # pricing_list_id
                        try:
                            check = db.execute("SELECT 1 FROM pricing_lists WHERE id = ?", (values[2],)).fetchone()
                            if not check:
                                values[2] = None
                        except:
                            values[2] = None
                    
                    # Handle cases where row might not have all columns
                    while len(values) < 11:  # Pad with None for missing columns
                        values.append(None)
                    
                    db.execute("""
                    INSERT INTO campaigns (id, name, pricing_list_id, start_date, end_date, 
                                         agency, client, product, country, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values[:10])
                
                db.execute("PRAGMA foreign_keys=ON")
                db.commit()
                print("Successfully removed NOT NULL constraint from pricing_list_id")
            else:
                print("pricing_list_id already allows NULL values")
        else:
            print("pricing_list_id column does not exist")
        
        db.commit()
