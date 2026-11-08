"""Central DuckDB manager for unified Brazilian Government public data lakehouse."""

import duckdb
import polars as pl
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table

from .config import settings

console = Console()


class DatabaseManager:
    """Manages local embedded DuckDB analytical database for all gov-skills."""

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(database=str(self.db_path), read_only=False)
        self._init_extensions()

    def _init_extensions(self):
        """Loads helpful DuckDB extensions like parquet, icu, spatial if available."""
        try:
            self.conn.execute("INSTALL parquet; LOAD parquet;")
            self.conn.execute("INSTALL icu; LOAD icu;")
        except Exception:
            pass

    def execute(self, sql: str, params: Optional[List[Any] | Dict[str, Any]] = None) -> duckdb.DuckDBPyConnection:
        """Executes a DDL or DML statement."""
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def query(self, sql: str, params: Optional[List[Any] | Dict[str, Any]] = None) -> List[tuple]:
        """Returns fetched tuples."""
        cur = self.execute(sql, params)
        return cur.fetchall()

    def query_df(self, sql: str, params: Optional[List[Any] | Dict[str, Any]] = None) -> pl.DataFrame:
        """Executes query and returns Polars DataFrame for high-performance analysis."""
        arrow_table = self.execute(sql, params).arrow()
        return pl.from_arrow(arrow_table)

    def insert_polars(self, table_name: str, df: pl.DataFrame, mode: str = "append"):
        """
        Inserts a Polars DataFrame into DuckDB table.
        mode: 'append' or 'replace'
        """
        arrow_table = df.to_arrow()
        if mode == "replace":
            self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM arrow_table")
        else:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM arrow_table WHERE 1=0")
            self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM arrow_table")

    def list_tables(self) -> List[str]:
        """Returns names of all tables currently stored in the database."""
        result = self.conn.execute("SHOW TABLES").fetchall()
        return [row[0] for row in result]

    def table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Returns columns and types for a table."""
        res = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return [{"column": row[0], "type": row[1], "null": row[2]} for row in res]

    def count(self, table_name: str) -> int:
        """Returns row count of a table."""
        try:
            return self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        except Exception:
            return 0

    def display_results(self, sql: str, params: Optional[List[Any] | Dict[str, Any]] = None, limit: int = 20):
        """Displays SQL query results as a formatted CLI table using Rich."""
        limited_sql = f"SELECT * FROM ({sql}) LIMIT {limit}" if "LIMIT" not in sql.upper() else sql
        if params:
            res = self.conn.execute(limited_sql, params)
        else:
            res = self.conn.execute(limited_sql)
        cols = [desc[0] for desc in res.description]
        rows = res.fetchall()

        table = Table(title=f"Resultados ({len(rows)} linhas)")
        for col in cols:
            table.add_column(col, style="cyan", overflow="fold")

        for row in rows:
            table.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])

        console.print(table)


_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Returns singleton DatabaseManager instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
