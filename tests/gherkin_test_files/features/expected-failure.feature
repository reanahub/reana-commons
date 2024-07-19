Feature: Expected failure
  Scenario: Only test status
    When the workflow execution completes
    Then the workflow status should be "failed"

  Scenario: Test status and a successful test
    When the workflow execution completes
    Then the workflow status should be "failed"
    And the workspace size should be less than 250GiB

  Scenario: Test status and a successful test, different order
    When the workflow execution completes
    Then the workspace size should be less than 250GiB
    And the workflow status should be "failed"