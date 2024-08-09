Feature: One failing test
    Scenario: This test will succeed
        When the workflow is finished
        Then the workspace should include "output1.png"

    Scenario: This test will fail
        When the workflow is finished
        Then the engine logs should contain "something that is not there"

    Scenario: This test will succeed again
        When the workflow is finished
        Then the workspace should include "output1.png"