# AGENTS.md

This file defines the operating rules for AI assistants working on this repository.

The goal is to ensure that different AI sessions (ChatGPT, Codex, Copilot, etc.)
can continue development with consistent behavior.

---

# 1. Project Goal

This repository is a **project-based learning platform** for building a
realistic data platform.

Learning path:

Data Engineer
→ ML Engineer
→ AI Engineer

The project mimics real-world data platform architecture.

---

# 2. Development Workflow

All development follows **PR-based workflow**.

Steps:

1. design the change
2. implement in a feature branch
3. add smoke tests if needed
4. update documentation
5. create PR

Branch naming:

feat/<feature-name>
fix/<issue-name>
chore/<maintenance>

Example:

feat/dbt-trino-gold-models

---

# 3. Coding Principles

Follow these rules when generating code.

### Prefer reproducibility

Local environments must be reproducible.

Avoid solutions that require manual steps.

---

### Avoid committing large binary artifacts

Never commit:

* large JAR files
* datasets
* cache directories
* build artifacts

Use:

* local cache
* download scripts
* docker volumes

---

### Prefer scripts over manual commands

If a workflow requires more than one manual command,
convert it into a script under:

scripts/

Example:

prepare_hive_cache.ps1
smoke_shared_catalog_spark_trino.ps1

---

### Deterministic smoke tests

Smoke tests must be:

* deterministic
* rerunnable
* environment-independent

Example pattern:

drop table if exists
create table
insert test rows
validate results

---

# 4. Infrastructure Principles

Infrastructure is defined under:

infra/

Components:

Spark
Trino
Hive Metastore
MinIO
Postgres

The architecture follows a **lakehouse multi-engine pattern**.

Spark → write engine
Trino → query engine
Hive Metastore → Iceberg catalog

---

# 5. Documentation Rules

Important decisions must be documented.

Two types of documents exist:

### ADR

docs/adr/

Architecture decision records.

Used when:

* architecture changes
* major infrastructure changes

---

### Learning Notes

docs/learning/

These capture:

* mistakes
* debugging process
* lessons learned

Learning notes are written in Korean.

---

# 6. Smoke Testing

Smoke tests validate the local platform.

Location:

scripts/

Example:

smoke_shared_catalog_spark_trino.ps1

Validation pattern:

Spark write → Trino read

---

# 7. Security Rules

Credentials must not be committed to Git.

Configuration files should be generated from:

infra/.env

Templates are stored as:

*.template

Rendered files are ignored by Git.

---

# 8. AI Assistant Behavior

AI assistants should:

* prefer minimal design
* avoid overengineering
* keep infrastructure reproducible
* update documentation with changes
* explain reasoning when architecture changes

When unsure, ask before modifying infrastructure.

---

# End
