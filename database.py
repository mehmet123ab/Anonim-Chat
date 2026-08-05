import sqlite3
import datetime
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Veritabanı tablolarını oluşturur ve hazırlar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Kullanıcılar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                gender TEXT,
                gender_credits INTEGER DEFAULT 0,
                preferred_gender TEXT DEFAULT 'ANY'
            )
        """)
        
        # Bekleme kuyruğu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                user_id INTEGER PRIMARY KEY,
                joined_queue_at TIMESTAMP,
                target_gender TEXT DEFAULT 'ANY',
                own_gender TEXT
            )
        """)
        
        # Aktif sohbet eşleşmeleri (İki yönlü sorgulama için)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_chats (
                user1_id INTEGER PRIMARY KEY,
                user2_id INTEGER UNIQUE,
                started_at TIMESTAMP
            )
        """)
        
        # Şikayet raporları
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reported_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP
            )
        """)

        # Migration - Kolon Kontrolleri
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [col["name"] for col in cursor.fetchall()]
        if "gender" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT")
        if "gender_credits" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN gender_credits INTEGER DEFAULT 0")
        if "preferred_gender" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_gender TEXT DEFAULT 'ANY'")

        cursor.execute("PRAGMA table_info(queue)")
        queue_cols = [col["name"] for col in cursor.fetchall()]
        if "target_gender" not in queue_cols:
            cursor.execute("ALTER TABLE queue ADD COLUMN target_gender TEXT DEFAULT 'ANY'")
        if "own_gender" not in queue_cols:
            cursor.execute("ALTER TABLE queue ADD COLUMN own_gender TEXT")

        conn.commit()

def add_or_update_user(user_id: int, username: str = None, first_name: str = None):
    """Kullanıcıyı kaydeder veya bilgilerini günceller."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at, is_banned, gender_credits, preferred_gender)
            VALUES (?, ?, ?, ?, 0, 0, 'ANY')
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name, now))
        conn.commit()

def set_user_gender(user_id: int, gender: str):
    """Kullanıcının kendi cinsiyetini kaydeder."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        conn.commit()

def get_user_gender(user_id: int) -> str:
    """Kullanıcının kendi cinsiyetini döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT gender FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["gender"] if row and row["gender"] else None

def add_gender_credits(user_id: int, amount: int):
    """Kullanıcıya cinsiyet filtreli eşleşme hakkı ekler."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET gender_credits = COALESCE(gender_credits, 0) + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

def get_gender_credits(user_id: int) -> int:
    """Kullanıcının kalan cinsiyet filtreli eşleşme hakkını döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT gender_credits FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["gender_credits"] if row and row["gender_credits"] else 0

def use_gender_credit(user_id: int) -> bool:
    """Kullanıcının 1 filtre hakkını düşer."""
    credits = get_gender_credits(user_id)
    if credits > 0:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET gender_credits = gender_credits - 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
    return False

def is_user_banned(user_id: int) -> bool:
    """Kullanıcının engelli olup olmadığını kontrol eder."""
    with get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row["is_banned"]) if row else False

def ban_user(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def unban_user(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def add_to_queue(user_id: int, target_gender: str = "ANY", own_gender: str = None) -> bool:
    """Kullanıcıyı bekleme kuyruğuna ekler."""
    if not own_gender:
        own_gender = get_user_gender(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now()
        cursor.execute(
            "INSERT OR REPLACE INTO queue (user_id, joined_queue_at, target_gender, own_gender) VALUES (?, ?, ?, ?)",
            (user_id, now, target_gender, own_gender)
        )
        conn.commit()
        return True

def remove_from_queue(user_id: int):
    """Kullanıcıyı bekleme kuyruğundan çıkarır."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
        conn.commit()

def is_in_queue(user_id: int) -> bool:
    """Kullanıcının kuyrukta olup olmadığını döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT 1 FROM queue WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None

def pop_queue_partner(current_user_id: int, own_gender: str = None, target_gender: str = "ANY"):
    """Kuyruktan filtreli veya filtresiz partner çeker."""
    if not own_gender:
        own_gender = get_user_gender(current_user_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        if target_gender != "ANY":
            query = """
                SELECT q.user_id FROM queue q
                LEFT JOIN users u ON q.user_id = u.user_id
                WHERE q.user_id != ?
                AND (q.own_gender = ? OR u.gender = ?)
                AND (q.target_gender = 'ANY' OR q.target_gender = ?)
                ORDER BY q.joined_queue_at ASC LIMIT 1
            """
            params = (current_user_id, target_gender, target_gender, own_gender)
        else:
            query = """
                SELECT q.user_id FROM queue q
                WHERE q.user_id != ?
                AND (q.target_gender = 'ANY' OR q.target_gender = ?)
                ORDER BY q.joined_queue_at ASC LIMIT 1
            """
            params = (current_user_id, own_gender)

        row = cursor.execute(query, params).fetchone()
        if row:
            partner_id = row["user_id"]
            cursor.execute("DELETE FROM queue WHERE user_id = ?", (partner_id,))
            conn.commit()
            return partner_id
        return None

def create_active_chat(user1_id: int, user2_id: int):
    """İki kullanıcı arasında aktif sohbet eşleşmesi oluşturur."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now()
        # Her iki kullanıcıyı da sohbet ve kuyruktan temizle
        cursor.execute("DELETE FROM queue WHERE user_id IN (?, ?)", (user1_id, user2_id))
        cursor.execute("INSERT OR REPLACE INTO active_chats (user1_id, user2_id, started_at) VALUES (?, ?, ?)",
                       (user1_id, user2_id, now))
        conn.commit()

def get_active_partner(user_id: int):
    """Kullanıcının şu anki sohbet partnerinin ID'sini döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT user2_id AS partner FROM active_chats WHERE user1_id = ? UNION SELECT user1_id AS partner FROM active_chats WHERE user2_id = ?",
            (user_id, user_id)
        ).fetchone()
        return row["partner"] if row else None

def end_active_chat(user_id: int):
    """Kullanıcının dahil olduğu sohbeti sonlandırır ve partner ID'sini döndürür."""
    partner_id = get_active_partner(user_id)
    if partner_id:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM active_chats WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
                (user_id, partner_id, partner_id, user_id)
            )
            conn.commit()
    return partner_id

def add_report(reporter_id: int, reported_id: int, reason: str = "Şikayet edildi"):
    """Şikayet kaydı ekler."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO reports (reporter_id, reported_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (reporter_id, reported_id, reason, now)
        )
        conn.commit()

def get_stats():
    """Bot istatistiklerini döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_chats = cursor.execute("SELECT COUNT(*) FROM active_chats").fetchone()[0]
        in_queue = cursor.execute("SELECT COUNT(*) FROM queue").fetchone()[0]
        return total_users, active_chats, in_queue

def get_all_user_ids():
    """Tüm kayıtlı kullanıcı ID'lerini döner."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT user_id FROM users").fetchall()
        return [row["user_id"] for row in rows]

