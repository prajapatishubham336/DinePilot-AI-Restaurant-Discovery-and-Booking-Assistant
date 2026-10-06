import ipaddress
import json
import math
import re
import socket
import threading
import time
from functools import lru_cache
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from .config import (DEFAULT_COUNTRY, NOMINATIM_URL, OSM_USER_AGENT, OVERPASS_URLS,)


HEADERS = {
    "User-Agent": OSM_USER_AGENT,
    "Accept-Language": "en",
}

_geo_lock = threading.Lock()
_last_geo_call = 0.0


def build_address(tags):
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:neighbourhood"),
        tags.get("addr:city"),
        tags.get("addr:district"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    return ", ".join(str(x).strip() for x in parts  if x)

def _distance_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2)

    return 2 * earth_radius * math.asin( math.sqrt(a))

# NOMINATIM
def _nominatim(params, reverse=False):
    global _last_geo_call

    base_url = NOMINATIM_URL.rstrip("/")

    if reverse:
        url = (base_url.rsplit("/", 1)[0]  + "/reverse")
    else:
        url = base_url
    with _geo_lock:
        wait = 1.1 - (time.time() - _last_geo_call)

        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(url, params=params,  headers=HEADERS, timeout=15,)
        except requests.RequestException:
            raise
        finally:
            _last_geo_call = time.time()

    if response.status_code != 200:
        raise ValueError(
            f"Location service error "
            f"{response.status_code}. "
            "Please try again."
        )

    return response.json()

@lru_cache(maxsize=256)
def _geocode(query):
    base = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
    }

    data = []

    if DEFAULT_COUNTRY:
        data = _nominatim({ **base, "countrycodes": DEFAULT_COUNTRY,})

    if not data:
        data = _nominatim(base)

    if not data:
        raise ValueError(
            f'Location not found: "{query}". '
            'Try "area, city" '
            '(e.g. Koregaon Park, Pune).')

    item = data[0]

    return (
        float(item["lat"]),
        float(item["lon"]),
        item.get("display_name", query,),)


@lru_cache(maxsize=500)
def _reverse_geocode(lat, lon):
    data = _nominatim(
        {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
        },
        reverse=True,
    )

    if not isinstance(data, dict):
        return ""

    return data.get("display_name", "",)


@tool
def geocode_location(query: str) -> dict:
    """Convert a place name or address into coordinates."""

    query = (query or "").strip()

    if not query:
        raise ValueError("Location is empty.")

    lat, lon, name = _geocode(query)
    return {
        "lat": lat,
        "lon": lon,
        "display_name": name,
    }


# WEBSITE SECURITY
def _is_public_url(url):
    try:
        parsed = urlparse(url)
        if (
            parsed.scheme
            not in ("http", "https")
            or not parsed.hostname):
            return False

        for info in socket.getaddrinfo(parsed.hostname,  None,):

            ip = ipaddress.ip_address(info[4][0])

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False
        return True
    except (OSError, ValueError,):
        return False


def _get_public(url, hops=3):
    for _ in range(hops + 1):
        if not _is_public_url(url):
            return None
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "DinePilotAI/1.0", "Accept-Language":  "en",},
                timeout=12,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException:
            raise

        if (
            response.status_code
            in (301, 302, 303, 307, 308,)
            and response.headers.get("Location")):

            url = urljoin(url, response.headers["Location"],)
            continue

        if response.status_code >= 400:
            return None

        body = b""
        for chunk in response.iter_content(65536):
            body += chunk
            if len(body) >= 1_000_000:
                break

        response.encoding = (response.encoding  or "utf-8")
        return body.decode( response.encoding, errors="ignore",)

    return None


