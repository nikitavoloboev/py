# Python

## Setup

Install [task](https://taskfile.dev/docs/installation). Then run `task setup` & follow instructions until it says `✔️ you are setup`.

## Maintenance

Run `python scripts/update_python_version.py` to bump the pinned Python version to the latest stable CPython release.

## Run

Run `task` to see all possible commands.

## Scripts CLI

After `task deploy`, `py-scripts` is added to your `PATH` (defaults to `~/bin/py-scripts`). Launch it to fuzzy-pick any Python file from `scripts/` and run it:

```bash
py-scripts            # interactive picker
py-scripts update -- --flag value  # pre-filter and pass args after --
py-scripts --list     # just list available scripts
```

## `flow` CLI

`flow` is a CLI as a dump of various commands written in Python that are useful to me. See [cli/flow](cli/flow) for its code/docs.

## Contributing

Any PR to improve is welcome. [codex](https://github.com/openai/codex) & [cursor](https://cursor.com) are nice for dev. Great **working** & **useful** patches are most appreciated (ideally).

### 🖤

[![Discord](https://go.nikiv.dev/badge-discord)](https://go.nikiv.dev/discord) [![X](https://go.nikiv.dev/badge-x)](https://x.com/nikivdev) [![nikiv.dev](https://go.nikiv.dev/badge-nikiv)](https://nikiv.dev)
