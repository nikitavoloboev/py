#!/usr/bin/env python3
"""Simple Textual-powered TUI to download MLX VLM models from Hugging Face."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from huggingface_hub import snapshot_download

try:  # huggingface_hub 0.25+
    from huggingface_hub.errors import HfHubHTTPError
except ImportError:  # older versions expose it under utils._errors
    from huggingface_hub.utils._errors import HfHubHTTPError  # type: ignore[attr-defined]
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Log,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option


@dataclass(frozen=True)
class ModelSuggestion:
    model_id: str
    description: str
    note: str | None = None


POPULAR_MODELS: list[ModelSuggestion] = [
    ModelSuggestion("mlx-community/idefics2-8b-chatty-4bit", "General multimodal chat, 4-bit quantized."),
    ModelSuggestion("mlx-community/nanoLLaVA-1.5-8bit", "Lightweight 1.5B LLaVA-style model."),
    ModelSuggestion("mlx-community/llava-next-0.5b-hf", "Very small VLM for quick tests."),
    ModelSuggestion("mlx-community/qwen2.5-vl-3b-instruct-4bit", "Qwen 2.5 VL instruct, 3B 4-bit."),
    ModelSuggestion("mlx-community/gpt4omni-mini-3.8b-mlx", "GPT4OMNI-mini compatible weights."),
    ModelSuggestion("mlx-community/paligemma-3b-mix-448-mlx", "PaLiGemma image captioning fine-tune."),
    ModelSuggestion("mlx-community/aya-vision-8b-mlx", "Aya-Vision multilingual VLM."),
    ModelSuggestion("mlx-community/deepseek-vl-1.3b-mlx", "DeepSeek VL compact vision model."),
]


class ModelInstallerApp(App):
    """Textual application that lets a user pick a model and download it."""

    CSS = """
    Screen {
        align: center middle;
    }

    #content {
        width: 90%;
        max-width: 90;
        padding: 2 4;
        border: round $accent;
        height: 90%;
    }

    #title {
        content-align: center middle;
        margin-bottom: 1;
    }

    #subtitle {
        color: $text-muted;
        margin-bottom: 1;
        height: 2;
    }

    Input {
        margin-bottom: 1;
    }

    OptionList {
        height: 12;
        border: tall $warning;
        margin-bottom: 1;
    }

    #buttons {
        height: 3;
        margin-bottom: 1;
    }

    Log {
        border: round $surface;
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "download", "Download selected model"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    selected_model: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            yield Static("MLX Model Installer", id="title")
            yield Static(
                "Pick from the curated list below or type any Hugging Face repo id.",
                id="subtitle",
            )
            yield Input(
                placeholder="Search or enter repo id (e.g. mlx-community/idefics2-8b-chatty-4bit)",
                id="model_input",
            )
            yield OptionList(id="model_list")
            yield Input(
                placeholder="Optional destination directory (defaults to Hugging Face cache)",
                id="dest_input",
            )
            with Horizontal(id="buttons"):
                yield Button("Download", id="download_button", variant="primary")
                yield Button("Quit", id="quit_button", variant="error")
            yield Log(id="status_log")
        yield Footer()

    def on_mount(self) -> None:
        self._suggestion_map: dict[str, ModelSuggestion] = {}
        self._model_input = self.query_one("#model_input", Input)
        self._dest_input = self.query_one("#dest_input", Input)
        self._option_list = self.query_one("#model_list", OptionList)
        self._status_log = self.query_one("#status_log", Log)
        self._status_log.write("Ready. Start typing to filter or use the suggestions list.")
        self._refresh_suggestions("")
        self.selected_model = POPULAR_MODELS[0].model_id
        self._model_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "model_input":
            self.selected_model = event.value.strip()
            self._refresh_suggestions(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "model_input":
            self.selected_model = event.value.strip()
            self.call_after_refresh(self.action_download)
        elif event.input.id == "dest_input":
            self.call_after_refresh(self.action_download)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id or ""
        suggestion = self._suggestion_map.get(option_id)
        if suggestion is not None:
            self.selected_model = suggestion.model_id
            self._model_input.value = suggestion.model_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "download_button":
            self.call_after_refresh(self.action_download)
        elif event.button.id == "quit_button":
            self.exit()

    def _refresh_suggestions(self, query: str) -> None:
        self._option_list.clear_options()
        self._suggestion_map.clear()
        matches = list(self._matching_suggestions(query))
        if not matches:
            self._option_list.add_option(
                Option("No matches found; enter a full repo id manually.", disabled=True)
            )
            return
        for suggestion in matches:
            summary = suggestion.description
            if suggestion.note:
                summary = f"{summary} ({suggestion.note})"
            prompt = f"{suggestion.model_id} — {summary}"
            self._suggestion_map[suggestion.model_id] = suggestion
            self._option_list.add_option(Option(prompt, id=suggestion.model_id))

    @staticmethod
    def _matching_suggestions(query: str) -> Iterable[ModelSuggestion]:
        if not query:
            return POPULAR_MODELS
        query_lower = query.lower()
        return [
            suggestion
            for suggestion in POPULAR_MODELS
            if query_lower in suggestion.model_id.lower()
            or query_lower in suggestion.description.lower()
        ]

    async def action_download(self) -> None:
        model_id = (self.selected_model or self._model_input.value or "").strip()
        if not model_id:
            self._status_log.write("[red]Please enter a model id before downloading.[/red]")
            return

        dest_raw = self._dest_input.value.strip()
        destination = Path(dest_raw).expanduser() if dest_raw else None
        download_button = self.query_one("#download_button", Button)
        download_button.disabled = True
        self._status_log.write(f"[cyan]Downloading {model_id} ...[/cyan]")
        try:
            path = await self._download_model(model_id, destination)
        except Exception as exc:  # pragma: no cover - interactive app
            self._status_log.write(f"[red]Download failed: {exc}[/red]")
        else:
            self._status_log.write(f"[green]Saved model to {path}[/green]")
        finally:
            download_button.disabled = False

    @staticmethod
    async def _download_model(model_id: str, destination: Path | None) -> str:
        def _task() -> str:
            kwargs = {
                "repo_id": model_id,
                "resume_download": True,
                "local_dir_use_symlinks": False,
            }
            if destination:
                destination.mkdir(parents=True, exist_ok=True)
                kwargs["local_dir"] = str(destination)
            return snapshot_download(**kwargs)

        try:
            return await asyncio.to_thread(_task)
        except HfHubHTTPError as error:
            raise RuntimeError(f"Hugging Face error: {error}") from error


def main() -> None:
    app = ModelInstallerApp()
    app.run()


if __name__ == "__main__":
    main()
