"""End-to-end tests for the HTTP API, using the real sample dataset (12 listings)."""

import pytest


# Calls /api/listings with the given query parameters and returns the response
def search(client, **params):
    return client.get("/api/listings", params=params)


# ---------- default behaviour ----------


# No parameters: everything, first page, original JSON order, no score
def test_no_params_returns_original_order(client):
    res = search(client)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 12
    assert body["page"] == 1
    assert body["pageSize"] == 5
    assert body["totalPages"] == 3
    assert [l["id"] for l in body["items"]] == ["A1", "B7", "A2", "B8", "A3"]
    assert all(l["score"] is None for l in body["items"])


# Responses use camelCase field names
def test_response_uses_camel_case(client):
    item = search(client).json()["items"][0]
    assert "listedDate" in item
    assert "listed_date" not in item


# The cities endpoint lists each city once, sorted
def test_cities_endpoint(client):
    res = client.get("/api/cities")
    assert res.status_code == 200
    assert res.json() == ["Chantilly", "Fairfax", "Manassas", "Reston", "Springfield", "Vienna"]


# ---------- filters ----------


# Filters combine: the cheapest 3-bedroom listing comes first
def test_combined_filters_and_sort(client):
    body = search(client, minBedrooms=3, maxBedrooms=3, sortBy="price", order="asc").json()
    assert all(l["bedrooms"] == 3 for l in body["items"])
    assert body["items"][0]["address"] == "300 Cedar Blvd"
    prices = [l["price"] for l in body["items"]]
    assert prices == sorted(prices)


# City filter ignores case
def test_city_filter_is_case_insensitive(client):
    body = search(client, city="reston").json()
    assert body["total"] == 2
    assert all(l["city"] == "Reston" for l in body["items"])


# ---------- no matches ----------


# A keyword that matches nothing is a valid empty result, not an error
def test_no_matches_returns_empty_200(client):
    res = search(client, keyword="castle")
    assert res.status_code == 200
    assert res.json() == {"items": [], "page": 1, "pageSize": 5, "total": 0, "totalPages": 0}


# Valid filters that exclude everything also give an empty 200
def test_valid_filters_with_no_matches(client):
    res = search(client, city="Reston", minBedrooms=10)
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ---------- invalid filter values ----------


# Each invalid input returns 422 instead of crashing or returning wrong data
@pytest.mark.parametrize(
    "params",
    [
        {"minPrice": -1},
        {"maxPrice": "abc"},
        {"minBedrooms": -2},
        {"minBedrooms": 2.5},
        {"targetBudget": 0},
        {"targetBudget": -100},
        {"pageSize": 0},
        {"pageSize": -5},
        {"pageSize": 101},
        {"page": 0},
        {"sortBy": "city"},
        {"order": "up"},
    ],
)
def test_invalid_values_return_422(client, params):
    assert search(client, **params).status_code == 422


# min greater than max is rejected with a clear message
@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"minPrice": 900000, "maxPrice": 100000}, "minPrice cannot be greater than maxPrice"),
        ({"minBedrooms": 4, "maxBedrooms": 2}, "minBedrooms cannot be greater than maxBedrooms"),
    ],
)
def test_min_greater_than_max(client, params, message):
    res = search(client, **params)
    assert res.status_code == 422
    assert res.json()["detail"] == message


# Equal min and max is valid (an exact value)
def test_min_equal_to_max_is_valid(client):
    assert search(client, minBedrooms=3, maxBedrooms=3).status_code == 200


# A city that does not exist in the data is an input error, not an empty result
def test_unknown_city_returns_422(client):
    res = search(client, city="Atlantis")
    assert res.status_code == 422
    assert res.json()["detail"] == "Unknown city 'Atlantis'"


# ---------- pagination boundaries ----------


# The last page holds the remaining items (12 listings, 5 per page -> 2 on page 3)
def test_last_page_is_partial(client):
    body = search(client, page=3, pageSize=5).json()
    assert len(body["items"]) == 2
    assert body["totalPages"] == 3


# A page past the end is a clear error
def test_page_out_of_range(client):
    res = search(client, page=4, pageSize=5)
    assert res.status_code == 422
    assert res.json()["detail"] == "page 4 is out of range (total pages: 3)"


# The maximum page size returns everything in one page
def test_page_size_at_maximum(client):
    body = search(client, pageSize=100).json()
    assert len(body["items"]) == 12
    assert body["totalPages"] == 1


# Walking through every page returns each listing exactly once, in ranked order
def test_pages_cover_all_results_without_overlap(client):
    full = search(client, targetBudget=430000, pageSize=100).json()["items"]
    paged = []
    for page in (1, 2, 3):
        paged += search(client, targetBudget=430000, pageSize=5, page=page).json()["items"]
    assert [(l["source"], l["id"]) for l in paged] == [(l["source"], l["id"]) for l in full]
    assert len({(l["source"], l["id"]) for l in paged}) == 12


# ---------- ranking ----------


# With a budget, results are sorted by score from highest to lowest
def test_budget_ranks_by_score(client):
    items = search(client, targetBudget=430000, pageSize=100).json()["items"]
    scores = [l["score"] for l in items]
    assert scores == sorted(scores, reverse=True)
    assert items[0]["address"] == "300 Cedar Blvd"


# The pending listing ends up last because its score is halved
def test_pending_listing_ranks_last(client):
    items = search(client, targetBudget=500000, pageSize=100).json()["items"]
    assert items[-1]["status"] == "pending"


# An explicit sort column wins over the score, but the score is still returned
def test_sort_column_overrides_score(client):
    items = search(client, targetBudget=430000, sortBy="price", order="desc", pageSize=100).json()["items"]
    prices = [l["price"] for l in items]
    assert prices == sorted(prices, reverse=True)
    assert all(l["score"] is not None for l in items)