# WEBSITE ADDRESS + OPENING HOURS
def _extract_website_details(html_text):
    address = ""
    hours = ""

    soup = BeautifulSoup( html_text, "html.parser",)

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json",):
        try:
            raw = (script.string or script.get_text()  or "")
            data = json.loads(raw)
            objects = (data if isinstance(data, list) else [data])
            expanded = []
            for obj in objects:
                if not isinstance( obj, dict,):
                    continue

                expanded.append(obj)
                graph = obj.get("@graph")
                if isinstance(graph, list,):
                    expanded.extend(item  for item in graph if isinstance(item,  dict,))

            for obj in expanded:
                # ADDRESS
                if not address:
                    addr = obj.get("address")
                    if isinstance(addr, dict,):

                        parts = [addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),]

                        address = ", ".join(
                            str(x).strip()
                            for x in parts
                            if x)

                    elif isinstance(addr, str,):
                        if len(addr.strip()) > 10:
                            address = (addr.strip())

                # OPENING HOURS
                if not hours:
                    opening = obj.get("openingHours")
                    if opening:
                        if isinstance(opening, list,):
                            hours = " • ".join(str(x) for x in opening)
                        else:
                            hours = str(opening)

                # OPENING HOURS SPECIFICATION
                if not hours:
                    specs = obj.get("openingHoursSpecification")
                    if isinstance(specs, dict,):
                        specs = [specs]

                    if isinstance(specs, list,):
                        parts = []
                        for spec in specs:
                            if not isinstance(spec,  dict,):
                                continue

                            opens = spec.get("opens")
                            closes = spec.get("closes")
                            days = spec.get("dayOfWeek", "",)

                            if ( opens and closes):
                                if isinstance(days, list,):
                                    days = ", ".join( str(x).split("/")[-1] for x in days)

                                elif days:
                                    days = str(days).split("/")[-1]
                                text = (
                                    f"{days}: "
                                    f"{opens} - "
                                    f"{closes}"
                                )

                                parts.append(text.strip(": "))

                        if parts:
                            hours = " • ".join(parts)

        except (json.JSONDecodeError, TypeError,  ValueError,):
            continue


    # Visible text
    for tag in soup.find_all(["script", "style", "noscript",]):
        tag.decompose()

    text = " ".join(soup.stripped_strings)

    # Address fallback
    if not address:

        patterns = [
            r"(?:address|located at|visit us)"
            r"[:\s-]+(.{20,300}?)"
            r"(?:phone|tel|email|"
            r"opening hours|hours|$)",

            r"(?:our address)"
            r"[:\s-]+(.{20,300}?)"
            r"(?:phone|tel|email|hours|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text,re.I,)
            if match:
                candidate = (match.group(1).strip(" .,-|"))
                if len(candidate) > 10:
                    address = candidate
                    break

    # Hours fallback
    if not hours:
        match = re.search(
            r"(?:opening hours|"
            r"open daily|hours)"
            r"[:\s-]+(.{10,200}?)"
            r"(?:address|phone|tel|"
            r"email|menu|$)",
            text,
            re.I,
        )

        if match:
            hours = (match.group(1).strip(" .,-|"))
    return address, hours

def fetch_website_details(url):

    if not url:
        return "", ""

    if not re.match(r"^https?://", url, re.I,):
        url = "https://" + url

    pages = [
        url,
        url.rstrip("/") + "/contact",
        url.rstrip("/") + "/contact-us",
        url.rstrip("/") + "/about",
        url.rstrip("/") + "/location",
        url.rstrip("/") + "/hours",
    ]

    address = ""
    hours = ""

    for page in pages:
        try:
            html_text = _get_public(page)
        except requests.RequestException:
            continue

        if not html_text:
            continue

        page_address, page_hours = (
            _extract_website_details(html_text))

        if page_address and not address:
            address = page_address

        if page_hours and not hours:
            hours = page_hours

        if address and hours:
            break

    return address, hours


# OVERPASS
def _overpass(query):
    errors = []
    for url in OVERPASS_URLS:
        try:
            response = requests.post(url, data={"data": query},
                headers=HEADERS,
                timeout=(5, 20,),)

            if response.status_code == 200:
                data = response.json()
                if (
                    data.get("elements")
                    or "remark" not in data):
                    return data

                errors.append(f"{url}: server timeout")

            else:
                errors.append(
                    f"{url}: HTTP "
                    f"{response.status_code}"
                )

        except (requests.RequestException, ValueError,) as exc:

            errors.append(
                f"{url}: "
                f"{type(exc).__name__}"
            )

    raise RuntimeError(
        "Restaurant data service is busy. "
        "Please retry in a minute. "
        + "; ".join(errors[-3:]))


# RESTAURANT PARSER
def _parse_restaurants(elements, lat,lon, limit,):
    items = []
    seen = set()
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get( "name")

        if not name:
            continue

        name_key = (name.lower().strip())

        if name_key in seen:
            continue

        e_lat = element.get("lat", element.get("center",{}).get("lat"),)
        e_lon = element.get("lon", element.get("center", {}).get("lon"),)

        if (e_lat is None  or e_lon is None):
            continue

        seen.add(name_key)
        e_lat = float(e_lat)
        e_lon = float(e_lon)

        # Website
        website = (tags.get( "website" )  or tags.get( "contact:website") or "")

        # Address from OSM
        address = build_address( tags)

        # Opening hours from OSM
        opening_hours = tags.get( "opening_hours", "")

        # Website fallback
        if (website  and (not address  or not opening_hours)):

            try:
                web_address, web_hours = (fetch_website_details(website))

                if not address:
                    address = web_address

                if not opening_hours:
                    opening_hours = web_hours

            except Exception:
                pass

        # Reverse geocoding fallback
        if not address:
            try:
                address = _reverse_geocode(round(e_lat, 6), round(e_lon, 6),)
            except Exception:
                address = ""

        # Other fields
        cuisine = (tags.get("cuisine", "Not listed",)
            .replace(";", ", ",)
            .replace("_", " ",))
        phone = (tags.get("phone")
            or tags.get("contact:phone")  or "")

        items.append({
            "name": name,
            "lat": e_lat,
            "lon": e_lon,
            "distance_km": round(
                _distance_km(lat, lon, e_lat, e_lon,), 2,),
            "cuisine": cuisine,
            "opening_hours": (opening_hours  or "Opening hours not available"),
            "address": (address or "Address not available"),
            "website": website,
            "phone": phone,
        })

    return sorted(items, key=lambda x: x["distance_km"],)[:limit]

# SEARCH CACHE
_search_cache = {}
_CACHE_TTL = 600


@tool
def search_nearby_restaurants(lat: float, lon: float, radius_m: int = 4000,limit: int = 15,) -> list:
    """Find nearby restaurants using OpenStreetMap Overpass."""

    radius_m = max( 500, min(int(radius_m), 10000,),)
    radii = [radius_m]
    if radius_m < 10000:
        radii.append(min(radius_m * 2, 10000,))

    items = []
    for radius in radii:
        key = (round(lat, 3),round(lon, 3), radius, limit,)
        cached = _search_cache.get(key)
        if (cached  and time.time() - cached[0] < _CACHE_TTL):
            items = cached[1]
        else:
            query = (
                '[out:json][timeout:20];'
                'nwr["amenity"="restaurant"]'
                '["name"]'
                f"(around:{radius},{lat},{lon});"
                "out center tags 300;")

            try:
                data = _overpass(query)
                items = (
                    _parse_restaurants(data.get("elements",[],), lat, lon, limit, ))

            except RuntimeError:
                if cached:
                    items = cached[1]
                else:
                    raise
            else:
                _search_cache[key] = (time.time(), items,)

        if items:
            break
    return items


# MENU
@tool
def fetch_website_menu(url: str) -> dict:

    """Fetch restaurant website and extract a small menu preview."""

    if not url:
        return {
            "status": "missing",
            "text": "",
            "url": "",
        }

    if not re.match(r"^https?://", url, re.I,):
        url = "https://" + url

    targets = [url.rstrip("/") + "/menu", url,]
    for target in targets:
        try:
            html_text = _get_public(target)
        except requests.RequestException:
            continue
        if not html_text:
            continue
        soup = BeautifulSoup(html_text, "html.parser",)

        for tag in soup.find_all(["script", "style", "noscript",]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)

        if not text:
            continue

        lower = text.lower()
        positions = [lower.find(word)
            for word in (
                "menu",
                "dinner",
                "food",
                "pizza",
                "pasta",
            )
            if lower.find(word) >= 0
        ]

        start = max(0,(min(positions) if positions  else 0) // 6,)
        preview = " ".join(text.split()[start:start + 220])
        return {
            "status": "ok",
            "text": preview[:2200],
            "url": target,
        }

    return {
        "status": "unavailable",
        "text": "",
        "url": url,
    }