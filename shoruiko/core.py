"""shoruiko core engine — prose-level AI pattern detection and rewriting.

25+ linguistic pattern categories adapted from blader/humanizer v2.8.2
and Wikipedia's "Signs of AI-generated prose" guidelines.

Architecture:
  Phase 1 — Line-level removal   (chatbot artifacts, sycophantic, disclaimers)
  Phase 2 — Phrase substitution   (filler, hedging, copula, formal linking)
  Phase 3 — Sentence rewrites     (rule-of-three, contrasts, overstructuring)
  Phase 4 — Vocabulary swap       (AI-leaning words → neutral alternatives)
  Phase 5 — Full-text metrics     (em-dash density, colon patterns, suffix load)
  Phase 6 — Whitespace normalize  (always on)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Callable

# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class Mode:
    """Processing knobs — what gets stripped, substituted, or rewritten."""

    remove_chatbot_artifacts: bool = True
    remove_sycophantic: bool = True
    remove_disclaimers: bool = True
    remove_generic_endings: bool = True
    remove_sign_offs: bool = True
    substitute_filler: bool = True
    substitute_hedging: bool = False
    substitute_copula: bool = False
    substitute_formal_linking: bool = False
    rewrite_rule_of_three: bool = False
    rewrite_contrasts: bool = False
    rewrite_overstructuring: bool = False
    vocabulary_swap: bool = False
    normalize_em_dashes: bool = False
    normalize_passive_voice: bool = False
    normalize_whitespace: bool = True
    aggressive: bool = False


def mode_light() -> Mode:
    """Normalize whitespace only — minimal touch."""
    return Mode(
        remove_chatbot_artifacts=False,
        remove_sycophantic=False,
        remove_disclaimers=False,
        remove_generic_endings=False,
        remove_sign_offs=False,
        substitute_filler=False,
        normalize_whitespace=True,
    )


def mode_medium() -> Mode:
    """Strip obvious AI artifacts — default for general use."""
    return Mode()


def mode_aggressive() -> Mode:
    """Full de-AI-fication — rewrites, vocabulary swap, deep cleanup."""
    return Mode(
        substitute_hedging=True,
        substitute_copula=True,
        substitute_formal_linking=True,
        rewrite_rule_of_three=True,
        rewrite_contrasts=True,
        rewrite_overstructuring=True,
        vocabulary_swap=True,
        normalize_em_dashes=True,
        normalize_passive_voice=True,
        aggressive=True,
    )


def mode_academic() -> Mode:
    """Essays, papers, theses — conservative. Removes obvious AI fingerprints
    while preserving formal academic tone, hedging, and structure."""
    return Mode(
        remove_chatbot_artifacts=True,
        remove_sycophantic=True,
        remove_disclaimers=True,
        remove_generic_endings=True,
        remove_sign_offs=True,
        substitute_filler=True,
        substitute_hedging=False,         # academic hedging is normal
        substitute_copula=False,
        substitute_formal_linking=False,
        rewrite_rule_of_three=False,
        rewrite_contrasts=False,
        rewrite_overstructuring=False,
        vocabulary_swap=False,            # keep academic vocabulary
        normalize_em_dashes=False,
        normalize_passive_voice=False,    # passive voice is standard
        normalize_whitespace=True,
    )


def mode_creator() -> Mode:
    """Blog posts, newsletters, social media — balanced. Strips AI tics
    while preserving authentic voice and personality."""
    return Mode(
        remove_chatbot_artifacts=True,
        remove_sycophantic=True,
        remove_disclaimers=True,
        remove_generic_endings=True,
        remove_sign_offs=True,
        substitute_filler=True,
        substitute_hedging=True,
        substitute_copula=True,
        substitute_formal_linking=True,
        rewrite_rule_of_three=False,
        rewrite_contrasts=False,
        rewrite_overstructuring=False,
        vocabulary_swap=True,
        normalize_em_dashes=True,
        normalize_passive_voice=False,
        normalize_whitespace=True,
    )


def mode_publisher() -> Mode:
    """SEO articles, web copy, commercial content — maximum de-AI-fication.
    Every pattern category is active for the lowest possible AI detection score."""
    return Mode(
        remove_chatbot_artifacts=True,
        remove_sycophantic=True,
        remove_disclaimers=True,
        remove_generic_endings=True,
        remove_sign_offs=True,
        substitute_filler=True,
        substitute_hedging=True,
        substitute_copula=True,
        substitute_formal_linking=True,
        rewrite_rule_of_three=True,
        rewrite_contrasts=True,
        rewrite_overstructuring=True,
        vocabulary_swap=True,
        normalize_em_dashes=True,
        normalize_passive_voice=True,
        normalize_whitespace=True,
        aggressive=True,
    )


@dataclass
class Stats:
    """Per-file scan statistics."""

    chatbot_lines: int = 0
    sycophantic_lines: int = 0
    disclaimers: int = 0
    generic_endings: int = 0
    filler_substitutions: int = 0
    hedging_substitutions: int = 0
    copula_substitutions: int = 0
    formal_linking_substitutions: int = 0
    rule_of_three_rewrites: int = 0
    contrast_rewrites: int = 0
    overstructuring_rewrites: int = 0
    vocabulary_swaps: int = 0
    em_dashes_normalized: int = 0
    passive_rewrites: int = 0
    bytes_before: int = 0
    bytes_after: int = 0

    @property
    def total_changes(self) -> int:
        return (
            self.chatbot_lines
            + self.sycophantic_lines
            + self.disclaimers
            + self.generic_endings
            + self.filler_substitutions
            + self.hedging_substitutions
            + self.copula_substitutions
            + self.formal_linking_substitutions
            + self.rule_of_three_rewrites
            + self.contrast_rewrites
            + self.overstructuring_rewrites
            + self.vocabulary_swaps
            + self.em_dashes_normalized
            + self.passive_rewrites
        )

    @property
    def ratio(self) -> float:
        if self.bytes_before == 0:
            return 0.0
        return round((1 - self.bytes_after / self.bytes_before) * 100, 1)


# ═══════════════════════════════════════════════════════════════════════════
# Pattern 1: Inflated significance
# ═══════════════════════════════════════════════════════════════════════════

SIGNIFICANCE_INFLATION = re.compile(
    r"(not just|more than just|isn['’]t merely|is not merely|"
    r"in a world where|in today['’]s world|in an era of|"
    r"in the age of|transcends|redefines what it means)",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 2: Promotional / marketing language
# ═══════════════════════════════════════════════════════════════════════════

PROMOTIONAL = re.compile(
    r"(unleash (your|the)|revolutioni[sz]e|game-?changing|"
    r"next[ -]level|you can now|elevate your|take your .+ to the next level|"
    r"supercharge|turbocharge|world-?class|best-?in-?class|industry-?leading|"
    r"cutting-?edge|state-?of-?the-?art)",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 3: Overstructuring — formulaic paragraph/section openers
# ═══════════════════════════════════════════════════════════════════════════

OVERSTRUCTURING = re.compile(
    r"^\s*(First(ly)?,|Second(ly)?,|Third(ly)?,|Fourth(ly)?,|Fifth(ly)?,|"
    r"Finally,|Lastly,|In conclusion,|To conclude,|To sum up,|"
    r"In summary,|As a final point,|Last but not least,)\s",
    re.IGNORECASE | re.MULTILINE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 4: Adjective overuse — AI-favorite intensifiers
# ═══════════════════════════════════════════════════════════════════════════

ADJECTIVE_OVERUSE = re.compile(
    r"\b(seamless(ly)?|robust(ly)?|innovative|cutting-edge|powerful|"
    r"comprehensive|dynamic|holistic|synergistic|streamlined|optimized|"
    r"next-generation|advanced|best-in-class|world-class|unparalleled|"
    r"unmatched|exceptional|outstanding|incredible|remarkable|fantastic)\b",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 5: Exaggerated contrasts
# ═══════════════════════════════════════════════════════════════════════════

EXAGGERATED_CONTRAST = re.compile(
    r"(However,|Nevertheless,|Nonetheless,|On the other hand,|"
    r"In contrast,|Conversely,|That said,|Having said that,|"
    r"Despite this,|In spite of this,)",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 7: AI vocabulary — words that scream "I was written by an LLM"
# ═══════════════════════════════════════════════════════════════════════════

AI_VOCABULARY = {
    "delve": "explore",
    "delve into": "explore",
    "delves into": "explores",
    "tapestry": "fabric",
    "landscape": "field",
    "realm": "area",
    "crucial": "important",
    "vibrant": "lively",
    "moreover": "also",
    "furthermore": "also",
    "consequently": "so",
    "thus": "so",
    "therefore": "so",
    "hence": "so",
    "accordingly": "so",
    "notably": "",
    "interestingly": "",
    "importantly": "",
    "significantly": "",
    "particularly": "especially",
    "specifically": "",
    "essentially": "",
    "fundamentally": "",
    "inherently": "",
}

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 8: Copula avoidance — "serves as" / "boasts" / "features"
# ═══════════════════════════════════════════════════════════════════════════

COPULA_REWRITES = [
    (re.compile(r"\bserves as\b", re.IGNORECASE), "is"),
    (re.compile(r"\bserves as a\b", re.IGNORECASE), "is a"),
    (re.compile(r"\bboasts\b", re.IGNORECASE), "has"),
    (re.compile(r"\bfeatures\b(?=\s+(?:a|an|the|advanced|built-in|integrated|multiple))",
              re.IGNORECASE), "includes"),
    (re.compile(r"\bshowcases\b", re.IGNORECASE), "shows"),
    (re.compile(r"\bhouses\b", re.IGNORECASE), "contains"),
    (re.compile(r"\bpossesses\b", re.IGNORECASE), "has"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 9: Tailing negations
# ═══════════════════════════════════════════════════════════════════════════

TAILING_NEGATIONS = [
    (re.compile(r",\s*no exceptions\.?", re.IGNORECASE), "."),
    (re.compile(r",\s*no questions asked\.?", re.IGNORECASE), "."),
    (re.compile(r",\s*without (exception|question|fail)\.?", re.IGNORECASE), "."),
    (re.compile(r",\s*bar none\.?", re.IGNORECASE), "."),
    (re.compile(r",\s*hands down\.?", re.IGNORECASE), "."),
    (re.compile(r",\s*period\.?\s*$", re.IGNORECASE), "."),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 10: Rule of three — "fast, reliable, and secure"
# ═══════════════════════════════════════════════════════════════════════════

RULE_OF_THREE = re.compile(
    r"(\b\w+),\s+(\w+),\s+and\s+(\w+)\b",
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 11: Excessive hedging
# ═══════════════════════════════════════════════════════════════════════════

HEDGING = [
    (re.compile(r"\bit is (?:important|worth|essential|crucial|vital|necessary|key) to note that\b",
              re.IGNORECASE), ""),
    (re.compile(r"\bit should be (?:noted|mentioned|pointed out|emphasized|stressed) that\b",
              re.IGNORECASE), ""),
    (re.compile(r"\bit is worth (?:mentioning|noting|pointing out|highlighting)\b",
              re.IGNORECASE), ""),
    (re.compile(r"\bit (?:can|could|might|may) be (?:argued|said|stated|suggested|claimed) that\b",
              re.IGNORECASE), ""),
    (re.compile(r"\barguably\b", re.IGNORECASE), ""),
    (re.compile(r"\b(?:potentially|could possibly|might possibly)\b",
              re.IGNORECASE), ""),
    (re.compile(r"\bto (?:a certain extent|some degree|some extent)\b",
              re.IGNORECASE), ""),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 12: Em-dash overuse
# ═══════════════════════════════════════════════════════════════════════════

EM_DASH = re.compile(r"\s?—\s?")

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 13: Passive auxiliary overuse
# ═══════════════════════════════════════════════════════════════════════════

PASSIVE_AUXILIARY = [
    (re.compile(r"\bcan be (used|found|seen|accessed|applied|utilized|employed|implemented)\b",
              re.IGNORECASE), lambda m: f"is {m.group(1)}"),
    (re.compile(r"\bcan be (easily|quickly|readily|simply) (used|found|accessed)\b",
              re.IGNORECASE), lambda m: f"is {m.group(2)}"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 14: Formal linking word overuse
# ═══════════════════════════════════════════════════════════════════════════

FORMAL_LINKING = [
    (re.compile(r"\bFurthermore,?\s+", re.IGNORECASE), ""),
    (re.compile(r"\bMoreover,?\s+", re.IGNORECASE), ""),
    (re.compile(r"\bConsequently,?\s+", re.IGNORECASE), ""),
    (re.compile(r"\bIn addition,?\s+", re.IGNORECASE), "Also, "),
    (re.compile(r"\bAdditionally,?\s+", re.IGNORECASE), "Also, "),
    (re.compile(r"\bThus,?\s+", re.IGNORECASE), "So, "),
    (re.compile(r"\bHence,?\s+", re.IGNORECASE), "So, "),
    (re.compile(r"\bTherefore,?\s+", re.IGNORECASE), "So, "),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 15: Suffix-heavy words
# ═══════════════════════════════════════════════════════════════════════════

SUFFIX_HEAVY = re.compile(
    r"\b\w{8,}(?:ization|ability|fulness|ational|istically|ological)\b",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 16: Colon explosion — "X: Y definition" patterns
# ═══════════════════════════════════════════════════════════════════════════

COLON_EXPLOSION = re.compile(
    r"(\w[\w\s]{3,40}):\s+(\w[\w\s]{3,40})[.,;]",
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 17: Contradiction pauses — "while X, Y" repetition
# ═══════════════════════════════════════════════════════════════════════════

CONTRADICTION_PAUSE = re.compile(
    r"^(While|Although|Even though|Though)\s",
    re.IGNORECASE | re.MULTILINE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 18: Emoji overuse — more than 2 emoji in formal text
# ═══════════════════════════════════════════════════════════════════════════

EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\u2600-\u27BF\u2B50\u2702-\u27B0\u24C2-\U0001F251"
    r"\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    r"\U0001F600-\U0001F64F\u200D\uFE0F]",
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 19: Thinking-like pace — "let's think about this step by step"
# ═══════════════════════════════════════════════════════════════════════════

THINKING_PACE = re.compile(
    r"(let['’]s (think|consider|break|walk|step|explore|dive|unpack|"
    r"take a (moment|step|look)|go through)|"
    r"step[- ]by[- ]step|"
    r"let me (explain|break|walk you through|elaborate))",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 20: Chatbot artifacts
# ═══════════════════════════════════════════════════════════════════════════

CHATBOT_ARTIFACTS = re.compile(
    r"^\s*(I hope this|I trust this|Let me know|Feel free|Would you like|"
    r"Should I|Want me to|you['’]d like|you would like|"
    r"If you have (any|further|more) questions|"
    r"Don['’]t hesitate|Please (let me know|reach out|don['’]t hesitate)|"
    r"I['’]m (happy|glad|here) to|Reach out if|"
    r"Feel free to (reach out|ask|contact|let me know)|"
    r"Please note that|It is (?:important|worth|essential) to (?:note|mention|remember) that)",
    re.IGNORECASE | re.MULTILINE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 21: Knowledge-cutoff disclaimers
# ═══════════════════════════════════════════════════════════════════════════

DISCLAIMERS = re.compile(
    r"(as of (?:my knowledge|my training|\w+ \d{2,4})|"
    r"based on (?:available information|my training|the information)|"
    r"according to (?:my training|available|the latest)|"
    r"not (?:extensively|publicly|widely) (?:documented|available|known)|"
    r"may not be (?:fully |completely )?accurate|"
    r"limited (?:in|by) (?:available|my |the ))",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 22: Sycophantic tone
# ═══════════════════════════════════════════════════════════════════════════

SYCOPHANTIC = re.compile(
    r"^\s*(Great question|Excellent point|You['’]re absolutely right|"
    r"That['’]s a great|What a great|"
    r"I (?:completely|totally|absolutely) agree|"
    r"You (?:make|raise) (?:a|an) (?:great|excellent|good|valid|interesting) point|"
    r"I couldn['’]t agree more|Well (?:said|put))",
    re.IGNORECASE | re.MULTILINE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 23: Filler phrases
# ═══════════════════════════════════════════════════════════════════════════

def _preserve_case(original: str, replacement: str) -> str:
    """Preserve the case of the first letter from the original text."""
    if original and original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def _make_filler_replacer(replacement: str):
    """Make a replacement lambda that preserves case."""
    return lambda m: _preserve_case(m.group(0), replacement)


FILLER_PHRASES = [
    (re.compile(r"\bin order to\b", re.IGNORECASE), _make_filler_replacer("to")),
    (re.compile(r"\bdue to the fact that\b", re.IGNORECASE), _make_filler_replacer("because")),
    (re.compile(r"\bowing to the fact that\b", re.IGNORECASE), _make_filler_replacer("because")),
    (re.compile(r"\bin the event that\b", re.IGNORECASE), _make_filler_replacer("if")),
    (re.compile(r"\bon the grounds that\b", re.IGNORECASE), _make_filler_replacer("because")),
    (re.compile(r"\bfor the purpose of\b", re.IGNORECASE), _make_filler_replacer("for")),
    (re.compile(r"\bwith regard to\b", re.IGNORECASE), _make_filler_replacer("about")),
    (re.compile(r"\bin regard to\b", re.IGNORECASE), _make_filler_replacer("about")),
    (re.compile(r"\bwith respect to\b", re.IGNORECASE), _make_filler_replacer("about")),
    (re.compile(r"\bin terms of\b", re.IGNORECASE), _make_filler_replacer("for")),
    (re.compile(r"\bin the process of\b", re.IGNORECASE), _make_filler_replacer("")),
    (re.compile(r"\ba number of\b", re.IGNORECASE), _make_filler_replacer("several")),
    (re.compile(r"\bthe vast majority of\b", re.IGNORECASE), _make_filler_replacer("most")),
    (re.compile(r"\ba wide (?:variety|range) of\b", re.IGNORECASE), _make_filler_replacer("many")),
    (re.compile(r"\bat the present time\b", re.IGNORECASE), _make_filler_replacer("now")),
    (re.compile(r"\bat this point in time\b", re.IGNORECASE), _make_filler_replacer("now")),
    (re.compile(r"\bhas the ability to\b", re.IGNORECASE), _make_filler_replacer("can")),
    (re.compile(r"\bis able to\b", re.IGNORECASE), _make_filler_replacer("can")),
    (re.compile(r"\bhas the capacity to\b", re.IGNORECASE), _make_filler_replacer("can")),
    (re.compile(r"\bmake use of\b", re.IGNORECASE), _make_filler_replacer("use")),
    (re.compile(r"\btake advantage of\b", re.IGNORECASE), _make_filler_replacer("use")),
    (re.compile(r"\bmake a decision\b", re.IGNORECASE), _make_filler_replacer("decide")),
    (re.compile(r"\btake into account\b", re.IGNORECASE), _make_filler_replacer("consider")),
    (re.compile(r"\btake into consideration\b", re.IGNORECASE), _make_filler_replacer("consider")),
    (re.compile(r"\bdraw (?:your|the) attention to\b", re.IGNORECASE), _make_filler_replacer("note")),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 24: Excessive hedging — "could potentially", "might possibly"
# ═══════════════════════════════════════════════════════════════════════════

EXCESSIVE_HEDGING = [
    (re.compile(r"\bcould potentially\b", re.IGNORECASE), "may"),
    (re.compile(r"\bmight possibly\b", re.IGNORECASE), "may"),
    (re.compile(r"\bpotentially could\b", re.IGNORECASE), "may"),
    (re.compile(r"\bpossibly might\b", re.IGNORECASE), "may"),
    (re.compile(r"\bmay potentially\b", re.IGNORECASE), "may"),
    (re.compile(r"\bit is possible that\b", re.IGNORECASE), ""),
    (re.compile(r"\bthere is a possibility that\b", re.IGNORECASE), ""),
    (re.compile(r"\bin some cases\b", re.IGNORECASE), "sometimes"),
    (re.compile(r"\bin certain situations\b", re.IGNORECASE), "sometimes"),
    (re.compile(r"\bunder certain circumstances\b", re.IGNORECASE), "sometimes"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 25: Generic endings / conclusions
# ═══════════════════════════════════════════════════════════════════════════

GENERIC_ENDINGS = re.compile(
    r"^\s*(In conclusion|To sum up|Overall|All in all|"
    r"In summary|To conclude|As we have seen|As demonstrated|"
    r"As discussed|In closing|To wrap up|In the final analysis|"
    r"Ultimately|In the end|At the end of the day)\b",
    re.IGNORECASE | re.MULTILINE,
)

# ═══════════════════════════════════════════════════════════════════════════
# Pattern 26: Formulaic transitional padding
# ═══════════════════════════════════════════════════════════════════════════

TRANSITIONAL_PADDING = re.compile(
    r"^\s*(It is (?:also )?worth (?:noting|mentioning|highlighting|pointing out|remembering) that|"
    r"It (?:should|must|can|may|might|could) be (?:noted|mentioned|said|argued|stated|emphasized) that|"
    r"What['’]s more,|On top of that,|"
    r"Not (?:only|just) that, but|"
    r"As an added bonus,)\s",
    re.IGNORECASE | re.MULTILINE,
)


# Phase 1 helper: check if a line is purely sign-offs
_SIGN_OFF_TOKENS = re.compile(
    r"(Happy coding|Enjoy!|Cheers!|Have fun|Good luck|"
    r"Happy (?:writing|building|hacking|learning|reading|exploring)|"
    r"Best of luck|All the best|Warm regards)",
    re.IGNORECASE,
)


def _is_signoff_only(line: str) -> bool:
    """Return True if the line contains ONLY sign-off phrases."""
    stripped = line.strip()
    if not stripped:
        return False
    # Remove all sign-off tokens and punctuation/whitespace
    remainder = _SIGN_OFF_TOKENS.sub("", stripped)
    remainder = re.sub(r"[!.,;:\s]+", "", remainder)
    return remainder == ""


# ═══════════════════════════════════════════════════════════════════════════
# Core pipeline
# ═══════════════════════════════════════════════════════════════════════════


def shoruiko(text: str, mode: Mode | None = None) -> tuple[str, Stats]:
    """Process text through the shoruiko pipeline.

    Returns (processed_text, stats).
    """
    if mode is None:
        mode = mode_medium()

    stats = Stats(bytes_before=len(text.encode("utf-8")))
    lines = text.split("\n")
    result_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # ── Phase 1: Line-level removal ──

        if mode.remove_chatbot_artifacts and CHATBOT_ARTIFACTS.match(stripped):
            stats.chatbot_lines += 1
            continue

        if mode.remove_sycophantic and SYCOPHANTIC.match(stripped):
            stats.sycophantic_lines += 1
            continue

        if mode.remove_disclaimers and DISCLAIMERS.search(stripped):
            stats.disclaimers += 1
            continue

        if mode.remove_generic_endings and GENERIC_ENDINGS.match(stripped):
            stats.generic_endings += 1
            continue

        if mode.remove_sign_offs and _is_signoff_only(line):
            stats.generic_endings += 1
            continue

        # Line survives Phase 1
        result_lines.append(line)

    text = "\n".join(result_lines)

    # ── Phase 2: Phrase substitution ──

    if mode.substitute_filler:
        for pattern, replacement in FILLER_PHRASES:
            count_before = len(pattern.findall(text))
            text = pattern.sub(replacement, text)
            stats.filler_substitutions += count_before

    if mode.substitute_hedging:
        for pattern, replacement in HEDGING + EXCESSIVE_HEDGING:
            count_before = len(pattern.findall(text))
            text = pattern.sub(replacement, text)
            stats.hedging_substitutions += count_before

    if mode.substitute_copula:
        for pattern, replacement in COPULA_REWRITES:
            count_before = len(pattern.findall(text))
            text = pattern.sub(replacement, text)
            stats.copula_substitutions += count_before

    if mode.substitute_formal_linking:
        for pattern, replacement in FORMAL_LINKING:
            count_before = len(pattern.findall(text))
            text = pattern.sub(replacement, text)
            stats.formal_linking_substitutions += count_before

    # ── Phase 3: Sentence rewrites ──

    if mode.rewrite_contrasts:
        # Replace leading contrast markers with nothing (keep the sentence)
        count_before = len(EXAGGERATED_CONTRAST.findall(text))
        text = EXAGGERATED_CONTRAST.sub("", text)
        stats.contrast_rewrites += count_before

    if mode.rewrite_overstructuring:
        count_before = len(OVERSTRUCTURING.findall(text))
        text = OVERSTRUCTURING.sub("", text)
        stats.overstructuring_rewrites += count_before

    if mode.rewrite_rule_of_three:
        def _reduce_three(m: re.Match) -> str:
            stats.rule_of_three_rewrites += 1
            return f"{m.group(1)} and {m.group(2)}"

        text = RULE_OF_THREE.sub(_reduce_three, text)
        # Reset counter (sub calls _reduce_three for each match)
        # The counter is incremented inside the callback

    # ── Phase 4: Vocabulary swap ──

    if mode.vocabulary_swap:
        words = text.split(" ")
        new_words: list[str] = []
        i = 0
        while i < len(words):
            word = words[i]
            # Try multi-word matches first
            matched = False
            for n in range(3, 0, -1):
                if i + n <= len(words):
                    phrase = " ".join(words[i : i + n])
                    clean = phrase.strip(".,;:!?\"'()[]{}")
                    if clean.lower() in AI_VOCABULARY:
                        replacement = AI_VOCABULARY[clean.lower()]
                        if replacement:
                            new_words.append(replacement)
                        stats.vocabulary_swaps += 1
                        i += n
                        matched = True
                        break
            if not matched:
                clean = word.strip(".,;:!?\"'()[]{}")
                if clean.lower() in AI_VOCABULARY:
                    replacement = AI_VOCABULARY[clean.lower()]
                    word_no_punct = word.strip(".,;:!?\"'()[]{}")
                    if replacement:
                        word = word.replace(word_no_punct, replacement)
                    else:
                        word = ""
                    stats.vocabulary_swaps += 1
                new_words.append(word)
                i += 1
        text = " ".join(new_words)

    # ── Phase 5: Full-text metrics ──

    if mode.normalize_em_dashes:
        dashes = EM_DASH.findall(text)
        # If more than 2 em-dashes per 500 chars, replace excess with commas
        char_count = len(text)
        dash_limit = max(2, char_count // 250)
        if len(dashes) > dash_limit:
            excess = len(dashes) - dash_limit
            count = 0
            def _cap_dashes(m: re.Match) -> str:
                nonlocal count
                count += 1
                if count > dash_limit:
                    stats.em_dashes_normalized += 1
                    return ", "
                return m.group(0)
            text = EM_DASH.sub(_cap_dashes, text)

    if mode.normalize_passive_voice:
        for pattern, replacement_fn in PASSIVE_AUXILIARY:
            count_before = len(pattern.findall(text))
            text = pattern.sub(replacement_fn, text)
            stats.passive_rewrites += count_before

    # ── Phase 6: Whitespace normalization ──

    if mode.normalize_whitespace:
        lines = text.split("\n")
        cleaned: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank:
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            else:
                cleaned.append(line.rstrip())
                prev_blank = False
        text = "\n".join(cleaned)
        text = text.rstrip() + "\n"

    stats.bytes_after = len(text.encode("utf-8"))
    return text, stats


def shoruiko_file(path: str, mode: Mode | None = None) -> tuple[str, Stats]:
    """Process a single file — auto-detects PDF/DOCX via extract_text()."""
    text = extract_text(path)
    return shoruiko(text, mode)


# ═══════════════════════════════════════════════════════════════════════════
# Document text extraction
# ═══════════════════════════════════════════════════════════════════════════

def extract_text(path: str) -> str:
    """Extract readable text from any supported document format.

    Supports: .txt, .md, .rst, .html/.htm/.xhtml, .pdf, .docx, .adoc, .markdown.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in (".pdf",):
        return _extract_pdf(path)
    elif ext in (".docx",):
        return _extract_docx(path)
    elif ext in (".html", ".htm", ".xhtml"):
        return _extract_html(path)
    else:
        # Plain text: .txt, .md, .rst, .adoc, .markdown, etc.
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def _extract_pdf(path: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError(
            "PyPDF2 is required to read PDF files. "
            "Install it with: pip install PyPDF2"
        )

    reader = PdfReader(path)
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_docx(path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx is required to read DOCX files. "
            "Install it with: pip install python-docx"
        )

    doc = Document(path)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    return "\n\n".join(paragraphs)


def _extract_html(path: str) -> str:
    """Extract readable text from an HTML file."""
    import html.parser

    class _HTMLTextExtractor(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts: list[str] = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript", "head"):
                self._skip = True
            elif tag in ("br", "p", "div", "li", "h1", "h2", "h3",
                         "h4", "h5", "h6", "tr", "blockquote"):
                self._parts.append("\n")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript", "head"):
                self._skip = False
            elif tag in ("p", "div", "li", "h1", "h2", "h3",
                         "h4", "h5", "h6", "tr", "blockquote"):
                self._parts.append("\n")

        def handle_data(self, data):
            if not self._skip:
                text = data.strip()
                if text:
                    self._parts.append(text + " ")

        def get_text(self) -> str:
            raw = "".join(self._parts)
            # Collapse multiple blank lines
            lines = [line.strip() for line in raw.split("\n")
                     if line.strip()]
            return "\n\n".join(lines)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html_text = f.read()

    extractor = _HTMLTextExtractor()
    extractor.feed(html_text)
    return extractor.get_text()
