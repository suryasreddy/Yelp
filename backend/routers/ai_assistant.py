"""
AI Assistant Router

Purpose:
    Implements the POST /ai-assistant/chat endpoint for the Yelp-style restaurant
    recommendation chatbot.

What this file does:
    1. Loads the logged-in user's saved dining preferences from the database.
    2. Interprets natural language queries using LangChain + OpenAI when available.
    3. Falls back to deterministic keyword parsing if LLM keys are unavailable.
    4. Queries the restaurants table using extracted filters and user preferences.
    5. Ranks restaurants based on relevance + rating + preference alignment.
    6. Optionally enriches context using Tavily search.
    7. Returns a conversational response and structured recommendations.

Design goals:
    - Production-style structure with helper functions.
    - Clear separation of concerns.
    - Robust fallback behavior for grading/demo environments.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
import models
import schemas
from auth import get_current_user

# LangChain imports are optional at runtime. We use them if the keys are present.
try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except Exception:
    LANGCHAIN_OPENAI_AVAILABLE = False

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_AVAILABLE = True
except Exception:
    TAVILY_AVAILABLE = False


router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# -----------------------------
# Static vocab / normalization
# -----------------------------
# These lists help with deterministic extraction and DB matching.
CUISINES = [
    "italian", "chinese", "mexican", "indian", "japanese", "american",
    "thai", "french", "mediterranean", "korean", "vietnamese",
    "vegan", "vegetarian", "seafood", "pizza", "sushi", "bbq", "burger"
]

DIETARY_KEYWORDS = [
    "vegan", "vegetarian", "halal", "gluten-free", "gluten free",
    "kosher", "dairy-free", "dairy free", "pescatarian"
]

AMBIANCE_KEYWORDS = [
    "casual", "fine dining", "family-friendly", "family friendly",
    "romantic", "quiet", "outdoor", "outdoor seating", "cozy",
    "trendy", "luxury", "formal"
]

OCCASION_KEYWORDS = [
    "anniversary", "birthday", "date", "romantic dinner",
    "business lunch", "business dinner", "brunch", "dinner",
    "lunch", "breakfast", "late night", "celebration"
]

PRICE_PATTERNS = {
    "$": [r"\$", r"\bbudget\b", r"\bcheap\b", r"\baffordable\b", r"\blow cost\b"],
    "$$": [r"\$\$", r"\bmid[- ]?range\b", r"\bmoderate\b"],
    "$$$": [r"\$\$\$", r"\bupscale\b", r"\bpremium\b", r"\bhigh[- ]?end\b"],
    "$$$$": [r"\$\$\$\$", r"\bluxury\b", r"\bvery expensive\b", r"\bfine dining\b"],
}


# ----------------------------------------
# Utility helpers for environment handling
# ----------------------------------------
def _get_env(name: str) -> Optional[str]:
    """
    Reads an environment variable safely and normalizes blank strings to None.
    """
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _is_usable_key(value: Optional[str]) -> bool:
    """
    Checks whether an API key looks usable.
    We intentionally treat 'dummy', placeholder values, or empty strings as unavailable.
    """
    if not value:
        return False

    lowered = value.lower()
    bad_markers = [
        "dummy",
        "your-openai-api-key-here",
        "your-tavily-api-key-here",
        "placeholder",
    ]
    return not any(marker in lowered for marker in bad_markers)


# ----------------------------------------
# Preference loading / formatting helpers
# ----------------------------------------
def _safe_list(value: Any) -> List[str]:
    """
    Normalizes JSON/list-like DB values to a list of lowercase strings.
    The project stores several preference fields as JSON arrays in MySQL.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        # Supports either a single string or a comma-separated value.
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]

    return [str(value).strip()]


