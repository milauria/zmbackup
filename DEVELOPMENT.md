# Development Guide

This guide provides instructions for setting up the development environment and running code quality tools and tests.

## Virtual Environment Setup

It is highly recommended to use a virtual environment to manage project dependencies.

1.  **Create a virtual environment**:
    ```bash
    python3 -m venv .venv
    ```

2.  **Activate the virtual environment**:
    ```bash
    . .venv/bin/activate
    ```
    (On Windows, use `.venv\Scripts\activate` or `.\.venv\Scripts\Activate.ps1` for PowerShell)

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Code Quality Tools

This project uses `black` for code formatting, `isort` for import sorting, and `mypy` for static type checking.

Before committing your changes, please run these tools:

*   **Run Black (code formatter)**:
    ```bash
    . .venv/bin/activate && black src tests
    ```

*   **Run Isort (import sorter)**:
    ```bash
    . .venv/bin/activate && isort src tests
    ```

*   **Run Mypy (static type checker)**:
    ```bash
    . .venv/bin/activate && mypy src tests --explicit-package-bases
    ```

## Running Tests

Tests are written using `pytest`. To run all tests:

*   **Run Pytest**:
    ```bash
    . .venv/bin/activate && PYTHONPATH=./src pytest tests

## Updating the Dependencies

*   **Run Pytest**:
    ```bash
    pip freeze > requirements.txt
    ```