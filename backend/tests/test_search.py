"""Unit tests for the pure search logic in app/search.py."""

from datetime import date

import pytest

from app.models import ScoredListing
from app.search import (
    budget_score,
    exclude_sold,
    filter_by_city,
    filter_by_keyword,
    filter_by_range,
    normalize,
    paginate,
    recency_score,
    score_listings,
    sort_by_score,
    sort_listings,
    space_score,
    unique_cities,
)

REFERENCE = date(2026, 9, 4)


# ---------- normalize ----------


# Lowercases and collapses repeated spaces
def test_normalize_ignores_case_and_extra_spaces():
    assert normalize("  Pet   FRIENDLY ") == "pet friendly"


# ---------- filters ----------


# Keyword matching ignores case and finds substrings
def test_keyword_is_case_insensitive_substring(make_listing):
    listings = [
        make_listing(id="1", description="Bright condo. Pet friendly."),
        make_listing(id="2", description="Quiet street"),
    ]
    assert [l.id for l in filter_by_keyword(listings, "PET friendly")] == ["1"]


# An empty or blank keyword does not filter anything
@pytest.mark.parametrize("keyword", [None, "", "   "])
def test_blank_keyword_returns_everything(make_listing, keyword):
    listings = [make_listing(id="1"), make_listing(id="2")]
    assert filter_by_keyword(listings, keyword) == listings


# A keyword that appears nowhere gives an empty list, not an error
def test_keyword_with_no_matches_returns_empty(make_listing):
    assert filter_by_keyword([make_listing()], "castle") == []


# City matching ignores case and extra spaces from inconsistent sources
def test_city_filter_normalizes_names(make_listing):
    listings = [
        make_listing(id="1", city="Reston"),
        make_listing(id="2", city="Fairfax"),
    ]
    assert [l.id for l in filter_by_city(listings, "  reston ")] == ["1"]


# Range limits are inclusive on both ends
def test_range_filter_is_inclusive(make_listing):
    listings = [make_listing(id=str(p), price=p) for p in (100, 200, 300)]
    result = filter_by_range(listings, "price", 100, 200)
    assert [l.price for l in result] == [100, 200]


# A None limit means "no limit" on that side
def test_range_filter_with_open_ends(make_listing):
    listings = [make_listing(id=str(b), bedrooms=b) for b in (1, 2, 3, 4)]
    assert [l.bedrooms for l in filter_by_range(listings, "bedrooms", 3, None)] == [3, 4]
    assert [l.bedrooms for l in filter_by_range(listings, "bedrooms", None, 2)] == [1, 2]
    assert len(filter_by_range(listings, "bedrooms", None, None)) == 4


# Sold listings are removed; active and pending stay
def test_exclude_sold(make_listing):
    listings = [
        make_listing(id="1", status="active"),
        make_listing(id="2", status="pending"),
        make_listing(id="3", status="sold"),
    ]
    assert [l.id for l in exclude_sold(listings)] == ["1", "2"]


# Cities that differ only in case or spaces appear once, sorted
def test_unique_cities_deduplicates_and_sorts(make_listing):
    listings = [
        make_listing(city="Vienna"),
        make_listing(city="Fairfax"),
        make_listing(city="vienna "),
    ]
    assert unique_cities(listings) == ["Fairfax", "Vienna"]


# ---------- sorting ----------


# Without a sort column the original order is kept
def test_sort_listings_without_field_keeps_order(make_listing):
    listings = [make_listing(id="b", price=2), make_listing(id="a", price=1)]
    assert sort_listings(listings, None, "asc") == listings


# Ascending and descending sort by any numeric field
def test_sort_listings_by_field(make_listing):
    listings = [make_listing(id=str(p), price=p) for p in (300, 100, 200)]
    assert [l.price for l in sort_listings(listings, "price", "asc")] == [100, 200, 300]
    assert [l.price for l in sort_listings(listings, "price", "desc")] == [300, 200, 100]


# ---------- budget score ----------


# A price exactly on budget gets the full score
def test_budget_score_exact_match():
    assert budget_score(500_000, 500_000) == 1.0


# Going over budget costs twice as much as coming in under it
def test_budget_score_is_asymmetric():
    under = budget_score(450_000, 500_000)  # 10% under
    over = budget_score(550_000, 500_000)  # 10% over
    assert under == pytest.approx(0.9)
    assert over == pytest.approx(0.8)
    assert over < under


# The score never goes below zero, however far the price is
def test_budget_score_is_floored_at_zero():
    assert budget_score(2_000_000, 500_000) == 0.0
    assert budget_score(0, 500_000) == 0.0


# ---------- space score ----------


