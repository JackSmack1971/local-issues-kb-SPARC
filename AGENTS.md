# AGENTS.md: AI Collaboration Guide

This document provides essential context for AI models interacting with this project. Adhering to these guidelines will ensure consistency, maintain code quality, and optimize agent performance for the Issues→Fixes Knowledge Base system.

## 1. Project Overview & Purpose
*   **Primary Goal:** Maintain a local, file-first knowledge base for programming issues → fixes, optimized for AI agent ingestion and fast local search using SQLite FTS5.
*   **Business Domain:** Developer Tools, Knowledge Management, AI/ML Infrastructure for Code Analysis.
*   **Key Features:** Issue collection from multiple sources, SQLite FTS5 full-text search, LLM-ready chunk export, memory bank generation, license-aware data attribution.

## 2. Core Technologies & Stack
*   **Languages:** Python 3.x (primary), SQL (SQLite with FTS5 extension).
*   **Frameworks & Runtimes:** SQLite with FTS5 virtual tables, standard Python libraries.
*   **Databases:** SQLite with FTS5 extension for full-text search indexing.
*   **Key Libraries/Dependencies:** `requests>=2.32.2` (API collection), `pyyaml>=6.0.1` (YAML processing), `sqlite3` (built-in), `json`, `pathlib`, `hashlib`.
*   **Package Manager:** pip (using `requirements.txt`).
*   **Platforms:** Cross-platform Python (Linux, macOS, Windows) with local-only operation.

## 3. Architectural Patterns & Structure
*   **Overall Architecture:** File-first data storage with SQLite FTS5 indexing. Files are the source of truth, SQLite provides fast search capabilities, and exports enable LLM integration.
*   **Directory Structure Philosophy:**
    *   `/issuesdb`: Main data directory containing issues and search index.
    *   `/issuesdb/issues/<source>/<language>/`: Individual JSON issue files organized by source and language.
    *   `/scripts`: Collection, processing, and export utilities.
    *   `/schemas`: JSON schema validation files.
    *   `/memory_bank`: Generated context files for AI agents.
    *   `/exports`: LLM-ready chunk exports.
*   **Module Organization:** Script-based architecture with each Python script handling a specific workflow stage (collect, build, export, render).
*   **Common Patterns & Idioms:** 
    *   **File-first approach:** JSON files are canonical data source, database is derived.
    *   **SQLite FTS5:** Contentless FTS tables with external content references for space efficiency.
    *   **Chunking strategy:** Text chunked at paragraph boundaries with max 1400 characters.
    *   **Schema validation:** JSON schemas enforce data structure consistency.

## 4. Coding Conventions & Style Guide
*   **Formatting:** Follow PEP 8 Python style guide. Use 4-space indentation, 100-character line limit. Prefer f-strings for string formatting.
*   **Naming Conventions:** 
    *   Variables, functions: `snake_case` (e.g., `issue_id`, `write_issue`)
    *   Classes: `PascalCase` (minimal usage in this codebase)
    *   Constants: `SCREAMING_SNAKE_CASE` (e.g., `MAX_CHARS`, `ROOT`)
    *   Files: `snake_case.py`
*   **API Design Principles:** Simple, functional approach with clear input/output contracts. Functions should have single responsibilities and be easily testable.
*   **Documentation Style:** Use docstrings for complex functions. Inline comments for SQLite FTS5 specific optimizations and business logic.
*   **Error Handling:** Use assertions for preconditions (`assert 'issue_id' in doc`). Use try/except for external API calls and file operations. Fail fast with descriptive error messages.
*   **Forbidden Patterns:** **NEVER** hardcode API keys or secrets in source code. **DO NOT** modify SQLite schema without considering FTS5 implications from the ruleset.

## 5. Key Files & Entrypoints
*   **Main Scripts:** 
    *   `scripts/collect_sonar.py`: Collects issues from SonarCloud API
    *   `scripts/build_index.py`: Builds SQLite FTS5 search index from JSON files
    *   `scripts/chunk_export.py`: Exports issues to LLM-friendly chunks
    *   `scripts/render_memory_bank.py`: Generates memory bank context files
*   **Configuration:** 
    *   `requirements.txt`: Python dependencies
    *   `schemas/*.json`: JSON validation schemas
    *   `issues_index.sql`: SQLite FTS5 schema definition
