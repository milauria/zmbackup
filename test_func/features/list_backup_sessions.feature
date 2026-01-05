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
    Given the database has 1 session from "test_func/features/data/single_session.json"
    When I run the list command
    Then the output should contain a table with 1 row
    And the table should have columns "Session Name", "Start", "Ending", "Size", "Description"
    And row 1 should contain data from "test_func/features/data/single_session_expected.json"
    And the exit code should be 0

  Scenario: List multiple backup sessions
    Given the database has 3 sessions from "test_func/features/data/multiple_sessions.json"
    When I run the list command
    Then the output should contain a table with 3 rows
    And the exit code should be 0

  Scenario: List sessions with different backup types
    Given the database has sessions by type from "test_func/features/data/sessions_by_type.json"
    When I run the list command
    Then the output should contain a table with 6 rows
    And the exit code should be 0

  Scenario: List sessions with different statuses
    Given the database has sessions by status from "test_func/features/data/sessions_by_status.json"
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
