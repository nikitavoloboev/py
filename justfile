python := "python3.14"

default:
	@just --list

sync:
	uv sync

s:
	uv run -m scripts.run

# TODO: how to make this work:
# `just r <script>` & it works
r +module:
	uv run -m scripts.{{module}}
