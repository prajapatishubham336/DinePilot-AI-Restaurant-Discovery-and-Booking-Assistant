import html
import re
import time
from datetime import date
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

from app.owner import owner_dashboard
from app.availability import init_availability
from app.db import cancel_booking
from app.availability import init_availability

from app.agents import booking_agent, menu_agent
from app.config import ADMIN_PASSWORD, GROQ_API_KEY
from app.db import init_db, list_bookings, save_booking
from app.graph import search_graph

st.set_page_config(page_title='DinePilot AI', page_icon='🍽️', layout='wide',
                   initial_sidebar_state='expanded')
init_db()
init_availability()

st.markdown('''<style>
.block-container {padding-top: 1.2rem; max-width: 1400px;}
.hero {padding: 28px; border-radius: 22px; background: linear-gradient(135deg,#111827,#4338ca); color: white; margin-bottom: 18px;}
.hero h1 {margin:0; font-size: 38px; color:white;}
.hero p {opacity:.85; margin:6px 0 0;}
.card {background:white; color:#111827; border:1px solid #e8ebf1; border-radius:18px; padding:18px; margin:10px 0; box-shadow:0 5px 18px rgba(20,25,40,.05);}
.card h3, .card h4 {color:#111827;}
.badge {display:inline-block; padding:4px 9px; border-radius:999px; background:#eef2ff; color:#4338ca; font-weight:700; font-size:12px;}
.small {color:#6b7280; font-size:13px;}
</style>''', unsafe_allow_html=True)

ss = st.session_state
ss.setdefault('results', [])
ss.setdefault('place', None)
ss.setdefault('selected', None)
ss.setdefault('searched', False)
ss.setdefault('last_search', 0.0)
ss.setdefault('gps', None)
ss.setdefault('admin_ok', False)

esc = html.escape

st.markdown('<div class="hero"><h1>🍽️ DinePilot AI</h1><p>Multi-agent restaurant discovery, '
            'menu intelligence and booking requests.</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## DinePilot')
    page = st.radio("Navigate",["Discover", "Bookings", "Owner Dashboard", "Agent Activity"])
    st.divider()
    st.caption('AI: Groq • Orchestration: LangGraph • Data: OpenStreetMap')
    if not GROQ_API_KEY:
        st.warning('GROQ_API_KEY not set: search still works, but ranking uses distance only.')

