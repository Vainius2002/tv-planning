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
    # GRP Planned = TRP × Channel Share × PT Zone Share (matches Excel structure)
    grp_planned = excel_data["trps"] * excel_data["channel_share"] * excel_data["pt_zone_share"]
    # CPP = price per second × clip duration
    gross_cpp_eur = (rate["price_per_sec_eur"] * excel_data["clip_duration"]) if rate else (1.0 * excel_data["clip_duration"])
    
    # Get indices from database if available, otherwise use form values
    # Get wave dates for seasonal index calculation
    with get_db() as db:
        wave_data = db.execute("SELECT start_date, end_date FROM waves WHERE id = ?", (wave_id,)).fetchone()
        wave_start_date = wave_data["start_date"] if wave_data else None
        wave_end_date = wave_data["end_date"] if wave_data else None
    
    # Get indices from database using target group and wave date range
    db_indices = get_indices_for_wave_item(excel_data["target_group"], excel_data["clip_duration"], wave_start_date, wave_end_date)
    
    # Use database indices if available, otherwise fall back to form values
    duration_index = db_indices.get("duration_index", excel_data.get("duration_index", 1.25))
    seasonal_index = db_indices.get("seasonal_index", excel_data.get("seasonal_index", 0.9))
    
    # Calculate gross price with all indices (CPP already includes clip duration)
    gross_price_eur = (excel_data["trps"] * gross_cpp_eur * 
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
    
    # Recalculate prices if discounts or indices were updated
    need_price_recalc = any(field in data for field in ["client_discount", "agency_discount", "trps", "trp_purchase_index", "advance_purchase_index", "position_index", "duration_index", "seasonal_index"])
    
    if need_price_recalc:
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
                
                # Recalculate gross price with all indices
                gross_price = (trps * gross_cpp * duration_index * seasonal_index * 
                             trp_purchase_index * advance_purchase_index * position_index)
                
                # Get discounts
                client_discount = data.get("client_discount", item["client_discount"] or 0)
                agency_discount = data.get("agency_discount", item["agency_discount"] or 0)
                
                # Calculate net prices
                net_price = gross_price * (1 - client_discount / 100)
                net_net_price = net_price * (1 - agency_discount / 100)
                
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

# ---------- INDICES MANAGEMENT ----------

def migrate_add_indices_tables():
    """Create tables for duration and seasonal indices management"""
    with get_db() as db:
        # Duration indices table (based on clip duration and target group)
        db.execute("""
        CREATE TABLE IF NOT EXISTS duration_indices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_group TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(target_group, duration_seconds)
        )""")
        
        # Seasonal indices table (based on months and target group)
        db.execute("""
        CREATE TABLE IF NOT EXISTS seasonal_indices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_group TEXT NOT NULL,
            month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(target_group, month)
        )""")
        
        # Position indices table (based on ad position and target group)
        db.execute("""
        CREATE TABLE IF NOT EXISTS position_indices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_group TEXT NOT NULL,
            position_type TEXT NOT NULL,
            index_value REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            UNIQUE(target_group, position_type)
        )""")
        
        # Get all available target groups from TRP rates
        trp_rates = db.execute("SELECT DISTINCT target_group FROM trp_rates").fetchall()
        target_groups = [rate["target_group"] for rate in trp_rates]
        
        if not target_groups:
            # Add some default target groups if none exist
            target_groups = ["W18-49", "W25-54", "M18-49", "M25-54", "ALL18-49"]
        
        # Duration indices based on industry standard values
        # These apply to all target groups (same in both images)
        duration_ranges = [
            ((5, 9), 1.35, "5\"-9\""),
            ((10, 14), 1.25, "10\"-14\""), 
            ((15, 19), 1.2, "15\"-19\""),
            ((20, 24), 1.15, "20\"-24\""),
            ((25, 29), 1.1, "25\"-29\""),
            ((30, 44), 1.0, "30\"-44\""),
            ((45, 999), 1.0, "≥45\"")
        ]
        
        # Create duration indices for each TG (same values for all)
        for tg in target_groups:
            for (min_dur, max_dur), index_val, desc in duration_ranges:
                # Create entries for each second in the range
                for duration in range(min_dur, min(max_dur + 1, 301)):  # Cap at 300 seconds
                    db.execute("""
                        INSERT OR IGNORE INTO duration_indices (target_group, duration_seconds, index_value, description)
                        VALUES (?, ?, ?, ?)
                    """, (tg, duration, index_val, f"{desc} ({tg})"))
        
        # Seasonal indices - different patterns based on target group type
        # Pattern 1: A25-55, A25-65, A55+, W25-55, W25-65, M25-65 (from image 1)
        seasonal_pattern_1 = [
            (1, 0.9, "Sausis"), (2, 0.95, "Vasaris"), (3, 1.5, "Kovas"),
            (4, 1.55, "Balandis"), (5, 1.6, "Gegužė"), (6, 1.55, "Birželis"),
            (7, 1.1, "Liepa"), (8, 1.1, "Rugpjūtis"), (9, 1.65, "Rugsėjis"),
            (10, 1.65, "Spalis"), (11, 1.65, "Lapkritis"), (12, 1.5, "Gruodis")
        ]
        
        # Pattern 2: Visi, Moterys (from image 2) 
        seasonal_pattern_2 = [
            (1, 0.9, "Sausis"), (2, 1.0, "Vasaris"), (3, 1.4, "Kovas"),
            (4, 1.45, "Balandis"), (5, 1.45, "Gegužė"), (6, 1.4, "Birželis"),
            (7, 0.95, "Liepa"), (8, 1.0, "Rugpjūtis"), (9, 1.60, "Rugsėjis"),
            (10, 1.65, "Spalis"), (11, 1.65, "Lapkritis"), (12, 1.5, "Gruodis")
        ]
        
        # Assign patterns based on target group characteristics
        for tg in target_groups:
            # Use pattern 2 for broad demographics (Visi, Moterys, ALL)
            if any(keyword in tg.upper() for keyword in ['ALL', 'VISI', 'MOTER', 'WOMEN']):
                pattern = seasonal_pattern_2
            else:
                # Use pattern 1 for specific age/gender groups
                pattern = seasonal_pattern_1
            
            for month, index_val, desc in pattern:
                db.execute("""
                    INSERT OR IGNORE INTO seasonal_indices (target_group, month, index_value, description)
                    VALUES (?, ?, ?, ?)
                """, (tg, month, index_val, f"{desc} ({tg})"))
        
        # Position indices - different values based on target group type
        # Position values from images (image 1 vs image 2)
        position_pattern_1 = [
            ("first", 1.45, "Pirma pozicija"),
            ("second", 1.3, "Antra pozicija"), 
            ("last", 1.3, "Paskutinė"),
            ("other", 1.2, "Kita spec.")
        ]
        
        position_pattern_2 = [
            ("first", 1.5, "Pirma pozicija"),
            ("second", 1.4, "Antra pozicija"),
            ("last", 1.4, "Paskutinė"), 
            ("other", 1.3, "Kita spec.")
        ]
        
        # Assign position patterns based on target group characteristics
        for tg in target_groups:
            # Use pattern 2 for broad demographics (Visi, Moterys, ALL)
            if any(keyword in tg.upper() for keyword in ['ALL', 'VISI', 'MOTER', 'WOMEN']):
                pattern = position_pattern_2
            else:
                # Use pattern 1 for specific age/gender groups
                pattern = position_pattern_1
            
            for pos_type, index_val, desc in pattern:
                db.execute("""
                    INSERT OR IGNORE INTO position_indices (target_group, position_type, index_value, description)
                    VALUES (?, ?, ?, ?)
                """, (tg, pos_type, index_val, f"{desc} ({tg})"))
        
        db.commit()

def list_duration_indices():
    """Get all duration indices grouped by target group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM duration_indices ORDER BY target_group, duration_seconds"
        ).fetchall()]

def list_seasonal_indices():
    """Get all seasonal indices grouped by target group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM seasonal_indices ORDER BY target_group, month"
        ).fetchall()]

