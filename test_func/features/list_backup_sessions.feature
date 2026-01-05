Feature: List Backup Sessions
  As a system administrator
  I want to list all backup sessions
  So that I can view the backup history

  Background:
    Given a clean zmbackup environment
    And a valid configuration file

  Scenario: List sessions when database is empty
    Given the database has no sessions
    When I run the list command
    Then the output should contain "No backup sessions found."
    And the exit code should be 0

  Scenario: List a single backup session
    Given the database has 1 session with:
      | backup_type | status    | description       |
      | full        | completed | Full backup Jan 5 |
    When I run the list command
    Then the output should contain a table with 1 row
    And the table should have columns "Session Name", "Start", "Ending", "Size", "Description"
    And row 1 should contain:
      | Description       |
      | Full backup Jan 5 |
    And the exit code should be 0

  Scenario: List multiple backup sessions
    Given the database has 3 sessions with:
      | backup_type  | status    | description          | size   |
      | full         | completed | Full backup Jan 5    | 2.5 GB |
      | incremental  | completed | Incremental Jan 6    | 500 MB |
      | full         | failed    | Full backup Jan 7    | N/A    |
    When I run the list command
    Then the output should contain a table with 3 rows
    And the exit code should be 0

  Scenario: List sessions with different backup types
    Given the database has sessions with backup types:
      | backup_type  | count |
      | full         | 2     |
      | incremental  | 3     |
      | mailbox      | 1     |
    When I run the list command
    Then the output should contain a table with 6 rows
    And the exit code should be 0

  Scenario: List sessions with different statuses
    Given the database has sessions with statuses:
      | status      | count |
      | completed   | 3     |
      | in_progress | 1     |
      | failed      | 2     |
    When I run the list command
    Then the output should contain a table with 6 rows
    And the exit code should be 0

  Scenario: List sessions with null values
    Given the database has a session with null ending and size
    When I run the list command
    Then the output should contain "N/A" for missing fields
    And the exit code should be 0

  Scenario: List sessions with formatted dates
    Given the database has a session with start "2026-01-05 14:30:00" and ending "2026-01-05 16:45:00"
    When I run the list command
    Then the output should contain "2026-01-05 14:30"
    And the output should contain "2026-01-05 16:45"
    And the exit code should be 0

  Scenario: List sessions when configuration is missing
    Given no configuration file exists
    When I run the list command
    Then the output should contain "Configuration error"
    And the exit code should be 1

  Scenario: List sessions when database is inaccessible
    Given a configuration with invalid database path
    When I run the list command
    Then the output should contain "Error accessing database"
    And the exit code should be 1
