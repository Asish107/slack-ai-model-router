import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    category: str
    tier: str
    reason: str


RULES = (
    (
        "code_generation_debugging",
        "mid",
        r"\b(code|python|javascript|typescript|sql|api|function|class|bug|debug|stack trace|refactor|regex)\b",
        "code or debugging terms",
    ),
    (
        "math_logic",
        "mid",
        r"\b(calculate|equation|proof|probability|derivative|integral|algebra|logic|algorithm|complexity)\b",
        "math, logic, or algorithmic terms",
    ),
    (
        "creative_architecture",
        "frontier",
        r"\b(architecture|system design|design a system|brainstorm|creative|campaign|story|strategy|roadmap)\b",
        "creative or architecture terms",
    ),
    (
        "complex_reasoning",
        "frontier",
        r"\b(analyze|trade-?offs?|multi-?step|investigate|root cause|evaluate|compare deeply|research|decision)\b",
        "multi-step reasoning or judgment terms",
    ),
    (
        "summarization_translation",
        "fast",
        r"\b(summarize|summary|translate|translation|rewrite|paraphrase|shorten)\b",
        "summarization or translation terms",
    ),
    (
        "data_extraction_formatting",
        "fast",
        r"\b(extract|format|json|csv|table|bullet points|structured|fields|parse)\b",
        "extraction or formatting terms",
    ),
)


def classify_prompt(prompt: str) -> Classification:
    normalized = " ".join(prompt.lower().split())
    for category, tier, pattern, reason in RULES:
        if re.search(pattern, normalized):
            return Classification(category, tier, reason)
    if len(normalized) > 1200:
        return Classification("complex_reasoning", "frontier", "long prompt")
    return Classification("simple_qa", "fast", "short general question")