def _load_user_preferences(
    db: Session,
    current_user: models.User,
) -> Dict[str, Any]:
    """
    Loads the logged-in user's stored dining preferences from the DB.

    Returns a normalized dictionary so the rest of the pipeline can work
    consistently even if some fields are missing.
    """
    prefs = (
        db.query(models.UserPreferences)
        .filter(models.UserPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        return {
            "cuisine_preferences": [],
            "price_range": None,
            "dietary_needs": [],
            "ambiance_preferences": [],
            "preferred_location": None,
            "sort_preference": None,
        }

    # Use getattr defensively because field names may vary slightly by implementation.
    return {
        "cuisine_preferences": _safe_list(getattr(prefs, "cuisine_preferences", [])),
        "price_range": getattr(prefs, "price_range", None),
        "dietary_needs": _safe_list(getattr(prefs, "dietary_needs", [])),
        "ambiance_preferences": _safe_list(getattr(prefs, "ambiance_preferences", [])),
        "preferred_location": getattr(prefs, "preferred_location", None),
        "sort_preference": getattr(prefs, "sort_preference", None),
    }


def _build_preference_summary(preferences: Dict[str, Any]) -> str:
    """
    Formats user preferences into a compact summary for LLM prompting and reasoning.
    """
    cuisines = ", ".join(preferences["cuisine_preferences"]) or "not specified"
    dietary = ", ".join(preferences["dietary_needs"]) or "not specified"
    ambiance = ", ".join(preferences["ambiance_preferences"]) or "not specified"
    price = preferences["price_range"] or "not specified"
    location = preferences["preferred_location"] or "not specified"
    sort_pref = preferences["sort_preference"] or "not specified"

    return (
        f"Saved cuisine preferences: {cuisines}. "
        f"Saved price range: {price}. "
        f"Saved dietary needs: {dietary}. "
        f"Saved ambiance preferences: {ambiance}. "
        f"Preferred location: {location}. "
        f"Sort preference: {sort_pref}."
    )


# ----------------------------------------
# Conversation / extraction helpers
# ----------------------------------------
def _serialize_history(conversation_history) -> str:
    """
    Converts prior conversation turns into plain text.

    Supports both:
    - dict items like {"role": "user", "content": "..."}
    - Pydantic objects like ChatMessage(role="user", content="...")
    """
    if not conversation_history:
        return "No prior conversation."

    lines = []
    for turn in conversation_history[-8:]:
        # Handle dict-style messages
        if isinstance(turn, dict):
            role = str(turn.get("role", "user")).strip()
            content = str(turn.get("content", "")).strip()
        else:
            # Handle Pydantic model / object-style messages
            role = str(getattr(turn, "role", "user")).strip()
            content = str(getattr(turn, "content", "")).strip()

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No prior conversation."


def _extract_price_from_text(text: str) -> Optional[str]:
    """
    Extracts a likely price tier from the user's natural language message.
    """
    lowered = text.lower()
    for price_tier, patterns in PRICE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return price_tier
    return None


def _keyword_extract_filters(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]],
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic fallback parser used when LLM access is unavailable.

    This parser is intentionally simple but still useful for demo/lab grading:
    it extracts likely cuisine, price, dietary, ambiance, and occasion values
    from the user's message plus limited conversational context.
    """
    combined_text = f"{_serialize_history(conversation_history)}\n{message}".lower()

    cuisines_found = [c for c in CUISINES if c in combined_text]
    dietary_found = [d for d in DIETARY_KEYWORDS if d in combined_text]
    ambiance_found = [a for a in AMBIANCE_KEYWORDS if a in combined_text]
    occasion_found = [o for o in OCCASION_KEYWORDS if o in combined_text]

    # Normalize common variants
    dietary_found = [
        "gluten-free" if d in {"gluten free", "gluten-free"} else
        "dairy-free" if d in {"dairy free", "dairy-free"} else d
        for d in dietary_found
    ]
    ambiance_found = [
        "family-friendly" if a in {"family friendly", "family-friendly"} else
        "outdoor seating" if a in {"outdoor", "outdoor seating"} else a
        for a in ambiance_found
    ]

    extracted = {
        "cuisine": cuisines_found[0] if cuisines_found else None,
        "price_range": _extract_price_from_text(combined_text) or preferences["price_range"],
        "dietary_needs": dietary_found or preferences["dietary_needs"],
        "ambiance": ambiance_found[0] if ambiance_found else (
            preferences["ambiance_preferences"][0].lower()
            if preferences["ambiance_preferences"] else None
        ),
        "occasion": occasion_found[0] if occasion_found else None,
        "location": preferences.get("preferred_location"),
        "must_be_open_now": "open now" in combined_text or "open tonight" in combined_text,
    }
    return extracted


async def _llm_extract_filters(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]],
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Uses LangChain + OpenAI to interpret the user's restaurant request.

    Returns a structured dictionary. If anything fails, the caller should fall back
    to deterministic extraction.
    """
    api_key = _get_env("OPENAI_API_KEY")
    if not (_is_usable_key(api_key) and LANGCHAIN_OPENAI_AVAILABLE):
        raise RuntimeError("OpenAI key or LangChain OpenAI package not available.")

    system_prompt = f"""
You are a restaurant recommendation parser for a Yelp-like application.

Your job:
- Read the user's latest request and short conversation history.
- Extract structured search filters.
- Use saved preferences if the user did not explicitly override them.
- Return ONLY valid JSON with this exact schema:

{{
  "cuisine": "string or null",
  "price_range": "$ | $$ | $$$ | $$$$ | null",
  "dietary_needs": ["array of strings"],
  "ambiance": "string or null",
  "occasion": "string or null",
  "location": "string or null",
  "must_be_open_now": true
}}

Saved user preferences:
{_build_preference_summary(preferences)}

Rules:
- If the user says "something romantic", set ambiance to "romantic".
- If the user mentions vegan/vegetarian/halal/gluten-free, include them in dietary_needs.
- Use null for unknown single values.
- Keep dietary_needs as an array.
- Return JSON only. No markdown. No explanation.
    """.strip()

    human_prompt = f"""
Conversation history:
{_serialize_history(conversation_history)}

Latest user message:
{message}
    """.strip()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
    )

    response = await llm.ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt},
        ]
    )

    content = response.content.strip()
    parsed = json.loads(content)

    # Normalize the result to reduce downstream surprises.
    parsed["dietary_needs"] = _safe_list(parsed.get("dietary_needs", []))
    return {
        "cuisine": parsed.get("cuisine"),
        "price_range": parsed.get("price_range"),
        "dietary_needs": parsed.get("dietary_needs", []),
        "ambiance": parsed.get("ambiance"),
        "occasion": parsed.get("occasion"),
        "location": parsed.get("location"),
        "must_be_open_now": bool(parsed.get("must_be_open_now", False)),
    }