# The best price per sqft gets 1, one twice as expensive per sqft gets 0.5
def test_space_score_relative_to_best(make_listing):
    best = make_listing(price=200_000, sqft=1000)  # 200 $/sqft
    worse = make_listing(price=400_000, sqft=1000)  # 400 $/sqft
    assert space_score(best, 200) == pytest.approx(1.0)
    assert space_score(worse, 200) == pytest.approx(0.5)


# Bad data (zero sqft) scores 0 instead of crashing with a division by zero
def test_space_score_with_zero_sqft(make_listing):
    assert space_score(make_listing(sqft=0), 200) == 0.0


# ---------- recency score ----------


# Half-life of 30 days: 1 on the reference date, 0.5 after 30 days, 0.25 after 60
@pytest.mark.parametrize(
    ("listed", "expected"),
    [
        (date(2026, 9, 4), 1.0),
        (date(2026, 8, 5), 0.5),
        (date(2026, 7, 6), 0.25),
    ],
)
def test_recency_half_life(listed, expected):
    assert recency_score(listed, REFERENCE) == pytest.approx(expected)


# A date after the reference counts as brand new, never above 1
def test_recency_future_date_is_capped():
    assert recency_score(date(2026, 9, 10), REFERENCE) == 1.0


# ---------- full scoring ----------


# Without a budget there is no score and the order is untouched
def test_score_listings_without_budget(make_listing):
    listings = [make_listing(id="1"), make_listing(id="2")]
    scored = score_listings(listings, None, REFERENCE)
    assert [l.score for l in scored] == [None, None]
    assert [l.id for l in scored] == ["1", "2"]


# Every score is between 0 and 1
def test_scores_are_between_zero_and_one(make_listing):
    listings = [
        make_listing(id="1", price=100_000, sqft=3000, listed_date=REFERENCE),
        make_listing(id="2", price=5_000_000, sqft=500, listed_date=date(2025, 1, 1)),
    ]
    for l in score_listings(listings, 400_000, REFERENCE):
        assert 0.0 <= l.score <= 1.0


# A pending listing scores half of an otherwise identical active one
def test_pending_listing_scores_half(make_listing):
    active = make_listing(id="1", status="active")
    pending = make_listing(id="2", status="pending")
    by_id = {l.id: l.score for l in score_listings([active, pending], 400_000, REFERENCE)}
    assert by_id["2"] == pytest.approx(by_id["1"] / 2, abs=0.001)


# A closer price, more space per dollar and a newer date all rank higher
def test_better_listing_ranks_first(make_listing):
    good = make_listing(id="good", price=400_000, sqft=1600, listed_date=REFERENCE)
    bad = make_listing(id="bad", price=600_000, sqft=1000, listed_date=date(2026, 6, 1))
    ranked = sort_by_score(score_listings([bad, good], 400_000, REFERENCE))
    assert [l.id for l in ranked] == ["good", "bad"]


# ---------- tied scores ----------


# Equal scores: the cheaper listing comes first
def test_tied_scores_cheaper_first(make_listing):
    expensive = ScoredListing(**make_listing(id="1", price=500_000).model_dump(), score=0.8)
    cheap = ScoredListing(**make_listing(id="2", price=400_000).model_dump(), score=0.8)
    assert [l.id for l in sort_by_score([expensive, cheap])] == ["2", "1"]


# Equal score and price: ordered by source, then id, whatever the input order
def test_tied_scores_and_price_are_deterministic(make_listing):
    a = make_listing(id="A1", source="MLS_A")
    b = make_listing(id="B1", source="MLS_B")
    first = sort_by_score(score_listings([a, b], 400_000, REFERENCE))
    second = sort_by_score(score_listings([b, a], 400_000, REFERENCE))
    assert first[0].score == first[1].score
    assert [l.id for l in first] == [l.id for l in second] == ["A1", "B1"]


# ---------- pagination ----------


# First page, a full middle page and a partial last page
def test_paginate_boundaries():
    items = list(range(12))
    assert paginate(items, 1, 5) == ([0, 1, 2, 3, 4], 3)
    assert paginate(items, 2, 5) == ([5, 6, 7, 8, 9], 3)
    assert paginate(items, 3, 5) == ([10, 11], 3)


# A page size larger than the total gives a single page with everything
def test_paginate_page_size_larger_than_total():
    assert paginate([1, 2, 3], 1, 100) == ([1, 2, 3], 1)


# An exact multiple does not create an empty extra page
def test_paginate_exact_multiple():
    assert paginate(list(range(10)), 2, 5) == ([5, 6, 7, 8, 9], 2)


# No items means zero pages (the API turns this into an empty 200, not an error)
def test_paginate_empty():
    assert paginate([], 1, 5) == ([], 0)
