"""shoruiko — strip AI writing patterns from natural-language prose.

Inspired by blader/humanizer and Wikipedia's 'Signs of AI writing' guide.
Targets 25+ linguistic patterns that betray machine-generated text.
"""

__version__ = "0.1.0"

from shoruiko.core import (
    shoruiko,
    shoruiko_file,
    extract_text,
    mode_light,
    mode_medium,
    mode_aggressive,
    Mode,
    Stats,
)
