"""Database manager for storing DDR report data."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ddr_assistant.config import DatabaseConfig, get_db_connection
from ddr_assistant.utils.models import (
    DrillingFluidRecord,
    GasReadingRecord,
    OperationRecord,
    ReportMetadata,
)


class DatabaseManager:
    """Manage database operations for DDR reports."""
    
    # Database schema
    SCHEMA = """
    -- Report metadata table
    CREATE TABLE IF NOT EXISTS report_metadata (
        report_id TEXT PRIMARY KEY,
        status TEXT,
        report_creation_time TEXT,
        report_number TEXT,
        days_ahead_behind TEXT,
        operator TEXT,
        rig_name TEXT,
        drilling_contractor TEXT,
        spud_date TEXT,
        wellbore_type TEXT,
        wellbore_name TEXT,
        date_well_complete TEXT,
        report_period TEXT,
        summary_activities TEXT,
        planned_activities TEXT,
        file_name TEXT,
        elevation_rkb_msl_m REAL,
        water_depth_msl_m REAL,
        dist_drilled_m REAL,
        penetration_rate_m_h REAL,
        hole_dia_in REAL,
        pressure_test_type TEXT,
        formation_strength_g_cm3 REAL,
        dia_last_casing TEXT,
        tight_well TEXT,
        hpht TEXT,
        temperature TEXT,
        pressure TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    
    -- Operations table
    CREATE TABLE IF NOT EXISTS operations (
        operation_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        end_depth_mmd REAL,
        main_sub_activity TEXT,
        state TEXT,
        remark TEXT,
        created_at TEXT,
        FOREIGN KEY (report_id) REFERENCES report_metadata(report_id) ON DELETE CASCADE
    );
    
    -- Drilling fluid table
    CREATE TABLE IF NOT EXISTS drilling_fluid (
        fluid_record_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        parameter_name TEXT,
        value TEXT,
        unit TEXT,
        created_at TEXT,
        FOREIGN KEY (report_id) REFERENCES report_metadata(report_id) ON DELETE CASCADE
    );
    
    -- Gas readings table
    CREATE TABLE IF NOT EXISTS gas_readings (
        gas_reading_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        depth_m REAL,
        c1 REAL,
        c2 REAL,
        c3 REAL,
        ic4 REAL,
        nc4 REAL,
        ic5 REAL,
        nc5 REAL,
        total_gas REAL,
        trip_gas REAL,
        background_gas REAL,
        connection_gas REAL,
        created_at TEXT,
        FOREIGN KEY (report_id) REFERENCES report_metadata(report_id) ON DELETE CASCADE
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_operations_report_id ON operations(report_id);
    CREATE INDEX IF NOT EXISTS idx_drilling_fluid_report_id ON drilling_fluid(report_id);
    CREATE INDEX IF NOT EXISTS idx_gas_readings_report_id ON gas_readings(report_id);
    CREATE INDEX IF NOT EXISTS idx_report_metadata_report_number ON report_metadata(report_number);
    CREATE INDEX IF NOT EXISTS idx_report_metadata_rig_name ON report_metadata(rig_name);
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager.
        
        Args:
            config: Database configuration. If None, uses default.
        """
        self.config = config or DatabaseConfig()
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema and handle migrations."""
        conn = get_db_connection(self.config)
        cursor = conn.cursor()
        cursor.executescript(self.SCHEMA)
        
        # Simple migration: add missing columns to report_metadata
        cursor.execute("PRAGMA table_info(report_metadata)")
        existing_cols = [col[1] for col in cursor.fetchall()]
        
        new_cols = [
            ('wellbore_name', 'TEXT'),
            ('report_period', 'TEXT'),
            ('summary_activities', 'TEXT'),
            ('planned_activities', 'TEXT'),
            ('file_name', 'TEXT')
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE report_metadata ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    print(f"Migration error for {col_name}: {e}")
                    
        conn.commit()
        cursor.close()
        conn.close()
    
    def save_report_metadata(self, metadata: ReportMetadata) -> str:
        """Save report metadata to database.
        
        Args:
            metadata: ReportMetadata instance
            
        Returns:
            The report_id
        """
        df = pd.DataFrame([metadata.to_dict()])
        
        conn = get_db_connection(self.config)
        df.to_sql(
            'report_metadata',
            conn,
            if_exists='append',
            index=False,
        )
        conn.close()
        
        return metadata.report_id
    
    def save_operations(
        self, operations: List[OperationRecord]
    ) -> int:
        """Save operation records to database.
        
        Args:
            operations: List of OperationRecord instances
            
        Returns:
            Number of records saved
        """
        if not operations:
            return 0
        
        df = pd.DataFrame([op.to_dict() for op in operations])
        
        conn = get_db_connection(self.config)
        df.to_sql(
            'operations',
            conn,
            if_exists='append',
            index=False,
        )
        conn.close()
        
        return len(operations)
    
    def save_drilling_fluid(
        self, fluid_records: List[DrillingFluidRecord]
    ) -> int:
        """Save drilling fluid records to database.
        
        Args:
            fluid_records: List of DrillingFluidRecord instances
            
        Returns:
            Number of records saved
        """
        if not fluid_records:
            return 0
        
        df = pd.DataFrame([rec.to_dict() for rec in fluid_records])
        
        conn = get_db_connection(self.config)
        df.to_sql(
            'drilling_fluid',
            conn,
            if_exists='append',
            index=False,
        )
        conn.close()
        
        return len(fluid_records)
    
    def save_gas_readings(
        self, gas_readings: List[GasReadingRecord]
    ) -> int:
        """Save gas reading records to database.
        
        Args:
            gas_readings: List of GasReadingRecord instances
            
        Returns:
            Number of records saved
        """
        if not gas_readings:
            return 0
        
        df = pd.DataFrame([rec.to_dict() for rec in gas_readings])
        
        conn = get_db_connection(self.config)
        df.to_sql(
            'gas_readings',
            conn,
            if_exists='append',
            index=False,
        )
        conn.close()
        
        return len(gas_readings)
    
    def save_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = 'append'
    ) -> int:
        """Save a DataFrame directly to database.
        
        Args:
            df: DataFrame to save
            table_name: Name of the table
            if_exists: How to behave if table exists ('fail', 'replace', 'append')
            
        Returns:
            Number of rows saved
        """
        conn = get_db_connection(self.config)
        df.to_sql(
            table_name,
            conn,
            if_exists=if_exists,
            index=False,
        )
        conn.close()
        
        return len(df)
    
    def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """Get report metadata by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Dictionary with report data or None
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(
            "SELECT * FROM report_metadata WHERE report_id = ?",
            conn,
            params=(report_id,)
        )
        conn.close()
        
        if len(df) == 0:
            return None
        
        return df.iloc[0].to_dict()
    
    def get_operations_by_report(self, report_id: str) -> pd.DataFrame:
        """Get all operations for a report.
        
        Args:
            report_id: Report ID
            
        Returns:
            DataFrame with operations
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(
            "SELECT * FROM operations WHERE report_id = ? ORDER BY start_time",
            conn,
            params=(report_id,)
        )
        conn.close()
        
        return df
    
    def get_drilling_fluid_by_report(self, report_id: str) -> pd.DataFrame:
        """Get drilling fluid data for a report.
        
        Args:
            report_id: Report ID
            
        Returns:
            DataFrame with drilling fluid data
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(
            "SELECT * FROM drilling_fluid WHERE report_id = ?",
            conn,
            params=(report_id,)
        )
        conn.close()
        
        return df
    
    def get_gas_readings_by_report(self, report_id: str) -> pd.DataFrame:
        """Get gas readings for a report.
        
        Args:
            report_id: Report ID
            
        Returns:
            DataFrame with gas readings
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(
            "SELECT * FROM gas_readings WHERE report_id = ? ORDER BY depth_m",
            conn,
            params=(report_id,)
        )
        conn.close()
        
        return df
    
    def get_all_reports(self) -> pd.DataFrame:
        """Get all reports metadata.
        
        Returns:
            DataFrame with all reports
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(
            "SELECT * FROM report_metadata ORDER BY report_creation_time DESC",
            conn
        )
        conn.close()
        
        return df
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report and all related data.
        
        Args:
            report_id: Report ID
            
        Returns:
            True if deleted, False if not found
        """
        conn = get_db_connection(self.config)
        cursor = conn.cursor()
        
        # Check if report exists
        cursor.execute(
            "SELECT COUNT(*) FROM report_metadata WHERE report_id = ?",
            (report_id,)
        )
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.close()
            conn.close()
            return False
        
        # Delete report (cascades to related tables)
        cursor.execute(
            "DELETE FROM report_metadata WHERE report_id = ?",
            (report_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    
    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a custom SQL query.
        
        Args:
            sql: SQL query
            params: Query parameters
            
        Returns:
            DataFrame with results
        """
        conn = get_db_connection(self.config)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        
        return df
