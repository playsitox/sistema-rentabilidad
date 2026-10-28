"""
Base de datos del Sistema de Rentabilidad
Soporta:
  - SQLite (local / desarrollo)
  - PostgreSQL / Supabase (producción - datos persistentes)
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import bcrypt

# ─── Detección del motor de base de datos ───────────────────────
def _get_database_url() -> Optional[str]:
    """Busca la URL de PostgreSQL en variables de entorno o secrets de Streamlit."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return None


DATABASE_URL = _get_database_url()
IS_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith(("postgres://", "postgresql://"))

# SQLite path (solo se usa si no hay Postgres)
SQLITE_PATH = Path(__file__).parent.parent / "data" / "rentabilidad.db"


def _get_pg_connection():
    """Conexión a PostgreSQL (Supabase)."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Supabase a veces usa postgres:// → psycopg2 prefiere postgresql://
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    return conn


def _get_sqlite_connection():
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection():
    """Context manager que devuelve una conexión (Postgres o SQLite)."""
    if IS_POSTGRES:
        conn = _get_pg_connection()
    else:
        conn = _get_sqlite_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute(conn, query: str, params: tuple = ()):
    """Ejecuta una query adaptando placeholders (? → %s para Postgres)."""
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor


def init_db():
    """Crea todas las tablas si no existen."""
    with get_connection() as conn:
        # Usuarios
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Empresas
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                industry TEXT,
                currency TEXT DEFAULT 'ARS',
                created_at TEXT NOT NULL
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                industry TEXT,
                currency TEXT DEFAULT 'ARS',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Productos
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                sku TEXT,
                category TEXT,
                unit_cost REAL DEFAULT 0,
                selling_price REAL DEFAULT 0,
                units_sold_monthly REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sku TEXT,
                category TEXT,
                unit_cost REAL DEFAULT 0,
                selling_price REAL DEFAULT 0,
                units_sold_monthly REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        # Costos
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS cost_items (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                cost_type TEXT NOT NULL CHECK(cost_type IN ('fijo', 'variable')),
                amount REAL NOT NULL,
                frequency TEXT DEFAULT 'mensual',
                category TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS cost_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cost_type TEXT NOT NULL CHECK(cost_type IN ('fijo', 'variable')),
                amount REAL NOT NULL,
                frequency TEXT DEFAULT 'mensual',
                category TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        # Cash flow
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS cashflow_entries (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                entry_date TEXT NOT NULL,
                description TEXT NOT NULL,
                entry_type TEXT NOT NULL CHECK(entry_type IN ('ingreso', 'egreso')),
                amount REAL NOT NULL,
                category TEXT,
                is_projected INTEGER DEFAULT 0,
                scenario TEXT DEFAULT 'realista',
                created_at TEXT NOT NULL
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS cashflow_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                description TEXT NOT NULL,
                entry_type TEXT NOT NULL CHECK(entry_type IN ('ingreso', 'egreso')),
                amount REAL NOT NULL,
                category TEXT,
                is_projected INTEGER DEFAULT 0,
                scenario TEXT DEFAULT 'realista',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        # Logs de uso
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                company_id INTEGER,
                action TEXT NOT NULL,
                tool TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_id INTEGER,
                action TEXT NOT NULL,
                tool TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Sesiones
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """ if IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _row_to_dict(row) -> Dict:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return dict(row)


