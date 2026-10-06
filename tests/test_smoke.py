from app.agents import _json, _num, _fallback_rank
from app.tools import _distance_km, _parse_restaurants, _is_public_url


def test_distance_zero():
    assert _distance_km(18.5204, 73.8567, 18.5204, 73.8567) == 0


def test_json_parsing_with_fences():
    assert _json('```json\n{"a": 1}\n```') == {'a': 1}
    assert _json('text [{"id": 1}] more', 'array') == [{'id': 1}]


def test_num_is_forgiving():
    assert _num('85.5', 0) == 85
    assert _num('₹3,000', 0) == 3000
    assert _num(None, 7) == 7


def test_parse_restaurants_dedupes_and_sorts():
    els = [
        {'lat': 18.53, 'lon': 73.86, 'tags': {'name': 'B', 'cuisine': 'indian;thai'}},
        {'lat': 18.521, 'lon': 73.857, 'tags': {'name': 'A'}},
        {'lat': 18.521, 'lon': 73.857, 'tags': {'name': 'a'}},
        {'center': {'lat': 18.6, 'lon': 73.9}, 'tags': {}},
    ]
    out = _parse_restaurants(els, 18.5204, 73.8567, 15)
    assert [r['name'] for r in out] == ['A', 'B']
    assert out[1]['cuisine'] == 'indian, thai'


def test_fallback_rank_limits_to_five():
    rs = [{'name': str(i), 'distance_km': i} for i in range(8)]
    assert len(_fallback_rank(rs)) == 5


def test_ssrf_blocked():
    assert not _is_public_url('http://127.0.0.1:8501')
    assert not _is_public_url('file:///etc/passwd')
