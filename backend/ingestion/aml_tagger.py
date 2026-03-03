"""
AML Chunk Tagger
================
Classifies regulatory text chunks with AML domain metadata:
  - regulation_type   : KYC | STR | CTR | PEP | EDD | CDD | Sanctions | RecordKeeping | BeneficialOwnership
  - obligation_level  : Mandatory | Recommended | Optional
  - jurisdiction      : RBI | FATF | FIU-IND | SEBI | PMLA | EU | USA
  - entity_type       : Bank | NBFC | PaymentBank | Broker | VASP

Three tagging modes (set via TAG_MODE env var or argument):
  "rules"   – keyword/regex lookup table (fast, free, ~80% accuracy)
  "llm"     – GPT-4o-mini prompt (accurate, costs tokens, ~95%)
  "hybrid"  – rules first; LLM called only for ambiguous chunks (balanced)

Default is "hybrid".
"""
from __future__ import annotations

import re
import logging
from typing import Optional, List
from backend.ingestion.schemas import StructuredChunk

logger = logging.getLogger(__name__)

# ── Typing helpers ─────────────────────────────────────────────────────────────
TagMode = str   # "rules" | "llm" | "hybrid"


# ── Keyword rule table ─────────────────────────────────────────────────────────
# Each rule: (compiled_regex, regulation_type, obligation_level)
# Rules are evaluated in order; first match wins.
_RULES: list[tuple[re.Pattern, str, str]] = [
    # CTR — Cash Transaction Report (mandatory threshold)
    (re.compile(
        r"\b(cash\s+transaction\s+report|CTR|₹\s*10\s*(lakh|lac)|transaction\s+report\s+to\s+FIU)",
        re.IGNORECASE,
    ), "CTR", "Mandatory"),

    # STR — Suspicious Transaction Report
    (re.compile(
        r"\b(suspicious\s+transaction|STR|unusual\s+transaction|report\s+suspicious)",
        re.IGNORECASE,
    ), "STR", "Mandatory"),

    # PEP — Politically Exposed Person
    (re.compile(
        r"\b(politically\s+exposed\s+person|PEP\b|public\s+figure|prominent\s+public)",
        re.IGNORECASE,
    ), "PEP", "Mandatory"),

    # EDD — Enhanced Due Diligence
    (re.compile(
        r"\b(enhanced\s+due\s+diligence|EDD\b|high\s+risk\s+(customer|client|country))",
        re.IGNORECASE,
    ), "EDD", "Mandatory"),

    # Sanctions / Freeze
    (re.compile(
        r"\b(sanction(s|ed)?|freeze\s+account|designated\s+(person|entity)|UNSC\s+list|OFAC)",
        re.IGNORECASE,
    ), "Sanctions", "Mandatory"),

    # Beneficial Ownership / UBO
    (re.compile(
        r"\b(beneficial\s+owner(ship)?|UBO\b|ultimate\s+beneficial|25\s*(%|percent)\s+threshold)",
        re.IGNORECASE,
    ), "BeneficialOwnership", "Mandatory"),

    # Record Keeping / Retention
    (re.compile(
        r"\b(record\s+keeping|record\s+retention|maintain\s+(records?|documents?)|5\s+year(s)?\s+retention)",
        re.IGNORECASE,
    ), "RecordKeeping", "Mandatory"),

    # CDD — Customer Due Diligence
    (re.compile(
        r"\b(customer\s+due\s+diligence|CDD\b|due\s+diligence\s+on\s+customer)",
        re.IGNORECASE,
    ), "CDD", "Mandatory"),

    # KYC — Know Your Customer (broad, check after more specific rules)
    (re.compile(
        r"\b(know\s+your\s+customer|KYC\b|customer\s+identification|CKYC|re-?KYC|periodic\s+KYC)",
        re.IGNORECASE,
    ), "KYC", "Mandatory"),
]

# ── Jurisdiction keyword rules ─────────────────────────────────────────────────
_JURISDICTION_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bRBI\b|Reserve\s+Bank\s+of\s+India|Master\s+Direction", re.IGNORECASE), "RBI"),
    (re.compile(r"\bFATF\b|Financial\s+Action\s+Task\s+Force", re.IGNORECASE), "FATF"),
    (re.compile(r"\bFIU-?IND\b|Financial\s+Intelligence\s+Unit", re.IGNORECASE), "FIU-IND"),
    (re.compile(r"\bSEBI\b|Securities\s+and\s+Exchange\s+Board", re.IGNORECASE), "SEBI"),
    (re.compile(r"\bPMLA\b|Prevention\s+of\s+Money\s+Laundering\s+Act", re.IGNORECASE), "PMLA"),
    (re.compile(r"\b(EU|European\s+Union|6AMLD|6th\s+AML\s+Directive)", re.IGNORECASE), "EU"),
    (re.compile(r"\b(FinCEN|BSA|Bank\s+Secrecy\s+Act|USA|United\s+States)", re.IGNORECASE), "USA"),
]

# ── Entity type rules ──────────────────────────────────────────────────────────
_ENTITY_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(payment\s+bank|payments?\s+bank)", re.IGNORECASE), "PaymentBank"),
    (re.compile(r"\b(NBFC|non-?banking\s+financial)", re.IGNORECASE), "NBFC"),
    (re.compile(r"\b(broker|stock\s+broker|market\s+intermediar)", re.IGNORECASE), "Broker"),
    (re.compile(r"\b(VASP|virtual\s+asset\s+service\s+provider|crypto\s+exchange)", re.IGNORECASE), "VASP"),
    (re.compile(r"\b(scheduled\s+commercial\s+bank|commercial\s+bank|bank(?:ing)?\s+compan)", re.IGNORECASE), "Bank"),
]


