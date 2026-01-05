Feature: zmbackup init operation
    As a system administrator
    I want to initialize the zmbackup configuration
    So that I can configure the backup environment

    Scenario: Successful initialization with default and custom values
        Given I am running as root
        When I run the init command and provide inputs from "test_func/features/data/init_inputs.json"
        Then the exit code should be 0
        And the output should contain "Configuration successfully written"
        And the configuration file should exist
        And the configuration file should contain "BACKUPUSER=zimbra"
        And the configuration file should contain "LDAPSERVER=ldap://192.168.1.10:389"
        And the configuration file should contain "ROTATE_TIME=15"

    Scenario: Initialization fails if not run as root
        Given I am not running as root
        When I run the init command
        Then the exit code should be 1
        And the output should contain "Error: This command can only be executed by root user."

    Scenario: Initialization fails with invalid email
        Given I am running as root
        When I run the init command and provide an invalid email "invalid-email"
        Then the output should contain "is not a valid email address"
