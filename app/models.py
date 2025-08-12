# app/models.py
import os, sqlite3
DB_PATH = os.path.join(os.path.dirname(__file__), "tv-calc.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        # --- Channel groups & channels ---
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

        # --- Legacy TRP rates (kept for backward compatibility) ---
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

        # --- NEW: Pricing lists & items ---
        db.execute("""
        CREATE TABLE IF NOT EXISTS pricing_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS pricing_list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id INTEGER NOT NULL,
            channel_group_id INTEGER NOT NULL,
            target_group TEXT NOT NULL,
            primary_label TEXT NOT NULL,
            secondary_label TEXT,
            share_primary REAL,
            share_secondary REAL,
            prime_share_primary REAL,
            prime_share_secondary REAL,
            price_per_sec_eur REAL NOT NULL,
            UNIQUE(list_id, channel_group_id, target_group),
            FOREIGN KEY(list_id) REFERENCES pricing_lists(id) ON DELETE CASCADE,
            FOREIGN KEY(channel_group_id) REFERENCES channel_groups(id) ON DELETE RESTRICT
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
    size = (size or "").lower()
    if size not in ("big","small"):
        raise ValueError("size must be 'big' or 'small'")
    with get_db() as db:
        db.execute(
            "INSERT INTO channels(channel_group_id, name, size) VALUES (?,?,?)",
            (channel_group_id, name, size)
        )

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
    existing = {(r["channel_group_id"], r["name"]) for r in list_channels()}
    def ensure(gid, name, size):
        if (gid, name) not in existing:
            create_channel(gid, name, size)
    # AMB Baltics
    ensure(amb_id, "TV3", "big")
    ensure(amb_id, "TV6", "small")
    ensure(amb_id, "TV8", "small")
    ensure(amb_id, "TV3 Plus", "small")
    # MG grupė
    ensure(mg_id, "LNK", "big")

def update_channel_group(group_id: int, name: str):
    name = (name or "").strip()
    if not name:
        raise ValueError("name required")
    with get_db() as db:
        db.execute("UPDATE channel_groups SET name=? WHERE id=?", (name, group_id))

def delete_channel_group(group_id: int):
    with get_db() as db:
        db.execute("DELETE FROM channel_groups WHERE id=?", (group_id,))

# ---------------- Legacy TRP rates helpers ----------------

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
            )
            VALUES (
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
            rows = db.execute(
                "SELECT * FROM trp_rates WHERE owner=? ORDER BY target_group", (owner,)
            ).fetchall()
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

# ---------------- Pricing lists ----------------

def list_pricing_lists():
    with get_db() as db:
        rows = db.execute("SELECT id, name, created_at FROM pricing_lists ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def create_pricing_list(name: str) -> int:
    with get_db() as db:
        db.execute("INSERT INTO pricing_lists(name) VALUES (?)", (name,))
        row = db.execute("SELECT id FROM pricing_lists WHERE name=?", (name,)).fetchone()
        return row["id"]

def delete_pricing_list(list_id: int):
    with get_db() as db:
        db.execute("DELETE FROM pricing_lists WHERE id=?", (list_id,))

def duplicate_pricing_list(src_list_id: int, new_name: str) -> int:
    with get_db() as db:
        db.execute("INSERT INTO pricing_lists(name) VALUES (?)", (new_name,))
        new_id = db.execute("SELECT id FROM pricing_lists WHERE name=?", (new_name,)).fetchone()["id"]
        db.execute("""
            INSERT INTO pricing_list_items (
                list_id, channel_group_id, target_group, primary_label, secondary_label,
                share_primary, share_secondary, prime_share_primary, prime_share_secondary, price_per_sec_eur
            )
            SELECT ?, channel_group_id, target_group, primary_label, secondary_label,
                   share_primary, share_secondary, prime_share_primary, prime_share_secondary, price_per_sec_eur
            FROM pricing_list_items
            WHERE list_id=?
        """, (new_id, src_list_id))
        return new_id

def list_pricing_list_items(list_id: int):
    with get_db() as db:
        rows = db.execute("""
            SELECT i.id, i.list_id, i.channel_group_id, cg.name AS owner,
                   i.target_group, i.primary_label, i.secondary_label,
                   i.share_primary, i.share_secondary, i.prime_share_primary, i.prime_share_secondary,
                   i.price_per_sec_eur
            FROM pricing_list_items i
            JOIN channel_groups cg ON cg.id = i.channel_group_id
            WHERE i.list_id=?
            ORDER BY owner, target_group
        """, (list_id,)).fetchall()
        return [dict(r) for r in rows]

def create_pricing_list_item(
    list_id: int,
    channel_group_id: int,
    target_group: str,
    primary_label: str,
    secondary_label: str | None,
    share_primary, share_secondary,
    prime_share_primary, prime_share_secondary,
    price_per_sec_eur
):
    payload = {
        "list_id": list_id,
        "channel_group_id": channel_group_id,
        "target_group": target_group,
        "primary_label": primary_label,
        "secondary_label": secondary_label,
        "share_primary": _norm_number(share_primary),
        "share_secondary": _norm_number(share_secondary),
        "prime_share_primary": _norm_number(prime_share_primary),
        "prime_share_secondary": _norm_number(prime_share_secondary),
        "price_per_sec_eur": _norm_number(price_per_sec_eur),
    }
    if not payload["target_group"] or not payload["primary_label"] or payload["price_per_sec_eur"] is None:
        raise ValueError("target_group, primary_label and price_per_sec_eur are required")
    with get_db() as db:
        db.execute("""
            INSERT INTO pricing_list_items (
                list_id, channel_group_id, target_group, primary_label, secondary_label,
                share_primary, share_secondary, prime_share_primary, prime_share_secondary, price_per_sec_eur
            ) VALUES (
                :list_id, :channel_group_id, :target_group, :primary_label, :secondary_label,
                :share_primary, :share_secondary, :prime_share_primary, :prime_share_secondary, :price_per_sec_eur
            )
        """, payload)

def update_pricing_list_item(item_id: int, data: dict):
    if not data:
        return
    to_update = {}
    for key in ["channel_group_id","target_group","primary_label","secondary_label",
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
    args = list(to_update.values()) + [item_id]
    with get_db() as db:
        db.execute(f"UPDATE pricing_list_items SET {sets} WHERE id=?", args)

def delete_pricing_list_item(item_id: int):
    with get_db() as db:
        db.execute("DELETE FROM pricing_list_items WHERE id=?", (item_id,))

# Optional helper to import your existing trp_rates into a default list
def migrate_trp_rates_to_pricing_list(list_name: str) -> int:
    # ensure list
    list_id = create_pricing_list(list_name)
    # map owner -> channel_group_id (create if missing)
    owners = {}
    for row in list_trp_rates():
        owner = row["owner"]
        if owner not in owners:
            owners[owner] = upsert_channel_group(owner)
        create_pricing_list_item(
            list_id=list_id,
            channel_group_id=owners[owner],
            target_group=row["target_group"],
            primary_label=row["primary_label"],
            secondary_label=row["secondary_label"],
            share_primary=row["share_primary"],
            share_secondary=row["share_secondary"],
            prime_share_primary=row["prime_share_primary"],
            prime_share_secondary=row["prime_share_secondary"],
            price_per_sec_eur=row["price_per_sec_eur"],
        )
    return list_id
