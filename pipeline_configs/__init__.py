# ==============================================================================
# PIPELINE CONFIGURATION SETTINGS
# ==============================================================================
import os
import re
import pytz
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()

"""
Configuration settings for Relational Databases ETL Pipeline.

This module contains all the configuration variables and settings
used throughout the pipeline components and scripts.
"""


class PipelineConfig:
    def __init__(self, data: dict) -> None:
        log.info("LOADING PIPELINE CONFIG...")
        try:
            # --- Google Cloud Configuration ---
            self.CLIENT_NUMBER: str = os.getenv("CLIENT_NUMBER")
            self.CLIENT_REGION: str = os.getenv("CLIENT_REGION")
            self.CLIENT_TIMEZONE: str = os.getenv("CLIENT_TIMEZONE")
            self.CLIENT_PROJECT_ID: str = os.getenv("CLIENT_PROJECT_ID")
            self.IST: pytz.timezone = pytz.timezone(self.CLIENT_TIMEZONE)
            self.ETL_SOURCE: str = data.get("ETL_SOURCE", "")
            self.WINDOW_DAYS: int = data.get("WINDOW_DAYS", 1)
            self.START_DATE: str = data.get("START_DATE", "")
            self.END_DATE: str = data.get("END_DATE", "")
            self.SAFETY_BUFFER_DAYS: int = 1
            self.SERVICE_ACCOUNT_KEY = os.getenv("SERVICE_ACCOUNT_KEY", None)
            self.BUCKET_NAME: str = f"etl-pipeline-statefiles-{self.CLIENT_NUMBER}"
            self.CLEAN_ETL_SOURCE: str = re.sub(r"[^0-9A-Za-z\s]+", "", self.ETL_SOURCE)
            self.FILENAME_NAME: str = re.sub(r"\s+", "_", self.CLEAN_ETL_SOURCE).strip(
                "_"
            )
            self.PIPELINE_NAME: str = "MicrosoftSQL"
            self.SCHEMA_FILEPATH: str = (
                f"{self.PIPELINE_NAME}/{self.FILENAME_NAME}.json"
            )
            # Mapping as a class constant for better performance
            self.MSSQL_TYPE_MAPPING: dict[str, str] = {
                # Integers
                "int": "INT64",
                "tinyint": "INT64",
                "smallint": "INT64",
                "bigint": "INT64",
                "bit": "BOOL",  # In MSSQL, 0/1 bit is the standard Boolean
                # Decimals & Floats
                "decimal": "NUMERIC",
                "numeric": "NUMERIC",
                "money": "NUMERIC",
                "smallmoney": "NUMERIC",
                "float": "FLOAT64",
                "real": "FLOAT64",
                # Date & Time
                "datetime": "DATETIME",
                "datetime2": "DATETIME",
                "smalldatetime": "DATETIME",
                "date": "DATE",
                "datetimeoffset": "TIMESTAMP",  # Includes timezone offset
                "timestamp": "BYTES",  # IMPORTANT: MSSQL 'timestamp' is a row version (binary), NOT a date!
                "rowversion": "BYTES",
                "time": "TIME",
                # Strings & Objects (Unicode and Non-Unicode)
                "char": "STRING",
                "varchar": "STRING",
                "nchar": "STRING",
                "nvarchar": "STRING",
                "text": "STRING",
                "ntext": "STRING",
                "xml": "STRING",
                # Binary
                "binary": "BYTES",
                "varbinary": "BYTES",
                "image": "BYTES",
                # Defaults / Others
                "uniqueidentifier": "STRING",  # UUIDs
            }

            # --- Relational Database Configuration ---
            self.MSSQL_USERNAME = os.getenv("MSSQL_USERNAME")
            self.MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")
            self.MSSQL_HOST = os.getenv("MSSQL_HOST")
            self.MSSQL_PORT = os.getenv("MSSQL_PORT")
            log.success("Pipeline Config loaded successfully")
            log.info(f"PIPELINE CONFIG LOADED")

        except Exception as e:
            log.error(f"Error in Pipeline Config: {str(e)}")
            raise e