*   **Data Storage:**
    *   `issuesdb/issues.sqlite`: SQLite database with FTS5 search index
    *   `issuesdb/issues/<source>/<language>/<issue_id>.json`: Individual issue files

## 6. Development & Testing Workflow
*   **Local Development Environment:** 
    ```bash
    # Setup
    pip install -r requirements.txt
    
    # Full workflow
    python scripts/collect_sonar.py --base https://sonarcloud.io --langs py --limit 200
    python scripts/build_index.py
    python scripts/chunk_export.py
    python scripts/render_memory_bank.py
    ```
*   **Task Configuration:** Each script is self-contained with command-line arguments. Use `--help` flag for script-specific options.
*   **Testing:** **All new functionality requires corresponding tests.** Test file structure should mirror source structure. Use `pytest` for testing framework. **CRITICAL:** Mock external API calls to prevent rate limiting and ensure deterministic tests.
*   **Quality Gates:**
    *   JSON schema validation (enforced in `write_issue()`)
    *   SQLite FTS5 integrity checks (`INSERT INTO table(table) VALUES('integrity-check')`)
    *   Ensure ≥1 signal per issue
    *   License attribution for all references
*   **CI/CD Process:** Manual workflow currently. Future: GitHub Actions for automated testing and data refresh.

## 7. Specific Instructions for AI Collaboration
*   **SQLite FTS5 Requirements:** **CRITICAL - Follow sqlite_fts5_ruleset.md guidelines:**
    *   Use explicit column definitions in FTS5 virtual tables
    *   Implement porter stemming tokenizer for English content search
    *   Use prefix indexes (`prefix='2 3 4'`) for autocomplete functionality
    *   Maintain contentless FTS tables with external content references
    *   Use `bm25()` function for relevance ranking
    *   Run integrity checks after bulk operations
    *   Configure appropriate tokenizers based on content type
*   **Data Collection Guidelines:**
    *   Always include rate limiting (`time.sleep(0.15)`) for API calls
    *   Clean HTML content using `clean_html()` utility function
    *   Validate all collected data against JSON schemas before writing
    *   Include license attribution in references array
    *   Use `sha1()` for generating deterministic issue IDs
*   **Security:** 
    *   **Local-only operation** - no external dependencies in production usage
    *   Validate and sanitize all external data inputs (HTML cleaning, JSON validation)
    *   **DO NOT** hardcode API endpoints or credentials - use command-line parameters
    *   Be mindful of PII when processing issue descriptions
*   **Dependencies:** Use `pip install <package>` and update `requirements.txt` with version constraints (`>=x.x.x`).
*   **Commit Messages & Pull Requests:** Follow conventional commits format (`feat:`, `fix:`, `docs:`). Include: What changed? Why? Breaking changes?
*   **Avoidances/Forbidden Actions:**
    *   **DO NOT** modify SQLite schema without consulting FTS5 ruleset
    *   **DO NOT** commit API keys or secrets to repository
    *   **NEVER** bypass JSON schema validation in data pipeline
    *   **DO NOT** modify existing issue files directly - use pipeline for updates
*   **Quality Assurance & Verification:** 
    *   **ALWAYS** run `python scripts/build_index.py` after data changes
    *   Verify SQLite FTS5 integrity: `INSERT INTO issues_fts(issues_fts) VALUES('integrity-check')`
    *   Test search functionality with sample queries after index changes
    *   Validate chunk export produces valid JSONL format
*   **Debugging Guidance:** 
    *   For SQLite issues: Use `.schema` and `PRAGMA table_info()` to inspect structure
    *   For FTS5 problems: Check `sqlite_fts5_ruleset.md` for optimization guidance
    *   For API collection errors: Include full response headers and status codes
    *   Use `json.dumps(obj, indent=2)` for readable JSON debugging output
*   **Project-Specific Quirks:**
    *   Issue IDs are SHA1 hashes for deterministic generation
    *   FTS5 uses contentless tables - content stored in main `issues` table
    *   Chunk export uses paragraph-boundary splitting with 1400 char max
    *   Memory bank files are auto-generated - modify templates in render script
    *   HTML cleaning removes script/style tags and converts entities
*   **Performance Considerations:**
    *   Batch SQLite operations using transactions
    *   Use FTS5 `merge` operations for index optimization after bulk updates
    *   Configure FTS5 `automerge` and `crisismerge` for production usage
    *   Monitor SQLite database size and consider `VACUUM` for cleanup
