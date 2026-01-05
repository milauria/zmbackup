"""Database session and engine management."""

from contextlib import contextmanager
from functools import cached_property
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base


class DatabaseSessionManager:
    """
    Manages SQLAlchemy engine and session lifecycle.

    Provides centralized database connection management with support
    for different database backends via connection strings.
    """

    def __init__(self, db_path: str):
        """
        Initialize the database session manager.

        :param db_path: Database connection string (e.g., 'sqlite:///path/to/db.sqlite')
        """
        self.db_path = db_path

    @cached_property
    def engine(self) -> Engine:
        """
        Get or create the SQLAlchemy engine.

        :return: Configured SQLAlchemy engine
        """
        # Create engine with SQLite-specific optimizations
        if self.db_path.startswith("sqlite"):
            return create_engine(
                self.db_path,
                echo=False,  # Set to True for SQL query logging
                connect_args={"check_same_thread": False},  # For SQLite
            )
        return create_engine(self.db_path, echo=False)

    @cached_property
    def session_factory(self) -> sessionmaker:
        """
        Get or create the session factory.

        :return: Configured sessionmaker bound to engine
        """
        return sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create all tables defined in the ORM models."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Provides automatic session cleanup and transaction management.

        :yield: SQLAlchemy session instance
        :raises Exception: If database operation fails, session is rolled back
        """
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def __enter__(self) -> "DatabaseSessionManager":
        """
        Support for context manager.

        :return: self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Dispose the engine when exiting the context.

        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        """
        # Note: cached_property stores the result in __dict__
        if "engine" in self.__dict__:
            self.engine.dispose()
