# Repository Map

This document explains the structure of the repository.

It helps AI assistants and developers quickly understand
where different components are located.

---

# Top-Level Structure

project root

infra
scripts
jobs
docs
analytics

---

# infra/

Infrastructure configuration for the local data platform.

Key components:

docker-compose.yml

Subdirectories:

infra/hive
Hive Metastore configuration

infra/trino
Trino configuration

infra/spark
Spark configuration

infra/hive/cache
Local cache for large Hadoop dependencies

---

# scripts/

Utility scripts used for platform operation.

Examples:

prepare_hive_cache.ps1
Downloads required Hadoop dependencies.

render_catalog_configs.ps1
Generates configuration files from templates.

smoke_shared_catalog_spark_trino.ps1
Validates Spark write / Trino read through Iceberg catalog.

Scripts are preferred over manual command sequences.

---

# jobs/

Spark jobs used in the pipeline.

Examples:

shared_catalog_write_smoke.py

Future jobs:

silver → iceberg ingestion
gold metrics generation

---

# docs/

Project documentation.

Subdirectories:

docs/adr
Architecture Decision Records.

docs/learning
Learning notes and debugging history.

docs/assistant_context.md
Context snapshot for AI assistants.

docs/repository_map.md
This document.

---

# analytics/

dbt project for analytics engineering layer

source / staging / marts model structure

Trino-based analytics modeling on shared Iceberg catalog

---

# Data Platform Architecture

The project implements a simplified lakehouse.

Components:

Spark → data processing engine

Trino → query engine

Hive Metastore → shared Iceberg catalog

MinIO → object storage

Postgres → metastore database

---

# Data Flow

Raw ingestion
→ Silver transform
→ Iceberg tables
→ Shared catalog
→ Trino queries
→ dbt analytics layer

---

# Smoke Test Strategy

Smoke tests verify critical platform capabilities.

Example:

Spark creates Iceberg table
Trino reads the same table

If this passes, the shared catalog works.

---

# End
