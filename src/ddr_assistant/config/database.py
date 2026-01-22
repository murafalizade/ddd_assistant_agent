"""SQLite database configuration and utilities for DDR Assistant."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional


@dataclass
class DatabaseConfig:
    """Configuration for SQLite database.
    
    Attributes:
        db_path: Path to the SQLite database file
        timeout: Connection timeout in seconds
        check_same_thread: Whether to check if connection is used in same thread
        isolation_level: Transaction isolation level (None for autocommit)
        enable_foreign_keys: Whether to enable foreign key constraints
        journal_mode: SQLite journal mode (DELETE, WAL, MEMORY, etc.)
        synchronous: SQLite synchronous mode (OFF, NORMAL, FULL)
    """
    
    db_path: Path = Path("data/ddr_assistant.db")
    timeout: float = 30.0
    check_same_thread: bool = False
    isolation_level: Optional[str] = None  # Autocommit mode
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"  # Write-Ahead Logging for better concurrency
    synchronous: str = "NORMAL"  # Balance between safety and performance
    
    def __post_init__(self):
        """Ensure the database directory exists."""
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)
        
        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection(config: Optional[DatabaseConfig] = None) -> sqlite3.Connection:
    """Create and configure a SQLite database connection.
    
    Args:
        config: Database configuration. If None, uses default configuration.
        
    Returns:
        Configured SQLite connection object
        
    Example:
        >>> config = DatabaseConfig(db_path=Path("data/my_db.db"))
        >>> conn = get_db_connection(config)
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM my_table")
    """
    if config is None:
        config = DatabaseConfig()
    
    # Create connection
    conn = sqlite3.connect(
        str(config.db_path),
        timeout=config.timeout,
        check_same_thread=config.check_same_thread,
        isolation_level=config.isolation_level,
    )
    
    # Configure connection
    cursor = conn.cursor()
    
    # Enable foreign keys if requested
    if config.enable_foreign_keys:
        cursor.execute("PRAGMA foreign_keys = ON")
    
    # Set journal mode
    cursor.execute(f"PRAGMA journal_mode = {config.journal_mode}")
    
    # Set synchronous mode
    cursor.execute(f"PRAGMA synchronous = {config.synchronous}")
    
    # Enable row factory for dict-like access
    conn.row_factory = sqlite3.Row
    
    cursor.close()
    
    return conn


@contextmanager
def db_session(config: Optional[DatabaseConfig] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database sessions with automatic commit/rollback.
    
    Args:
        config: Database configuration. If None, uses default configuration.
        
    """
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
    """Initialize the database with optional schema."""
    if config is None:
        config = DatabaseConfig()
    
    conn = get_db_connection(config)
    
    if schema_sql:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        cursor.close()
    
    conn.close()
    print(f"Database initialized at: {config.db_path}")


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    config: Optional[DatabaseConfig] = None,
    fetch: str = "all"
) -> list:
    """Execute a SQL query and return results."""
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