def list_position_indices():
    """Get all position indices grouped by target group"""
    with get_db() as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM position_indices ORDER BY target_group, position_type"
        ).fetchall()]

def get_duration_index(target_group, duration_seconds):
    """Get duration index for specific target group and duration"""
    with get_db() as db:
        row = db.execute(
            "SELECT index_value FROM duration_indices WHERE target_group = ? AND duration_seconds = ?",
            (target_group, duration_seconds)
        ).fetchone()
        return float(row["index_value"]) if row else 1.0

def get_seasonal_index(target_group, month):
    """Get seasonal index for specific target group and month (1-12)"""
    with get_db() as db:
        row = db.execute(
            "SELECT index_value FROM seasonal_indices WHERE target_group = ? AND month = ?",
            (target_group, month)
        ).fetchone()
        return float(row["index_value"]) if row else 1.0

def get_position_index(target_group, position_type):
    """Get position index for specific target group and position type"""
    with get_db() as db:
        row = db.execute(
            "SELECT index_value FROM position_indices WHERE target_group = ? AND position_type = ?",
            (target_group, position_type)
        ).fetchone()
        return float(row["index_value"]) if row else 1.0

def update_duration_index(target_group, duration_seconds, index_value, description=None):
    """Update or create duration index"""
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO duration_indices (target_group, duration_seconds, index_value, description)
            VALUES (?, ?, ?, ?)
        """, (target_group, duration_seconds, index_value, description))
        db.commit()

def update_seasonal_index(target_group, month, index_value, description=None):
    """Update seasonal index for specific target group and month"""
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO seasonal_indices (target_group, month, index_value, description)
            VALUES (?, ?, ?, ?)
        """, (target_group, month, index_value, description))
        db.commit()

