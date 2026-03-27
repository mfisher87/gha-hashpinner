"""Mock workflows for use in unit tests."""

from textwrap import dedent

WORKFLOW_WITH_MUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                # One quoted, one not
                - uses: actions/checkout@v4
                - uses: "actions/setup-python@v5"
""").strip()

WORKFLOW_WITH_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                # One quoted, one not
                - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
                - uses: "actions/setup-python@deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"  #v5
""").strip()


WORKFLOW_WITH_MUTABLE_AND_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
                - name: "Doop!"
                  uses: actions/setup-python@v5
""").strip()


WORKFLOW_WITH_QUOTED_MUTABLE_AND_IMMUTABLE_PINS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: 'actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3'  # v4
                - uses: 'actions/setup-python@v5'
""").strip()


WORKFLOW_WITH_COMMENTS = dedent("""
    name: "Test"
    on: push
    jobs:
        test:
            runs_on: ubuntu-latest
            steps:
                - uses: actions/checkout@v4  # Checkout
                - uses: "actions/setup-python@v5" # Setup Python
""").strip()


WORKFLOW_WITH_LOCAL_AND_DOCKER_ACTIONS = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
            - uses: "./local-action"
            - uses: docker://alpine:latest
            - uses: actions/checkout@v4
""").strip()


COMPLEX_WORKFLOW = dedent("""
    name: "Complex Test"
    on: [push, pull_request]

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
            - name: "Checkout"
              uses: actions/checkout@v4

            - name: "Setup Node"
              uses: actions/setup-node@v3

            - name: "Local action"
              uses: ./github/actions/custom

      test:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
            - uses: docker://node:18
            - uses: codecov/codecov-action@v3

      deploy:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # v4
            - uses: actions/deploy@main
""").strip()


WORKFLOW_WITH_NO_JOBS = dedent("""
    name: Test
    on: push
    jobs: {}
""").strip()


WORKFLOW_WITH_BORDERLINE_YAML = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        steps:
          - uses:actions/checkout@v4
""").strip()


WORKFLOW_WITH_INVALID_YAML = dedent("""
    name: "Test"
    on: push
    jobs:
      test:
        steps:
          - uses: actions/checkout@v4
        invalid: [unclosed list
""").strip()
