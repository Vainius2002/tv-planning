import sqlite3, os, re

DB_PATH = os.path.join(os.path.dirname(__file__), "tv-calc.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS trp_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,              -- 'AMB Baltics' | 'MG grupė'
            target_group TEXT NOT NULL,       -- e.g. 'A25-55', 'Visi nuo 4 m.'
            primary_label TEXT NOT NULL,      -- e.g. 'TV3' or 'LNK'
            secondary_label TEXT,             -- may be NULL
            share_primary REAL,
            share_secondary REAL,
            prime_share_primary REAL,
            prime_share_secondary REAL,
            price_per_sec_eur REAL NOT NULL,
            UNIQUE(owner, target_group)
        );
        """)
        db.commit()

def _norm_number(x):
    """
    Accepts: 18.40, 18,40, 18,40 €, 1 234,56, 1\u00A0234,56, 1,234.56, 60%
    Returns float or raises ValueError.
    """
    if x is None or str(x).strip() == "":
        return None
    s = str(x).strip()
    s = s.replace("€", "").replace("%", "").replace("\u00A0", " ")
    s = s.replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")           # 1,234.56
        else:
            s = s.replace(".", "").replace(",", ".")  # 1.234,56
    else:
        s = s.replace(",", ".")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if not m:
        raise ValueError(f"Invalid number: {x}")
    return float(m.group())

def upsert_trp_rate(**k):
    k["price_per_sec_eur"] = _norm_number(k.get("price_per_sec_eur"))
    for fld in ["share_primary", "share_secondary", "prime_share_primary", "prime_share_secondary"]:
        if fld in k:
            val = k.get(fld)
            k[fld] = None if val in (None, "", "null") else _norm_number(val)

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
            price_per_sec_eur=excluded.price_per_sec_eur;
        """, k)

def update_trp_rate_by_id(row_id: int, data: dict):
    num_keys = ["share_primary","share_secondary","prime_share_primary","prime_share_secondary","price_per_sec_eur"]
    clean = {}
    for k, v in data.items():
        if k in num_keys:
            clean[k] = _norm_number(v) if v not in (None, "", "null") else None
        else:
            clean[k] = v
    if not clean:
        return
    sets = ", ".join(f"{col}=:{col}" for col in clean.keys())
    clean["row_id"] = row_id
    with get_db() as db:
        db.execute(f"UPDATE trp_rates SET {sets} WHERE id=:row_id")

def delete_trp_rate(row_id: int):
    with get_db() as db:
        db.execute("DELETE FROM trp_rates WHERE id=?", (row_id,))

def list_trp_rates(owner=None):
    with get_db() as db:
        if owner:
            rows = db.execute(
                "SELECT * FROM trp_rates WHERE owner=? ORDER BY target_group",
                (owner,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM trp_rates ORDER BY owner, target_group"
            ).fetchall()
    return [dict(r) for r in rows]