def _rows_to_list(rows) -> List[Dict]:
    return [_row_to_dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
#  USUARIOS
# ═══════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_user(username: str, email: str, password: str, full_name: str = "") -> Optional[int]:
    with get_connection() as conn:
        try:
            now = datetime.utcnow().isoformat()
            cursor = _execute(
                conn,
                """
                INSERT INTO users (username, email, password_hash, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, email, hash_password(password), full_name, now),
            )
            if IS_POSTGRES:
                cursor.execute("SELECT lastval()")
                return cursor.fetchone()["lastval"]
            return cursor.lastrowid
        except Exception:
            return None


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = _execute(
            conn,
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        )
        row = cursor.fetchone()
        if row and verify_password(password, row["password_hash"]):
            user = _row_to_dict(row)
            _execute(
                conn,
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user["id"]),
            )
            return user
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = _execute(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
        return _row_to_dict(cursor.fetchone())


# ═══════════════════════════════════════════════════════════════
#  EMPRESAS
# ═══════════════════════════════════════════════════════════════

def create_company(user_id: int, name: str, industry: str = "", currency: str = "ARS") -> int:
    with get_connection() as conn:
        now = datetime.utcnow().isoformat()
        cursor = _execute(
            conn,
            """
            INSERT INTO companies (user_id, name, industry, currency, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, industry, currency, now),
        )
        if IS_POSTGRES:
            cursor.execute("SELECT lastval()")
            return cursor.fetchone()["lastval"]
        return cursor.lastrowid


def get_companies_by_user(user_id: int) -> List[Dict]:
    with get_connection() as conn:
        cursor = _execute(
            conn,
            "SELECT * FROM companies WHERE user_id = ? ORDER BY name",
            (user_id,),
        )
        return _rows_to_list(cursor.fetchall())


def get_company(company_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        cursor = _execute(conn, "SELECT * FROM companies WHERE id = ?", (company_id,))
        return _row_to_dict(cursor.fetchone())


# ═══════════════════════════════════════════════════════════════
#  PRODUCTOS
# ═══════════════════════════════════════════════════════════════

def create_product(
    company_id: int,
    name: str,
    unit_cost: float = 0,
    selling_price: float = 0,
    units_sold_monthly: float = 0,
    category: str = "",
    sku: str = "",
) -> int:
    with get_connection() as conn:
        now = datetime.utcnow().isoformat()
        cursor = _execute(
            conn,
            """
            INSERT INTO products
            (company_id, name, sku, category, unit_cost, selling_price, units_sold_monthly, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company_id, name, sku, category, unit_cost, selling_price, units_sold_monthly, now, now),
        )
        if IS_POSTGRES:
            cursor.execute("SELECT lastval()")
            return cursor.fetchone()["lastval"]
        return cursor.lastrowid


def get_products(company_id: int, active_only: bool = True) -> List[Dict]:
    with get_connection() as conn:
        if active_only:
            cursor = _execute(
                conn,
                "SELECT * FROM products WHERE company_id = ? AND is_active = 1 ORDER BY name",
                (company_id,),
            )
        else:
            cursor = _execute(
                conn,
                "SELECT * FROM products WHERE company_id = ? ORDER BY name",
                (company_id,),
            )
        return _rows_to_list(cursor.fetchall())


def update_product(product_id: int, **kwargs) -> bool:
    allowed = {"name", "sku", "category", "unit_cost", "selling_price", "units_sold_monthly", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [product_id]
    with get_connection() as conn:
        _execute(conn, f"UPDATE products SET {set_clause} WHERE id = ?", tuple(values))
    return True


def delete_product(product_id: int) -> bool:
    with get_connection() as conn:
        _execute(conn, "UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
    return True


# ═══════════════════════════════════════════════════════════════
#  COSTOS
# ═══════════════════════════════════════════════════════════════

def create_cost_item(
    company_id: int,
    name: str,
    cost_type: str,
    amount: float,
    frequency: str = "mensual",
    category: str = "",
    notes: str = "",
) -> int:
    with get_connection() as conn:
        now = datetime.utcnow().isoformat()
        cursor = _execute(
            conn,
            """
            INSERT INTO cost_items
            (company_id, name, cost_type, amount, frequency, category, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company_id, name, cost_type, amount, frequency, category, notes, now),
        )
        if IS_POSTGRES:
            cursor.execute("SELECT lastval()")
            return cursor.fetchone()["lastval"]
        return cursor.lastrowid


def get_cost_items(company_id: int, cost_type: Optional[str] = None) -> List[Dict]:
    with get_connection() as conn:
        if cost_type:
            cursor = _execute(
                conn,
                "SELECT * FROM cost_items WHERE company_id = ? AND cost_type = ? ORDER BY name",
                (company_id, cost_type),
            )
        else:
            cursor = _execute(
                conn,
                "SELECT * FROM cost_items WHERE company_id = ? ORDER BY cost_type, name",
                (company_id,),
            )
        return _rows_to_list(cursor.fetchall())


def delete_cost_item(item_id: int) -> bool:
    with get_connection() as conn:
        _execute(conn, "DELETE FROM cost_items WHERE id = ?", (item_id,))
    return True


# ═══════════════════════════════════════════════════════════════
#  CASH FLOW
# ═══════════════════════════════════════════════════════════════

def create_cashflow_entry(
    company_id: int,
    entry_date: str,
    description: str,
    entry_type: str,
    amount: float,
    category: str = "",
    is_projected: bool = False,
    scenario: str = "realista",
) -> int:
    with get_connection() as conn:
        now = datetime.utcnow().isoformat()
        cursor = _execute(
            conn,
            """
            INSERT INTO cashflow_entries
            (company_id, entry_date, description, entry_type, amount, category, is_projected, scenario, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                entry_date,
                description,
                entry_type,
                amount,
                category,
                1 if is_projected else 0,
                scenario,
                now,
            ),
        )
        if IS_POSTGRES:
            cursor.execute("SELECT lastval()")
            return cursor.fetchone()["lastval"]
        return cursor.lastrowid


def get_cashflow_entries(
    company_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_projected: Optional[bool] = None,
    scenario: Optional[str] = None,
) -> List[Dict]:
    with get_connection() as conn:
        query = "SELECT * FROM cashflow_entries WHERE company_id = ?"
        params: List[Any] = [company_id]

        if start_date:
            query += " AND entry_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND entry_date <= ?"
            params.append(end_date)
        if is_projected is not None:
            query += " AND is_projected = ?"
            params.append(1 if is_projected else 0)
        if scenario:
            query += " AND scenario = ?"
            params.append(scenario)

        query += " ORDER BY entry_date"
        cursor = _execute(conn, query, tuple(params))
        return _rows_to_list(cursor.fetchall())


def delete_cashflow_entry(entry_id: int) -> bool:
    with get_connection() as conn:
        _execute(conn, "DELETE FROM cashflow_entries WHERE id = ?", (entry_id,))
    return True


# ═══════════════════════════════════════════════════════════════
#  LOGS DE USO
# ═══════════════════════════════════════════════════════════════

def log_usage(
    user_id: int,
    action: str,
    tool: Optional[str] = None,
    company_id: Optional[int] = None,
    details: Optional[str] = None,
):
    with get_connection() as conn:
        now = datetime.utcnow().isoformat()
        _execute(
            conn,
            """
            INSERT INTO usage_logs (user_id, company_id, action, tool, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, company_id, action, tool, details, now),
        )


def get_usage_logs(
    user_id: Optional[int] = None,
    company_id: Optional[int] = None,
    limit: int = 100,
) -> List[Dict]:
    with get_connection() as conn:
        query = "SELECT * FROM usage_logs WHERE 1=1"
        params: List[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = _execute(conn, query, tuple(params))
        return _rows_to_list(cursor.fetchall())


def get_usage_summary(user_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = _execute(conn, "SELECT COUNT(*) as total FROM usage_logs WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()["total"]

        cursor = _execute(
            conn,
            """
            SELECT tool, COUNT(*) as count
            FROM usage_logs
            WHERE user_id = ? AND tool IS NOT NULL
            GROUP BY tool
            ORDER BY count DESC
            """,
            (user_id,),
        )
        by_tool = {row["tool"]: row["count"] for row in cursor.fetchall()}

        if IS_POSTGRES:
            cursor = _execute(
                conn,
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM usage_logs
                WHERE user_id = ? AND created_at >= (CURRENT_DATE - INTERVAL '7 days')
                GROUP BY day
                ORDER BY day
                """,
                (user_id,),
            )
        else:
            cursor = _execute(
                conn,
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM usage_logs
                WHERE user_id = ? AND created_at >= date('now', '-7 days')
                GROUP BY day
                ORDER BY day
                """,
                (user_id,),
            )
        last_7_days = {str(row["day"]): row["count"] for row in cursor.fetchall()}

    return {
        "total_actions": total,
        "by_tool": by_tool,
        "last_7_days": last_7_days,
    }


# Inicializar tablas al importar
try:
    init_db()
except Exception as e:
    # En Streamlit Cloud a veces falla el primer import si aún no hay secrets
    print(f"[database] init_db pendiente: {e}")
