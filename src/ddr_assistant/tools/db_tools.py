import sqlite3
import pandas as pd
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from ddr_assistant.config import DatabaseConfig, get_db_connection

class SQLQuery(BaseModel):
    query: str = Field(description="A valid SQLite SELECT query")

@tool(args_schema=SQLQuery)
def query_drilling_db(query: str) -> str:
    """Execute a SQL SELECT query against the drilling reports database."""
    try:
        config = DatabaseConfig()
        conn = get_db_connection(config)
        df = pd.read_sql_query(query, conn)
        conn.close()
        print(f"Query: {query}")
        if df.empty:
            return "Query executed successfully. No results found."
        if len(df) > 10:
            return f"First 10 of {len(df)} results:\n" + df.head(10).to_markdown()
        return df.to_markdown()
    except Exception as e:
        return f"Error executing query: {str(e)} {query}"

@tool
def list_tables() -> str:
    """
    List available tables in the drilling database. 
    Use this if you need to know what types of data are available (e.g., fluid, gas, operations).
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
    Get the exact column names for tables in the drilling database.
    Use this before writing SQL queries to ensure you use the correct column names.
    """
    try:
        config = DatabaseConfig()
        conn = get_db_connection(config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
        
        schema_output = "Current Database Schema:\n"
        for table in tables:
            schema_output += f"\nTable: {table}\n"
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            for col in columns:
                pk = " (Primary Key)" if col[5] else ""
                schema_output += f"  - {col[1]} ({col[2]}){pk}\n"
        
        conn.close()
        return schema_output
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"
