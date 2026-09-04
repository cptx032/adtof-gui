"""Graphical interface for ADTOF-pytorch drum transcription.

The window accepts a local audio file. YouTube videos can be converted
to MP3 through an external converter.
"""

from __future__ import annotations

import collections.abc
import dataclasses
import os
import pathlib
import shutil
import tempfile
import threading
import tkinter
import webbrowser
from tkinter import filedialog
from tkinter import font
from tkinter import ttk

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {
        "aac",
        "aif",
        "aiff",
        "flac",
        "m4a",
        "mp3",
        "mpga",
        "oga",
        "ogg",
        "opus",
        "wav",
        "wma",
    }
)
AUDIO_FILETYPES: list[tuple[str, str]] = [
    (
        "Audio files",
        " ".join(f"*.{extension}" for extension in sorted(AUDIO_EXTENSIONS)),
    )
]
MIDI_FILETYPES: list[tuple[str, str]] = [
    ("MIDI files", "*.mid *.midi"),
]
CONVERTER_URL: str = "https://convertytmp3.org/"


@dataclasses.dataclass(frozen=True)
class Theme:
    """Color tokens used by the window."""

    background: str = "#eef1f6"
    surface: str = "#ffffff"
    border: str = "#d9dee8"
    text: str = "#1c2333"
    muted: str = "#667085"
    accent: str = "#3b5bdb"
    accent_hover: str = "#364fc7"
    danger: str = "#c92a2a"
    success: str = "#2b8a3e"
    button_text: str = "#000000"
    footer: str = "#9aa3b2"


def is_supported_audio_path(path: pathlib.Path) -> bool:
    """Return whether the path uses a supported audio extension."""
    suffix: str = path.suffix.lower().lstrip(".")
    return suffix in AUDIO_EXTENSIONS


def existing_audio_path(audio: str) -> tuple[pathlib.Path | None, str]:
    """Return the audio path if it exists on disk.

    Returns the path and an empty message when valid, or no path and an error
    message for the status label.
    """
    text: str = audio.strip()
    if not text:
        return (None, "Enter an audio file.")
    path: pathlib.Path = pathlib.Path(text).expanduser()
    try:
        if not path.is_file():
            return (None, "The audio file does not exist.")
    except OSError:
        return (None, "The audio file does not exist.")
    if not is_supported_audio_path(path):
        return (None, "Please choose an audio file.")
    return (path, "")


def make_temp_midi_path() -> pathlib.Path | None:
    """Create an empty temporary MIDI file path."""
    try:
        handle: int
        name: str
        handle, name = tempfile.mkstemp(prefix="adtof-", suffix=".mid")
        os.close(handle)
        return pathlib.Path(name)
    except OSError:
        return None


def remove_path(path: pathlib.Path) -> bool:
    """Delete a file if it exists."""
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        return False
    return True


def transcribe_audio_to_midi(audio_path: pathlib.Path, midi_path: pathlib.Path) -> bool:
    """Transcribe an audio file to a MIDI file with ADTOF-pytorch."""
    try:
        import adtof_pytorch
    except Exception:
        return False
    try:
        written: pathlib.Path = adtof_pytorch.transcribe_to_midi(audio_path, midi_path)
    except Exception:
        return False
    try:
        return written.is_file() and written.stat().st_size > 0
    except OSError:
        return False


def open_converter_url() -> bool:
    """Open the YouTube to MP3 converter in the default browser."""
    try:
        return bool(webbrowser.open(CONVERTER_URL))
    except Exception:
        return False


