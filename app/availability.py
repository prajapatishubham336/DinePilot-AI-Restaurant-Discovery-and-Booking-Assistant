import math
import sqlite3
from .config import DB_PATH


def init_availability():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS restaurant_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT UNIQUE NOT NULL,
            total_tables INTEGER NOT NULL DEFAULT 10,
            table_capacity INTEGER NOT NULL DEFAULT 4
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS slot_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            total_tables INTEGER NOT NULL,
            booked_tables INTEGER NOT NULL DEFAULT 0,
            UNIQUE(restaurant, date, time)
        )
    """)
    cols = {r[1] for r in con.execute("PRAGMA table_info(restaurant_tables)")}
    if "table_capacity" not in cols:
        con.execute("ALTER TABLE restaurant_tables ADD COLUMN table_capacity INTEGER DEFAULT 4")
    con.commit()
    con.close()


def create_restaurant(restaurant, total_tables=10, table_capacity=4):
    init_availability()
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO restaurant_tables(restaurant, total_tables, table_capacity)
        VALUES (?, ?, ?)
        ON CONFLICT(restaurant) DO UPDATE SET
        total_tables=excluded.total_tables,
        table_capacity=excluded.table_capacity
    """, (restaurant.strip(), int(total_tables), int(table_capacity)))
    con.commit()
    con.close()


def list_restaurants():
    init_availability()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT restaurant, total_tables, table_capacity
        FROM restaurant_tables
        ORDER BY restaurant
    """).fetchall()
    con.close()
    return rows


def create_slot(restaurant, booking_date, booking_time, total_tables=None):
    init_availability()
    con = sqlite3.connect(DB_PATH)

    if total_tables is None:
        row = con.execute(
            "SELECT total_tables FROM restaurant_tables WHERE restaurant=?",
            (restaurant,)
        ).fetchone()
        if not row:
            con.close()
            return False, "Restaurant is not configured."
        total_tables = row[0]

    con.execute("""
        INSERT OR IGNORE INTO slot_inventory
        (restaurant, date, time, total_tables)
        VALUES (?, ?, ?, ?)
    """, (restaurant, str(booking_date), str(booking_time), int(total_tables)))

    con.commit()
    con.close()
    return True, "Slot created."


def get_table_capacity(restaurant):
    init_availability()
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT table_capacity FROM restaurant_tables WHERE restaurant=?",
        (restaurant,)
    ).fetchone()
    con.close()
    return row[0] if row else 4


def get_slot(restaurant, booking_date, booking_time):
    init_availability()
    con = sqlite3.connect(DB_PATH)
    row = con.execute("""
        SELECT total_tables, booked_tables
        FROM slot_inventory
        WHERE restaurant=? AND date=? AND time=?
    """, (restaurant, str(booking_date), str(booking_time))).fetchone()
    con.close()

    if not row:
        return {"total": 0, "booked": 0, "available": 0, "status": "NOT_SET"}

    total, booked = row
    available = max(0, total - booked)

    return {
        "total": total,
        "booked": booked,
        "available": available,
        "status": "FULL" if available == 0 else "AVAILABLE"
    }


def reserve_slot(restaurant, booking_date, booking_time, guests):
    init_availability()

    tables_needed = max(
        1,
        math.ceil(int(guests) / get_table_capacity(restaurant))
    )

    con = sqlite3.connect(DB_PATH, timeout=10)

    row = con.execute("""
        SELECT total_tables, booked_tables
        FROM slot_inventory
        WHERE restaurant=? AND date=? AND time=?
    """, (restaurant, str(booking_date), str(booking_time))).fetchone()

    if not row:
        con.close()
        return False, "This time slot is not configured by the owner.", 0

    total, booked = row

    if total - booked < tables_needed:
        con.close()
        return False, f"Not enough tables available. {total - booked} table(s) left.", 0

    cur = con.execute("""
        UPDATE slot_inventory
        SET booked_tables = booked_tables + ?
        WHERE restaurant=? AND date=? AND time=?
        AND booked_tables + ? <= total_tables
    """, (
        tables_needed,
        restaurant,
        str(booking_date),
        str(booking_time),
        tables_needed
    ))

    if cur.rowcount != 1:
        con.rollback()
        con.close()
        return False, "Slot became FULL. Please try another time.", 0

    con.commit()
    con.close()
    return True, f"{tables_needed} table(s) reserved.", tables_needed


def cancel_slot(restaurant, booking_date, booking_time, tables_reserved=1):
    init_availability()

    con = sqlite3.connect(DB_PATH, timeout=10)

    con.execute("""
        UPDATE slot_inventory
        SET booked_tables = MAX(0, booked_tables - ?)
        WHERE restaurant=? AND date=? AND time=?
    """, (
        max(1, int(tables_reserved)),
        restaurant,
        str(booking_date),
        str(booking_time)
    ))

    con.commit()
    con.close()
    return True


def list_slots(restaurant, booking_date):
    init_availability()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT time, total_tables, booked_tables
        FROM slot_inventory
        WHERE restaurant=? AND date=?
        ORDER BY time
    """, (restaurant, str(booking_date))).fetchall()
    con.close()
    return rows