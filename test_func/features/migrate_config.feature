Feature: zmbackup migrate-config operation
    As a system administrator
    I want to migrate legacy KEY=VALUE configuration to JSON format
    So that I can use the modern JSON-based configuration system

    Background:
        Given I have a temporary directory for testing

    Scenario: Successfully migrate legacy config to JSON format
        Given I am running as root
        And I have a legacy config file
        When I run the migrate-config command
        Then the exit code should be 0
        And the output should contain "Migration completed successfully"
        And the JSON config file should exist
        And the backup file should exist with suffix ".bak"
        And the JSON config should contain version "1.0"
        And the JSON config should have correct values from legacy config

    Scenario: Skip migration if file is already JSON format
        Given I am running as root
        And I have a JSON config file
        When I run the migrate-config command
        Then the exit code should be 0
        And the output should contain "already in JSON format"
        And the output should contain "No migration needed"

    Scenario: Migration fails if source file does not exist
        Given I am running as root
        And the config file does not exist
        When I run the migrate-config command
        Then the exit code should be 1
        And the output should contain "Error: Configuration file not found"

    Scenario: Migration fails if target exists without --force flag
        Given I am running as root
        And I have a legacy config file
        And the target JSON file already exists
        When I run the migrate-config command
        Then the exit code should be 1
        And the output should contain "Error: Target file"
        And the output should contain "already exists"
        And the output should contain "Use --force to overwrite"

    Scenario: Force overwrite existing JSON file
        Given I am running as root
        And I have a legacy config file
        And the target JSON file already exists
        When I run the migrate-config command with --force flag
        Then the exit code should be 0
        And the output should contain "Migration completed successfully"
        And the JSON config file should exist
        And the JSON config should have correct values from legacy config

    Scenario: Dry run does not modify files
        Given I am running as root
        And I have a legacy config file
        When I run the migrate-config command with --dry-run flag
        Then the exit code should be 0
        And the output should contain "[Dry Run]"
        And the output should contain "Would migrate"
        And the JSON config file should not exist
        And the backup file should not exist

    Scenario: Migrate to custom output path
        Given I am running as root
        And I have a legacy config file
        When I run the migrate-config command with custom output path
        Then the exit code should be 0
        And the output should contain "Migration completed successfully"
        And the custom JSON config file should exist
        And the custom JSON config should have correct values from legacy config

    Scenario: Migration handles invalid legacy config gracefully
        Given I am running as root
        And I have an invalid legacy config file
        When I run the migrate-config command
        Then the exit code should be 1
        And the output should contain "Configuration Error"

    Scenario: Root requirement for /etc/zmbackup/ path
        Given I am not running as root
        And I have a legacy config file in /etc/zmbackup/
        When I run the migrate-config command for /etc/zmbackup/
        Then the exit code should be 1
        And the output should contain "Error: This command must be executed as root"

    Scenario: Non-root user can migrate to non-privileged path
        Given I am not running as root
        And I have a legacy config file in user directory
        When I run the migrate-config command for user directory
        Then the exit code should be 0
        And the output should contain "Migration completed successfully"
        And the JSON config file should exist in user directory

    Scenario: Custom backup suffix
        Given I am running as root
        And I have a legacy config file
        When I run the migrate-config command with backup suffix ".backup"
        Then the exit code should be 0
        And the output should contain "Migration completed successfully"
        And the backup file should exist with suffix ".backup"