class AdtofGui:
    """Main window for selecting an audio file."""

    _DEFAULT_STATUS: str = "Choose an audio file."

    def __init__(self, root: tkinter.Tk) -> None:
        """Build the window widgets."""
        self._root: tkinter.Tk = root
        self._theme: Theme = Theme()
        self._audio_var: tkinter.StringVar = tkinter.StringVar()
        self._last_width: int = 0
        self._is_busy: bool = False
        self._configure_window()
        self._configure_fonts()
        self._configure_style()
        self._build()
        self._fit_window()

    def _configure_window(self) -> None:
        """Set window title and background."""
        self._root.title("ADTOF")
        self._root.configure(bg=self._theme.background)

    def _fit_window(self) -> None:
        """Grow the window so the full layout, including the status bar, is visible."""
        try:
            self._root.update_idletasks()
            width: int = max(int(self._root.winfo_reqwidth()), 640)
            height: int = int(self._root.winfo_reqheight())
            self._root.minsize(width, height)
            self._root.geometry(f"{width}x{height}")
        except tkinter.TclError:
            return

    def _configure_fonts(self) -> None:
        """Create the fonts used across the window."""
        family: str = "Helvetica"
        try:
            default_font: font.Font = font.nametofont("TkDefaultFont")
            family = str(default_font.cget("family"))
        except tkinter.TclError:
            family = "Helvetica"
        self._font_title: font.Font = font.Font(
            root=self._root, family=family, size=22, weight="bold"
        )
        self._font_subtitle: font.Font = font.Font(root=self._root, family=family, size=11)
        self._font_section: font.Font = font.Font(
            root=self._root, family=family, size=12, weight="bold"
        )
        self._font_body: font.Font = font.Font(root=self._root, family=family, size=11)
        self._font_small: font.Font = font.Font(root=self._root, family=family, size=10)
        self._font_link: font.Font = font.Font(
            root=self._root, family=family, size=11, underline=True
        )
        self._font_button: font.Font = font.Font(
            root=self._root, family=family, size=11, weight="bold"
        )

    def _configure_style(self) -> None:
        """Apply ttk styles so text fields match the layout."""
        style: ttk.Style = ttk.Style(self._root)
        try:
            style.theme_use("clam")
        except tkinter.TclError:
            pass
        style.configure(
            "App.TEntry",
            fieldbackground=self._theme.surface,
            foreground=self._theme.text,
            bordercolor=self._theme.border,
            lightcolor=self._theme.border,
            darkcolor=self._theme.border,
            padding=8,
            insertcolor=self._theme.text,
        )
        style.map(
            "App.TEntry",
            bordercolor=[("focus", self._theme.accent)],
            lightcolor=[("focus", self._theme.accent)],
            darkcolor=[("focus", self._theme.accent)],
        )
        style.configure(
            "App.Horizontal.TProgressbar",
            troughcolor=self._theme.background,
            background=self._theme.accent,
            bordercolor=self._theme.border,
            lightcolor=self._theme.accent,
            darkcolor=self._theme.accent,
            thickness=10,
        )

    def _bind_hover(self, button: tkinter.Button, rest: str, hover: str) -> None:
        """Change a button background while the pointer is over it."""

        def on_enter(_event: tkinter.Event[tkinter.Button]) -> None:
            """Set the hover background."""
            try:
                button.configure(bg=hover)
            except tkinter.TclError:
                return

        def on_leave(_event: tkinter.Event[tkinter.Button]) -> None:
            """Restore the resting background."""
            try:
                button.configure(bg=rest)
            except tkinter.TclError:
                return

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _build(self) -> None:
        """Create the visible layout."""
        outer: tkinter.Frame = tkinter.Frame(
            self._root,
            bg=self._theme.background,
            padx=28,
            pady=24,
        )
        self._outer: tkinter.Frame = outer
        self._build_footer(self._root)
        self._build_status(self._root)
        outer.pack(fill="both", expand=True)
        outer.bind("<Configure>", self._on_resize)

        self._build_header(outer)
        audio_card: tkinter.Frame = self._make_card(
            outer,
            title="Audio file",
            subtitle="WAV, MP3, FLAC, and other common audio formats.",
        )
        self._build_audio_row(audio_card)
        self._build_divider(outer)
        converter_card: tkinter.Frame = self._make_card(
            outer,
            title="YouTube to MP3",
            subtitle="Convert a YouTube video, then choose the downloaded audio file.",
        )
        self._build_converter_link(converter_card)
        self._build_actions(outer)

    def _build_header(self, parent: tkinter.Frame) -> None:
        """Add the title and short description."""
        title: tkinter.Label = tkinter.Label(
            parent,
            text="ADTOF",
            bg=self._theme.background,
            fg=self._theme.text,
            font=self._font_title,
            anchor="w",
        )
        title.pack(fill="x")
        subtitle: tkinter.Label = tkinter.Label(
            parent,
            text="Transcribe drums from a local audio file.",
            bg=self._theme.background,
            fg=self._theme.muted,
            font=self._font_subtitle,
            anchor="w",
            pady=4,
        )
        subtitle.pack(fill="x", pady=(0, 18))

    def _make_card(self, parent: tkinter.Frame, *, title: str, subtitle: str) -> tkinter.Frame:
        """Create a bordered card and return its inner content frame."""
        shell: tkinter.Frame = tkinter.Frame(parent, bg=self._theme.border, highlightthickness=0)
        shell.pack(fill="x", pady=4)
        inner: tkinter.Frame = tkinter.Frame(shell, bg=self._theme.surface, padx=18, pady=16)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        heading: tkinter.Label = tkinter.Label(
            inner,
            text=title,
            bg=self._theme.surface,
            fg=self._theme.text,
            font=self._font_section,
            anchor="w",
        )
        heading.pack(fill="x")
        caption: tkinter.Label = tkinter.Label(
            inner,
            text=subtitle,
            bg=self._theme.surface,
            fg=self._theme.muted,
            font=self._font_small,
            anchor="w",
        )
        caption.pack(fill="x", pady=(0, 10))
        return inner

    def _build_audio_row(self, parent: tkinter.Frame) -> None:
        """Add the file path field and browse button."""
        row: tkinter.Frame = tkinter.Frame(parent, bg=self._theme.surface)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        self._audio_entry: ttk.Entry = ttk.Entry(
            row,
            textvariable=self._audio_var,
            style="App.TEntry",
        )
        self._audio_entry.grid(row=0, column=0, sticky="ew")
        browse_shell: tkinter.Frame = tkinter.Frame(row, bg=self._theme.border)
        browse_shell.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        browse_button: tkinter.Button = tkinter.Button(
            browse_shell,
            text="...",
            command=self._browse_audio,
            cursor="hand2",
            bg=self._theme.surface,
            fg=self._theme.button_text,
            activebackground=self._theme.background,
            activeforeground=self._theme.button_text,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=14,
            font=self._font_body,
        )
        browse_button.pack(fill="both", expand=True, padx=1, pady=1)
        self._bind_hover(browse_button, self._theme.surface, self._theme.background)

    def _build_converter_link(self, parent: tkinter.Frame) -> None:
        """Add a clickable link to the YouTube to MP3 converter."""
        self._converter_link: tkinter.Label = tkinter.Label(
            parent,
            text=CONVERTER_URL,
            bg=self._theme.surface,
            fg=self._theme.accent,
            font=self._font_link,
            cursor="hand2",
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self._converter_link.pack(fill="x")
        self._converter_link.bind("<Button-1>", self._on_converter_click)
        self._converter_link.bind("<Enter>", self._on_converter_enter)
        self._converter_link.bind("<Leave>", self._on_converter_leave)

    def _build_divider(self, parent: tkinter.Frame) -> None:
        """Add a horizontal divider labeled or."""
        row: tkinter.Frame = tkinter.Frame(parent, bg=self._theme.background)
        row.pack(fill="x", pady=12)
        left: tkinter.Frame = tkinter.Frame(row, bg=self._theme.border, height=1)
        left.pack(side="left", fill="x", expand=True, pady=6)
        label: tkinter.Label = tkinter.Label(
            row,
            text="or",
            bg=self._theme.background,
            fg=self._theme.muted,
            font=self._font_small,
        )
        label.pack(side="left", padx=12)
        right: tkinter.Frame = tkinter.Frame(row, bg=self._theme.border, height=1)
        right.pack(side="left", fill="x", expand=True, pady=6)

    def _build_actions(self, parent: tkinter.Frame) -> None:
        """Add the process button and an indeterminate progress bar."""
        self._process_button: tkinter.Button = tkinter.Button(
            parent,
            text="Process",
            command=self._process,
            cursor="hand2",
            bg=self._theme.accent,
            fg=self._theme.button_text,
            activebackground=self._theme.accent_hover,
            activeforeground=self._theme.button_text,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=28,
            pady=8,
            font=self._font_button,
        )
        self._process_button.pack(pady=(18, 8))
        self._bind_hover(self._process_button, self._theme.accent, self._theme.accent_hover)
        self._process_progress: ttk.Progressbar = ttk.Progressbar(
            parent,
            style="App.Horizontal.TProgressbar",
            mode="indeterminate",
        )
        self._process_progress.pack(fill="x", pady=(0, 8))

    def _build_status(self, parent: tkinter.Tk) -> None:
        """Add the status bar at the bottom of the window."""
        wrap: tkinter.Frame = tkinter.Frame(parent, bg=self._theme.background)
        wrap.pack(side="bottom", fill="x", padx=28, pady=(8, 8))
        status_shell: tkinter.Frame = tkinter.Frame(wrap, bg=self._theme.border)
        status_shell.pack(fill="x")
        status_inner: tkinter.Frame = tkinter.Frame(
            status_shell,
            bg=self._theme.surface,
            padx=14,
            pady=10,
        )
        status_inner.pack(fill="x", padx=1, pady=1)
        self._status: tkinter.Label = tkinter.Label(
            status_inner,
            text=self._DEFAULT_STATUS,
            bg=self._theme.surface,
            fg=self._theme.muted,
            font=self._font_small,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self._status.pack(fill="x")

    def _build_footer(self, parent: tkinter.Tk) -> None:
        """Add a discrete credit line at the bottom of the window."""
        footer: tkinter.Label = tkinter.Label(
            parent,
            text="made by Willie Lawrence",
            bg=self._theme.background,
            fg=self._theme.footer,
            font=self._font_small,
            anchor="e",
            justify="right",
        )
        footer.pack(side="bottom", fill="x", padx=28, pady=(0, 12))

    def _on_resize(self, event: tkinter.Event[tkinter.Frame]) -> None:
        """Keep wrapped text aligned with the window width."""
        if event.widget is not self._outer:
            return
        if event.width == self._last_width:
            return
        self._last_width = event.width
        wrap: int = max(event.width - 80, 240)
        try:
            self._converter_link.configure(wraplength=wrap)
            self._status.configure(wraplength=wrap)
        except tkinter.TclError:
            return

    def _on_converter_enter(self, _event: tkinter.Event[tkinter.Label]) -> None:
        """Highlight the converter link."""
        try:
            self._converter_link.configure(fg=self._theme.accent_hover)
        except tkinter.TclError:
            return

    def _on_converter_leave(self, _event: tkinter.Event[tkinter.Label]) -> None:
        """Restore the converter link color."""
        try:
            self._converter_link.configure(fg=self._theme.accent)
        except tkinter.TclError:
            return

    def _on_converter_click(self, _event: tkinter.Event[tkinter.Label]) -> None:
        """Open the converter page in the default browser."""
        if not open_converter_url():
            self._set_status("Could not open the converter in a browser.", is_error=True)

    def _browse_audio(self) -> bool:
        """Open a file dialog filtered to audio files and store the chosen path."""
        initialdir: str | None = None
        current: str = self._audio_var.get().strip()
        current_path: pathlib.Path = pathlib.Path(current).expanduser()
        try:
            if current_path.is_file():
                initialdir = str(current_path.parent)
        except OSError:
            initialdir = None

        try:
            chosen: str = filedialog.askopenfilename(
                parent=self._root,
                title="Open audio file",
                filetypes=AUDIO_FILETYPES,
                initialdir=initialdir,
            )
        except tkinter.TclError:
            return False
        if not chosen:
            return False

        path: pathlib.Path = pathlib.Path(chosen)
        if not is_supported_audio_path(path):
            self._set_status("Please choose an audio file.", is_error=True)
            return False

        self._audio_var.set(str(path))
        self._set_status("", is_error=False)
        return True

    def _process(self) -> bool:
        """Validate the audio file, then transcribe it in the background."""
        if self._is_busy:
            self._set_status("A transcription is already in progress.", is_error=True)
            return False

        audio_path: pathlib.Path | None
        message: str
        audio_path, message = existing_audio_path(self._audio_var.get())
        if audio_path is None:
            self._set_process_progress_active(False)
            self._set_status(message, is_error=True)
            return False

        self._set_busy(True)
        self._set_process_progress_active(True)
        self._set_status("Transcribing drums...", is_error=False)
        worker: threading.Thread = threading.Thread(
            target=self._transcribe_audio,
            args=(audio_path,),
            daemon=True,
            name="adtof-transcribe",
        )
        try:
            worker.start()
        except RuntimeError:
            self._set_busy(False)
            self._set_process_progress_active(False)
            self._set_status("Could not start transcription.", is_error=True)
            return False
        return True

    def _transcribe_audio(self, audio_path: pathlib.Path) -> None:
        """Run ADTOF transcription and then ask where to save the MIDI file."""
        midi_path: pathlib.Path | None = make_temp_midi_path()
        if midi_path is None:
            self._finish_transcription(
                False,
                "Could not create a temporary MIDI file.",
                None,
            )
            return
        if not transcribe_audio_to_midi(audio_path, midi_path):
            remove_path(midi_path)
            self._finish_transcription(
                False,
                "Could not transcribe the audio file.",
                None,
            )
            return
        self._finish_transcription(True, "", midi_path)

    def _finish_transcription(
        self,
        ok: bool,
        message: str,
        midi_path: pathlib.Path | None,
    ) -> None:
        """Handle transcription completion on the UI thread."""

        def apply() -> None:
            """Stop the progress bar and save or report an error."""
            self._set_process_progress_active(False)
            if not ok or midi_path is None:
                self._set_busy(False)
                if midi_path is not None:
                    remove_path(midi_path)
                self._set_status(
                    message or "Could not transcribe the audio file.",
                    is_error=True,
                )
                return
            self._save_transcribed_midi(midi_path)
            self._set_busy(False)

        self._call_on_ui(apply)

    def _save_transcribed_midi(self, midi_path: pathlib.Path) -> bool:
        """Ask where to save the transcribed MIDI file and write it."""
        audio_text: str = self._audio_var.get().strip()
        audio_path: pathlib.Path = pathlib.Path(audio_text).expanduser()
        initialdir: str | None = None
        initialfile: str = f"{audio_path.stem or 'drums'}.mid"
        try:
            if audio_path.parent.is_dir():
                initialdir = str(audio_path.parent)
        except OSError:
            initialdir = None

        try:
            chosen: str = filedialog.asksaveasfilename(
                parent=self._root,
                title="Save MIDI file",
                defaultextension=".mid",
                filetypes=MIDI_FILETYPES,
                initialdir=initialdir,
                initialfile=initialfile,
            )
        except tkinter.TclError:
            remove_path(midi_path)
            self._set_status("Could not open the save dialog.", is_error=True)
            return False

        if not chosen:
            remove_path(midi_path)
            self._set_status("", is_error=False)
            return False

        destination: pathlib.Path = pathlib.Path(chosen)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(midi_path, destination)
        except OSError:
            remove_path(midi_path)
            self._set_status("Could not save the MIDI file.", is_error=True)
            return False

        remove_path(midi_path)
        self._set_status("MIDI file saved.", is_error=False)
        return True

    def _call_on_ui(self, func: collections.abc.Callable[[], None]) -> None:
        """Run a callback on the Tk event loop."""
        try:
            self._root.after(0, func)
        except tkinter.TclError:
            return

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable the process button while work is running."""
        self._is_busy = busy
        state: str = "disabled" if busy else "normal"
        cursor: str = "arrow" if busy else "hand2"
        try:
            self._process_button.configure(state=state, cursor=cursor)
        except tkinter.TclError:
            return

    def _set_process_progress_active(self, active: bool) -> bool:
        """Start or stop the indeterminate process progress bar."""
        try:
            if active:
                self._process_progress.start()
            else:
                self._process_progress.stop()
        except tkinter.TclError:
            return False
        return True

    def _set_status(self, message: str, *, is_error: bool) -> None:
        """Update the process status label."""
        color: str
        text: str
        if not message:
            text = self._DEFAULT_STATUS
            color = self._theme.muted
        elif is_error:
            text = message
            color = self._theme.danger
        else:
            text = message
            color = self._theme.success
        try:
            self._status.configure(text=text, fg=color)
        except tkinter.TclError:
            return


def main() -> bool:
    """Start the graphical interface."""
    try:
        root: tkinter.Tk = tkinter.Tk()
        AdtofGui(root)
        root.mainloop()
    except tkinter.TclError:
        return False
    return True


if __name__ == "__main__":
    main()
