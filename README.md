# Simple AI agent

This package creates a simple AI agent.

## Getting started

### Package management

We recommend using [`uv`](https://docs.astral.sh/uv/) for Python package management.

### Set up the environment


#### Sync packages with `uv`
Call the following to set up the environment from within the top-level directory:
```bash
uv sync
```

#### Define environment variables
The package requires environment variables to be set for each provider you want to use,
in the form '*PROVIDER*_API_KEY' (e.g., 'GEMINI_API_KEY').

#### Install Docker Desktop

Code execution is handled using Docker Desktop, which must be running to execute code.
Follow the directions [here](https://docs.docker.com/desktop/) to install and run
Docker Desktop.

### Run the package

The package can be run with the following, which will request a prompt to the LLM:
```bash
uv run simple-agent
```
Information about additional command-line arguments is available by calling
```bash
uv run simple-agent --help
```