def delete_duration_index(target_group, duration_seconds):
    """Delete duration index"""
    with get_db() as db:
        db.execute("DELETE FROM duration_indices WHERE target_group = ? AND duration_seconds = ?", 
                   (target_group, duration_seconds))
        db.commit()

def get_target_groups_list():
    """Get all available target groups"""
    with get_db() as db:
        duration_tgs = db.execute("SELECT DISTINCT target_group FROM duration_indices").fetchall()
        seasonal_tgs = db.execute("SELECT DISTINCT target_group FROM seasonal_indices").fetchall()
        trp_tgs = db.execute("SELECT DISTINCT target_group FROM trp_rates").fetchall()
        
        # Combine all unique target groups
        all_tgs = set()
        for row in duration_tgs:
            all_tgs.add(row["target_group"])
        for row in seasonal_tgs:
            all_tgs.add(row["target_group"])
        for row in trp_tgs:
            all_tgs.add(row["target_group"])
            
        return sorted(list(all_tgs))

def get_indices_for_wave_item(target_group, duration_seconds, start_date, end_date=None):
    """Get appropriate duration and seasonal indices for wave item"""
    duration_index = get_duration_index(target_group, duration_seconds)
    
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
                    seasonal_index = calculate_average_seasonal_index(target_group, start_obj, end_obj)
                    print(f"DEBUG: Multi-month wave {start_date} to {end_date}, average seasonal_index={seasonal_index}")
                except Exception as e:
                    print(f"DEBUG: Error parsing end_date {end_date}, using start_date only: {e}")
                    seasonal_index = get_seasonal_index(target_group, start_obj.month)
            else:
                # Single month or no end date provided
                seasonal_index = get_seasonal_index(target_group, start_obj.month)
                print(f"DEBUG: Single month wave {start_date}, seasonal_index={seasonal_index}")
                
        except Exception as e:
            print(f"DEBUG: Error parsing start_date {start_date}: {e}")
    else:
        print(f"DEBUG: No start_date provided for target_group={target_group}")
    
    return {
        'duration_index': duration_index,
        'seasonal_index': seasonal_index
    }

def calculate_average_seasonal_index(target_group, start_date, end_date):
    """Calculate average seasonal index for a date range spanning multiple months"""
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    if start_date.year != end_date.year or start_date.month == end_date.month:
        # Same month or different years, use simple approach
        return get_seasonal_index(target_group, start_date.month)
    
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
        month_index = get_seasonal_index(target_group, current_date.month)
        
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