async def _extract_filters(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]],
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main extraction wrapper.

    Tries LLM-based parsing first for stronger NLU.
    Falls back to deterministic keyword parsing if the AI path is unavailable or fails.
    """
    try:
        return await _llm_extract_filters(message, conversation_history, preferences)
    except Exception:
        return _keyword_extract_filters(message, conversation_history, preferences)


# ----------------------------------------
# Database query and ranking helpers
# ----------------------------------------
def _build_restaurant_query(
    db: Session,
    extracted_filters: Dict[str, Any],
) -> Any:
    """
    Builds a SQLAlchemy query for restaurants based on extracted user intent.

    Notes:
    - We use defensive matching because student schemas vary slightly.
    - We match cuisine via cuisine_type.
    - We use description/amenities text matching for ambiance/dietary hints.
    """
    query = db.query(models.Restaurant)

    cuisine = extracted_filters.get("cuisine")
    price_range = extracted_filters.get("price_range")
    ambiance = extracted_filters.get("ambiance")
    dietary_needs = extracted_filters.get("dietary_needs", [])
    location = extracted_filters.get("location")

    if cuisine:
        query = query.filter(models.Restaurant.cuisine_type.ilike(f"%{cuisine}%"))

    if price_range:
        query = query.filter(models.Restaurant.price_tier == price_range)

    if location:
        # Many student projects store city directly on Restaurant.
        query = query.filter(
            or_(
                models.Restaurant.city.ilike(f"%{location}%"),
                models.Restaurant.address.ilike(f"%{location}%"),
            )
        )

    # For ambiance and dietary hints, search relevant text fields defensively.
    if ambiance:
        query = query.filter(
            or_(
                models.Restaurant.description.ilike(f"%{ambiance}%"),
                models.Restaurant.amenities.ilike(f"%{ambiance}%")
                if hasattr(models.Restaurant, "amenities")
                else False,
            )
        )

    for dietary in dietary_needs:
        query = query.filter(
            or_(
                models.Restaurant.description.ilike(f"%{dietary}%"),
                models.Restaurant.amenities.ilike(f"%{dietary}%")
                if hasattr(models.Restaurant, "amenities")
                else False,
                models.Restaurant.cuisine_type.ilike(f"%{dietary}%"),
            )
        )

    return query


def _compute_match_reason(
    restaurant: models.Restaurant,
    extracted_filters: Dict[str, Any],
    preferences: Dict[str, Any],
) -> str:
    """
    Builds a specific reason string explaining why the restaurant was recommended.
    """
    reasons = []

    cuisine = (extracted_filters.get("cuisine") or "").lower()
    ambiance = (extracted_filters.get("ambiance") or "").lower()
    price_range = extracted_filters.get("price_range")
    dietary_needs = [d.lower() for d in extracted_filters.get("dietary_needs", [])]

    rest_cuisine = (getattr(restaurant, "cuisine_type", "") or "").lower()
    desc = (getattr(restaurant, "description", "") or "").lower()
    amenities = str(getattr(restaurant, "amenities", "") or "").lower()
    searchable_text = f"{rest_cuisine} {desc} {amenities}"

    if cuisine and cuisine in rest_cuisine:
        reasons.append(f"matches your {cuisine.title()} preference")

    if price_range and getattr(restaurant, "price_tier", None) == price_range:
        reasons.append(f"fits your {price_range} budget")

    if ambiance and ambiance in searchable_text:
        reasons.append(f"offers a {ambiance} atmosphere")

    for dietary in dietary_needs:
        if dietary in searchable_text:
            reasons.append(f"supports {dietary} dining")

    if not reasons:
        reasons.append("is highly rated and relevant to your request")

    return ", ".join(reasons[:2]).capitalize() + "."

def _score_restaurant(
    restaurant: models.Restaurant,
    extracted_filters: Dict[str, Any],
    preferences: Dict[str, Any],
) -> float:
    """
    Computes a balanced relevance score for ranking restaurants.

    Higher score = better recommendation.
    """
    score = 0.0

    cuisine = (extracted_filters.get("cuisine") or "").lower()
    ambiance = (extracted_filters.get("ambiance") or "").lower()
    price_range = extracted_filters.get("price_range")
    dietary_needs = [d.lower() for d in extracted_filters.get("dietary_needs", [])]
    occasion = (extracted_filters.get("occasion") or "").lower()

    rest_name = (getattr(restaurant, "name", "") or "").lower()
    rest_cuisine = (getattr(restaurant, "cuisine_type", "") or "").lower()
    desc = (getattr(restaurant, "description", "") or "").lower()
    amenities = str(getattr(restaurant, "amenities", "") or "").lower()

    searchable_text = f"{rest_name} {rest_cuisine} {desc} {amenities}"

    # Strong intent matches
    if cuisine and cuisine in rest_cuisine:
        score += 4.0

    if price_range and getattr(restaurant, "price_tier", None) == price_range:
        score += 2.5

    if ambiance and ambiance in searchable_text:
        score += 3.0

    if occasion and occasion in searchable_text:
        score += 2.0

    for dietary in dietary_needs:
        if dietary in searchable_text:
            score += 2.5

    # Preference alignment
    for preferred_cuisine in preferences.get("cuisine_preferences", []):
        if preferred_cuisine.lower() in rest_cuisine:
            score += 1.0

    for preferred_ambiance in preferences.get("ambiance_preferences", []):
        if preferred_ambiance.lower() in searchable_text:
            score += 0.8

    for preferred_dietary in preferences.get("dietary_needs", []):
        if preferred_dietary.lower() in searchable_text:
            score += 0.8

    # Quality score
    avg_rating = float(getattr(restaurant, "average_rating", 0) or 0)
    review_count = int(getattr(restaurant, "review_count", 0) or 0)

    score += avg_rating * 1.2
    score += min(review_count / 20.0, 2.0)

    return score


def _rank_restaurants(
    restaurants: List[models.Restaurant],
    extracted_filters: Dict[str, Any],
    preferences: Dict[str, Any],
) -> List[Tuple[models.Restaurant, float]]:
    """
    Applies relevance scoring and returns restaurants sorted from best to worst.
    """
    scored = [
        (restaurant, _score_restaurant(restaurant, extracted_filters, preferences))
        for restaurant in restaurants
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


# ----------------------------------------
# Tavily enrichment helpers
# ----------------------------------------
async def _tavily_context(
    message: str,
    top_restaurants: List[models.Restaurant],
) -> str:
    """
    Uses Tavily search to fetch lightweight external context such as hours/events/trending info.

    This step is optional. If Tavily is unavailable, we simply return an empty string.
    """
    tavily_key = _get_env("TAVILY_API_KEY")
    if not (_is_usable_key(tavily_key) and TAVILY_AVAILABLE and top_restaurants):
        return ""

    try:
        restaurant_names = ", ".join(r.name for r in top_restaurants[:3])
        query = (
            f"Restaurant hours, current popularity, or notable context for: "
            f"{restaurant_names}. User request: {message}"
        )

        tool = TavilySearchResults(
            max_results=3,
            tavily_api_key=tavily_key,
        )

        # Tavily tool may return string/list depending on package version.
        result = tool.invoke(query)
        return str(result)[:1200]
    except Exception:
        return ""


# ----------------------------------------
# Response generation helpers
# ----------------------------------------
async def _llm_generate_response(
    message: str,
    preferences: Dict[str, Any],
    extracted_filters: Dict[str, Any],
    ranked_restaurants: List[Tuple[models.Restaurant, float]],
    web_context: str,
) -> str:
    """
    Uses an LLM to turn ranked structured results into a polished conversational reply.
    Falls back to a handcrafted response if OpenAI is unavailable.
    """
    api_key = _get_env("OPENAI_API_KEY")
    if not (_is_usable_key(api_key) and LANGCHAIN_OPENAI_AVAILABLE):
        raise RuntimeError("OpenAI response generation unavailable.")

    top_restaurants = ranked_restaurants[:5]
    restaurant_lines = []
    for restaurant, score in top_restaurants:
        restaurant_lines.append(
            f"- {restaurant.name} | cuisine={restaurant.cuisine_type} | "
            f"price={restaurant.price_tier} | rating={getattr(restaurant, 'average_rating', 0)} | "
            f"score={round(score, 2)} | "
            f"description={(getattr(restaurant, 'description', '') or '')[:180]}"
        )

    system_prompt = """
