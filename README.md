# findProperty

A small property search app. You can filter listings, rank them by relevance to a target budget, and page through the results.

- **Backend:** Python 3.11, FastAPI, Pydantic (managed with `uv`)
- **Frontend:** React 19 + Vite

## Running it locally

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js.

```bash
# Terminal 1 – API on http://localhost:8000
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 – UI on http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Interactive API docs are at http://localhost:8000/docs.

The Vite dev server proxies `/api/*` to the backend, so the frontend calls relative URLs and avoids CORS issues.

## Project structure

```
backend/
  data/sample_listings.json   sample dataset
  app/
    models.py    Pydantic models (Listing, ScoredListing, SearchResponse)
    data.py      loads and validates the JSON once at startup
    search.py    pure functions: filtering, scoring, sorting, pagination
    main.py      FastAPI endpoints and input validation
frontend/src/
  App.jsx        search state, data fetching, results table
  components/    DescriptionFilter, BudgetFilter, ColumnFilter, CityFilter, Pagination
```

`search.py` has no FastAPI code in it, so the search logic can be read and tested apart from the HTTP layer.

## API

### `GET /api/listings`

| Parameter | Type | Description |
|---|---|---|
| `keyword` | string | Case-insensitive substring match against `description` |
| `city` | string | Exact city match, ignoring case and extra spaces |
| `minPrice`, `maxPrice` | number ≥ 0 | Price range (USD) |
| `minBedrooms`, `maxBedrooms` | integer ≥ 0 | Bedroom range |
| `targetBudget` | number > 0 | Turns on relevance scoring (see below) |
| `sortBy` | `price` \| `bedrooms` | Explicit sort column |
| `order` | `asc` \| `desc` | Sort direction (default `asc`) |
| `page` | integer ≥ 1 | Default `1` |
| `pageSize` | integer 1–100 | Default `5` |

Response:

```json
{
  "items": [{ "id": "A6", "source": "MLS_A", "address": "...", "price": 415000, "score": 0.873, "...": "..." }],
  "page": 1,
  "pageSize": 5,
  "total": 12,
  "totalPages": 3
}
```

Each request runs this pipeline: **filter → score → sort → paginate**. Sorting happens on the full filtered set, before the page is cut, so page 1 always holds the top results overall.

Ordering rules:
1. If `sortBy` is given, it wins.
2. Otherwise, if `targetBudget` is given, results are sorted by relevance score, highest first.
3. Otherwise, listings keep their original order from the JSON.

### `GET /api/cities`

Returns the distinct cities in the dataset, sorted alphabetically. The UI uses this list to fill the city dropdown.

## Relevance scoring

The scoring only runs when the user enters a `targetBudget`. It answers this question: *"Given this budget, which listings are most worth looking at?"*

```
score = (0.50 × budget + 0.25 × space + 0.25 × recency) × status
```

Each component is between 0 and 1, so the final score is too.

### 1. Budget fit (50%)

```
under or at budget:  1 − |price − budget| / budget
over budget:         1 − 2 × |price − budget| / budget      (floored at 0)
```

- It uses **relative** difference, because $50k matters much more on a $200k budget than on a $2M one.
- It is **asymmetric**: going over budget costs twice as much as coming in under it. A listing 10% under budget scores 0.90; one 10% over scores 0.80. The budget is what the user can afford, so a cheaper home is still an option and a more expensive one may not be.
- It has the largest weight because it is the only signal the user states directly.

### 2. Space for the money (25%)

```
space = best price-per-sqft in the results / this listing's price-per-sqft
```

The listing with the lowest $/sqft among the current results scores 1.

I first tried rewarding raw square footage. That backfired: bigger homes are also more expensive, so raw sqft pulled the ranking towards listings well over budget. In one test, a home 22% over budget ranked first only because it was the largest. Price per sqft rewards *value*, so a large, cheap home rises and a large, expensive one doesn't jump the queue.

### 3. Recency (25%)

```
recency = 0.5 ^ (days since listed / 30)
```

This is a half-life decay: a listing is worth 1.0 on the reference date, 0.5 after 30 days and 0.25 after 60. It never reaches zero, so older listings still rank among themselves. New listings are more likely to be available, and listings that sit on the market for a long time are often less attractive.

- **Reference date:** days are counted from the **newest listing in the dataset**, not from today. With static sample data, "today" would make every listing look equally old and recency would stop mattering.
- **Why 30 days and not 14:** I started with 14. Recency then had so much weight that, with a $430k budget, a $415k / 1,600 sqft home (closest to budget and best value) ranked third, behind a $470k home that was simply newer. With 30 days, recency still breaks ties without overpowering price and space.

### 4. Status multiplier

| Status | Effect |
|---|---|
| `active` | × 1.0 |
| `pending` | × 0.5. The deal may still fall through, but the listing is less likely to be available |
| `sold` | Excluded from all results. It can't be bought, so it is never relevant |

### Example ($430k budget)

| Listing | Price | Sqft | Listed | Score |
|---|---|---|---|---|
| 300 Cedar Blvd | $415,000 | 1,600 | 25 days before newest | **0.873** |
| 55 Elm Ct | $470,000 | 1,300 | newest | 0.836 |
| 789 Pine Rd | $399,000 | 850 | 3 days before newest | 0.835 |

All weights and constants are defined at the top of `backend/app/search.py`, so they are easy to tune.

## Input validation

Invalid input returns a **422** with a clear message, never a crash or a silently wrong result.

| Input | Response |
|---|---|
| `minPrice > maxPrice` or `minBedrooms > maxBedrooms` | `422`, for example: `minPrice cannot be greater than maxPrice` |
| `pageSize ≤ 0`, `page ≤ 0`, negative prices, non-numeric values | `422` from FastAPI's built-in validation |
| `targetBudget ≤ 0` | `422` (a zero budget would also mean dividing by zero) |
| `sortBy` / `order` outside the allowed values | `422` |
| A city that doesn't exist in the data | `422`: `Unknown city 'X'` |
| `page` beyond the last page | `422`: `page N is out of range (total pages: M)` |
| Valid filters that match nothing | `200` with `items: []` and `total: 0` |

The last two rows mark a deliberate line. An **unknown city** is a mistake in the input. A **valid combination that happens to match nothing** (e.g. Reston with 5+ bedrooms) is a legitimate empty result. The UI shows these differently: an error message in the first case, "No listings match your filters" in the second.

The frontend reads both error shapes FastAPI returns (a string `detail` from our own checks, a list from automatic validation) and turns them into a readable message.

## Frontend notes

- **Filters live in the table header** (min/max and sort arrows for Price and Bedrooms, a dropdown for City), plus a description search box and a target budget input above the table.
- **Only one sort column is active at a time.** Clicking an active arrow again turns sorting off.
- **The table is always rendered.** Loading, error and empty states appear as a full-width row inside the table body. This way the filters in the header stay visible and the user can always correct their search.
- **Stale responses are discarded.** Each search cancels the previous in-flight request with an `AbortController`, so fast typing never shows results for an older query.
- **Any filter change resets to page 1**, so the user never lands on a page that no longer exists.
- **"Clear filters"** resets every filter and the sort back to the original JSON order.

## Data handling

- Listings are validated with Pydantic when the server starts. A malformed record fails loudly instead of causing errors later.
- The unique key is `source + id`, because `id` is only unique per source. It is also the React row key.
- City names are normalized (case and whitespace) for filtering and for building the dropdown, because sources may spell them slightly differently.

## Known limitations and next steps

- **Cross-source duplicates are not merged.** For example, `MLS_A/A1` "123 Main St, Apt 4B" and `MLS_B/B7` "123 Main Street, Unit 4B" are the same unit, with slightly different prices. Merging them would need address normalization (St/Street, Apt/Unit) plus a location check using latitude/longitude.
- **Every keystroke triggers a request.** Stale requests are cancelled, but debouncing the inputs would cut the number of calls.
- **No automated tests yet.** The scoring and filter functions in `search.py` are pure and would be simple to unit-test.
- **Data is held in memory.** That is fine for a small sample dataset; a real feed would need a database with indexed filters.
# findProperty
