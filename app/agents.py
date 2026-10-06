import json
import re

from .config import GROQ_API_KEY, GROQ_MODEL
from .tools import fetch_website_menu

DEFAULTS = {'location': '', 'use_current_location': False, 'meal': 'dinner',
            'people': 2, 'budget_inr': 0, 'cuisine': 'any', 'radius_km': 4.0}


def get_llm():
    if not GROQ_API_KEY:
        raise RuntimeError('GROQ_API_KEY is missing. Add it to .env or your deployment environment.')
    from langchain_groq import ChatGroq  # lazy import keeps tests/light tools fast
    return ChatGroq(model=GROQ_MODEL, temperature=0.1, api_key=GROQ_API_KEY,
                    timeout=30, max_retries=2)


def _text(content) -> str:
    if isinstance(content, list):
        return ''.join(c.get('text', '') if isinstance(c, dict) else str(c) for c in content)
    return str(content)


def _json(text: str, kind: str = 'object'):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    pattern = r'\[.*\]' if kind == 'array' else r'\{.*\}'
    match = re.search(pattern, text, re.S)
    return json.loads(match.group(0) if match else text)


def _num(v, default, cast=int):
    try:
        return cast(float(re.sub(r'[^\d.]', '', str(v))))
    except Exception:
        return default


def planner_agent(request: str) -> dict:
    out = DEFAULTS.copy()
    try:
        llm = get_llm()
        prompt = f'''You are a restaurant search planner. Parse this request into JSON only.
Request: {request}
Return keys: location, use_current_location, meal, people, budget_inr, cuisine, radius_km.
Defaults: meal=dinner, people=2, budget_inr=0, cuisine=any, radius_km=4.
If the user says near me/current location, set use_current_location=true and location="". Never invent a location.'''
        res = _json(_text(llm.invoke(prompt).content))
    except Exception as e:  # planner is optional: search still works from the UI inputs
        print('Planner failed:', e)
        return out
    out['location'] = str(res.get('location') or '').strip()
    out['use_current_location'] = bool(res.get('use_current_location'))
    out['meal'] = str(res.get('meal') or 'dinner')
    out['cuisine'] = str(res.get('cuisine') or 'any')
    out['people'] = _num(res.get('people'), 2)
    out['budget_inr'] = _num(res.get('budget_inr'), 0)
    out['radius_km'] = max(0.5, min(_num(res.get('radius_km'), 4.0, float), 10.0))
    return out


def _fallback_rank(restaurants):
    return [{**r, 'match_score': max(1, 100 - int(r['distance_km'] * 12)),
             'reason': 'Closest mapped restaurant based on available OSM data.'}
            for r in restaurants[:5]]


def rank_agent(criteria: dict, restaurants: list) -> list:
    if not restaurants:
        return []
    compact = [{'id': i, 'name': r['name'], 'distance_km': r['distance_km'],
                'cuisine': r['cuisine'], 'opening_hours': r['opening_hours'],
                'address': r['address']} for i, r in enumerate(restaurants)]
    prompt = f'''Rank these restaurants for the user's request.
Criteria: {json.dumps(criteria)}
Restaurants: {json.dumps(compact)}
Return a JSON array only. Each item: id (same as input), match_score (0-100 integer), reason (max 18 words).
Do not invent ratings, reviews, prices, or opening status. Use "unknown" when data is missing.'''
    try:
        ranked = _json(_text(get_llm().invoke(prompt).content), 'array')
        if isinstance(ranked, dict):
            ranked = ranked.get('restaurants', [])
        out, used = [], set()
        for item in ranked:
            idx = _num(item.get('id'), -1)
            if 0 <= idx < len(restaurants) and idx not in used:
                used.add(idx)
                out.append({**restaurants[idx],
                            'match_score': max(0, min(100, _num(item.get('match_score'), 0))),
                            'reason': str(item.get('reason', 'Matches the request.'))})
        if not out:
            return _fallback_rank(restaurants)
        return sorted(out, key=lambda x: (-x['match_score'], x['distance_km']))[:5]
    except Exception as e:
        print('Ranking failed:', e)
        return _fallback_rank(restaurants)


def menu_agent(restaurant: dict) -> dict:
    result = fetch_website_menu.invoke(restaurant.get('website', ''))
    result['restaurant'] = restaurant.get('name', '')
    return result


def booking_agent(booking: dict) -> str:
    safe = {k: v for k, v in booking.items() if k != 'contact'}  # don't send contact details to the LLM
    prompt = f'''Create a concise booking-request confirmation for this reservation.
{json.dumps(safe)}
Mention that the app submitted a booking request and that final confirmation depends on the restaurant/provider. Do not claim confirmed availability.'''
    return _text(get_llm().invoke(prompt).content).strip()
