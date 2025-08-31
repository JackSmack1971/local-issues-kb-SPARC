# AGENTS.md: AI Collaboration Guide

This document provides essential context for AI models interacting with this project. Adhering to these guidelines will ensure consistency, maintain code quality, and optimize agent performance.

*It is Sunday, August 31, 2025. This guide is optimized for clarity, efficiency, and maximum utility for modern AI coding agents like OpenAI's Codex, GitHub Copilot Workspace, and Claude.*

*This file should be placed at the root of your repository. More deeply-nested AGENTS.md files (e.g., in subdirectories) will take precedence for specific sub-areas of the codebase. Direct user prompts will always override instructions in this file.*

## 1. Project Overview & Purpose

*   **Primary Goal:** Maintain a local-only, file-first knowledge base for programming issues → fixes, optimized for LLM agent ingestion and fast local search.
*   **Business Domain:** Developer tooling, AI/LLM integration, static analysis, code quality knowledge management.
*   **Key Features:** Issue collection from multiple sources (SonarCloud, etc.), local SQLite FTS5 search, chunked export for LLM consumption, memory bank generation for agent context, schema-validated JSON storage.

## 2. Core Technologies & Stack

*   **Languages:** Python 3.7+ (primary)
*   **Frameworks & Runtimes:** Command-line utilities, no web framework
*   **Databases:** SQLite with FTS5 (full-text search) for indexing, JSON files as source of truth
*   **Key Libraries/Dependencies:** requests>=2.32.2 (HTTP client), pyyaml>=6.0.1 (YAML parsing), sqlite3 (built-in), json (built-in), pathlib (built-in), hashlib (built-in), datetime (built-in), argparse (built-in)
*   **Package Manager:** pip
*   **Platforms:** Cross-platform (Python-based, tested on systems with Python 3.7+)

## 3. Architectural Patterns & Structure

*   **Overall Architecture:** File-first data pipeline with SQLite indexing. Files are the authoritative source of truth; SQLite provides fast search capabilities; exports enable LLM consumption.
*   **Directory Structure Philosophy:**
    *   `/issuesdb/issues/<source>/<language>/`: One JSON file per issue (source of truth)
    *   `/issuesdb/issues.sqlite`: SQLite FTS5 search index built from JSON files
    *   `/exports/`: Generated outputs for LLM consumption (chunks.jsonl)
    *   `/memory_bank/`: Generated markdown files providing agent context
    *   `/schemas/`: JSON schemas for data validation
    *   `/scripts/`: Collection, processing, and export utilities
*   **Module Organization:** Simple script-based architecture with clear separation of concerns: collection (`collect_sonar.py`), indexing (`build_index.py`), export (`chunk_export.py`), context generation (`render_memory_bank.py`), and utilities (`emit_issue.py`).
*   **Common Patterns & Idioms:**
    *   **File-First Approach:** JSON files are authoritative; database is derived/cached
    *   **Schema Validation:** All data follows JSON Schema specifications
    *   **Deterministic IDs:** SHA1 hashing for consistent issue identification
    *   **Chunking:** Text segmentation for LLM consumption (max 1400 chars)
    *   **UTC Timestamps:** ISO format with 'Z' suffix for consistency

## 4. Coding Conventions & Style Guide

*   **Formatting:** Follow PEP 8. Use 4-space indentation. Max line length appears to be flexible (some long lines present). *Inferred: Consider adding Black/autopep8 for consistency.*
*   **Naming Conventions:** Python standard - snake_case for variables, functions, and files; SCREAMING_SNAKE_CASE for constants; PascalCase for classes (when used).
*   **API Design Principles:** Simple, functional approach with clear data contracts. Functions should be single-purpose and composable.
*   **Documentation Style:** Use docstrings for public functions. Include type hints where beneficial. *Currently inferred - not consistently present in codebase.*
*   **Error Handling:** Use appropriate exceptions; validate inputs with assertions for critical requirements; use `raise_for_status()` for HTTP operations; handle file operations with proper encoding.
*   **Data Handling:** Always use `encoding='utf-8'` for file operations; use `ensure_ascii=False` for JSON serialization; sort JSON keys for consistency.
*   **Forbidden Patterns:** **NEVER** hardcode sensitive information (API keys, secrets). **NEVER** modify the core schema without updating validators.

## 5. Development & Testing Workflow