# ----------- Discover----------------
if page == 'Discover':
    st.markdown('### Find your dinner spot')
    c1, c2 = st.columns([2, 1])
    with c1:
        request = st.text_input('What are you looking for?',
                                placeholder='Top dinner restaurants for 4 people under ₹3000')
        location_mode = st.radio('Location', ['Search a place', 'Use my current location'],
                                 horizontal=True)
        typed_location = ''
        if location_mode == 'Search a place':
            typed_location = st.text_input('City / area / address', placeholder='Koregaon Park, Pune')
    with c2:
        st.info('Examples:\n\n• Best dinner for 2\n• Vegetarian dinner in Bandra West\n'
                '• Restaurants in Koregaon Park under ₹2500')

    if location_mode == 'Use my current location':
        st.caption('Click the location button below and allow browser permission (HTTPS or localhost only).')
        loc = streamlit_geolocation()
        if loc and loc.get('latitude') and loc.get('longitude'):
            ss.gps = {'lat': float(loc['latitude']), 'lon': float(loc['longitude']),
                      'display_name': 'Current browser location'}
        if ss.gps:
            st.success(f"Location detected: {ss.gps['lat']:.4f}, {ss.gps['lon']:.4f}")

    if st.button('🔎 Find Top 5 Restaurants', type='primary', use_container_width=True):
        problem = None
        if location_mode == 'Use my current location' and not ss.gps:
            problem = 'Click the location button above and allow permission first (or switch to "Search a place").'
        elif location_mode == 'Search a place' and not typed_location.strip():
            problem = 'Type a city / area (for example "Koregaon Park, Pune").'
        elif time.time() - ss.last_search < 3:
            problem = 'Please wait a few seconds between searches.'

        if problem:
            st.warning(problem)
        else:
            ss.last_search = time.time()
            state = {'request': request.strip() or 'Find the best dinner restaurants nearby.'}
            if location_mode == 'Use my current location':
                state['current_location'] = ss.gps
            elif typed_location.strip():
                state['location'] = typed_location.strip()
            with st.spinner('Agents are planning, searching and ranking...'):
                try:
                    result = search_graph.invoke(state)
                    ss.results = result.get('ranked', [])
                    ss.place = result.get('place')
                    ss.selected = None
                    ss.searched = True
                except ValueError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f'Could not complete search: {e}')

    if ss.searched and not ss.results:
        st.info('No mapped restaurants found here. Try a bigger area or a different location '
                '(OpenStreetMap coverage varies).')

    if ss.results:
        st.markdown('### Top matches')
        cols = st.columns(2)
        for i, r in enumerate(ss.results):
            if i % 2 == 0:
                cols = st.columns(2)
            with cols[i % 2]:
                st.markdown(
                    f'''<div class="card"><div class="badge">#{i+1} • Match {int(r.get('match_score', 0))}/100</div>
<h3 style="margin-bottom:6px">{esc(r['name'])}</h3>
<div class="small">📍 {r['distance_km']} km • 🍴 {esc(r['cuisine'])}</div>
<p>{esc(r.get('reason', ''))}</p>
<div class="small">🕒 {esc(r['opening_hours'])}<br>📌 {esc(r['address'])}</div></div>''',
                    unsafe_allow_html=True)
                if st.button(f'View {r["name"]}', key=f'sel_{i}', use_container_width=True):
                    ss.selected = r

        if ss.place:
            st.markdown('### Restaurant map')
            center = [ss.place['lat'], ss.place['lon']]
            m = folium.Map(location=center, zoom_start=13)
            folium.Marker(center, tooltip='Search location', icon=folium.Icon(color='blue')).add_to(m)
            for r in ss.results:
                folium.Marker([r['lat'], r['lon']], tooltip=esc(r['name']),
                              popup=f"{esc(r['name'])} • {r['distance_km']} km").add_to(m)
            st_folium(m, width=1200, height=420, returned_objects=[])

    if ss.selected:
        r = ss.selected
        st.markdown('---')
        st.markdown(f'## {r["name"]}')
        d1, d2, d3 = st.columns(3)
        d1.metric('Distance', f"{r['distance_km']} km")
        d2.metric('Match', f"{int(r.get('match_score', 0))}/100")
        d3.metric('Cuisine', r['cuisine'] if len(r['cuisine']) < 18 else 'See details')
        st.link_button('📍 Open in Google Maps',
                       f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}")
        if r.get('phone'):
            st.write(f"📞 {r['phone']}")
        if r.get('website'):
            site = r['website'] if r['website'].startswith('http') else 'https://' + r['website']
            st.link_button('🌐 Open Restaurant Website', site)

        st.markdown('### 🍴 Menu preview')
        with st.spinner('Menu Agent is checking the mapped website...'):
            menu = menu_agent(r)
        if menu['status'] == 'ok':
            st.write(menu['text'])
            st.caption('Extracted from the public website. Verify final prices/items on the restaurant website.')
        else:
            if r.get('website'):
                st.info('No public menu page could be read. Use the official website button above.')
            else:
                st.info("No restaurant website is available, so the menu preview cannot be displayed.")

        st.markdown('### 📅 Request a table')
        with st.form('booking_form'):
            b1, b2, b3 = st.columns(3)
            bdate = b1.date_input('Date', min_value=date.today())
            btime = b2.time_input('Time')
            guests = b3.number_input('Guests', 1, 20, 2)
            name = st.text_input('Your name')
            contact = st.text_input('Email / phone')
            submitted = st.form_submit_button('🍽️ Send Booking Request', type='primary')
        if submitted:
            valid_contact = re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', contact.strip()) or \
                7 <= len(re.sub(r'\D', '', contact)) <= 15
            if not name.strip() or not contact.strip():
                st.error('Please enter your name and contact.')
            elif not valid_contact:
                st.error('Enter a valid email or phone number.')
            else:
                booking = {'restaurant': r['name'], 'date': str(bdate),
                           'time': btime.strftime('%H:%M'), 'guests': int(guests),
                           'name': name.strip()[:100], 'contact': contact.strip()[:100],
                           'website': r.get('website', '')}
                booking_id = save_booking(booking)
                try:
                    message = booking_agent(booking)
                except Exception:
                    message = f'Booking request #{booking_id} submitted.'
                st.success(f'Booking request #{booking_id} created.')
                st.write(message)
                if r.get('website'):
                    st.link_button('Open official website for final confirmation',
                                   r['website'] if r['website'].startswith('http') else 'https://' + r['website'])
                st.caption('DinePilot never marks a table as confirmed unless a real reservation provider confirms it.')