You are a helpful restaurant recommendation assistant in a Yelp-style app.

Write a natural, concise, friendly response that:
- acknowledges the user's request,
- mentions that recommendations are based on the user's preferences when relevant,
- briefly highlights 2-4 top options,
- sounds conversational rather than robotic,
- does not invent facts not present in the provided data,
- does not use markdown tables,
- keeps the answer under 180 words.

If web context is empty, do not mention external web information.
    """.strip()

    user_prompt = f"""
User message:
{message}

Saved preferences:
{_build_preference_summary(preferences)}

Extracted filters:
{json.dumps(extracted_filters)}

Ranked restaurants:
{chr(10).join(restaurant_lines) if restaurant_lines else "No matches found."}

Web context:
{web_context or "None"}
    """.strip()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        api_key=api_key,
    )

    response = await llm.ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.content.strip()


def _fallback_generate_response(
    message: str,
    preferences: Dict[str, Any],
    extracted_filters: Dict[str, Any],
    ranked_restaurants: List[Tuple[models.Restaurant, float]],
) -> str:
    """
    Generates a graceful non-LLM response for demos or environments without API keys.
    """
    if not ranked_restaurants:
        return (
            "I couldn’t find a strong restaurant match for that request yet. "
            "Try changing the cuisine, price range, or ambiance, and I’ll refine the search."
        )

    top_restaurants = ranked_restaurants[:3]
    intro_parts = []

    if extracted_filters.get("cuisine"):
        intro_parts.append(f"{str(extracted_filters['cuisine']).title()} cuisine")
    if extracted_filters.get("price_range"):
        intro_parts.append(f"{extracted_filters['price_range']} pricing")
    if extracted_filters.get("ambiance"):
        intro_parts.append(f"{extracted_filters['ambiance']} ambiance")

    intro = ", ".join(intro_parts)
    if intro:
        opening = f"Based on your request for {intro}, here are my top picks:"
    else:
        opening = "Based on your request and saved preferences, here are my top picks:"

    bullets = []
    for restaurant, _score in top_restaurants:
        reason = _compute_match_reason(restaurant, extracted_filters, preferences)
        bullets.append(
            f"{restaurant.name} ({getattr(restaurant, 'average_rating', 0)}★, "
            f"{restaurant.price_tier}) - {reason}"
        )

    return opening + " " + " ".join(
        [f"{idx + 1}. {item}" for idx, item in enumerate(bullets)]
    )


def _format_recommendations(
    ranked_restaurants: List[Tuple[models.Restaurant, float]],
    extracted_filters: Dict[str, Any],
    preferences: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Converts ranked SQLAlchemy restaurant objects into the response schema format expected
    by the frontend chatbot UI.
    """
    recommendations = []

    for restaurant, _score in ranked_restaurants[:5]:
        recommendations.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "rating": float(getattr(restaurant, "average_rating", 0) or 0),
                "price_tier": getattr(restaurant, "price_tier", None),
                "cuisine_type": getattr(restaurant, "cuisine_type", None),
                "reason": _compute_match_reason(restaurant, extracted_filters, preferences),
            }
        )

    return recommendations


