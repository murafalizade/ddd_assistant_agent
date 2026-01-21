import sqlite3
import pandas as pd
from typing import Optional
from langchain_core.tools import tool
from ddr_assistant.config import DatabaseConfig, get_db_connection

@tool
def query_drilling_db(query: str) -> str:
    """
    Execute a SQL query against the drilling reports database.
    Use this to retrieve data from tables: report_metadata, operations, drilling_fluid, and gas_readings.
    Input should be a valid SQLite query.
    """
    try:
        config = DatabaseConfig()
        conn = get_db_connection(config)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Debug print: results will appear in your terminal, not in the chat UI
        print(df.values.tolist())
        if df.empty:
            return "Query executed successfully. No results found."
        # Limit results for LLM context
        if len(df) > 10:
            return f"First 10 of {len(df)} results:\n" + df.head(10).to_markdown()
        return df.to_markdown()
    except Exception as e:
        return f"Error executing query: {str(e)}"

@tool
def list_tables() -> str:
    """
    List all available tables in the drilling database with a brief description of their purpose.
    Use this first to decide which table likely contains the information you need.
    """
    return """
1. **report_metadata**: Core metadata for each daily report. Contains high-level info like rig name, operator, date (report_period), well depth, and overall summaries.
2. **operations**: Time-log of activities. Use this for questions about "what happened at 10:00" or "how long did drilling take".
3. **drilling_fluid**: Technical parameters of the drilling mud (density, viscosity, etc.).
4. **gas_readings**: Detailed gas chromatography data (C1-C5) and total gas levels at specific depths.
"""

@tool
def get_db_schema() -> str:
    """
    Get the dynamic FULL schema of the drilling database directly from the SQL engine.
    Use this to see the current tables and exact column names for your SQL queries.
    """
    try:
        config = DatabaseConfig()
        conn = get_db_connection(config)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
        
        schema_output = "Current Database Schema:\n"
        for table in tables:
            schema_output += f"\nTable: {table}\n"
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            for col in columns:
                # col[1] is name, col[2] is type, col[4] is default value, col[5] is pk
                pk = " (Primary Key)" if col[5] else ""
                schema_output += f"  - {col[1]} ({col[2]}){pk}\n"
        
        conn.close()
        return schema_output
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"
