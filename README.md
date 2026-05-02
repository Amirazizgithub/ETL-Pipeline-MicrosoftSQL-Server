# ETL-Pipeline-MicrosoftSQL-Server

---

## 📖 Overview

**etl-pipeline-microsoftsql-server** is an automated ETL (Extract, Transform, Load) pipeline designed to extract data from **Microsoft SQL Server**, process and transform it, and load it into **Google BigQuery**. It supports full historical data extraction as well as incremental syncing. The project exposes these ETL processes via a FastAPI application and is containerized for deployment on Kubernetes.

---

## 📂 Project Structure

```plaintext
etl-pipeline-microsoftsql-server/
├── pipeline_configs/           # Core pipeline configurations
│   └── __init__.py
├── routes/                     # API route definitions
│   ├── run_cron_job.py         # FastAPI endpoint for periodic incremental syncs
│   └── run_historic_job.py     # FastAPI endpoint for triggering historic data extractions
├── gitlab-pipelines/           # CI/CD pipelines for various environments
│   ├── .gitlab-ci-dev.yml      # Development pipeline
│   ├── .gitlab-ci-update.yml   # Update pipeline
│   ├── .gitlab-ci-stag.yml     # Staging pipeline
│   └── .gitlab-ci-prod.yml     # Production pipeline
├── k8s-pipelines/              # Kubernetes Manifests
│   ├── cronjob-data-sync-deploy-service.yml # K8s CronJob configuration for scheduled syncs
│   └── historic-data-deploy-service.yml     # K8s Deployment for the historic job API
├── scripts/                    # Core ETL logic
│   ├── data_extractor.py       # Connects to MSSQL and extracts data incrementally
│   ├── data_loader.py          # Loads transformed data into BigQuery
│   ├── data_transformer.py     # Cleans data and reformats schemas for BigQuery compatibility
│   ├── gcp_manager.py          # Manages GCP operations and dataset lifecycles
│   ├── microsoftsql_config.py  # MSSQL connection handling, schema fetching & data type mapping
│   └── run_etl_pipeline.py     # Main orchestrator to run the complete ETL flow
├── utils/                      # Helper utilities
│   ├── gcpcloud_postgres_conn.py # Legacy/Optional Postgres connections
│   └── logger.py               # Centralized logging configuration
├── Dockerfile                  # Containerization instructions
├── requirements.txt            # Python dependencies
└── .env (example)              # Environment variables template
```

---

## ⚙️ Key Flow

1. **Extraction (`data_extractor.py`)**: Uses `pyodbc` to connect to Microsoft SQL Server. It identifies the maximum sync dates and handles incremental fetches or full syncs depending on configuration.
2. **Transformation (`data_transformer.py` & `microsoftsql_config.py`)**: Scrubs and maps MSSQL column names and data types to valid BigQuery compatible schemas.
3. **Loading (`data_loader.py` & `gcp_manager.py`)**: Utilizes Google Cloud authentication to push datasets to the corresponding BigQuery tables.
4. **Orchestration (`run_etl_pipeline.py`)**: Ties the modules together and logs progression.
5. **API Gateways (`routes/`)**: Exposes FastAPI endpoints bringing the pipeline to life for on-demand processing.

---

## 🛠️ Prerequisites & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Amirazizgithub/ETL-Pipeline-MicrosoftSQL-Server.git
cd etl-pipeline-microsoftsql-server
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

You'll need the ODBC Driver 18 for SQL Server installed on your system to connect to MSSQL.
Install Python libraries via:
```bash
pip install -r requirements.txt
```

### 4. Configuration

Provide an `.env` file at the root of the project with the corresponding MSSQL and Google Cloud credentials:
```env
MSSQL_HOST=your_host
MSSQL_PORT=1433
MSSQL_USERNAME=your_username
MSSQL_PASSWORD=your_password

CLIENT_PROJECT_ID=your_gcp_project_id
# And other required settings as seen in your settings module...
```
You will also need to place your Service Account JSON key in the directory, mapped properly.

---

## 🚀 Deployment

The project handles containerization using Docker and runs scheduled operations mapped through GitLab CI/CD pipelines deploying to a **Kubernetes cluster**.

- **Cron Jobs**: Run routinely to fetch incremental patches from Microsoft SQL to keep BigQuery updated (managed via `cronjob-data-sync-deploy-service.yml`).
- **Historic Data Syncs**: Exposed via FastAPI on Kubernetes to ingest historical database structures entirely (managed via `historic-data-deploy-service.yml`).

## 🐳 Docker Deployment

### Build the Docker image:
```bash
docker build -t etl-pipeline-microsoftsql-server-{ENVIRONMENT}:latest .
```

### Run the container:
```bash
docker run -p 8000:8000 etl-pipeline-microsoftsql-server-{ENVIRONMENT}:latest
```

## 🛠️ CI/CD Pipelines

The project includes GitLab CI/CD pipelines for:

- **Development**: Code formatting and linting
- **Staging**: Automated testing and deployment
- **Production**: Full deployment pipeline

Pipelines are triggered based on branch:
- development branch: Development pipeline
- staging branch: Staging deployment
- production branch: Production deployment

### Logging

The application uses structured logging configured in app/utils/logger.py. Logs include:
- API request/response details
- Error tracking
- Performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: git checkout -b feature/your-feature
3. Make your changes and add tests
4. Run tests: pytest
5. Format code: black .
6. Commit your changes: git commit -am 'Add your feature'
7. Push to the branch: git push origin feature/your-feature
8. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## ⚙️ Support

For support or questions:
- Create an issue in the repository
- Contact the development team