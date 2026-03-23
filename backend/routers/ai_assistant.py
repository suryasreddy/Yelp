"""
routers/ai_assistant.py
========================
AI restaurant assistant: LangChain + OpenAI for NLP, MySQL for listings,
optional Tavily web search when the model requests live context.

Environment variables (.env):
  OPENAI_API_KEY=sk-...
  TAVILY_API_KEY=tvly-...
"""

import json
import os
import re
from typing import Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

# ─────────────────────────────────────────────────────────────────────────────
# LLM + Tavily — initialised once at module load
# ─────────────────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)


def _get_tavily() -> TavilySearch:
    return TavilySearch(
        max_results=3,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load preferences from DB (used for ranking + system prompt only)
#
#    UserPreferences columns:
#      cuisine_preferences, price_range, preferred_location, dietary_needs,
#      ambiance_preferences, sort_preference
# ─────────────────────────────────────────────────────────────────────────────


def _load_preferences(user_id: int, db: Session) -> dict:
    """Return saved preferences or {} if none — used for personalization in scoring."""
    row = (
        db.query(models.UserPreferences)
        .filter(models.UserPreferences.user_id == user_id)
        .first()
    )
    if not row:
        return {}

    def safe_list(value) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        return []

    return {
        "cuisines": safe_list(row.cuisine_preferences),
        "price_range": (row.price_range or "").strip(),
        "location": (row.preferred_location or "").strip(),
        "dietary": safe_list(row.dietary_needs),
        "ambiance": safe_list(row.ambiance_preferences),
        "sort_preference": (row.sort_preference or "rating").strip().lower(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. System prompt — instructs exact JSON output and multi-turn merge rules
# ─────────────────────────────────────────────────────────────────────────────


def _build_system_prompt(prefs: dict, user: models.User) -> str:
    lines = []
    if getattr(user, "city", None) or getattr(user, "state", None):
        acct = ", ".join(
            x for x in [getattr(user, "city", None) or "", getattr(user, "state", None) or ""] if x
        )
        if acct:
            lines.append(f"- Account city/state   : {acct} (use for 'near me' when the user implies it)")
    if prefs.get("cuisines"):
        lines.append(f"- Preferred cuisines : {', '.join(prefs['cuisines'])}")
    if prefs.get("price_range"):
        lines.append(f"- Price preference   : {prefs['price_range']}")
    if prefs.get("location"):
        lines.append(f"- Preferred area     : {prefs['location']}")
    if prefs.get("dietary"):
        lines.append(f"- Dietary needs      : {', '.join(prefs['dietary'])}")
    if prefs.get("ambiance"):
        lines.append(f"- Ambiance           : {', '.join(prefs['ambiance'])}")

    pref_block = (
        "\n".join(lines)
        if lines
        else "No preferences saved yet — still be helpful and friendly."
    )

    return f"""You are a warm, knowledgeable restaurant discovery assistant for a Yelp-style app.

Saved profile (use ONLY to personalize tone and ranking — see critical rules below):
{pref_block}

For EVERY user message you must output EXACTLY one JSON block in this shape (use ```json fences):

```json
{{
  "filters": {{
    "cuisine_type": null,
    "price_range": null,
    "dietary": [],
    "ambiance": [],
    "keywords": [],
    "location": null
  }},
  "needs_web_search": false,
  "web_search_query": null,
  "reply": "Your short, natural reply here."
}}
```

Critical rules for "filters" (these drive database search — follow strictly):
1. ONLY include cuisine_type, price_range, location, dietary, keywords, or ambiance when the USER (or prior turns in the conversation) clearly asked for them.
2. NEVER copy saved profile cuisines, price, location, dietary, or ambiance into "filters" just because they exist in the profile. Profile is not a search filter.
3. Generic hunger ("I'm hungry", "what restaurants do you recommend?", "surprise me") → leave cuisine_type null, price_range null, dietary/ambiance/keywords empty unless the user said otherwise. The backend WILL return real restaurant cards from the database — do not reply with only "tell me your preference"; give a short friendly intro and the JSON so the user sees picks immediately.
4. Multi-turn: MERGE the full intent. Example: "I want Mexican" then "make it vegan" → cuisine_type "Mexican", dietary ["vegan"] (keep Mexican; add vegan).
5. "Best rated near me" / location in conversation → set "location" from the user's city if they gave it; if they refer to saved area, you may set location to that string only when the user implied "near me" or similar.
6. price_range must be one of: "$", "$$", "$$$", "$$$$", or null — only when the user cares about budget or you infer it clearly from their words (not from profile alone).
7. needs_web_search: true ONLY for live web data (hours today, is X open now, trending this week, special events). Set web_search_query to a short search phrase when true.
8. reply: conversational, friendly, not robotic — brief setup only; do not paste a long numbered list (the app shows cards).
9. NEVER invent or guess restaurant names in "reply". Real names come only from the server after your JSON.
10. dietary[] = HARD constraints only (vegan, gluten-free, halal, nut-free). keywords[] / ambiance[] = SOFT wishes (sweet, dessert, romantic, spicy) — they influence ranking, not exclusion. Do not put "sweet" or "dessert" in dietary unless it is a medical/restriction need.
11. If the user narrows a follow-up (e.g. only "Mexican" after a sweeter ask), drop obsolete keywords from filters so you do not keep stale terms.
12. Questions about "open right now" / hours → set needs_web_search true and a focused web_search_query; still output filters for cuisine/location so the DB can show cards.

Extract from natural language: cuisine, budget, dietary needs, occasion/ambiance (map occasion into keywords or ambiance arrays), and location when relevant.
"""


# ─────────────────────────────────────────────────────────────────────────────
# 3. LangChain messages from history + current user message
# ─────────────────────────────────────────────────────────────────────────────


def _build_lc_messages(
    system_prompt: str,
    history: List[schemas.ChatMessage],
    current_message: str,
) -> List[Any]:
    messages: List[Any] = [SystemMessage(content=system_prompt)]
    for turn in history or []:
        role = (turn.role or "").strip().lower()
        content = (turn.content or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=current_message))
    return messages


# ─────────────────────────────────────────────────────────────────────────────
# 4. Parse structured JSON from the LLM response
# ─────────────────────────────────────────────────────────────────────────────


def _parse_llm_output(raw: str) -> dict:
    """Extract ```json ... ``` or first brace object; safe defaults on failure."""
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        brace = re.search(r"\{.*\}", raw, re.DOTALL)
        json_str = brace.group(0) if brace else "{}"

    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        parsed = {}

    parsed.setdefault("filters", {})
    parsed.setdefault("needs_web_search", False)
    parsed.setdefault("web_search_query", None)
    parsed.setdefault("reply", raw)
    return parsed


def _normalize_filters(filters: dict) -> dict:
    """Ensure list fields are lists of non-empty strings; strip strings."""
    f = dict(filters or {})
    ct = f.get("cuisine_type")
    f["cuisine_type"] = (str(ct).strip() if ct else "") or None

    pr = f.get("price_range")
    if pr is None or str(pr).strip() == "":
        f["price_range"] = None
    else:
        f["price_range"] = str(pr).strip()

    loc = f.get("location")
    f["location"] = (str(loc).strip() if loc else "") or None

    for key in ("dietary", "ambiance", "keywords"):
        v = f.get(key)
        if v is None:
            f[key] = []
        elif isinstance(v, list):
            f[key] = [str(x).strip() for x in v if x and str(x).strip()]
        else:
            s = str(v).strip()
            f[key] = [s] if s else []
    return f


# ─────────────────────────────────────────────────────────────────────────────
# 5. Text blob for matching dietary / ambiance / keywords against a restaurant
# ─────────────────────────────────────────────────────────────────────────────


def _restaurant_text_blob(r: models.Restaurant) -> str:
    """Lowercased text from searchable fields + JSON keyword/amenity lists."""
    parts: List[str] = [
        r.name or "",
        r.description or "",
        r.cuisine_type or "",
    ]
    try:
        parts.append(json.dumps(r.keywords or []))
        parts.append(json.dumps(r.amenities or []))
    except (TypeError, ValueError):
        pass
    return " ".join(parts).lower()


def _matches_all_terms(r: models.Restaurant, terms: List[str]) -> bool:
    """Every term must appear somewhere in the blob (AND)."""
    if not terms:
        return True
    blob = _restaurant_text_blob(r)
    return all(t.lower() in blob for t in terms if t)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Query restaurants — LLM filters only (never saved profile as hard filters)
# ─────────────────────────────────────────────────────────────────────────────

_DB_FETCH_CAP = 250


def _location_tokens(loc: str) -> List[str]:
    """
    Split locations like 'San Francisco, CA' into ['San Francisco', 'CA'] so we OR-match
    columns. A single ilike on the full string fails when city is stored as 'San Francisco'
    only (substring 'San Francisco, CA' never matches).
    """
    if not loc or not str(loc).strip():
        return []
    raw = str(loc).strip()
    parts = [p.strip() for p in re.split(r"[,|]", raw) if p.strip()]
    if not parts:
        parts = [raw]
    aliases = {"sf": "San Francisco", "san fran": "San Francisco"}
    out: List[str] = []
    for p in parts:
        key = p.lower()
        if key in aliases:
            out.append(aliases[key])
        out.append(p)
    seen = set()
    uniq: List[str] = []
    for x in out:
        if len(x) < 2:
            continue
        lk = x.lower()
        if lk not in seen:
            seen.add(lk)
            uniq.append(x)
    return uniq


def _apply_location_filter(q, location: str):
    tokens = _location_tokens(location)
    if not tokens:
        return q
    conds = []
    for t in tokens:
        pat = f"%{t}%"
        conds.extend(
            [
                models.Restaurant.city.ilike(pat),
                models.Restaurant.address.ilike(pat),
                models.Restaurant.state.ilike(pat),
                models.Restaurant.zip_code.ilike(pat),
            ]
        )
    return q.filter(or_(*conds))


def _query_restaurants(filters: dict, db: Session) -> List[models.Restaurant]:
    """
    Apply SQL filters from the LLM only. Saved preferences are NOT merged here.

    Broad queries (no cuisine, location, price, or dietary constraints): return many
    rows so ranking can surface diverse results.

    **Strict post-filter (Python): only `dietary` terms** (vegan, halal, etc.).
    Keywords and ambiance are NOT used to exclude rows — they are scored in
    `_rank_restaurants` only. Requiring "sweet" or "romantic" in the text used to
    wipe all candidates when no row contained that substring.
    """
    f = _normalize_filters(filters)

    cuisine = f.get("cuisine_type") or ""
    location = f.get("location") or ""
    price_str = f.get("price_range")

    diet = list(f.get("dietary") or [])
    dietary_strict = [t for t in diet if t]

    q = db.query(models.Restaurant)

    if cuisine:
        q = q.filter(models.Restaurant.cuisine_type.ilike(f"%{cuisine}%"))

    if location:
        q = _apply_location_filter(q, location)

    if price_str:
        try:
            pt = models.PriceTier(price_str)
            q = q.filter(models.Restaurant.price_tier == pt)
        except ValueError:
            pass

    # Broad: nothing from LLM narrows the candidate set — return a large slice for ranking
    if not cuisine and not location and not price_str and not dietary_strict:
        return (
            q.order_by(desc(models.Restaurant.average_rating))
            .limit(_DB_FETCH_CAP)
            .all()
        )

    rows = (
        q.order_by(desc(models.Restaurant.average_rating))
        .limit(_DB_FETCH_CAP)
        .all()
    )

    if not dietary_strict:
        return rows

    matched = [r for r in rows if _matches_all_terms(r, dietary_strict)]
    # If nothing mentions vegan/halal/etc. in our text fields, still return rows so we
    # can show cards; ranking + reason will nudge toward best textual fit.
    return matched if matched else rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Rank by relevance: query filters + soft boosts from saved preferences
# ─────────────────────────────────────────────────────────────────────────────


def _rank_restaurants(
    restaurants: List[models.Restaurant],
    filters: dict,
    prefs: dict,
) -> List[dict]:
    f = _normalize_filters(filters)

    pref_cuisines = [c.lower() for c in (prefs.get("cuisines") or [])]
    pref_price = (prefs.get("price_range") or "").strip()
    pref_loc = (prefs.get("location") or "").strip().lower()

    q_cuisine = (f.get("cuisine_type") or "").lower().strip()
    q_price = (f.get("price_range") or "").strip()
    q_terms = (
        [x.lower() for x in (f.get("keywords") or [])]
        + [x.lower() for x in (f.get("ambiance") or [])]
        + [x.lower() for x in (f.get("dietary") or [])]
    )

    scored: List[tuple] = []

    for r in restaurants:
        score = 0.0
        score += float(r.average_rating or 0.0)
        if prefs.get("sort_preference") == "rating":
            score += float(r.average_rating or 0.0) * 0.1

        r_cuisine = (r.cuisine_type or "").lower()
        if q_cuisine and q_cuisine in r_cuisine:
            score += 2.5
        elif pref_cuisines and any(c in r_cuisine for c in pref_cuisines):
            score += 1.0

        r_price = r.price_tier.value if r.price_tier else ""
        if q_price and r_price == q_price:
            score += 2.0
        elif pref_price and r_price == pref_price:
            score += 1.0

        text_blob = _restaurant_text_blob(r)
        for term in q_terms:
            if term and term in text_blob:
                score += 1.2

        city = (r.city or "").lower()
        if pref_loc and pref_loc and pref_loc in city:
            score += 1.5

        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[dict] = []
    for _, r in scored[:5]:
        r_price = r.price_tier.value if r.price_tier else ""
        r_cuisine = r.cuisine_type or ""
        rating_val = float(r.average_rating or 0.0)
        blob = _restaurant_text_blob(r)

        reason_parts: List[str] = []
        if q_cuisine and q_cuisine in (r_cuisine.lower()):
            reason_parts.append(f"matches your {r_cuisine} search")
        elif r_cuisine:
            reason_parts.append(f"{r_cuisine} food")

        if q_terms:
            matched = [t for t in q_terms if t in blob]
            if matched:
                reason_parts.append("fits " + ", ".join(matched[:3]))

        if r_price:
            reason_parts.append(f"{r_price} price tier")

        if rating_val >= 4.5:
            reason_parts.append("highly rated")

        if pref_cuisines and any(c in r_cuisine for c in pref_cuisines) and not (
            q_cuisine and q_cuisine in r_cuisine
        ):
            reason_parts.append("aligned with a cuisine you enjoy")

        if pref_price and r_price == pref_price and q_price != pref_price:
            reason_parts.append("matches your usual budget")

        reason = "; ".join(reason_parts) if reason_parts else "Strong match for what you asked for"

        results.append(
            {
                "id": r.id,
                "name": r.name or "",
                "rating": rating_val,
                "price_tier": r_price,
                "cuisine_type": r_cuisine,
                "address": r.address or "",
                "city": r.city or "",
                "reason": reason,
            }
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 8. Tavily — only when needs_web_search is true (live hours, trends, events)
# ─────────────────────────────────────────────────────────────────────────────


def _run_tavily(query: str) -> str:
    """Run Tavily and return plain text snippets; empty string on failure."""
    if not query or not (os.getenv("TAVILY_API_KEY") or "").strip():
        return ""
    try:
        tool = _get_tavily()
        raw: Any = tool.invoke({"query": query})
        if isinstance(raw, dict):
            if raw.get("error"):
                return ""
            items = raw.get("results") or []
            lines: List[str] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or ""
                content = item.get("content") or ""
                if title or content:
                    lines.append(f"{title}: {content}".strip())
            return "\n".join(lines)
        return str(raw)
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 9. POST /ai-assistant/chat
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Input: {{ message, conversation_history }}
    Output: {{ response, recommendations }}
    """
    user_message = (payload.message or "").strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="message cannot be empty.",
        )

    prefs = _load_preferences(current_user.id, db)
    system_prompt = _build_system_prompt(prefs, current_user)

    lc_messages = _build_lc_messages(
        system_prompt,
        payload.conversation_history or [],
        user_message,
    )

    try:
        ai_msg = _llm.invoke(lc_messages)
        raw_text: str = ai_msg.content or ""
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM call failed: {str(exc)}",
        )

    parsed = _parse_llm_output(raw_text)
    filters: dict = _normalize_filters(parsed.get("filters") or {})
    needs_web = bool(parsed.get("needs_web_search"))
    web_query = parsed.get("web_search_query") or ""
    reply_text = parsed.get("reply") or raw_text

    # Optional second pass with web context — only when the model asked for search
    if needs_web and web_query:
        web_context = _run_tavily(str(web_query).strip())
        if web_context:
            enrichment_msgs = lc_messages + [
                AIMessage(content=raw_text),
                HumanMessage(
                    content=(
                        "Here is live web information relevant to the query:\n"
                        f"{web_context}\n\n"
                        "Update your JSON if needed (same schema). "
                        "Incorporate useful facts into reply only when appropriate."
                    )
                ),
            ]
            try:
                enriched = _llm.invoke(enrichment_msgs)
                enriched_data = _parse_llm_output(enriched.content or "")
                if enriched_data.get("reply"):
                    filters = _normalize_filters(enriched_data.get("filters") or filters)
                    reply_text = enriched_data["reply"]
            except Exception:
                pass

    # Do NOT merge saved preferences into filters — that caused over-filtering.
    # Preferences are applied only inside _rank_restaurants.

    try:
        candidates = _query_restaurants(filters, db)
        # If filters over-constrain (bad location string, etc.), still show top listings
        if not candidates:
            candidates = _query_restaurants({}, db)
        recommendations = _rank_restaurants(candidates, filters, prefs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restaurant query failed: {exc}",
        )

    if recommendations:
        lines: List[str] = []
        for i, rec in enumerate(recommendations, 1):
            stars = f"{rec['rating']:.1f}★" if rec["rating"] else "No rating"
            price = rec["price_tier"] or "N/A"
            lines.append(
                f"{i}. {rec['name']} ({stars}, {price}) — {rec['reason']}"
            )
        reply_text = reply_text.rstrip() + "\n\n" + "\n".join(lines)

    return schemas.ChatResponse(
        response=reply_text,
        recommendations=[
            schemas.RestaurantRecommendation(**rec) for rec in recommendations
        ],
    )