def _apply_rules(text: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Apply keyword rules to classify a chunk.

    Returns:
        (regulation_type, obligation_level, jurisdiction, entity_type)
        Any field may be None if no rule matched.
    """
    regulation_type = None
    obligation_level = None

    for pattern, reg_type, obl_level in _RULES:
        if pattern.search(text):
            regulation_type = reg_type
            obligation_level = obl_level
            break

    # Jurisdiction — first match wins
    jurisdiction = None
    for pattern, jur in _JURISDICTION_RULES:
        if pattern.search(text):
            jurisdiction = jur
            break

    # Entity type — first match wins
    entity_type = None
    for pattern, ent in _ENTITY_RULES:
        if pattern.search(text):
            entity_type = ent
            break

    return regulation_type, obligation_level, jurisdiction, entity_type


def _is_ambiguous(regulation_type: Optional[str], text: str) -> bool:
    """
    Determine if a chunk is ambiguous enough to warrant an LLM call.
    Ambiguous = regulation_type not found OR text mentions multiple AML topics.
    """
    if regulation_type is None:
        aml_keywords = re.findall(
            r"\b(AML|anti.money.laundering|compliance|financial\s+crime|monitoring)\b",
            text, re.IGNORECASE
        )
        return len(aml_keywords) >= 2   # AML-relevant but unclassified

    return False


def _llm_tag(chunk: StructuredChunk) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Use the LLM to classify an ambiguous chunk.
    Falls back gracefully if LLM call fails.
    """
    try:
        from backend.config.settings import get_llm_client, get_model_name
        client = get_llm_client()

        prompt = f"""You are an AML regulatory expert. Classify this text chunk from a regulatory document.

Text:
{chunk.content[:800]}

Respond ONLY as JSON with these exact keys:
{{
  "regulation_type": "KYC" | "STR" | "CTR" | "PEP" | "EDD" | "CDD" | "Sanctions" | "RecordKeeping" | "BeneficialOwnership" | null,
  "obligation_level": "Mandatory" | "Recommended" | "Optional" | null,
  "jurisdiction": "RBI" | "FATF" | "FIU-IND" | "SEBI" | "PMLA" | "EU" | "USA" | null,
  "entity_type": "Bank" | "NBFC" | "PaymentBank" | "Broker" | "VASP" | null
}}"""

        response = client.chat_completion(
            model=get_model_name("router"),   # use cheaper/faster router model
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return (
            result.get("regulation_type"),
            result.get("obligation_level"),
            result.get("jurisdiction"),
            result.get("entity_type"),
        )
    except Exception as exc:
        logger.warning(f"[aml_tagger] LLM tagging failed, falling back to rules: {exc}")
        return None, None, None, None


def tag_chunk(
    chunk: StructuredChunk,
    mode: TagMode = "hybrid",
    document_tier: Optional[str] = None,
) -> StructuredChunk:
    """
    Tag a single chunk with AML domain metadata in-place.

    Args:
        chunk:          StructuredChunk to classify
        mode:           "rules" | "llm" | "hybrid"
        document_tier:  "regulatory" | "internal_policy" — set on the chunk directly

    Returns:
        The same chunk object with AML fields populated.
    """
    text = chunk.content

    if mode == "rules":
        reg_type, obl, jur, ent = _apply_rules(text)

    elif mode == "llm":
        reg_type, obl, jur, ent = _llm_tag(chunk)

    else:   # "hybrid" — rules first, LLM for ambiguous
        reg_type, obl, jur, ent = _apply_rules(text)
        if _is_ambiguous(reg_type, text):
            logger.debug(f"[aml_tagger] ambiguous chunk — calling LLM: {text[:80]}…")
            llm_reg, llm_obl, llm_jur, llm_ent = _llm_tag(chunk)
            # LLM result wins for unresolved fields
            reg_type = reg_type or llm_reg
            obl      = obl or llm_obl
            jur      = jur or llm_jur
            ent      = ent or llm_ent

    chunk.regulation_type  = reg_type
    chunk.obligation_level = obl
    chunk.jurisdiction     = jur
    chunk.entity_type      = ent

    if document_tier is not None:
        chunk.document_tier = document_tier

    return chunk


def tag_chunks(
    chunks: List[StructuredChunk],
    mode: TagMode = "hybrid",
    document_tier: Optional[str] = None,
) -> List[StructuredChunk]:
    """
    Tag a list of chunks. Returns the same list with AML metadata populated.

    Args:
        chunks:         List of StructuredChunk to classify
        mode:           "rules" | "llm" | "hybrid"
        document_tier:  "regulatory" | "internal_policy"

    Returns:
        Tagged chunk list (same objects, mutated in-place).
    """
    tagged, skipped = 0, 0
    for chunk in chunks:
        tag_chunk(chunk, mode=mode, document_tier=document_tier)
        if chunk.regulation_type:
            tagged += 1
        else:
            skipped += 1

    logger.info(
        f"[aml_tagger] tagged={tagged} untagged={skipped} "
        f"(mode={mode}, tier={document_tier})"
    )
    return chunks
