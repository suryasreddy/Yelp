"""
routers/ai_assistant.py
========================
AI restaurant assistant for the MongoDB + Kafka Lab 2 backend.

Uses:
- MongoDB collections via get_db()
- LangChain + OpenAI for intent parsing / conversational replies
- Optional Tavily web search for live-hour / live-context queries

Required environment variables:
  ENABLE_AI_ROUTE=true
  OPENAI_API_KEY=sk-...
Optional:
  TAVILY_API_KEY=tvly-...
"""

import json
import re
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

import schemas
from auth import get_current_user
from config import settings
from database import get_db

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# ─────────────────────────────────────────────────────────────────────────────
# LLM + Tavily (lazy init so missing keys do not break import-time)
# ─────────────────────────────────────────────────────────────────────────────

_llm_instance: Optional[ChatOpenAI] = None


def _get_llm() -> ChatOpenAI:
    global _llm_instance
    if _llm_instance is None:
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured",
            )
        _llm_instance = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    return _llm_instance


def _get_tavily() -> TavilySearchResults:
    if not settings.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    return TavilySearchResults(max_results=3)


# ─────────────────────────────────────────────────────────────────────────────
# Preferences
# ─────────────────────────────────────────────────────────────────────────────


def _safe_list(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _load_preferences(user_id: int, db) -> dict:
    row = db.user_preferences.find_one({"user_id": user_id})
    if not row:
        return {}

    return {
        "cuisines": _safe_list(row.get("cuisine_preferences")),
        "price_range": (row.get("price_range") or "").strip(),
        "location": (row.get("preferred_location") or "").strip(),
        "dietary": _safe_list(row.get("dietary_needs")),
        "ambiance": _safe_list(row.get("ambiance_preferences")),
        "sort_preference": (row.get("sort_preference") or "rating").strip().lower(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────


def _build_system_prompt(prefs: dict, user: dict) -> str:
    lines = []
    acct_city = user.get("city")
    acct_state = user.get("state")
    if acct_city or acct_state:
        acct = ", ".join(x for x in [acct_city or "", acct_state or ""] if x)
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
3. Generic hunger ("I'm hungry", "what restaurants do you recommend?", "surprise me") → leave cuisine_type null, price_range null, dietary/ambiance/keywords empty unless the user said otherwise.
4. Multi-turn: MERGE the full intent. Example: "I want Mexican" then "make it vegan" → cuisine_type "Mexican", dietary ["vegan"].
5. "Best rated near me" / location in conversation → set "location" from the user's city if they gave it; if they refer to saved area, you may set location to that string only when the user implied "near me" or similar.
6. price_range must be one of: "$", "$$", "$$$", "$$$$", or null.
7. needs_web_search: true ONLY for live web data (hours today, is X open now, trending this week, special events).
8. reply: conversational, friendly, brief. Do not produce long lists because the app shows cards.
9. NEVER invent restaurant names in "reply". Real names come from the database.
10. dietary[] = HARD constraints only (vegan, gluten-free, halal, nut-free). keywords[] / ambiance[] = SOFT wishes.
11. If the user narrows a follow-up, drop obsolete keywords.
12. Questions about "open right now" / hours → set needs_web_search true and a focused web_search_query; still output filters.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Messages + JSON parsing
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


def _parse_llm_output(raw: str) -> dict:
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
    f = dict(filters or {})

    cuisine = f.get("cuisine_type")
    f["cuisine_type"] = (str(cuisine).strip() if cuisine else "") or None

    price = f.get("price_range")
    f["price_range"] = (str(price).strip() if price else "") or None

    loc = f.get("location")
    f["location"] = (str(loc).strip() if loc else "") or None

    for key in ("dietary", "ambiance", "keywords"):
        value = f.get(key)
        if value is None:
            f[key] = []
        elif isinstance(value, list):
            f[key] = [str(x).strip() for x in value if str(x).strip()]
        else:
            s = str(value).strip()
            f[key] = [s] if s else []

    return f


# ─────────────────────────────────────────────────────────────────────────────
# Occasion helpers
# ─────────────────────────────────────────────────────────────────────────────


def _occasion_profile(filters: dict) -> dict:
    f = _normalize_filters(filters)
    terms = [x.lower() for x in (f.get("ambiance") or []) + (f.get("keywords") or []) if x]
    joined = " ".join(terms)

    occasion_map = {
        "romantic": {
            "required_any": ["anniversary", "date night", "date", "valentine", "proposal", "romantic"],
            "fit_terms": ["romantic", "fine dining", "upscale", "special occasion", "wine", "view", "date night"],
            "intro": "I prioritized romantic and special-occasion options",
        },
        "family": {
            "required_any": ["mother's day", "mothers day", "father's day", "fathers day", "family", "kids", "parents"],
            "fit_terms": ["family-friendly", "casual", "brunch", "outdoor", "group-friendly"],
            "intro": "I prioritized family-friendly, comfortable options",
        },
        "celebration": {
            "required_any": ["birthday", "graduation", "celebration", "party"],
            "fit_terms": ["special occasion", "upscale", "dessert", "group-friendly", "private dining"],
            "intro": "I prioritized celebration-friendly places",
        },
        "business": {
            "required_any": ["business dinner", "client dinner", "work dinner", "corporate"],
            "fit_terms": ["fine dining", "upscale", "quiet", "reservations"],
            "intro": "I prioritized business-appropriate dining options",
        },
    }

    for label, cfg in occasion_map.items():
        if any(t in joined for t in cfg["required_any"]):
            return {
                "label": label,
                "fit_terms": cfg["fit_terms"],
                "intro": cfg["intro"],
            }
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Restaurant text / matching
# ─────────────────────────────────────────────────────────────────────────────


def _restaurant_text_blob(r: dict) -> str:
    parts: List[str] = [
        r.get("name") or "",
        r.get("description") or "",
        r.get("cuisine_type") or "",
        r.get("address") or "",
        r.get("city") or "",
        r.get("state") or "",
    ]
    try:
        parts.append(json.dumps(r.get("keywords") or []))
        parts.append(json.dumps(r.get("amenities") or []))
    except (TypeError, ValueError):
        pass
    return " ".join(parts).lower()


def _matches_all_terms(r: dict, terms: List[str]) -> bool:
    if not terms:
        return True
    blob = _restaurant_text_blob(r)
    return all(t.lower() in blob for t in terms if t)


# ─────────────────────────────────────────────────────────────────────────────
# Mongo restaurant query
# ─────────────────────────────────────────────────────────────────────────────

_DB_FETCH_CAP = 250


def _location_tokens(loc: str) -> List[str]:
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
        lk = x.lower()
        if lk not in seen and len(x) >= 2:
            seen.add(lk)
            uniq.append(x)
    return uniq


def _build_restaurant_query(filters: dict) -> dict:
    f = _normalize_filters(filters)
    query = {}

    cuisine = f.get("cuisine_type")
    price = f.get("price_range")
    location = f.get("location")

    if cuisine and not f.get("dietary"):
        query["cuisine_type"] = {"$regex": re.escape(cuisine), "$options": "i"}

    if price:
        query["price_tier"] = price

    if location:
        or_clauses = []
        for token in _location_tokens(location):
            regex = {"$regex": re.escape(token), "$options": "i"}
            or_clauses.extend(
                [
                    {"city": regex},
                    {"address": regex},
                    {"state": regex},
                    {"zip_code": regex},
                ]
            )
        if or_clauses:
            query["$or"] = or_clauses

    return query


def _query_restaurants(filters: dict, db) -> List[dict]:
    f = _normalize_filters(filters)
    dietary_strict = [t for t in (f.get("dietary") or []) if t]

    query = _build_restaurant_query(f)

    rows = list(
        db.restaurants.find(query, {"_id": 0})
        .sort("average_rating", -1)
        .limit(_DB_FETCH_CAP)
    )

    if not dietary_strict:
        return rows

    matched = [r for r in rows if _matches_all_terms(r, dietary_strict)]
    return matched if matched else rows


# ─────────────────────────────────────────────────────────────────────────────
# Ranking
# ─────────────────────────────────────────────────────────────────────────────


def _rank_restaurants(restaurants: List[dict], filters: dict, prefs: dict) -> List[dict]:
    f = _normalize_filters(filters)

    pref_cuisines = [c.lower() for c in (prefs.get("cuisines") or [])]
    pref_price = (prefs.get("price_range") or "").strip()
    pref_loc = (prefs.get("location") or "").strip().lower()

    q_cuisine = (f.get("cuisine_type") or "").lower().strip()
    q_price = (f.get("price_range") or "").strip()
    q_location = (f.get("location") or "").lower().strip()
    q_dietary = [x.lower() for x in (f.get("dietary") or [])]
    q_ambiance = [x.lower() for x in (f.get("ambiance") or [])]
    q_keywords = [x.lower() for x in (f.get("keywords") or [])]
    q_terms = q_keywords + q_ambiance + q_dietary
    occasion = _occasion_profile(f)

    def _all_terms_match(blob: str, terms: List[str]) -> bool:
        if not terms:
            return False
        return all(t in blob for t in terms if t)

    def _tier_for(r: dict) -> int:
        blob = _restaurant_text_blob(r)
        cuisine_match = bool(q_cuisine) and q_cuisine in (r.get("cuisine_type") or "").lower()
        dietary_match = _all_terms_match(blob, q_dietary)
        ambiance_match = _all_terms_match(blob, q_ambiance)
        keyword_match = _all_terms_match(blob, q_keywords)
        occasion_match = any(t in blob for t in (occasion.get("fit_terms") or [])) if occasion else False

        if q_location:
            city = (r.get("city") or "").lower()
            address = (r.get("address") or "").lower()
            location_match = any(tok.lower() in city or tok.lower() in address for tok in _location_tokens(q_location))
        else:
            location_match = True

        secondary_match = (
            ambiance_match and keyword_match
            if q_ambiance and q_keywords
            else (ambiance_match or keyword_match)
        )

        if occasion:
            if q_cuisine and q_dietary:
                if cuisine_match and dietary_match and occasion_match:
                    tier = 0
                elif cuisine_match and dietary_match:
                    tier = 1
                elif dietary_match and occasion_match:
                    tier = 2
                elif dietary_match:
                    tier = 3
                elif cuisine_match and occasion_match:
                    tier = 4
                else:
                    tier = 5
                return tier if location_match else tier + 3

            if q_cuisine and not q_dietary:
                if cuisine_match and occasion_match:
                    tier = 0
                elif cuisine_match:
                    tier = 1
                elif occasion_match:
                    tier = 2
                elif secondary_match:
                    tier = 3
                else:
                    tier = 4
                return tier if location_match else tier + 3

            if q_dietary and not q_cuisine:
                if dietary_match and occasion_match:
                    tier = 0
                elif dietary_match:
                    tier = 1
                elif occasion_match:
                    tier = 2
                elif secondary_match:
                    tier = 3
                else:
                    tier = 4
                return tier if location_match else tier + 3

            if q_ambiance and q_keywords:
                dessertish = {
                    "sweet", "dessert", "cake", "pastry", "pastries",
                    "bakery", "gelato", "ice cream", "chocolate"
                }
                keyword_food_intent = any(k in dessertish for k in q_keywords)
                if secondary_match:
                    tier = 0
                elif keyword_match and keyword_food_intent:
                    tier = 1
                elif occasion_match or ambiance_match:
                    tier = 2
                elif keyword_match:
                    tier = 3
                else:
                    tier = 4
                return tier if location_match else tier + 3

            tier = 0 if occasion_match else (1 if secondary_match else 2)
            return tier if location_match else tier + 3

        if q_cuisine and q_dietary:
            if cuisine_match and dietary_match and (secondary_match or (not q_ambiance and not q_keywords)):
                tier = 0
            elif cuisine_match and dietary_match:
                tier = 1
            elif dietary_match:
                tier = 2
            elif cuisine_match:
                tier = 3
            else:
                tier = 4
            return tier if location_match else tier + 3

        if q_cuisine and not q_dietary:
            if cuisine_match and (secondary_match or (not q_ambiance and not q_keywords)):
                tier = 0
            elif cuisine_match:
                tier = 1
            elif secondary_match:
                tier = 2
            else:
                tier = 3
            return tier if location_match else tier + 3

        if q_dietary and not q_cuisine:
            if dietary_match and (secondary_match or (not q_ambiance and not q_keywords)):
                tier = 0
            elif dietary_match:
                tier = 1
            elif secondary_match:
                tier = 2
            else:
                tier = 3
            return tier if location_match else tier + 3

        if q_ambiance or q_keywords:
            tier = 0 if secondary_match else 1
            return tier if location_match else tier + 3

        return 0 if location_match else 3

    ranked: List[tuple] = []

    for r in restaurants:
        score = 0.0
        rating_val = float(r.get("average_rating") or 0.0)
        score += rating_val
        if prefs.get("sort_preference") == "rating":
            score += rating_val * 0.1

        r_cuisine = (r.get("cuisine_type") or "").lower()
        if q_cuisine and q_cuisine in r_cuisine:
            score += 2.5
        elif pref_cuisines and any(c in r_cuisine for c in pref_cuisines):
            score += 1.0

        r_price = r.get("price_tier") or ""
        if q_price and r_price == q_price:
            score += 2.0
        elif pref_price and r_price == pref_price:
            score += 1.0

        text_blob = _restaurant_text_blob(r)
        for term in q_terms:
            if term and term in text_blob:
                score += 1.2

        if occasion and any(t in text_blob for t in (occasion.get("fit_terms") or [])):
            score += 2.0

        city = (r.get("city") or "").lower()
        if pref_loc and pref_loc in city:
            score += 1.5

        ranked.append((_tier_for(r), score, r))

    ranked.sort(key=lambda x: (x[0], -x[1]))

    results: List[dict] = []
    for tier, _, r in ranked[:5]:
        r_price = r.get("price_tier") or ""
        r_cuisine = r.get("cuisine_type") or ""
        rating_val = float(r.get("average_rating") or 0.0)
        blob = _restaurant_text_blob(r)

        reason_parts: List[str] = []
        if tier == 0:
            reason_parts.append("best exact match for your request")
        elif tier == 1:
            reason_parts.append("strong match for your core constraints")
        elif tier == 2:
            reason_parts.append("matches your dietary needs")
        elif tier == 3 and q_cuisine:
            reason_parts.append(f"matches your {r_cuisine} preference")
        else:
            reason_parts.append("good fallback option")

        if occasion and any(t in blob for t in (occasion.get("fit_terms") or [])):
            reason_parts.append(f"fits your {occasion['label']} occasion")

        if q_terms:
            matched = [t for t in q_terms if t in blob]
            if matched:
                reason_parts.append("fits " + ", ".join(matched[:3]))

        if r_price:
            reason_parts.append(f"{r_price} price tier")
        if rating_val >= 4.5:
            reason_parts.append("highly rated")

        results.append(
            {
                "id": r.get("id"),
                "name": r.get("name") or "",
                "rating": rating_val,
                "price_tier": r_price,
                "cuisine_type": r_cuisine,
                "address": r.get("address") or "",
                "city": r.get("city") or "",
                "reason": "; ".join(reason_parts),
            }
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Tavily
# ─────────────────────────────────────────────────────────────────────────────


def _run_tavily(query: str) -> str:
    if not query or not settings.TAVILY_API_KEY:
        return ""
    try:
        tool = _get_tavily()
        raw: Any = tool.invoke({"query": query})
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return raw.strip()

        if isinstance(raw, list):
            lines: List[str] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or ""
                content = item.get("content") or ""
                if title or content:
                    lines.append(f"{title}: {content}".strip())
            return "\n".join(lines)

        if isinstance(raw, dict):
            if raw.get("error"):
                return ""
            items = raw.get("results") or []
            lines = []
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
# Live-hours helpers
# ─────────────────────────────────────────────────────────────────────────────


def _is_live_hours_query(message: str) -> bool:
    m = (message or "").lower()
    patterns = [
        "open now",
        "open right now",
        "currently open",
        "what's open",
        "what is open",
        "opening hours",
        "closing time",
        "close now",
        "open today",
    ]
    return any(p in m for p in patterns)


def _build_live_hours_query(message: str, filters: dict, prefs: dict) -> str:
    f = _normalize_filters(filters)
    location = f.get("location") or prefs.get("location") or ""
    cuisine = f.get("cuisine_type") or ""
    if cuisine and location:
        return f"{cuisine} restaurants open now in {location}"
    if location:
        return f"restaurants open now in {location}"
    return "popular restaurants open now nearby"


def _to_minutes(token: str) -> Optional[int]:
    t = (token or "").strip().lower()
    if not t:
        return None
    if t == "noon":
        return 12 * 60
    if t == "midnight":
        return 24 * 60

    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", t)
    if not m:
        return None
    h = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)
    if h == 12:
        h = 0
    if ampm == "pm":
        h += 12
    return h * 60 + minute


def _is_open_now_from_hours(hours: Any, now: datetime) -> Optional[bool]:
    if not isinstance(hours, dict):
        return None

    day = now.strftime("%A")
    day_hours = hours.get(day)
    if not day_hours:
        return None

    s = str(day_hours).strip().lower()
    if not s:
        return None
    if s in {"closed", "close", "n/a", "na"}:
        return False
    if s in {"open 24 hours", "24 hours", "24/7", "all day"}:
        return True

    now_m = now.hour * 60 + now.minute
    windows = [w.strip() for w in re.split(r"[,;]", s) if w.strip()]
    for w in windows:
        if "-" not in w:
            continue
        start_s, end_s = [x.strip() for x in w.split("-", 1)]
        start_m = _to_minutes(start_s)
        end_m = _to_minutes(end_s)
        if start_m is None or end_m is None:
            continue

        if end_m <= start_m:
            if now_m >= start_m or now_m <= end_m:
                return True
        else:
            if start_m <= now_m <= end_m:
                return True

    if any("-" in w for w in windows):
        return False
    return None


def _prioritize_open_now(recommendations: List[dict], candidates: List[dict]) -> List[dict]:
    if not recommendations:
        return recommendations

    id_to_rest = {r.get("id"): r for r in candidates}
    now = datetime.now()

    open_items: List[dict] = []
    unknown_items: List[dict] = []
    closed_items: List[dict] = []

    for rec in recommendations:
        r = id_to_rest.get(rec.get("id"))
        if not r:
            unknown_items.append(rec)
            continue

        status = _is_open_now_from_hours(r.get("hours"), now)
        if status is True:
            open_items.append(rec)
        elif status is False:
            closed_items.append(rec)
        else:
            unknown_items.append(rec)

    return (open_items + unknown_items + closed_items)[:5]


# ─────────────────────────────────────────────────────────────────────────────
# Grounded intro
# ─────────────────────────────────────────────────────────────────────────────


def _build_grounded_intro(filters: dict, recommendations: List[dict]) -> str:
    if not recommendations:
        return "I couldn't find strong matches right now, but I can refine this with another preference."

    f = _normalize_filters(filters)
    q_cuisine = (f.get("cuisine_type") or "").strip().lower()
    q_location = (f.get("location") or "").strip().lower()
    q_dietary = [d.lower() for d in (f.get("dietary") or []) if d]
    occasion = _occasion_profile(f)

    def _cuisine_match(rec: dict) -> bool:
        return bool(q_cuisine) and q_cuisine in (rec.get("cuisine_type") or "").lower()

    def _location_match(rec: dict) -> bool:
        if not q_location:
            return True
        city = (rec.get("city") or "").lower()
        address = (rec.get("address") or "").lower()
        for tok in _location_tokens(q_location):
            t = tok.lower()
            if t in city or t in address:
                return True
        return False

    cuisine_hits = sum(1 for r in recommendations if _cuisine_match(r))
    location_hits = sum(1 for r in recommendations if _location_match(r))
    n = len(recommendations)

    parts: List[str] = []
    if q_cuisine:
        if cuisine_hits == n:
            parts.append(f"Here are the best {q_cuisine.title()} options")
        elif cuisine_hits > 0:
            parts.append(f"I found a few {q_cuisine.title()} matches plus close alternatives")
        else:
            parts.append(f"I couldn't find strong {q_cuisine.title()} matches, so here are the closest alternatives")
    else:
        parts.append("Here are some strong options")

    if occasion:
        parts.append(occasion["intro"])

    if q_dietary:
        parts.append(f"with {', '.join(q_dietary)} options")

    if q_location:
        if location_hits == n:
            parts.append(f"in {f.get('location')}")
        elif location_hits > 0:
            parts.append(f"mostly around {f.get('location')}")
        else:
            parts.append(f"nearby beyond {f.get('location')}")

    return " ".join(parts).strip() + "."


# ─────────────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    payload: schemas.ChatRequest,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_message = (payload.message or "").strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="message cannot be empty.",
        )

    prefs = _load_preferences(current_user["id"], db)
    system_prompt = _build_system_prompt(prefs, current_user)

    lc_messages = _build_lc_messages(
        system_prompt,
        payload.conversation_history or [],
        user_message,
    )

    try:
        llm = _get_llm()
        ai_msg = llm.invoke(lc_messages)
        raw_text = ai_msg.content or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM call failed: {str(exc)}",
        )

    parsed = _parse_llm_output(raw_text)
    filters = _normalize_filters(parsed.get("filters") or {})
    needs_web = bool(parsed.get("needs_web_search"))
    web_query = parsed.get("web_search_query") or ""
    reply_text = parsed.get("reply") or raw_text

    if _is_live_hours_query(user_message):
        needs_web = True
        if not web_query:
            web_query = _build_live_hours_query(user_message, filters, prefs)

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
                enriched = _get_llm().invoke(enrichment_msgs)
                enriched_data = _parse_llm_output(enriched.content or "")
                if enriched_data.get("reply"):
                    filters = _normalize_filters(enriched_data.get("filters") or filters)
                    reply_text = enriched_data["reply"]
            except Exception:
                pass
        else:
            reply_text = (
                "I couldn't verify live opening status from web sources right now, "
                "so here are strong options from our listings."
            )

    try:
        candidates = _query_restaurants(filters, db)
        if not candidates:
            fallback_filters = {
                "cuisine_type": None,
                "price_range": filters.get("price_range"),
                "dietary": filters.get("dietary", []),
                "ambiance": [],
                "keywords": [],
                "location": filters.get("location"),
            }
            candidates = _query_restaurants(fallback_filters, db)
        if not candidates:
            candidates = _query_restaurants({}, db)

        recommendations = _rank_restaurants(candidates, filters, prefs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restaurant query failed: {exc}",
        )

    live_hours_query = _is_live_hours_query(user_message)
    if live_hours_query and recommendations:
        recommendations = _prioritize_open_now(recommendations, candidates)

    if recommendations:
        grounded_intro = _build_grounded_intro(filters, recommendations)
        if live_hours_query:
            grounded_intro = (
                "I prioritized places that appear open right now based on available hours data. "
                + grounded_intro
            )

        lines: List[str] = []
        for i, rec in enumerate(recommendations, 1):
            stars = f"{rec['rating']:.1f}★" if rec.get("rating") else "No rating"
            price = rec.get("price_tier") or "N/A"
            lines.append(
                f"{i}. {rec.get('name', '')} ({stars}, {price}) — {rec.get('reason', '')}"
            )
        reply_text = grounded_intro + "\n\n" + "\n".join(lines)

    return schemas.ChatResponse(
        response=reply_text,
        recommendations=[
            schemas.RestaurantRecommendation(**rec) for rec in recommendations
        ],
    )
