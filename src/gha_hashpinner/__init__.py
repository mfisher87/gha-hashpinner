"""Finds mutable pins in GitHub Actions config and replaces them with immutable hashes.

This is a security best practice that protects against supply chain attacks.

The immutable hashpins include version comments which are Dependabot-compatible.

E.g.:

    ```yaml
    # ...
    uses: "..." # ...
    # ...
    ```
"""
