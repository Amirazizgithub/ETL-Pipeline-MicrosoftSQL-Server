import re
import os
import time
import json
import functools
import pyodbc
from pipeline_configs import PipelineConfig
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()


class BigQueryNamespaceValidator:
    @staticmethod
    def validate_dataset_name(raw_name: str) -> str:
        """
        Cleans and validates a MySQL database name for BigQuery compatibility.
        """
        if not raw_name:
            raise ValueError("Database name is empty or None")

        clean_name = raw_name.lower()
        clean_name = re.sub(r"[-\s]+", "_", clean_name)
        clean_name = re.sub(r"[^a-z0-9_]", "", clean_name)

        if clean_name[0].isdigit():
            clean_name = f"db_{clean_name}"

        reserved_words = {"all", "default", "information_schema", "public"}
        if clean_name in reserved_words:
            clean_name = f"data_{clean_name}"

        return clean_name[:1024]


def retry_microsoftsql_connection(retries=3, delay=1, backoff=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            m_retries, m_delay = retries, delay
            while m_retries > 1:
                try:
                    return func(*args, **kwargs)
                except pyodbc.Error as e:
                    log.warning(f"Connection failed: {e}. Retrying in {m_delay}s...")
                    time.sleep(m_delay)
                    m_retries -= 1
                    m_delay *= backoff
            return func(*args, **kwargs)

        return wrapper

    return decorator


class MicrosoftSqlConfig(PipelineConfig):
    def __init__(self, data: dict) -> None:
        super().__init__(data=data)
        # Blacklist for sensitive or irrelevant columns
        self.BLACKLIST_REGEX = re.compile(
            r"(birth|dob|delet|expir|valid_from|valid_to)"
        )
        self.live_schema_info = {}
        log.debug("MicrosoftSqlConfig class initialized")

    # def _save_schema_local(self, filepath: str, schema: dict) -> None:
    #     with open(filepath, "w") as f:
    #         log.info(f"Saving schema state to {filepath}...")
    #         json.dump(schema, f, indent=4)

    @retry_microsoftsql_connection(retries=3, delay=2, backoff=2)
    def _microsoftsql_connector(self, database=None):
        log.info(f"{25*'='} Initiating MSSQL Connection {25*'='}")
        try:
            # Using ODBC Driver 18 (ensure this is installed on your runner)
            if database:
                conn_args = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={self.MSSQL_HOST},{self.MSSQL_PORT};"
                    f"UID={self.MSSQL_USERNAME};"
                    f"PWD={self.MSSQL_PASSWORD};"
                    f"Database={database};"
                    f"Encrypt=yes;"
                    f"TrustServerCertificate=yes;"
                    f"LoginTimeout=30;"
                )
            else:
                conn_args = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={self.MSSQL_HOST},{self.MSSQL_PORT};"
                    f"UID={self.MSSQL_USERNAME};"
                    f"PWD={self.MSSQL_PASSWORD};"
                    f"Encrypt=yes;"
                    f"TrustServerCertificate=yes;"
                    f"LoginTimeout=30;"
                )
            return pyodbc.connect(conn_args, autocommit=True)
        except pyodbc.Error as err:
            log.error(f"MSSQL Connection Error: {err}")
            return None

    def _sanitize_bigquery_columns(self, columns: dict) -> dict:
        """
        Sanitizes dictionary keys to follow BigQuery column naming conventions.
        Returns a new dictionary with cleaned keys and original types.
        """
        try:
            sanitized_columns = {}

            for col_name, col_type in columns.items():
                # 1. Replace all non-alphanumeric characters (except underscores) with '_'
                clean_name = re.sub(r"[^0-9a-zA-Z_]", "_", col_name)

                # 2. Collapse multiple underscores into one
                clean_name = re.sub(r"_+", "_", clean_name)

                # 3. Strip leading/trailing underscores (optional but recommended for cleanliness)
                clean_name = clean_name.strip("_")

                # 4. BigQuery names must start with a letter or underscore.
                # If it starts with a number, prepend an underscore.
                if re.match(r"^[0-9]", clean_name):
                    clean_name = f"_{clean_name}"

                # 5. Handle empty strings (if original name was only special characters)
                if not clean_name:
                    clean_name = f"unnamed_column_{len(sanitized_columns)}"

                sanitized_columns[clean_name] = col_type
            # log.info(f"Sanitized columns: {len(sanitized_columns)}")
            return sanitized_columns

        except Exception as e:
            log.error(f"Error sanitizing columns: {e}")
            raise e

    def _get_sync_date_column(self, mssql_types: dict) -> str:
        if not mssql_types:
            return None

        # MSSQL specific date types
        date_types = {
            "datetime",
            "datetime2",
            "smalldatetime",
            "datetimeoffset",
            "date",
        }
        priority_keywords = ["updat", "modif", "chang", "sync", "last"]
        fallback_keywords = ["creat", "insert", "event", "ts", "timestamp"]

        best_match = None
        best_priority_index = float("inf")
        found_generic_date = None

        for col, dtype in mssql_types.items():
            col_lower = col.lower()
            dtype_lower = dtype.lower()

            if self.BLACKLIST_REGEX.search(col_lower):
                continue

            if not any(d in dtype_lower for d in date_types):
                continue

            if not found_generic_date:
                found_generic_date = col

            for i, kw in enumerate(priority_keywords):
                if kw in col_lower and i < best_priority_index:
                    best_match = col
                    best_priority_index = i
                    break

            if best_match is None:
                for i, kw in enumerate(fallback_keywords):
                    actual_prio = i + len(priority_keywords)
                    if kw in col_lower and actual_prio < best_priority_index:
                        best_match = col
                        best_priority_index = actual_prio
                        break

        return best_match if best_match else found_generic_date

    def _map_mssql_to_bigquery_schema(self, mssql_schema: dict) -> dict:
        bq_schema = {}
        for column, dtype in mssql_schema.items():
            base_type = str(dtype).lower().strip()

            # Handling common MSSQL string types
            if any(
                kw in base_type
                for kw in ["varchar", "nvarchar", "text", "ntext", "char", "nchar"]
            ):
                bq_schema[column] = "STRING"
            elif "bit" in base_type:
                bq_schema[column] = "BOOLEAN"
            elif any(
                kw in base_type for kw in ["decimal", "numeric", "money", "smallmoney"]
            ):
                bq_schema[column] = "NUMERIC"
            else:
                bq_schema[column] = self.MSSQL_TYPE_MAPPING.get(base_type, "STRING")
        return bq_schema

    def _get_all_table_schema_with_dtype(self) -> dict:
        log.info(f"{25*'='} Fetching MSSQL Schemas {25*'='}")
        conn = self._microsoftsql_connector()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            # MSSQL query to get user databases
            cursor.execute(
                "SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')"
            )
            databases = [db[0] for db in cursor.fetchall()]
            cursor.close()
            conn.close()

            for db_name in databases:
                db_conn = self._microsoftsql_connector(database=db_name)
                if not db_conn:
                    continue

                current_db_tables = {}
                try:
                    db_cursor = db_conn.cursor()
                    # Query to get tables and their primary keys using system views
                    # fmt: off
                    schema_query = """
                        SELECT 
                            t.name AS table_name,
                            c.name AS column_name,
                            tp.name AS data_type,
                            ISNULL(i.is_primary_key, 0) AS is_pk
                        FROM sys.tables t
                        JOIN sys.columns c ON t.object_id = c.object_id
                        JOIN sys.types tp ON c.user_type_id = tp.user_type_id
                        LEFT JOIN sys.index_columns ic ON ic.object_id = t.object_id AND ic.column_id = c.column_id
                        LEFT JOIN sys.indexes i ON i.object_id = t.object_id AND i.index_id = ic.index_id AND i.is_primary_key = 1
                        WHERE t.is_ms_shipped = 0
                    """
                    # fmt: on
                    db_cursor.execute(schema_query)
                    rows = db_cursor.fetchall()

                    # Organize flat rows into table structures
                    table_data = {}
                    for row in rows:
                        t_name, col_name, d_type, is_pk = row
                        if t_name not in table_data:
                            table_data[t_name] = {"cols": {}, "pk": None}

                        table_data[t_name]["cols"][col_name] = d_type
                        if is_pk:
                            table_data[t_name]["pk"] = col_name

                    for t_name, info in table_data.items():
                        sanitized_columns = self._sanitize_bigquery_columns(
                            info["cols"]
                        )
                        current_db_tables[t_name] = {
                            "columns": self._map_mssql_to_bigquery_schema(
                                sanitized_columns
                            ),
                            "primary_key": info["pk"],
                            "sync_date_column": self._get_sync_date_column(
                                info["cols"]
                            ),
                        }

                    bq_dataset = BigQueryNamespaceValidator.validate_dataset_name(
                        db_name
                    )
                    self.live_schema_info[bq_dataset] = current_db_tables
                    db_cursor.close()
                finally:
                    db_conn.close()

        except Exception as e:
            log.error(f"Global Schema Fetch Error: {e}")

        # self._save_schema_local("live_schema_info.json", self.live_schema_info)
        return self.live_schema_info


# Example Usage:
# if __name__ == "__main__":
#     data = {"START_DATE": "", "END_DATE": "", "ETL_SOURCE": "MicrosoftSQL", "WINDOW_DAYS": 1}
#     config = MicrosoftSqlConfig(data=data)
#     live_schema = config._get_all_table_schema_with_dtype()
# print(live_schema)
