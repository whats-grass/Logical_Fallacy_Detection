"""Text normalisation and the a-priori token lexicons used in the shortcut analysis.

The three-way lexicon was written from the Label Guide definitions BEFORE inspecting
any model coefficients, so it is not tuned to make the result look a particular way.
"""
import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

TOKEN_RE = re.compile(r"\b[a-z][a-z']*[a-z]\b|\b[a-z]\b")


def tokenize(text):
    """Lower-case word tokens (keeps contractions like don't / they'll)."""
    return TOKEN_RE.findall(text.lower())


_SENT_START = re.compile(r"(^|[.!?:;]\s+|['\"(]\s*)$")
_CAP = re.compile(r"\b([A-Z][a-z]+(?:\.[A-Z][a-z]*)?)\b")
_KEEP_CAPS = {"I", "So", "We", "The", "Oh", "If", "It", "This", "They", "You"}


def mask_proper_nouns(text, placeholder="propername"):
    """Heuristic proper-noun masking (no tagger download needed).

    A capitalised word that is not sentence-initial / quote-initial is treated as a
    proper noun (Dr, Smith, Harvard, Tesla, ...). Known limitation: sentence-initial
    names are kept and capitalised common nouns mid-sentence are masked.
    """
    out, last = [], 0
    for m in _CAP.finditer(text):
        word = m.group(1)
        prefix = text[: m.start()]
        if word in _KEEP_CAPS or _SENT_START.search(prefix):
            continue
        out.append(text[last : m.start()])
        out.append(placeholder)
        last = m.end()
    out.append(text[last:])
    return "".join(out)


# --- Rhetorical cue lexicon: words whose *meaning* signals a fallacy pattern -------
RHETORICAL_CUES = {
    # slippery slope / chain consequences
    "eventually", "soon", "lead", "leads", "leading", "inevitably", "next", "collapse",
    "ruin", "end", "spiral", "chain", "ultimately", "domino",
    # authority
    "expert", "experts", "scientist", "scientists", "doctor", "doctors", "dr", "professor",
    "celebrity", "famous", "authority", "nobel", "says", "said", "claims", "trust",
    # popularity / bandwagon
    "everyone", "everybody", "popular", "millions", "majority", "trend", "trending",
    "nobody", "people", "agree", "agrees", "believe", "believes",
    # emotion
    "fear", "afraid", "pity", "guilt", "shame", "heartbroken", "devastated", "scared",
    "danger", "dangerous", "think", "children", "imagine", "feel",
    # ad hominem
    "idiot", "stupid", "liar", "hypocrite", "ignorant", "fool", "corrupt", "lazy",
    "incompetent", "dishonest", "crazy", "character",
    # false dilemma
    "either", "or", "only", "choice", "choices", "options", "otherwise", "unless",
    # causation / generalisation
    "because", "caused", "causes", "cause", "after", "since", "therefore", "proves",
    "proof", "all", "always", "never", "every", "must", "clearly", "obviously",
    # composition / equivocation / circular
    "whole", "parts", "part", "each", "entire", "true", "means", "so",
    # ignorance / straw man / red herring
    "proven", "disproven", "evidence", "nobody", "saying", "wants", "anyway", "besides",
    "what", "about",
}

FUNCTION_WORDS = set(ENGLISH_STOP_WORDS) - RHETORICAL_CUES


def token_group(token):
    """Return 'cue', 'function' or 'topic' for a vocabulary item (unigram or n-gram).

    An n-gram is 'topic' if any word in it is topical, else 'cue' if any word is a cue,
    else 'function'. A token containing the proper-noun placeholder counts as topic.
    """
    words = token.split()
    if any((w not in RHETORICAL_CUES and w not in FUNCTION_WORDS) for w in words):
        return "topic"
    if any(w in RHETORICAL_CUES for w in words):
        return "cue"
    return "function"


def keep_groups(text, groups):
    """Return text with only tokens of the given groups kept (used for masking tests)."""
    return " ".join(t for t in tokenize(text) if token_group(t) in groups)