# -------------------------------- My Bookings ----------------------------------
elif page == "My Bookings":
    st.markdown("### 📋 My Bookings")
    contact = st.text_input("Email / Phone", key="my_booking_contact")
    if st.button("🔎 View My Bookings", type="primary"):
        if not contact.strip():
            st.warning("Enter the email or phone used for booking.")
        else:
            rows = list_bookings(contact.strip())
            if not rows:
                st.info("No bookings found.")
            else:
                for row in rows:
                    booking_id, restaurant, bdate, btime, guests, name, status, created = row
                    st.markdown(f'<div class="card"><div class="badge">Booking #{booking_id}</div><h3>{esc(restaurant)}</h3><p>📅 {bdate} • 🕒 {btime} • 👥 {guests} guests</p><p><b>Name:</b> {esc(name)} • <b>Status:</b> {esc(status)}</p><div class="small">Created: {created}</div></div>', unsafe_allow_html=True)
                    if status in ("PENDING", "CONFIRMED"):

                        if st.button(f"❌ Cancel Booking #{booking_id}", key=f"cancel_{booking_id}"):
                            ok, message = cancel_booking(booking_id, contact.strip())
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

# ------------------------------- Owner Dashboard -----------------------------
elif page == "Owner Dashboard":
    if not ADMIN_PASSWORD:
        st.error("ADMIN_PASSWORD is not configured.")
    elif not ss.owner_ok:
        st.markdown("### 🔐 Owner Login")
        password = st.text_input("Owner Password", type="password")
        if st.button("Login", type="primary"):
            if password == ADMIN_PASSWORD:
                ss.owner_ok = True
                st.rerun()
            else:
                st.error("Invalid owner password.")
    else:
        c1, c2 = st.columns([5, 1])
        with c1: st.markdown("### 🏪 Owner Dashboard")
        with c2:
            if st.button("Logout"):
                ss.owner_ok = False
                st.rerun()
        owner_dashboard()

# ------------------------------ Agent Activity ------------------------------
else:
    st.markdown("### 🤖 Agent Activity")
    steps = [
        ("Planner Agent", "Parses dinner, location, guest count, budget and cuisine preferences."),
        ("Location Agent", "Uses browser coordinates or OpenStreetMap geocoding."),
        ("Restaurant Search Agent", "Calls the Overpass restaurant search tool with fallback."),
        ("Ranking Agent", "Uses Groq to rank only returned restaurant data."),
        ("Menu Agent", "Fetches a public restaurant website menu preview."),
        ("Booking Agent", "Creates a booking request and generates a booking response.")
    ]
    for n, d in steps:
        st.markdown(f'<div class="card"><span class="badge">ACTIVE ROLE</span><h4>{n}</h4><div class="small">{d}</div></div>', unsafe_allow_html=True)
    st.info("No fake ratings, menus or availability are generated. Missing information is shown as unavailable.")