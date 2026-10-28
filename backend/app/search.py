import math
from datetime import date

from app.models import Listing, ScoredListing

# Relevance scoring settings (see score_listings)
BUDGET_WEIGHT = 0.50
SPACE_WEIGHT = 0.25
RECENCY_WEIGHT = 0.25
OVER_BUDGET_PENALTY = 2
RECENCY_HALF_LIFE_DAYS = 30
STATUS_FACTOR = {"active": 1.0, "pending": 0.5}


# Cleans text for comparisons: lowercase and single spaces
def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


# Keeps only the listings whose description contains the keyword
def filter_by_keyword(listings: list[Listing], keyword: str | None) -> list[Listing]:
    if not keyword or not keyword.strip():
        return listings
    term = normalize(keyword)
    return [l for l in listings if term in normalize(l.description)]


# Returns one page of items and the total number of pages
def paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total_pages = math.ceil(len(items) / page_size)
    start = (page - 1) * page_size
    return items[start : start + page_size], total_pages


# Keeps the listings whose field (e.g. "price") is between min and max.
# Works for any numeric field; a None limit means "no limit".
def filter_by_range(
    listings: list[Listing],
    field: str,
    min_value: float | None,
    max_value: float | None,
) -> list[Listing]:
    return [
        l
        for l in listings
        if (min_value is None or getattr(l, field) >= min_value)
        and (max_value is None or getattr(l, field) <= max_value)
    ]


# Sorts the listings by a field, ascending or descending.
# If no field is given, keeps the original JSON order.
def sort_listings(
    listings: list[Listing], sort_by: str | None, order: str
) -> list[Listing]:
    if sort_by is None:
        return listings
    return sorted(
        listings, key=lambda l: getattr(l, sort_by), reverse=(order == "desc")
    )


# Keeps only the listings from the given city.
# The comparison ignores case and extra spaces, because sources may write it differently.
def filter_by_city(listings: list[Listing], city: str | None) -> list[Listing]:
    if not city or not city.strip():
        return listings
    target = normalize(city)
    return [l for l in listings if normalize(l.city) == target]


# Returns the list of distinct cities, sorted alphabetically.
# Cities that only differ in case or spaces count as one; the first spelling found is kept.
def unique_cities(listings: list[Listing]) -> list[str]:
    cities: dict[str, str] = {}
    for l in listings:
        cities.setdefault(normalize(l.city), l.city.strip())
    return sorted(cities.values())


# Removes the sold listings: they can no longer be bought, so they are never shown
def exclude_sold(listings: list[Listing]) -> list[Listing]:
    return [l for l in listings if l.status != "sold"]


# How close the price is to the target budget, from 0 to 1.
# Being under budget loses 1 point per 100% of difference; being over budget
# loses twice as much, because the user may not be able to afford it.
def budget_score(price: float, budget: float) -> float:
    difference = abs(price - budget) / budget
    if price > budget:
        difference *= OVER_BUDGET_PENALTY
    return max(0.0, 1 - difference)


# How much space the listing gives for its price, from 0 to 1.
# The listing with the best (lowest) price per sqft in the results gets 1.
def space_score(listing: Listing, best_price_per_sqft: float) -> float:
    if listing.sqft <= 0 or listing.price <= 0 or best_price_per_sqft <= 0:
        return 0.0
    return best_price_per_sqft / (listing.price / listing.sqft)


# How recent the listing is, from 0 to 1, using a half-life:
# it is worth 1 on the reference date and loses half its value every 30 days.
def recency_score(listed: date, reference: date) -> float:
    days = max(0, (reference - listed).days)
    return 0.5 ** (days / RECENCY_HALF_LIFE_DAYS)


# Adds the relevance score to every listing:
#   score = (0.50 * budget + 0.25 * space + 0.25 * recency) * status factor
# Without a budget there is nothing to compare with, so the score stays None.
def score_listings(
    listings: list[Listing], budget: float | None, reference: date
) -> list[ScoredListing]:
    if budget is None:
        return [ScoredListing(**l.model_dump()) for l in listings]

    prices_per_sqft = [l.price / l.sqft for l in listings if l.sqft > 0 and l.price > 0]
    best_price_per_sqft = min(prices_per_sqft, default=0.0)

    scored = []
    for l in listings:
        relevance = (
            BUDGET_WEIGHT * budget_score(l.price, budget)
            + SPACE_WEIGHT * space_score(l, best_price_per_sqft)
            + RECENCY_WEIGHT * recency_score(l.listed_date, reference)
        ) * STATUS_FACTOR.get(l.status, 0.0)
        scored.append(ScoredListing(**l.model_dump(), score=round(relevance, 3)))
    return scored


# Sorts by relevance score, highest first. Ties keep their previous order.
def sort_by_score(listings: list[ScoredListing]) -> list[ScoredListing]:
    return sorted(listings, key=lambda l: -(l.score or 0))
