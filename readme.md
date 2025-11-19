# Python

## Setup

Install [task](https://taskfile.dev/docs/installation). Then run `task setup` & follow instructions until it says `✔️ you are setup`.

## Maintenance

Run `python scripts/update_python_version.py` to bump the pinned Python version to the latest stable CPython release.

## Run

Run `task` to see all possible commands.

## API server

Run `task api` (or `uv run --python 3.13 uvicorn server.app:app --reload`) to start the FastAPI server. A `/health` route is exposed for readiness/liveness checks and will respond with `{"status": "ok"}`.

## Scripts CLI

After `task deploy`, `py-scripts` is added to your `PATH` (defaults to `~/bin/py-scripts`). Launch it to fuzzy-pick any Python file from `scripts/` and run it:

```bash
py-scripts            # interactive picker
py-scripts update -- --flag value  # pre-filter and pass args after --
py-scripts --list     # just list available scripts
```

## `flow` CLI

`flow` is a CLI as a dump of various commands written in Python that are useful to me. See [cli/flow](cli/flow) for its code/docs.

Run `task deploy` to install `flow-py` into PATH. It also puts `fa` command in path (my own personal shorthand, but you can change it).

Invoking `flow`, `flow-py`, or `fa` with no arguments opens a fuzzy command palette so you can quickly pick from any registered commands.

## `snapvision` CLI

`snapvision` is a single-purpose CLI that captures the current desktop, pipes it into an MLX-powered vision backend, and prints structured context about the frame. Run it via `task snapvision -- --help` or after `task deploy` simply invoke `snapvision`.

The default backend uses MLX tensors to keep everything on-device. Pass `--backend rust --rust-lib path/to/libsnapvision.dylib` once a Rust acceleration layer is ready. The Rust library is expected to export `run_inference(uint8_t* data, size_t h, size_t w, size_t c, const char* prompt)` and return a UTF-8 string (JSON or plain text) that the CLI surfaces verbatim.

Flags of note:

- `--monitor` selects which display to capture (`0` is the combined desktop).
- `--output /tmp/frame.png` writes the screenshot to a deterministic path.
- `--model-path` points the MLX backend at a specific checkpoint.
- `--json` emits a machine-readable summary rather than the Rich table.

This is a scaffold—the MLX summary is intentionally lightweight so we can swap in a real model or Rust-backed inference code without changing the front-end contract.

## Contributing

Any PR to improve is welcome. [codex](https://github.com/openai/codex) & [cursor](https://cursor.com) are nice for dev. Great **working** & **useful** patches are most appreciated (ideally).

### 🖤

[![Discord](https://go.nikiv.dev/badge-discord)](https://go.nikiv.dev/discord) [![X](https://go.nikiv.dev/badge-x)](https://x.com/nikivdev) [![nikiv.dev](https://go.nikiv.dev/badge-nikiv)](https://nikiv.dev)
