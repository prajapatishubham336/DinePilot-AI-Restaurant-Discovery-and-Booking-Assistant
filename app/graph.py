from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import planner_agent, rank_agent
from .tools import geocode_location, search_nearby_restaurants


class SearchState(TypedDict, total=False):
    request: str
    location: str
    current_location: dict
    criteria: dict
    place: dict
    restaurants: list
    ranked: list


def plan_node(state):
    criteria = planner_agent(state['request'])
    # Explicit UI inputs always win over what the LLM guessed.
    if state.get('current_location'):
        criteria['use_current_location'] = True
        criteria['location'] = ''
    elif state.get('location'):
        criteria['location'] = state['location']
        criteria['use_current_location'] = False
    return {'criteria': criteria}


def location_node(state):
    if state.get('current_location'):
        return {'place': state['current_location']}

    criteria = state.get('criteria', {})
    location = (state.get('location') or criteria.get('location') or '').strip()
    if not location:
        if criteria.get('use_current_location'):
            raise ValueError('Your request says "near me". Choose "Use my current location" and click '
                             'the location button first, or type an area name.')
        raise ValueError('Please enter a city / area, or use your current location.')
    return {'place': geocode_location.invoke(location)}


def search_node(state):
    p, c = state['place'], state['criteria']
    radius_m = int(float(c.get('radius_km') or 4) * 1000)
    rows = search_nearby_restaurants.invoke(
        {'lat': p['lat'], 'lon': p['lon'], 'radius_m': radius_m, 'limit': 15})
    return {'restaurants': rows}


def rank_node(state):
    return {'ranked': rank_agent(state['criteria'], state.get('restaurants', []))}


def build_search_graph():
    wf = StateGraph(SearchState)
    wf.add_node('planner_agent', plan_node)
    wf.add_node('location_agent', location_node)
    wf.add_node('restaurant_search_agent', search_node)
    wf.add_node('ranking_agent', rank_node)
    wf.add_edge(START, 'planner_agent')
    wf.add_edge('planner_agent', 'location_agent')
    wf.add_edge('location_agent', 'restaurant_search_agent')
    wf.add_edge('restaurant_search_agent', 'ranking_agent')
    wf.add_edge('ranking_agent', END)
    return wf.compile()


search_graph = build_search_graph()
