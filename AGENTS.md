# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Dev Environment Setup
- **MANDATORY** to use minion for running tests and building environment
- **MANDATORY** to write unit tests for any code you create

## Commands
- **Lint**: `./minion format`
- **Test**: `./minion test`
- **Single Test**: `./minion test tests/path/to/test.py`

## Code Style
- **MANDATORY** include type hinting
- **MANDATORY** one class per file
- **NEVER** design circular dependencies
- **MANDATORY** use SQLAlchemy ORM with `DatabaseSessionManager` context manager for all DB operations.
- **NEVER** use `TYPE_CHECKING` to solve circular dependencies
- **MANDATORY** define `__all__` in `__init__.py` files to explicity list public module exports
- **NEVER** use typing.Any unless using it to avoid making deeply nested generic type hints
    - Prefer using TypeDict, NamedTuple, or custom classes for complex data structures
    - Use typing.Any only as a last resort when other typing solutions become unwieldy
    - Acceptable case: replacing overly nested structures like Dict[str, Dict[str, List[int]]] with Dict[str, Any]
    - Document the reason for using Any in comment when used
- **MANDATORY** include clear docstring following reST format. Example:
```
def calculate_loan_payment(principal: float, annual_rate: float, years: int, extra_payment: float = 0) -> float:
    """
    Calculate the monthly payment for a loan with optional extra payments.
    
    This function computes the standard monthly payment using the amortization
    formula and adds any extra payment amount specified by the user.
    
    :param principal: The initial loan amount in dollars
    :param annual_rate: The annual interest rate as a decimal (e.g., 0.05 for 5%)
    :param years: The loan term in years
    :param extra_payment: Additional amount to pay each month (optional)
    :return: The total monthly payment amount
    :raises ValueError: If principal, annual_rate, or years is negative
    :raises ZeroDivisionError: If annual_rate is zero
    
    .. note::
       This calculation assumes monthly compounding and payments.
    
    .. warning::
       Interest rates should be provided as decimals, not percentages.
    
    :Example:
    
    >>> calculate_loan_payment(200000, 0.045, 30)
    1013.37
    >>> calculate_loan_payment(200000, 0.045, 30, extra_payment=200)
    1213.3
    """
```
- **MANDATORY** to always design code for dependency injection instead of relying on monkey patching
    * Design classes and functions to accept dependencies as constructor parameters or function arguments
    * Prefer injecting real objects or test specific implementations over monkey pathing module-level. Example of what is MANDATORY:
    ```
    class Example:
    def __init__(data_instance: DataClass):
        self.data_instance = data_instance
    ```
    * Example of what SHOULD NOT do:
        ```
    class Example:
    def __init__():
        self.data_instance = DataClass()
    ```

## Test Rules
* **MANDATORY** achieve 100% code coverage on changes, verified using pytest-cov
* **NEVER** mock internal code, only external dependencies
* **MANDATORY** use of `@pytest.mark.parametrize` decorator to reduce the number of single tests that do the same thing but has different parameters
* **NEVER** create tests for enums, constants and exceptions. Use `# pragma: no cover` to ignore on python-cov
* **MANDATORY** to check if a fixture exist before creating a new one
* **MANDATORY** to create fixtures for objects that are repeatable in the test code

## Project Gotchas
- **Config Path**: Default is `/etc/zmbackup/zmbackup.conf`. Use `--config-path` to override.
- **Root Requirement**: `init` command and writing to `/etc/` requires root privileges.
- **Mutually Exclusive Flags**: In `backup` command, `--mail`, `--distributionlist`, `--alias`, and `--ldap` are mutually exclusive.
- **Database Client**: `DatabaseClient` automatically creates tables on initialization by default.
- **Jinja2 Templates**: Configuration is generated from templates in `src/templates/`.
- **Session ID**: Generated via `generate_session_uuid()` combining type and timestamp.