# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Commands
- **Lint**: `black src tests && isort src tests && mypy src tests --explicit-package-bases`
- **Test**: `PYTHONPATH=./src pytest tests`
- **Single Test**: `PYTHONPATH=./src pytest tests/path/to/test.py`
- **Init Config**: `sudo python3 src/zmbackup.py init` (Requires root)

## Code Style
- **Formatting**: Black (120 chars), isort (profile: black).
- **Types**: Mandatory type hinting (Python 3.12+), checked by `mypy`.
- **Imports**: `isort` configured with `known_first_party = ["src"]`. Avoid circular imports; use `TYPE_CHECKING` blocks for type-only imports in clients.
- **Config**: Use `attrs.frozen` for configuration objects (`src/lib/config.py`).
- **Database**: Use SQLAlchemy ORM with `DatabaseSessionManager` context manager for all DB operations.

## Project Gotchas
- **Config Path**: Default is `/etc/zmbackup/zmbackup.conf`. Use `--config-path` to override.
- **Root Requirement**: `init` command and writing to `/etc/` requires root privileges.
- **Mutually Exclusive Flags**: In `backup` command, `--mail`, `--distributionlist`, `--alias`, and `--ldap` are mutually exclusive.
- **Database Client**: `DatabaseClient` automatically creates tables on initialization by default.
- **Jinja2 Templates**: Configuration is generated from templates in `src/templates/`.
- **Session ID**: Generated via `generate_session_uuid()` combining type and timestamp.
