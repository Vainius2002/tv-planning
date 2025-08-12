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