*   **Local Development Setup:**
    1. Ensure Python 3.7+ is installed
    2. Create virtual environment: `python3 -m venv .venv && source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
    3. Install dependencies: `pip install -r requirements.txt`
    4. Run the standard workflow pipeline as needed (see workflow below)
*   **Build Commands:** No traditional build process - this is a data pipeline project.
*   **Standard Workflow Pipeline:**
    ```bash
    # Collect issues from sources
    python scripts/collect_sonar.py --base https://sonarcloud.io --langs py --limit 200
    
    # Build search index
    python scripts/build_index.py
    
    # Export chunks for LLM consumption
    python scripts/chunk_export.py
    
    # Generate memory bank context
    python scripts/render_memory_bank.py
    ```
*   **Testing Commands:** *Note: No test files currently present in the codebase. This is an area for improvement.*
    *   **SHOULD ADD:** Unit tests for core functions (chunking, schema validation, data processing)
    *   **SHOULD ADD:** Integration tests for the full pipeline
    *   **Suggested:** `python -m pytest tests/` (after implementing tests)
*   **Linting/Formatting Commands:** *Inferred - not currently configured*
    *   **SHOULD ADD:** `python -m black .` for formatting
    *   **SHOULD ADD:** `python -m flake8 .` for linting
    *   **SHOULD ADD:** `python -m isort .` for import sorting
*   **CI/CD Process Overview:** *Not currently implemented - suggested for future enhancement.*

## 6. Git Workflow & PR Instructions

*   **Pre-Commit Checks:** *Inferred recommendations:*
    *   **SHOULD:** Run schema validation on any modified JSON files
    *   **SHOULD:** Ensure all scripts execute without errors
    *   **SHOULD:** Test the full pipeline if core functionality is modified
*   **Branching Strategy:** *Not explicitly defined - recommend standard Git flow*
*   **Commit Messages:** *No specific format enforced - suggest conventional commits:*
    *   Use clear, descriptive messages
    *   Follow format: `type: brief description` (e.g., `feat: add new data source`, `fix: handle encoding issues`)
*   **Pull Request (PR) Process:** *Not currently defined - suggest standard practices*
*   **Force Pushes:** **NEVER** use `git push --force` on shared branches
*   **Clean State:** **You MUST leave your worktree in a clean state after completing a task.**

## 7. Security Considerations

*   **General Security Practices:** **Be mindful of security** when handling file I/O, HTTP requests, and external data sources.
*   **Sensitive Data Handling:** **Do NOT** hardcode API keys, URLs with credentials, or other sensitive information. Use environment variables or configuration files (excluded from version control).
*   **Input Validation:** **ALWAYS** validate JSON data against schemas. Sanitize any user-provided input before processing.
*   **Vulnerability Avoidance:** Be cautious with:
    *   HTTP requests to external sources (validate SSL, handle timeouts)
    *   File path construction (prevent directory traversal)
    *   JSON parsing (handle malformed data gracefully)
*   **Dependency Management:** Keep dependencies updated. Regularly scan for vulnerabilities in `requests` and other external packages.

## 8. Specific Agent Instructions & Known Issues

*   **Tool Usage:**
    *   Use `python scripts/emit_issue.py` utilities for creating new issue documents
    *   Always validate new issues against `schemas/issue.schema.json`
    *   Use `pathlib` for file operations (already established pattern)
*   **Context Management:** 
    *   For large datasets, process in batches to avoid memory issues
    *   When modifying schemas, ensure backward compatibility or provide migration scripts
*   **Quality Assurance & Verification:** 
    *   **ALWAYS** run the full pipeline after making changes to core scripts
    *   **MUST** validate JSON schema compliance for any new or modified issue documents
    *   **MUST** ensure SQLite index rebuilds successfully after structural changes
*   **Project-Specific Quirks/Antipatterns:**
    *   Files are source of truth - **NEVER** modify the SQLite database directly
    *   Issue IDs are deterministic (SHA1-based) - don't generate random IDs
    *   Chunking logic has specific paragraph-based splitting - preserve this behavior
    *   UTC timestamps must include 'Z' suffix for consistency
*   **Data Collection Guidelines:**
    *   Always include proper attribution and licensing information in `references`
    *   Ensure at least one signal per issue for searchability
    *   Follow the established directory structure: `<source>/<language>/<issue_id>.json`
*   **Memory Bank Integration:** 
    *   The generated memory bank files (`/memory_bank/*.md`) provide context for other AI agents
    *   These files are auto-generated and should not be manually edited
    *   Update the rendering logic in `scripts/render_memory_bank.py` for structural changes

## Development Priorities

**Immediate improvements recommended:**
1. Add comprehensive test suite
2. Implement linting and formatting configuration  
3. Add CI/CD pipeline for automated validation
4. Document API endpoints for external data sources
5. Add configuration management for different environments

**Agent Focus Areas:**
- Maintain file-first architecture principles
- Ensure schema compliance for all data operations
- Preserve deterministic behavior for reproducible results
- Optimize for LLM consumption patterns in exports
