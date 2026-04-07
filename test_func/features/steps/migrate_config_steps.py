"""Step implementations for migrate-config functional tests."""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

from behave import given, when, then
from behave.runner import Context

from zmbackup import cli
from test_func.fixtures.mock_filesystem import MockFileSystem, MockTempFile


@given("I have a temporary directory for testing")
def step_have_temp_directory(context: Context) -> None:
    """
    Ensure temporary directory is available and setup mock filesystem.
    
    :param context: Behave context
    """
    assert context.temp_path.exists(), "Temporary directory not found"
    
    # Setup mock filesystem for this scenario
    context.mock_fs = MockFileSystem()
    
    # Pre-load test fixture files into mock filesystem (before patching)
    test_files_real_dir = context.test_files_dir
    for filename in os.listdir(test_files_real_dir):
        file_path = test_files_real_dir / filename
        if file_path.is_file():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Store in mock filesystem with same structure
            context.mock_fs.write_text(file_path, content)
    
    # Mock Path operations
    def mock_exists(path_self: Path) -> bool:
        return context.mock_fs.exists(path_self)
    
    def mock_read_text(path_self: Path, encoding: str = "utf-8") -> str:
        return context.mock_fs.read_text(path_self)
    
    def mock_write_text(path_self: Path, content: str, encoding: str = "utf-8") -> None:
        context.mock_fs.write_text(path_self, content)
    
    def mock_mkdir(path_self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        context.mock_fs.mkdir(path_self, parents=parents, exist_ok=exist_ok)
    
    # Mock shutil.copy2
    def mock_copy2(src: Any, dst: Any) -> Any:
        context.mock_fs.copy_file(Path(src), Path(dst))
        return dst
    
    # Mock os.rename
    def mock_rename(src: Any, dst: Any) -> None:
        content = context.mock_fs.read_text(Path(src))
        context.mock_fs.write_text(Path(dst), content)
        context.mock_fs.unlink(Path(src))
    
    # Mock os.chmod
    def mock_chmod(path: Any, mode: int) -> None:
        pass  # No-op for mocks
    
    # Mock tempfile.NamedTemporaryFile
    def mock_named_temp_file(mode: str = "w", dir: Any = None, delete: bool = True, 
                             suffix: str = "", encoding: str = "utf-8") -> MockTempFile:
        dir_path = Path(dir) if dir else context.temp_path
        return MockTempFile(mode, dir_path, delete, suffix, encoding, context.mock_fs)
    
    # Mock open() - now fully uses mock filesystem
    def mock_open_func(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        file_path = Path(file) if not isinstance(file, Path) else file
        
        # All file operations use mock filesystem
        if "r" in mode:
            return context.mock_fs.open_read(file_path, kwargs.get("encoding", "utf-8"))
        elif "w" in mode:
            return context.mock_fs.open_write(file_path, kwargs.get("encoding", "utf-8"))
        
        # Fallback - should not reach here in tests
        return context.mock_fs.open_read(file_path, kwargs.get("encoding", "utf-8"))
    
    # Apply patches
    path_exists_patcher = patch.object(Path, "exists", mock_exists)
    path_read_text_patcher = patch.object(Path, "read_text", mock_read_text)
    path_write_text_patcher = patch.object(Path, "write_text", mock_write_text)
    path_mkdir_patcher = patch.object(Path, "mkdir", mock_mkdir)
    shutil_copy2_patcher = patch("shutil.copy2", mock_copy2)
    os_rename_patcher = patch("os.rename", mock_rename)
    os_chmod_patcher = patch("os.chmod", mock_chmod)
    tempfile_patcher = patch("tempfile.NamedTemporaryFile", mock_named_temp_file)
    builtins_open_patcher = patch("builtins.open", mock_open_func)
    
    # Start all patchers and register cleanup
    patchers = [path_exists_patcher, path_read_text_patcher, path_write_text_patcher,
                path_mkdir_patcher, shutil_copy2_patcher, os_rename_patcher,
                os_chmod_patcher, tempfile_patcher, builtins_open_patcher]
    
    for patcher in patchers:
        patcher.start()
        context.add_cleanup(patcher.stop)


@given('I have the config file "{config_file_name}"')
def step_have_config_file(context: Context, config_file_name: str) -> None:
    """
    Copy config file from test-files (in mock fs) to temp directory (in mock fs).
    
    :param context: Behave context
    :param config_file_name: Name of config file in test-files/config/
    """
    source_path = context.test_files_dir / config_file_name
    
    # Store source file name for validation
    context.source_config_file = config_file_name
    
    # Determine target filename
    if config_file_name.endswith('.json'):
        target_filename = "zmbackup.json"
    else:
        target_filename = "zmbackup.conf"
    
    context.legacy_config_path = context.temp_path / target_filename
    # Copy within mock filesystem
    context.mock_fs.copy_file(source_path, context.legacy_config_path)
    context.expected_json_path = context.temp_path / "zmbackup.json"
    
    # Set config_file for generic step
    context.config_file = context.legacy_config_path


@given("the config file does not exist")
def step_config_does_not_exist(context: Context) -> None:
    """
    Set up context for non-existent config file.
    
    :param context: Behave context
    """
    context.legacy_config_path = context.temp_path / "nonexistent.conf"
    context.expected_json_path = context.temp_path / "nonexistent.json"
    context.config_file = context.legacy_config_path


@given("the target JSON file already exists")
def step_target_json_exists(context: Context) -> None:
    """
    Create an existing target JSON file in mock filesystem.
    
    :param context: Behave context
    """
    context.mock_fs.write_text(context.expected_json_path, '{"version": "1.0", "old": "data"}')


@given('I have the config file "{config_file_name}" in /etc/zmbackup/')
def step_have_config_file_in_etc(context: Context, config_file_name: str) -> None:
    """
    Copy config file for /etc/zmbackup/ path testing in mock filesystem.
    
    :param context: Behave context
    :param config_file_name: Name of config file in test-files/config/
    """
    source_path = context.test_files_dir / config_file_name
    
    # Store source file name for validation
    context.source_config_file = config_file_name
    
    context.legacy_config_path = context.temp_path / "zmbackup.conf"
    # Copy within mock filesystem
    context.mock_fs.copy_file(source_path, context.legacy_config_path)
    # Simulate /etc/zmbackup/ path
    context.etc_path = Path("/etc/zmbackup/zmbackup.json")
    context.config_file = context.legacy_config_path


@given('I have the config file "{config_file_name}" in user directory')
def step_have_config_file_in_user_dir(context: Context, config_file_name: str) -> None:
    """
    Copy config file to user (non-privileged) directory.
    
    :param context: Behave context
    :param config_file_name: Name of config file in test-files/config/
    """
    source_path = context.test_files_dir / config_file_name
    assert source_path.exists(), f"Test config file {source_path} not found"
    
    # Store source file name for validation
    context.source_config_file = config_file_name
    
    context.user_dir = context.temp_path / "user_config"
    context.user_dir.mkdir(exist_ok=True)
    context.legacy_config_path = context.user_dir / "zmbackup.conf"
    shutil.copy2(source_path, context.legacy_config_path)
    context.expected_json_path = context.user_dir / "zmbackup.json"
    context.config_file = context.legacy_config_path


@then("the JSON config file should exist")
def step_json_config_exists(context: Context) -> None:
    """
    Verify the JSON config file was created.
    
    :param context: Behave context
    """
    assert context.expected_json_path.exists(), f"JSON config {context.expected_json_path} was not created"


@then("the JSON config file should not exist")
def step_json_config_not_exists(context: Context) -> None:
    """
    Verify the JSON config file was NOT created.
    
    :param context: Behave context
    """
    assert not context.expected_json_path.exists(), f"JSON config {context.expected_json_path} should not exist"


@then('the backup file should exist with suffix "{suffix}"')
def step_backup_exists(context: Context, suffix: str) -> None:
    """
    Verify the backup file was created with the expected suffix.
    
    :param context: Behave context
    :param suffix: Expected backup suffix
    """
    backup_path = Path(str(context.legacy_config_path) + suffix)
    assert backup_path.exists(), f"Backup file {backup_path} was not created"
    context.backup_path = backup_path


@then("the backup file should not exist")
def step_backup_not_exists(context: Context) -> None:
    """
    Verify the backup file was NOT created.
    
    :param context: Behave context
    """
    backup_path = Path(str(context.legacy_config_path) + ".bak")
    assert not backup_path.exists(), f"Backup file {backup_path} should not exist"


@then('the JSON config should contain version "{version}"')
def step_json_contains_version(context: Context, version: str) -> None:
    """
    Verify the JSON config contains the expected version.
    
    :param context: Behave context
    :param version: Expected version string
    """
    with open(context.expected_json_path, "r") as f:
        config_data = json.load(f)
    assert config_data.get("version") == version, f"Expected version {version}, got {config_data.get('version')}"


@then("the JSON config should have correct values from legacy config")
def step_json_has_correct_values(context: Context) -> None:
    """
    Verify the JSON config has correctly migrated values from source config.
    
    :param context: Behave context
    """
    with open(context.expected_json_path, "r") as f:
        config_data = json.load(f)
    
    # Load expected values from source config file
    source_path = context.test_files_dir / context.source_config_file
    
    # Parse source config (KEY=VALUE format)
    expected_values = {}
    with open(source_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                expected_values[key.strip()] = value.strip()
    
    # Verify key values from source config
    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == expected_values["BACKUPUSER"]
    assert config_data["zimbra"]["workdir"] == expected_values["WORKDIR"]
    assert config_data["zimbra"]["ldap_server"] == expected_values["LDAPSERVER"]
    assert config_data["zimbra"]["ldap_password"] == expected_values["LDAPPASS"]
    assert config_data["email"]["notify_address"] == expected_values["EMAIL_NOTIFY"]
    assert config_data["email"]["sender_address"] == expected_values["EMAIL_SENDER"]
    assert config_data["backup"]["max_parallel_process"] == int(expected_values["MAX_PARALLEL_PROCESS"])
    assert config_data["backup"]["rotate_time"] == int(expected_values["ROTATE_TIME"])
    assert config_data["backup"]["lock_backup"] is (expected_values["LOCK_BACKUP"].lower() in ["true", "yes", "1"])
    assert config_data["backup"]["backup_inactive_accounts"] is (expected_values["BACKUP_INACTIVE_ACCOUNTS"].lower() in ["true", "yes", "1"])
    assert config_data["backup"]["ssl_enable"] is (expected_values["SSL_ENABLE"].lower() in ["true", "yes", "1"])
    assert config_data["session"]["type"] == expected_values["SESSION_TYPE"]


@then("the custom JSON config file should exist")
def step_custom_json_exists(context: Context) -> None:
    """
    Verify the custom JSON config file was created.
    
    :param context: Behave context
    """
    assert context.custom_output_path.exists(), f"Custom JSON config {context.custom_output_path} was not created"


@then("the custom JSON config should have correct values from legacy config")
def step_custom_json_has_correct_values(context: Context) -> None:
    """
    Verify the custom JSON config has correctly migrated values from source config.
    
    :param context: Behave context
    """
    with open(context.custom_output_path, "r") as f:
        config_data = json.load(f)
    
    # Load expected values from source config file
    source_path = context.test_files_dir / context.source_config_file
    
    # Parse source config (KEY=VALUE format)
    expected_values = {}
    with open(source_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                expected_values[key.strip()] = value.strip()
    
    # Verify key values from source config
    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == expected_values["BACKUPUSER"]
    assert config_data["email"]["notify_address"] == expected_values["EMAIL_NOTIFY"]


@then("the JSON config file should exist in user directory")
def step_json_exists_in_user_dir(context: Context) -> None:
    """
    Verify the JSON config was created in the user directory.
    
    :param context: Behave context
    """
    assert context.expected_json_path.exists(), f"JSON config {context.expected_json_path} was not created in user directory"
