"""shoruiko GUI — liquid glass bento-grid desktop application.

Design language:
  - Liquid glass: semi-transparent cards with subtle border glow
  - Bento grid: modular rounded-rect content blocks
  - Center-floating pill toolbar: mode selector + action buttons
  - Colors: blue (#4055ff), green (#22dd55), and purple (#8855ff) neon on deep purple (#050018)
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import difflib

from shoruiko.core import (
    shoruiko,
    extract_text,
    mode_light,
    mode_medium,
    mode_aggressive,
    mode_academic,
    mode_creator,
    mode_publisher,
    Mode,
    Stats,
)

# ═══════════════════════════════════════════════════════════════════════════
# Color palette — blue & purple neon on dark navy
# ═══════════════════════════════════════════════════════════════════════════

BG = "#050018"
CARD_BG = "#0a0030"
CARD_BORDER = "#200060"
INPUT_BG = "#030010"
TEXT = "#99bbff"
TEXT_MUTED = "#7766cc"
BLUE = "#4055ff"
BLUE_GLOW = "#6b7bff"
BLUE_DIM = "#2a3aaa"
PURPLE = "#8855ff"
PURPLE_GLOW = "#aa77ff"
PURPLE_DIM = "#5a35aa"
GREEN = "#22dd55"
RED = "#ff4055"
ORANGE = "#ff6622"
YELLOW = "#ffbb22"
TOOLBAR_BG = "#0f0038"
TOOLBAR_BORDER = "#300070"
PILL_BG = "#180048"
PILL_ACTIVE = "#280068"
PILL_BORDER = "#3a0080"
HIGHLIGHT_BG = "#100040"

FONT_TITLE = ("Inter", 13, "bold")
FONT_HEADING = ("Inter", 11, "bold")
FONT_BODY = ("Inter", 10)
FONT_MONO = ("JetBrains Mono", 9)
FONT_SMALL = ("Inter", 8)
FONT_PILL = ("Inter", 9, "bold")

SUPPORTED_EXTENSIONS = (
    ("All supported documents",
     "*.txt *.md *.rst *.html *.htm *.pdf *.docx *.xhtml *.markdown *.adoc"),
    ("Text files", "*.txt *.md *.rst *.markdown *.adoc"),
    ("HTML files", "*.html *.htm *.xhtml"),
    ("PDF documents", "*.pdf"),
    ("Word documents", "*.docx"),
    ("All files", "*"),
)


# ═══════════════════════════════════════════════════════════════════════════
# Glass card widget
# ═══════════════════════════════════════════════════════════════════════════

class GlassCard(tk.Frame):
    """A bento-grid card with liquid-glass styling."""

    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._title = title

        self.canvas = tk.Canvas(
            self, bg=BG, highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=CARD_BG)
        self._win_id = None

        if title:
            self._header = tk.Frame(self.inner, bg="#080030", height=28)
            self._header.pack(fill="x", side="top")
            self._header.pack_propagate(False)
            tk.Label(
                self._header, text=title, fg=BLUE_GLOW, bg="#080030",
                font=FONT_HEADING, anchor="w",
            ).pack(side="left", padx=12, pady=2)

        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        if self._win_id:
            self.canvas.delete(self._win_id)
        r = 10
        self.canvas.delete("card_shape")
        self._draw_rounded_rect(0, 0, w, h, r, fill=CARD_BG,
                                outline=CARD_BORDER, width=1)

        pad = 1
        if self._win_id:
            self.canvas.delete(self._win_id)
        self._win_id = self.canvas.create_window(
            pad, 28 if self._title else pad,
            window=self.inner, anchor="nw",
            width=w - pad * 2,
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,  x2 - r, y1,  x2, y1,  x2, y1 + r,
            x2, y2 - r,  x2, y2,  x2 - r, y2,  x1 + r, y2,
            x1, y2,  x1, y2 - r,  x1, y1 + r,  x1, y1,
        ]
        self.canvas.create_polygon(points, smooth=True, tags="card_shape", **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# Pill toolbar (center-floating)
# ═══════════════════════════════════════════════════════════════════════════

class PillToolbar(tk.Frame):
    """A centered floating pill-shaped toolbar with category pills + action buttons."""

    def __init__(self, parent, on_scan, on_mode_change, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._on_scan = on_scan
        self._on_mode_change = on_mode_change
        self._category = "creator"
        self._intensity = "medium"
        self._running = False
        self._pills: dict[str, tk.Label] = {}
        self._intensity_dots: dict[str, tk.Label] = {}
        self._scan_btn = None
        self._spinner_idx = 0
        self._spinner_chars = "◐◓◑◒"
        self._build()

    def _build(self):
        outer = tk.Frame(self, bg=TOOLBAR_BG, bd=0, highlightthickness=0)
        outer.pack(expand=True)

        canvas = tk.Canvas(outer, bg=BG, height=44, highlightthickness=0, bd=0)
        canvas.pack()

        pill_frame = tk.Frame(canvas, bg=TOOLBAR_BG)
        pill_win = canvas.create_window(0, 0, window=pill_frame, anchor="center")

        # Category pills
        categories = [
            ("academic",  "🎓 Academic",   BLUE),
            ("creator",   "✍️ Creator",    PURPLE),
            ("publisher", "📰 Publisher",  ORANGE),
        ]
        for cat_key, label_text, color in categories:
            pill = tk.Label(
                pill_frame, text=label_text,
                fg=color, bg=PILL_BG if cat_key != self._category else PILL_ACTIVE,
                font=FONT_PILL, padx=10, pady=6,
                cursor="hand2",
            )
            pill.pack(side="left", padx=2, pady=6)
            pill.bind("<Button-1>", lambda e, c=cat_key: self._select_category(c))
            pill.bind("<Enter>",
                lambda e, p=pill: p.configure(bg="#300068"))
            pill.bind("<Leave>",
                lambda e, p=pill, c=cat_key:
                    p.configure(bg=PILL_ACTIVE if self._category == c else PILL_BG))
            self._pills[cat_key] = pill

        # Intensity dots separator
        tk.Label(pill_frame, text=" · ", fg=TOOLBAR_BORDER, bg=TOOLBAR_BG,
                font=FONT_PILL).pack(side="left")

        # 3 intensity dot labels (clickable for manual override)
        intensities = [
            ("light",  "◐", PURPLE),
            ("medium", "◑", BLUE),
            ("aggressive", "◒", ORANGE),
        ]
        for key, symbol, color in intensities:
            dot = tk.Label(
                pill_frame, text=symbol,
                fg=color if key == self._intensity else "#2a1a50",
                bg=TOOLBAR_BG, font=("Inter", 11), padx=2,
                cursor="hand2",
            )
            dot.pack(side="left", pady=6)
            dot.bind("<Button-1>", lambda e, k=key: self._select_intensity(k))
            dot.bind("<Enter>",
                lambda e, d=dot, c=color: d.configure(fg=c))
            dot.bind("<Leave>",
                lambda e, d=dot, k=key:
                    d.configure(fg=self._dot_color(k)))
            self._intensity_dots[key] = dot

        # Separator
        tk.Label(pill_frame, text="│", fg=TOOLBAR_BORDER, bg=TOOLBAR_BG,
                font=FONT_PILL).pack(side="left", padx=6)

        # Scan button
        self._scan_btn = tk.Label(
            pill_frame, text="▶ Process",
            fg=GREEN, bg=PILL_BG, font=FONT_PILL, padx=14, pady=6,
            cursor="hand2",
        )
        self._scan_btn.pack(side="left", padx=2, pady=6)
        self._scan_btn.bind("<Button-1>", lambda e: self._on_scan())
        self._scan_btn.bind("<Enter>",
            lambda e: self._scan_btn.configure(bg="#003018"))
        self._scan_btn.bind("<Leave>",
            lambda e: self._scan_btn.configure(bg=PILL_BG))

        # Separator
        tk.Label(pill_frame, text="│", fg=TOOLBAR_BORDER, bg=TOOLBAR_BG,
                font=FONT_PILL).pack(side="left", padx=6)

        # Clear
        clear_btn = tk.Label(
            pill_frame, text="◕ Clear",
            fg=PURPLE_GLOW, bg=PILL_BG, font=FONT_PILL, padx=10, pady=6,
            cursor="hand2",
        )
        clear_btn.pack(side="left", padx=2, pady=6)
        clear_btn.bind("<Button-1>", lambda e: self._clear())
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(bg="#2a2050"))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(bg=PILL_BG))

        # Copy
        copy_btn = tk.Label(
            pill_frame, text="◔ Copy",
            fg=BLUE_GLOW, bg=PILL_BG, font=FONT_PILL, padx=10, pady=6,
            cursor="hand2",
        )
        copy_btn.pack(side="left", padx=2, pady=6)
        copy_btn.bind("<Button-1>", lambda e: self._copy())
        copy_btn.bind("<Enter>", lambda e: copy_btn.configure(bg="#080030"))
        copy_btn.bind("<Leave>", lambda e: copy_btn.configure(bg=PILL_BG))

        # Center and draw pill background
        def _center_pill(event=None):
            w = canvas.winfo_width()
            canvas.coords(pill_win, w // 2, 22)
            canvas.delete("pill_bg")
            pw = pill_frame.winfo_reqwidth() + 20
            canvas.create_rounded_rect(
                (w - pw) // 2, 1, (w + pw) // 2, 43,
                radius=21, fill=TOOLBAR_BG, outline=TOOLBAR_BORDER, width=1,
                tags="pill_bg",
            )
            canvas.tag_lower("pill_bg")

        canvas.bind("<Configure>", _center_pill)
        self._canvas = canvas
        self._center_pill = _center_pill
        self._pill_win = pill_win

    def _dot_color(self, key: str) -> str:
        colors = {"light": PURPLE, "medium": BLUE, "aggressive": ORANGE}
        return colors.get(key, BLUE) if key == self._intensity else "#2a1a50"

    def _refresh_dots(self):
        for key, dot in self._intensity_dots.items():
            dot.configure(fg=self._dot_color(key))

    def _select_category(self, cat_key: str):
        self._category = cat_key
        for key, pill in self._pills.items():
            pill.configure(bg=PILL_ACTIVE if key == cat_key else PILL_BG)
        # Reset intensity to category default
        defaults = {"academic": "medium", "creator": "medium", "publisher": "aggressive"}
        self._intensity = defaults.get(cat_key, "medium")
        self._refresh_dots()
        self._on_mode_change(cat_key)

    def _select_intensity(self, key: str):
        self._intensity = key
        self._refresh_dots()
        self._on_mode_change(self._category)

    def _clear(self):
        self._parent._clear_all()

    def _copy(self):
        if hasattr(self._parent, "_output"):
            text = self._parent._output.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
            self._parent._status_label.configure(
                text="✓ Copied to clipboard", fg=GREEN)

    def _animate_spinner(self):
        if not self._running:
            return
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self._scan_btn.configure(
            text=f"{self._spinner_chars[self._spinner_idx]} ...")
        self.after(120, self._animate_spinner)

    def start_scan(self):
        self._running = True
        self._animate_spinner()

    def stop_scan(self):
        self._running = False
        self._scan_btn.configure(text="▶ Process")

    @property
    def mode(self) -> Mode:
        """Resolve category + intensity override into a concrete Mode."""
        if self._category == "academic":
            m = mode_academic()
        elif self._category == "publisher":
            m = mode_publisher()
        else:
            m = mode_creator()

        if self._intensity == "light":
            # Strip to Phase 1 only — line-level removals + whitespace
            m.substitute_filler = False
            m.substitute_hedging = False
            m.substitute_copula = False
            m.substitute_formal_linking = False
            m.rewrite_rule_of_three = False
            m.rewrite_contrasts = False
            m.rewrite_overstructuring = False
            m.vocabulary_swap = False
            m.normalize_em_dashes = False
            m.normalize_passive_voice = False
            m.aggressive = False
        elif self._intensity == "aggressive":
            # Enable every phase on top of the category preset
            m.substitute_hedging = True
            m.substitute_copula = True
            m.substitute_formal_linking = True
            m.rewrite_rule_of_three = True
            m.rewrite_contrasts = True
            m.rewrite_overstructuring = True
            m.vocabulary_swap = True
            m.normalize_em_dashes = True
            m.normalize_passive_voice = True
            m.aggressive = True

        return m

    @property
    def category_name(self) -> str:
        names = {"academic": "Academic", "creator": "Creator", "publisher": "Publisher"}
        return names.get(self._category, "Creator")

    @property
    def _parent(self):
        """Traverse up from toolbar_frame to the ShoruikoApp root."""
        return self.master.master


# ═══════════════════════════════════════════════════════════════════════════
# Stats card
# ═══════════════════════════════════════════════════════════════════════════

class StatsPanel(tk.Frame):
    """Compact stats display showing change counts."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        self._stat_labels: dict[str, tuple[tk.Label, tk.Label]] = {}
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#080030", height=24)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="Scan Results", fg=PURPLE_GLOW, bg="#080030",
            font=FONT_SMALL, anchor="w",
        ).pack(side="left", padx=8, pady=3)

        self._summary = tk.Label(
            header, text="Ready", fg=TEXT_MUTED, bg="#080030",
            font=FONT_SMALL, anchor="e",
        )
        self._summary.pack(side="right", padx=8, pady=3)

        self._stats_frame = tk.Frame(self, bg=CARD_BG)
        self._stats_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def update(self, stats: Stats):
        for widget in self._stats_frame.winfo_children():
            widget.destroy()

        entries: list[tuple[str, int, str]] = []
        if stats.chatbot_lines:
            entries.append(("Chatbot", stats.chatbot_lines, RED))
        if stats.sycophantic_lines:
            entries.append(("Sycophantic", stats.sycophantic_lines, RED))
        if stats.disclaimers:
            entries.append(("Disclaimers", stats.disclaimers, ORANGE))
        if stats.generic_endings:
            entries.append(("Endings", stats.generic_endings, ORANGE))
        if stats.filler_substitutions:
            entries.append(("Filler", stats.filler_substitutions, YELLOW))
        if stats.hedging_substitutions:
            entries.append(("Hedging", stats.hedging_substitutions, YELLOW))
        if stats.copula_substitutions:
            entries.append(("Copula", stats.copula_substitutions, YELLOW))
        if stats.formal_linking_substitutions:
            entries.append(("Formal", stats.formal_linking_substitutions, YELLOW))
        if stats.rule_of_three_rewrites:
            entries.append(("Rule of 3", stats.rule_of_three_rewrites, BLUE))
        if stats.contrast_rewrites:
            entries.append(("Contrasts", stats.contrast_rewrites, BLUE))
        if stats.overstructuring_rewrites:
            entries.append(("Structure", stats.overstructuring_rewrites, BLUE))
        if stats.vocabulary_swaps:
            entries.append(("Vocab", stats.vocabulary_swaps, BLUE_GLOW))
        if stats.em_dashes_normalized:
            entries.append(("Em-dashes", stats.em_dashes_normalized, PURPLE))
        if stats.passive_rewrites:
            entries.append(("Passive", stats.passive_rewrites, PURPLE))

        if not entries:
            tk.Label(
                self._stats_frame, text="No AI patterns found",
                fg=TEXT_MUTED, bg=CARD_BG, font=FONT_SMALL,
            ).pack(padx=8, pady=8)
            self._summary.configure(text="Clean ✓", fg=GREEN)
            return

        for name, count, color in entries:
            row = tk.Frame(self._stats_frame, bg=CARD_BG)
            row.pack(fill="x", padx=4, pady=0)
            tk.Label(
                row, text=name, fg=color, bg=CARD_BG,
                font=FONT_SMALL, anchor="w", width=10,
            ).pack(side="left")
            tk.Label(
                row, text=str(count), fg=TEXT, bg=CARD_BG,
                font=FONT_SMALL, anchor="e",
            ).pack(side="right")

        pct = stats.ratio
        self._summary.configure(
            text=f"{stats.total_changes} changes | -{pct}%",
            fg=GREEN if stats.total_changes > 0 else TEXT_MUTED,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Patterns card
# ═══════════════════════════════════════════════════════════════════════════

class PatternsPanel(tk.Frame):
    """Checklist of AI pattern categories."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#080030", height=24)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="Pattern Filters", fg=BLUE_GLOW, bg="#080030",
            font=FONT_SMALL, anchor="w",
        ).pack(side="left", padx=8, pady=3)

        scroll = tk.Frame(self, bg=CARD_BG)
        scroll.pack(fill="both", expand=True, padx=6, pady=4)

        patterns = [
            ("Chatbot artifacts", True),
            ("Sycophantic tone", True),
            ("Knowledge-cutoff disclaimers", True),
            ("Generic endings", True),
            ("Filler phrases", True),
            ("Hedging / uncertainty", False),
            ("Copula avoidance", False),
            ("Formal linking words", False),
            ("Rule of three", False),
            ("Exaggerated contrasts", False),
            ("Overstructuring", False),
            ("AI vocabulary swap", False),
            ("Em-dash overuse", False),
            ("Passive voice", False),
        ]

        for name, enabled in patterns:
            var = tk.BooleanVar(value=enabled)
            cb = tk.Checkbutton(
                scroll, text=name, variable=var,
                fg=TEXT_MUTED, bg=CARD_BG, selectcolor=CARD_BG,
                font=FONT_SMALL, activebackground=CARD_BG,
                activeforeground=TEXT,
            )
            cb.pack(anchor="w", pady=1)


# ═══════════════════════════════════════════════════════════════════════════
# Main application window
# ═══════════════════════════════════════════════════════════════════════════

class ShoruikoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("shoruiko")
        self.configure(bg=BG)
        self.geometry("1100x750")
        self.minsize(800, 500)

        try:
            self.attributes("-alpha", 0.97)
        except Exception:
            pass

        self._last_result = ""
        self._last_stats = Stats(bytes_before=0, bytes_after=0)
        self._mode = mode_medium()
        self._current_file: str | None = None

        self._build_ui()

        # Keyboard shortcuts
        self.bind("<Control-Return>", lambda e: self._scan())
        self.bind("<Control-l>", lambda e: self._toolbar._select_intensity("light"))
        self.bind("<Control-m>", lambda e: self._toolbar._select_intensity("medium"))
        self.bind("<Control-a>", lambda e: self._toolbar._select_intensity("aggressive"))
        self.bind("<Control-1>", lambda e: self._toolbar._select_category("academic"))
        self.bind("<Control-2>", lambda e: self._toolbar._select_category("creator"))
        self.bind("<Control-3>", lambda e: self._toolbar._select_category("publisher"))
        self.bind("<Control-o>", lambda e: self._browse_file())
        self.bind("<Control-p>", lambda e: self._paste_clipboard())  # Ctrl+P = paste from clipboard into input
        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG, height=42)
        header.pack(fill="x", side="top", padx=16, pady=(10, 0))
        header.pack_propagate(False)

        tk.Label(
            header, text="◉", fg=BLUE_GLOW, bg=BG,
            font=("Inter", 18),
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            header, text="shoruiko", fg=TEXT, bg=BG,
            font=("Inter", 16, "bold"),
        ).pack(side="left")

        tk.Label(
            header, text="strip AI fingerprints from prose",
            fg=TEXT_MUTED, bg=BG, font=FONT_SMALL,
        ).pack(side="left", padx=10, pady=(6, 0))

        self._status_label = tk.Label(
            header, text="Ready", fg=TEXT_MUTED, bg=BG,
            font=FONT_SMALL,
        )
        self._status_label.pack(side="right", padx=8, pady=(6, 0))

        # ── Bento grid (main area) ──
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=12, pady=8)

        grid.columnconfigure(0, weight=3)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)

        # Right panel
        right = tk.Frame(grid, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # ── Input card (left) ──
        input_card = tk.Frame(grid, bg=CARD_BG, bd=0,
                              highlightthickness=1,
                              highlightbackground=CARD_BORDER)
        input_card.grid(row=0, column=0, sticky="nsew")

        input_header = tk.Frame(input_card, bg="#080030", height=28)
        input_header.pack(fill="x")
        input_header.pack_propagate(False)
        tk.Label(
            input_header, text="Input Text", fg=BLUE_GLOW, bg="#080030",
            font=FONT_HEADING, anchor="w",
        ).pack(side="left", padx=12, pady=2)

        # Browse button
        self._file_label = tk.Label(
            input_header, text="", fg=PURPLE_GLOW, bg="#080030",
            font=FONT_SMALL,
        )
        self._file_label.pack(side="right", padx=(0, 6), pady=2)

        browse_btn = tk.Label(
            input_header, text="📂 Browse", fg=PURPLE_GLOW, bg="#180048",
            font=FONT_SMALL, padx=10, pady=1, cursor="hand2",
        )
        browse_btn.pack(side="right", padx=(0, 4), pady=2)
        browse_btn.bind("<Button-1>", lambda e: self._browse_file())
        browse_btn.bind("<Enter>",
            lambda e: browse_btn.configure(bg="#300070"))
        browse_btn.bind("<Leave>",
            lambda e: browse_btn.configure(bg="#180048"))

        # Paste button
        paste_btn = tk.Label(
            input_header, text="📋 Paste", fg=PURPLE_GLOW, bg="#180048",
            font=FONT_SMALL, padx=10, pady=1, cursor="hand2",
        )
        paste_btn.pack(side="right", padx=(0, 4), pady=2)
        paste_btn.bind("<Button-1>", lambda e: self._paste_clipboard())
        paste_btn.bind("<Enter>",
            lambda e: paste_btn.configure(bg="#300070"))
        paste_btn.bind("<Leave>",
            lambda e: paste_btn.configure(bg="#180048"))

        tk.Label(
            input_header, text="paste or browse a document",
            fg=TEXT_MUTED, bg="#080030", font=FONT_SMALL,
        ).pack(side="right", padx=12, pady=2)

        self._input = scrolledtext.ScrolledText(
            input_card, bg=INPUT_BG, fg=TEXT, insertbackground=BLUE,
            font=FONT_BODY, wrap="word", relief="flat", bd=0,
            padx=12, pady=10, selectbackground="#280070",
        )
        self._input.pack(fill="both", expand=True)
        self._input.bind("<Control-v>",
            lambda e: self.after(100, self._update_char_count))
        self._input.bind("<KeyRelease>",
            lambda e: self._update_char_count())

        # ── Patterns card ──
        pat_frame = tk.Frame(right, bg=CARD_BG, bd=0, highlightthickness=1,
                             highlightbackground=CARD_BORDER)
        pat_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self._patterns = PatternsPanel(pat_frame)
        self._patterns.pack(fill="both", expand=True)

        # ── Stats card ──
        stats_frame = tk.Frame(right, bg=CARD_BG, bd=0, highlightthickness=1,
                               highlightbackground=CARD_BORDER)
        stats_frame.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self._stats_panel = StatsPanel(stats_frame)
        self._stats_panel.pack(fill="both", expand=True)

        # ── Output card (bottom, full width) ──
        grid.rowconfigure(1, weight=1)
        output_card = tk.Frame(grid, bg=CARD_BG, bd=0,
                               highlightthickness=1,
                               highlightbackground=CARD_BORDER)
        output_card.grid(row=1, column=0, columnspan=2,
                         sticky="nsew", pady=(6, 0))

        output_header = tk.Frame(output_card, bg="#080030", height=28)
        output_header.pack(fill="x")
        output_header.pack_propagate(False)
        tk.Label(
            output_header, text="Output", fg=GREEN, bg="#080030",
            font=FONT_HEADING, anchor="w",
        ).pack(side="left", padx=12, pady=2)

        self._char_count_label = tk.Label(
            output_header, text="", fg=TEXT_MUTED, bg="#080030",
            font=FONT_SMALL,
        )
        self._char_count_label.pack(side="right", padx=12, pady=2)

        self._output = scrolledtext.ScrolledText(
            output_card, bg=INPUT_BG, fg=TEXT, insertbackground=BLUE,
            font=FONT_BODY, wrap="word", relief="flat", bd=0,
            padx=12, pady=10, selectbackground="#280070",
        )
        self._output.pack(fill="both", expand=True)

        # ── Pill toolbar (floating at bottom) ──
        toolbar_frame = tk.Frame(self, bg=BG, height=50)
        toolbar_frame.pack(fill="x", side="bottom", padx=16, pady=(6, 10))
        toolbar_frame.pack_propagate(False)

        self._toolbar = PillToolbar(
            toolbar_frame,
            on_scan=self._scan,
            on_mode_change=self._on_mode_change,
        )
        self._toolbar.pack(fill="both", expand=True)

    # ── File browsing ──

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Open document",
            filetypes=SUPPORTED_EXTENSIONS,
        )
        if not path:
            return

        self._status_label.configure(
            text=f"Loading {os.path.basename(path)}...", fg=YELLOW)

        def _load():
            try:
                text = extract_text(path)
                self.after(0, self._file_loaded, path, text)
            except Exception as exc:
                self.after(0, self._file_error, path, exc)

        threading.Thread(target=_load, daemon=True).start()

    def _file_loaded(self, path: str, text: str):
        self._current_file = path
        self._input.delete("1.0", "end")
        self._input.insert("1.0", text)

        fname = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        labels = {".pdf": "📄", ".docx": "📝", ".txt": "📃",
                  ".md": "📋", ".rst": "📋", ".html": "🌐", ".htm": "🌐"}
        icon = labels.get(ext, "📎")
        self._file_label.configure(text=f"{icon} {fname}")

        self._status_label.configure(
            text=f"✓ Loaded {fname} ({len(text):,} chars)",
            fg=GREEN,
        )
        self._update_char_count()

    def _file_error(self, path: str, exc: Exception):
        fname = os.path.basename(path)
        self._status_label.configure(
            text=f"✗ Failed to load {fname}",
            fg=RED,
        )
        messagebox.showerror(
            "Load Error",
            f"Could not read {fname}:\n\n{exc}",
        )

    def _paste_clipboard(self):
        """Paste text from clipboard into the input area."""
        try:
            text = self.clipboard_get()
        except Exception:
            self._status_label.configure(
                text="✗ Clipboard is empty or inaccessible", fg=RED)
            return

        if not text.strip():
            self._status_label.configure(
                text="✗ Clipboard is empty", fg=YELLOW)
            return

        self._current_file = None
        self._file_label.configure(text="📋 clipboard")
        self._input.delete("1.0", "end")
        self._input.insert("1.0", text)
        self._status_label.configure(
            text=f"📋 Pasted from clipboard ({len(text):,} chars)",
            fg=BLUE_GLOW,
        )
        self._update_char_count()

    # ── Actions ──

    def _update_char_count(self):
        count = len(self._input.get("1.0", "end-1c"))
        self._char_count_label.configure(text=f"{count:,} chars")

    def _on_mode_change(self, cat_key: str):
        cat_names = {"academic": "Academic", "creator": "Creator",
                     "publisher": "Publisher"}
        self._status_label.configure(
            text=f"Category: {cat_names.get(cat_key, cat_key)}",
            fg=TEXT_MUTED,
        )

    def _scan(self):
        text = self._input.get("1.0", "end-1c")
        if not text.strip():
            self._status_label.configure(text="Nothing to process",
                                         fg=ORANGE)
            return

        self._toolbar.start_scan()
        src_label = (f"  ({os.path.basename(self._current_file)})"
                     if self._current_file else "  (pasted text)")
        self._status_label.configure(
            text=f"Processing{src_label}...", fg=YELLOW)

        def _run():
            try:
                result, stats = shoruiko(text, self._toolbar.mode)
                self._last_result = result
                self._last_stats = stats
                self.after(0, self._show_result, result, stats)
            except Exception as exc:
                self.after(0, self._show_error, str(exc))

        threading.Thread(target=_run, daemon=True).start()

    def _show_error(self, msg: str):
        self._toolbar.stop_scan()
        self._status_label.configure(
            text=f"✗ Error: {msg[:60]}", fg=RED)
        messagebox.showerror("Processing Error", msg)

    def _show_result(self, result: str, stats: Stats):
        self._output.delete("1.0", "end")
        self._output.insert("1.0", result)
        self._stats_panel.update(stats)
        self._toolbar.stop_scan()

        if stats.total_changes > 0:
            self._status_label.configure(
                text=f"✓ {stats.total_changes} change(s) | -{stats.ratio}%",
                fg=GREEN,
            )
        else:
            self._status_label.configure(
                text="✓ No AI patterns found", fg=GREEN)

        self._update_char_count()

    def _clear_all(self):
        self._input.delete("1.0", "end")
        self._output.delete("1.0", "end")
        self._stats_panel.update(Stats(bytes_before=0, bytes_after=0))
        self._current_file = None
        self._file_label.configure(text="")
        self._status_label.configure(text="Cleared", fg=TEXT_MUTED)
        self._update_char_count()


# ═══════════════════════════════════════════════════════════════════════════
# Canvas helper — rounded rectangles
# ═══════════════════════════════════════════════════════════════════════════

def _canvas_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1 + radius, y1,  x2 - radius, y1,
        x2 - radius, y1,  x2, y1,
        x2, y1 + radius,  x2, y1 + radius,
        x2, y2 - radius,  x2, y2 - radius,
        x2, y2,           x2 - radius, y2,
        x2 - radius, y2,  x1 + radius, y2,
        x1 + radius, y2,  x1, y2,
        x1, y2 - radius,  x1, y2 - radius,
        x1, y1 + radius,  x1, y1 + radius,
        x1, y1,
    ]
    return self.create_polygon(points, smooth=True, **kwargs)


tk.Canvas.create_rounded_rect = _canvas_rounded_rect


# ═══════════════════════════════════════════════════════════════════════════
# Launch
# ═══════════════════════════════════════════════════════════════════════════

def launch():
    """Start the shoruiko desktop GUI."""
    app = ShoruikoApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
