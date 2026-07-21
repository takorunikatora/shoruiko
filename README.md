# shoruiko

**Strip AI writing fingerprints from prose.** Zero glyphs — zero machine traces.

shoruiko detects and removes 25+ linguistic patterns that betray AI-generated text — from chatbot artifacts and sycophantic tone to filler phrases, hedging, and AI-favorite vocabulary. Built on patterns adapted from [blader/humanizer](https://github.com/blader/humanizer).

## Sister Tools

| Tool | Purpose |
|------|---------|
| [gijinkai](https://github.com/takorunikatora/gijinkai) | Strip AI fingerprints from **code** |
| **shoruiko** | Strip AI fingerprints from **prose** |
| [scrutineer](https://github.com/takorunikatora/scrutineer) | **Detect** AI patterns in code |

## Pattern Categories

| # | Category | Mode | Description |
|---|----------|------|-------------|
| 1 | Significance inflation | — | "not just X, but Y", "in a world where" |
| 2 | Promotional language | — | "revolutionize", "game-changing", "next-level" |
| 3 | Overstructuring | Aggressive | "First,", "Second,", "Finally," openers |
| 4 | Adjective overuse | — | "seamless", "robust", "innovative" |
| 5 | Exaggerated contrasts | Aggressive | "However,", "On the other hand," |
| 7 | AI vocabulary swap | Aggressive | "delve"→"explore", "crucial"→"important" |
| 8 | Copula avoidance | Aggressive | "serves as"→"is", "boasts"→"has" |
| 9 | Tailing negations | Aggressive | ", no exceptions."→"." |
| 10 | Rule of three | Aggressive | "fast, reliable, and secure"→"fast and reliable" |
| 11 | Hedging phrases | Aggressive | "it is important to note that"→"" |
| 12 | Em-dash overuse | Aggressive | Normalize excess em-dashes |
| 13 | Passive overuse | Aggressive | "can be used"→"is used" |
| 14 | Formal linking | Aggressive | "Furthermore,"→"", "Consequently,"→"" |
| 15 | Suffix-heavy words | — | Detection only |
| 16 | Colon explosion | — | Detection only |
| 20 | Chatbot artifacts | Medium | "I hope this helps", "Feel free to reach out" |
| 21 | Knowledge-cutoff | Medium | "As of July 2026...", "Based on available..." |
| 22 | Sycophantic tone | Medium | "Great question!", "You're absolutely right" |
| 23 | Filler phrases | Medium | "in order to"→"to", "due to the fact that"→"because" |
| 24 | Excessive hedging | Aggressive | "could potentially"→"may" |
| 25 | Generic endings | Medium | "In conclusion", "To sum up" |
| 26 | Transitional padding | — | Detection only |
| 27 | Sign-offs | Medium | "Happy coding!", "Cheers!", "Enjoy!" |

## Modes

| Mode | What it does |
|------|-------------|
| **Light** | Whitespace normalization only |
| **Medium** | Remove chatbot artifacts, sycophantic tone, disclaimers, generic endings, sign-offs + substitute filler phrases |
| **Aggressive** | Everything above + vocabulary swaps, copula fixes, hedging removal, contrast/overstructuring stripping, formal linking cleanup, passive voice normalization, em-dash capping |

## GUI

Liquid glass + bento grid desktop application:

- **Dark navy theme** with blue (#4055ff) and grey (#7b8caa) neon accents
- **Bento grid layout** — input, patterns, stats, and output cards
- **Center-floating pill toolbar** — mode selector + action buttons
- Real-time stats breakdown by category

Launch: `python3 main.py gui`

## CLI

```bash
# Process a file (medium mode, prints to stdout)
python3 main.py file essay.txt

# Aggressive mode — deep de-AI-fication
python3 main.py file essay.txt --aggressive

# Light mode — whitespace only
python3 main.py file essay.txt --light

# Overwrite file in place
python3 main.py file essay.txt --write

# Show stats only
python3 main.py file essay.txt --stats

# Process from clipboard
python3 main.py clip

# Launch GUI
python3 main.py gui
```

## Install

```bash
pip install -r requirements.txt
ln -sf $(pwd)/main.py ~/.local/bin/shoruiko
chmod +x main.py
```

## Requirements

- Python 3.10+
- typer, rich

## License

MIT — see [LICENSE](LICENSE)