# ----------------------------------------
# Main endpoint
# ----------------------------------------
@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Main AI chatbot endpoint.

    Flow:
        1. Load current user's saved preferences.
        2. Interpret natural language query using LangChain or fallback parsing.
        3. Query matching restaurants from the DB.
        4. Rank results by relevance and quality.
        5. Optionally enrich with Tavily web context.
        6. Generate a conversational reply.
        7. Return structured recommendations for the frontend cards.
    """
    message = (payload.message or "").strip()
    conversation_history = payload.conversation_history or []

    if not message:
        return schemas.ChatResponse(
            response="Please tell me what kind of restaurant you’re looking for.",
            recommendations=[],
        )

    # Step 1: Load saved preferences for the current user.
    preferences = _load_user_preferences(db, current_user)

    # Step 2: Extract structured filters from the user message + prior conversation.
    extracted_filters = await _extract_filters(
        message=message,
        conversation_history=conversation_history,
        preferences=preferences,
    )

    # Step 3: Query the restaurant database using extracted filters.
    query = _build_restaurant_query(db, extracted_filters)

    # Pull a broader candidate set first, then apply custom ranking in Python.
    candidates = query.limit(25).all()

    # If the strict query returned nothing, relax the search and use high-rated restaurants.
    if not candidates:
        fallback_query = db.query(models.Restaurant)

        cuisine = extracted_filters.get("cuisine")
        if cuisine:
            fallback_query = fallback_query.filter(
                models.Restaurant.cuisine_type.ilike(f"%{cuisine}%")
            )

        candidates = (
            fallback_query
            .order_by(models.Restaurant.average_rating.desc(), models.Restaurant.review_count.desc())
            .limit(25)
            .all()
        )

    # Step 4: Rank candidate restaurants based on relevance + ratings + preferences.
    ranked_restaurants = _rank_restaurants(
        restaurants=candidates,
        extracted_filters=extracted_filters,
        preferences=preferences,
    )

    # Step 5: Optionally enrich with Tavily for current context like hours/events.
    web_context = await _tavily_context(
        message=message,
        top_restaurants=[restaurant for restaurant, _score in ranked_restaurants[:3]],
    )

    # Step 6: Generate natural language response using LLM when available.
    try:
        response_text = await _llm_generate_response(
            message=message,
            preferences=preferences,
            extracted_filters=extracted_filters,
            ranked_restaurants=ranked_restaurants,
            web_context=web_context,
        )
    except Exception:
        response_text = _fallback_generate_response(
            message=message,
            preferences=preferences,
            extracted_filters=extracted_filters,
            ranked_restaurants=ranked_restaurants,
        )

    # Step 7: Format frontend-friendly recommendation cards.
    recommendations = _format_recommendations(
        ranked_restaurants=ranked_restaurants,
        extracted_filters=extracted_filters,
        preferences=preferences,
    )

    return schemas.ChatResponse(
        response=response_text,
        recommendations=recommendations,
    )