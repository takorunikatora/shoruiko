#!/usr/bin/env python3
"""shoruiko — strip AI writing patterns from natural-language prose."""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        from shoruiko.gui import launch
        launch()
    else:
        from shoruiko.cli import app
        app()
