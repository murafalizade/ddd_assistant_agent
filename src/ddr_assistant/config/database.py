import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

@dataclass
class DatabaseConfig:
    db_path: Path = Path("data/ddr_assistant.db")
    timeout: float = 30.0
    check_same_thread: bool = False
    isolation_level: Optional[str] = None
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    
    def __post_init__(self):
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

def get_db_connection(config: Optional[DatabaseConfig] = None) -> sqlite3.Connection:
    if config is None:
        config = DatabaseConfig()
    
    conn = sqlite3.connect(
        str(config.db_path),
        timeout=config.timeout,
        check_same_thread=config.check_same_thread,
        isolation_level=config.isolation_level,
    )
    
    cursor = conn.cursor()
    if config.enable_foreign_keys:
        cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute(f"PRAGMA journal_mode = {config.journal_mode}")
    cursor.execute(f"PRAGMA synchronous = {config.synchronous}")
    conn.row_factory = sqlite3.Row
    cursor.close()
    return conn

@contextmanager
def db_session(config: Optional[DatabaseConfig] = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection(config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_database(config: Optional[DatabaseConfig] = None, schema_sql: Optional[str] = None) -> None:
    if config is None:
        config = DatabaseConfig()
    
    conn = get_db_connection(config)
    if schema_sql:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        cursor.close()
    conn.close()

def execute_query(
    query: str,
    params: Optional[tuple] = None,
    config: Optional[DatabaseConfig] = None,
    fetch: str = "all"
) -> list:
    with db_session(config) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        if fetch == "all":
            results = cursor.fetchall()
        elif fetch == "one":
            results = [cursor.fetchone()] if cursor.fetchone() else []
        else:
            results = []
        cursor.close()
        return results