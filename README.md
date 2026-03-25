# `gha-hashpinner`

Finds mutable pins in GitHub Actions config and replaces them with immutable hashes.

This is a security best practice that protects against supply chain attacks.

The immutable hashpins include version comments which are Dependabot-compatible.

E.g.:

    ```yaml
    # ...
    uses: "..." # ...
    # ...
    ```


## Install

```bash
uv tool install gha-hashpinner
```


## Usage

From a GitHub repository:

```bash
gha-hashpinner .
```

Update a specific workflow file:

```bash
gha-hashpinner .github/workflows/my-workflow.yml
```


## Alternatives

* <https://github.com/azat-io/actions-up>: NPM package
* <https://github.com/Skipants/update-action-pins>: Go package


### Why?

I deeply distrust the NPM ecosystem.
The Go package above is not user-friendly to install.

I wanted something I could install with `uv tool install`.

LLMs (plus a little bit of review and engineering judgement) make it really fast and
easy to build tools like this.
