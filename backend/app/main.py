from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data import load_listings
from app.models import SearchResponse
from app.search import (
    exclude_sold,
    filter_by_city,
    filter_by_keyword,
    filter_by_range,
    normalize,
    paginate,
    score_listings,
    sort_by_score,
    sort_listings,
    unique_cities,
)

app = FastAPI(title="findProperty API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# load the list (sold listings are never shown)
ALL_LISTINGS = load_listings()
LISTINGS = exclude_sold(ALL_LISTINGS)
# Recency is measured from the newest listing, not from today,
# so old sample data does not make every listing look equally stale
REFERENCE_DATE = max(l.listed_date for l in ALL_LISTINGS)
CITIES = unique_cities(LISTINGS)
KNOWN_CITIES = {normalize(c) for c in CITIES}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Returns the cities that appear in the listings, to fill the city selector
@app.get("/api/cities", response_model=list[str])
def get_cities():
    return CITIES


# Returns a 422 error if the minimum of a range is greater than the maximum
def check_range(name: str, min_value: float | None, max_value: float | None) -> None:
    if min_value is not None and max_value is not None and min_value > max_value:
        raise HTTPException(422, f"min{name} cannot be greater than max{name}")


# Returns a 422 error if the city does not exist in the listings
def check_city(city: str | None) -> None:
    if city and city.strip() and normalize(city) not in KNOWN_CITIES:
        raise HTTPException(422, f"Unknown city '{city}'")


# Searches the listings: filters, scores, sorts and returns the requested page.
# With no parameters it returns the listings in the original JSON order.
# With a targetBudget it sorts by relevance score, unless a sort column is chosen.
@app.get("/api/listings", response_model=SearchResponse)
def get_listings(
    keyword: str | None = Query(None),
    city: str | None = Query(None),
    target_budget: float | None = Query(None, alias="targetBudget", gt=0),
    min_price: float | None = Query(None, alias="minPrice", ge=0),
    max_price: float | None = Query(None, alias="maxPrice", ge=0),
    min_bedrooms: int | None = Query(None, alias="minBedrooms", ge=0),
    max_bedrooms: int | None = Query(None, alias="maxBedrooms", ge=0),
    sort_by: Literal["price", "bedrooms"] | None = Query(None, alias="sortBy"),
    order: Literal["asc", "desc"] = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, alias="pageSize", ge=1, le=100),
):
    check_range("Price", min_price, max_price)
    check_range("Bedrooms", min_bedrooms, max_bedrooms)
    check_city(city)

    filtered = filter_by_keyword(LISTINGS, keyword)
    filtered = filter_by_city(filtered, city)
    filtered = filter_by_range(filtered, "price", min_price, max_price)
    filtered = filter_by_range(filtered, "bedrooms", min_bedrooms, max_bedrooms)
    scored = score_listings(filtered, target_budget, REFERENCE_DATE)
    if sort_by is not None:
        ordered = sort_listings(scored, sort_by, order)
    elif target_budget is not None:
        ordered = sort_by_score(scored)
    else:
        ordered = scored
    items, total_pages = paginate(ordered, page, page_size)

    if total_pages and page > total_pages:
        raise HTTPException(
            422, f"page {page} is out of range (total pages: {total_pages})"
        )

    return SearchResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=len(filtered),
        total_pages=total_pages,
    )
