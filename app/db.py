import sqlite3
from contextlib import closing
from .config import DB_PATH


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(_connect()) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                guests INTEGER NOT NULL,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                website TEXT DEFAULT '',
                tables_reserved INTEGER DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cols = {r[1] for r in con.execute("PRAGMA table_info(bookings)")}
        if "tables_reserved" not in cols:
            con.execute("ALTER TABLE bookings ADD COLUMN tables_reserved INTEGER DEFAULT 1")
        con.commit()


def save_booking(data):
    from .availability import init_availability, reserve_slot

    init_availability()
    ok, message, tables_reserved = reserve_slot(
        data["restaurant"], data["date"], data["time"], data["guests"]
    )

    if not ok:
        raise ValueError(message)

    try:
        with closing(_connect()) as con:
            cur = con.execute("""
                INSERT INTO bookings
                (restaurant,date,time,guests,name,contact,website,tables_reserved,status)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                data["restaurant"], data["date"], data["time"], data["guests"],
                data["name"], data["contact"], data.get("website", ""),
                tables_reserved, "PENDING"
            ))
            con.commit()
            return cur.lastrowid
    except Exception:
        from .availability import cancel_slot
        cancel_slot(data["restaurant"], data["date"], data["time"], tables_reserved)
        raise


def get_booking(booking_id):
    with closing(_connect()) as con:
        return con.execute("""
            SELECT id,restaurant,date,time,guests,name,contact,website,
                   tables_reserved,status,created_at
            FROM bookings WHERE id=?
        """, (booking_id,)).fetchone()


def list_bookings(contact=None, limit=50):
    with closing(_connect()) as con:
        if contact:
            return con.execute("""
                SELECT id,restaurant,date,time,guests,name,status,created_at
                FROM bookings
                WHERE LOWER(TRIM(contact))=LOWER(TRIM(?))
                ORDER BY id DESC LIMIT ?
            """, (contact.strip(), limit)).fetchall()

        return con.execute("""
            SELECT id,restaurant,date,time,guests,name,status,created_at
            FROM bookings ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()


def list_all_bookings():
    with closing(_connect()) as con:
        return con.execute("""
            SELECT id,restaurant,date,time,guests,name,contact,
                   tables_reserved,status,created_at
            FROM bookings ORDER BY date,time,id
        """).fetchall()


def cancel_booking(booking_id, contact=None):
    from .availability import cancel_slot

    booking = get_booking(booking_id)

    if not booking:
        return False, "Booking not found."

    if contact and booking[6].strip().lower() != contact.strip().lower():
        return False, "This booking does not belong to this contact."

    if booking[9] == "CANCELLED":
        return False, "Booking already cancelled."

    if booking[9] == "REJECTED":
        return False, "Rejected booking cannot be cancelled."

    cancel_slot(booking[1], booking[2], booking[3], booking[8] or 1)

    with closing(_connect()) as con:
        con.execute("UPDATE bookings SET status='CANCELLED' WHERE id=?", (booking_id,))
        con.commit()

    return True, "Booking cancelled. Table availability updated."


def update_booking_status(booking_id, new_status):
    from .availability import cancel_slot

    allowed = {"PENDING", "CONFIRMED", "REJECTED", "CANCELLED"}

    if new_status not in allowed:
        return False, "Invalid booking status."

    booking = get_booking(booking_id)

    if not booking:
        return False, "Booking not found."

    old_status = booking[9]

    if old_status == new_status:
        return True, f"Booking already {new_status}."

    if new_status in {"REJECTED", "CANCELLED"} and old_status not in {"REJECTED", "CANCELLED"}:
        cancel_slot(booking[1], booking[2], booking[3], booking[8] or 1)

    with closing(_connect()) as con:
        con.execute(
            "UPDATE bookings SET status=? WHERE id=?",
            (new_status, booking_id)
        )
        con.commit()

    return True, f"Booking marked {new_status}."