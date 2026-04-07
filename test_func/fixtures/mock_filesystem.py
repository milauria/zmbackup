"""Mock filesystem for functional tests without disk I/O."""

import json
import os
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional


class MockFileSystem:
    """
    In-memory file system mock for functional tests.
    
    Provides file operations without creating actual disk files.
    Stores file contents in memory using path strings as keys.
    """
    
    def __init__(self) -> None:
        """Initialize empty mock filesystem."""
        self.files: Dict[str, str] = {}
        self.directories: set = set()
        
    def write_text(self, path: Path, content: str) -> None:
        """
        Write text content to virtual file.
        
        :param path: Path to file
        :param content: Text content
        """
        str_path = str(path)
        self.files[str_path] = content
        # Ensure parent dirs exist
        self._ensure_parent_dirs(path)
        
    def read_text(self, path: Path) -> str:
        """
        Read text content from virtual file.
        
        :param path: Path to file
        :return: File content
        :raises FileNotFoundError: If file doesn't exist
        """
        str_path = str(path)
        if str_path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[str_path]
    
    def exists(self, path: Path) -> bool:
        """
        Check if path exists in virtual filesystem.
        
        :param path: Path to check
        :return: True if exists
        """
        str_path = str(path)
        return str_path in self.files or str_path in self.directories
    
    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        """
        Create directory in virtual filesystem.
        
        :param path: Path to directory
        :param parents: Create parent directories
        :param exist_ok: Don't raise if exists
        """
        str_path = str(path)
        if str_path in self.directories and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        self.directories.add(str_path)
        if parents:
            current = path
            while current.parent != current:
                self.directories.add(str(current))
                current = current.parent
    
    def copy_file(self, src: Path, dst: Path) -> None:
        """
        Copy file in virtual filesystem.
        
        :param src: Source path
        :param dst: Destination path
        """
        content = self.read_text(src)
        self.write_text(dst, content)
    
    def unlink(self, path: Path, missing_ok: bool = False) -> None:
        """
        Remove file from virtual filesystem.
        
        :param path: Path to file
        :param missing_ok: Don't raise if missing
        """
        str_path = str(path)
        if str_path in self.files:
            del self.files[str_path]
        elif not missing_ok:
            raise FileNotFoundError(f"No such file: {path}")
    
    def open_read(self, path: Path, encoding: str = "utf-8") -> StringIO:
        """
        Open file for reading as file-like object.
        
        :param path: Path to file
        :param encoding: Text encoding
        :return: StringIO object with file content
        """
        content = self.read_text(path)
        return StringIO(content)
    
    def open_write(self, path: Path, encoding: str = "utf-8") -> StringIO:
        """
        Open file for writing as file-like object.
        
        :param path: Path to file
        :param encoding: Text encoding
        :return: StringIO object that will update filesystem on close
        """
        # Create wrapper that captures writes
        class WritableStringIO(StringIO):
            def __init__(self, fs: MockFileSystem, file_path: Path):
                super().__init__()
                self.fs = fs
                self.file_path = file_path
                
            def close(self) -> None:
                """Write content to mock filesystem on close."""
                self.fs.write_text(self.file_path, self.getvalue())
                super().close()
        
        self._ensure_parent_dirs(path)
        return WritableStringIO(self, path)
    
    def _ensure_parent_dirs(self, path: Path) -> None:
        """
        Ensure parent directories exist.
        
        :param path: File path
        """
        parent = path.parent
        while parent != parent.parent:
            self.directories.add(str(parent))
            parent = parent.parent
    
    def clear(self) -> None:
        """Clear all files and directories."""
        self.files.clear()
        self.directories.clear()


class MockTempFile:
    """Mock temporary file for use in testing."""
    
    def __init__(self, mode: str, dir: Path, delete: bool, suffix: str, encoding: str, fs: MockFileSystem):
        """
        Initialize mock temp file.
        
        :param mode: File mode
        :param dir: Directory
        :param delete: Auto-delete on close
        :param suffix: File suffix
        :param encoding: Text encoding
        :param fs: Mock filesystem
        """
        self.mode = mode
        self.dir = dir
        self.delete = delete
        self.suffix = suffix
        self.encoding = encoding
        self.fs = fs
        # Generate temp path
        self.name = str(dir / f"mock_temp_{id(self)}{suffix}")
        self._file_obj: Optional[StringIO] = None
        self._closed = False
        
    def __enter__(self) -> "MockTempFile":
        """Context manager entry."""
        if "w" in self.mode:
            self._file_obj = self.fs.open_write(Path(self.name), self.encoding)
        else:
            self._file_obj = self.fs.open_read(Path(self.name), self.encoding)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if self._file_obj and not self._closed:
            self._file_obj.close()
            self._closed = True
        if self.delete and Path(self.name) in [Path(p) for p in self.fs.files]:
            self.fs.unlink(Path(self.name), missing_ok=True)
    
    def write(self, content: str) -> None:
        """Write to temp file."""
        if self._file_obj:
            self._file_obj.write(content)
    
    def read(self) -> str:
        """Read from temp file."""
        if self._file_obj:
            return self._file_obj.read()
        return ""
