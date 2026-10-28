import { useEffect, useState } from 'react'
import './App.css'
import BudgetFilter from './components/BudgetFilter'
import CityFilter from './components/CityFilter'
import ColumnFilter from './components/ColumnFilter'
import DescriptionFilter from './components/DescriptionFilter'
import PageSizeSelect from './components/PageSizeSelect'
import Pagination from './components/Pagination'

const PAGE_SIZE_OPTIONS = [5, 10, 20]
const SERVER_ERROR = 'Could not reach the server. Please check that it is running and try again.'
const COLUMN_COUNT = 8
const NO_SORT = { by: null, order: null }

const EMPTY_FILTERS = {
  keyword: '',
  city: '',
  targetBudget: '',
  minPrice: '',
  maxPrice: '',
  minBedrooms: '',
  maxBedrooms: '',
}

const priceFormat = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

// Turns a FastAPI error body into a readable message.
// "detail" is a string for our own HTTPException and a list for automatic validation errors.
function errorMessage(body, status) {
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join('; ')
  }
  return `Error ${status}`
}

// Creates an error for problems the user can't fix by changing the filters
// (server down, server crash). These errors show a Retry button.
function serverError() {
  const err = new Error(SERVER_ERROR)
  err.canRetry = true
  return err
}

// Reads the response body as JSON, or returns null if it is not JSON
// (for example the empty 500 the dev proxy returns when the backend is down)
async function readJson(res) {
  try {
    return await res.json()
  } catch {
    return null
  }
}

// Builds the query string for /api/listings, skipping the empty filters
function buildParams(filters, sort, page, pageSize) {
  const params = new URLSearchParams({ page, pageSize })
  for (const [name, value] of Object.entries(filters)) {
    if (value.trim()) params.set(name, value.trim())
  }
  if (sort.by) {
    params.set('sortBy', sort.by)
    params.set('order', sort.order)
  }
  return params
}

// Main page: holds the search state, fetches the current page and renders the table
function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [sort, setSort] = useState(NO_SORT)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0])
  const [cities, setCities] = useState([])
  const [citiesFailed, setCitiesFailed] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  // Loads the list of cities to fill the selector, when the page opens and on Retry
  useEffect(() => {
    fetch('/api/cities')
      .then((res) => {
        if (!res.ok) throw serverError()
        return res.json()
      })
      .then((list) => {
        setCities(list)
        setCitiesFailed(false)
      })
      .catch(() => setCitiesFailed(true))
  }, [retryCount])

  // Fetches the listings every time the filters, the sort, the page or the page size change.
  // retryCount is also a dependency so the Retry button can repeat the same request.
  useEffect(() => {
    const controller = new AbortController()

    setLoading(true)
    setError(null)

    fetch(`/api/listings?${buildParams(filters, sort, page, pageSize)}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        const body = await readJson(res)
        if (res.ok && body) return body
        if (res.status >= 500 || !body) throw serverError()
        throw new Error(errorMessage(body, res.status))
      })
      .then(setData)
      .catch((err) => {
        if (err.name === 'AbortError') return
        // fetch itself rejects with a TypeError when the network or server is unreachable
        const failure = err instanceof TypeError ? serverError() : err
        setError({ message: failure.message, canRetry: Boolean(failure.canRetry) })
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    // Cancels this request if a new search starts before it finishes
    return () => controller.abort()
  }, [filters, sort, page, pageSize, retryCount])

  // Changes one filter, keeps the others, and goes back to the first page
  function updateFilter(name, value) {
    setFilters((prev) => ({ ...prev, [name]: value }))
    setPage(1)
  }

  // Sets the column to sort by (only one at a time) and goes back to the first page.
  // An empty order turns sorting off and restores the original JSON order.
  function updateSort(by, order) {
    setSort(order ? { by, order } : NO_SORT)
    setPage(1)
  }

  // Resets every filter and the sort, so the table shows the original JSON again
  function clearFilters() {
    setFilters(EMPTY_FILTERS)
    setSort(NO_SORT)
    setPage(1)
  }

  // Changes how many results are shown per page and goes back to the first page
  function updatePageSize(size) {
    setPageSize(size)
    setPage(1)
  }

  // Repeats the last request after a server error
  function retry() {
    setRetryCount((n) => n + 1)
  }

  const hasActiveFilters =
    Object.values(filters).some((v) => v.trim() !== '') || sort.by !== null

  // Decides what goes in the table body: an error, loading, no results, or the rows
  function renderRows() {
    if (error) {
      return (
        <tr>
          <td colSpan={COLUMN_COUNT} className="status error">
            Could not load listings: {error.message}
            {error.canRetry && (
              <button type="button" className="retry-button" onClick={retry}>
                Retry
              </button>
            )}
          </td>
        </tr>
      )
    }
    if (!data) {
      return (
        <tr>
          <td colSpan={COLUMN_COUNT} className="status">Loading…</td>
        </tr>
      )
    }
    if (data.items.length === 0) {
      return (
        <tr>
          <td colSpan={COLUMN_COUNT} className="status">No listings match your filters.</td>
        </tr>
      )
    }
    return data.items.map((l) => (
      <tr key={`${l.source}:${l.id}`}>
        <td>{l.address}</td>
        <td>{l.description}</td>
        <td className="num">{l.bedrooms}</td>
        <td className="num">{l.bathrooms}</td>
        <td className="num">{l.sqft.toLocaleString('en-US')}</td>
        <td>{l.city}</td>
        <td className="num">{priceFormat.format(l.price)}</td>
        <td className="num">{l.score === null ? '—' : l.score.toFixed(3)}</td>
      </tr>
    ))
  }

  return (
    <main>
      <h1>Listings Properties</h1>

      <DescriptionFilter
        value={filters.keyword}
        onChange={(v) => updateFilter('keyword', v)}
      />

      <BudgetFilter
        value={filters.targetBudget}
        onChange={(v) => updateFilter('targetBudget', v)}
      />

      <div className="toolbar">
        <p className="summary">
          {data && !error && `${data.total} results`} {loading && '· updating…'}
        </p>
        <div className="toolbar-actions">
          <PageSizeSelect value={pageSize} options={PAGE_SIZE_OPTIONS} onChange={updatePageSize} />
          <button
            type="button"
            className="clear-button"
            onClick={clearFilters}
            disabled={!hasActiveFilters}
          >
            Clear filters
          </button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Address</th>
            <th>Description</th>
            <ColumnFilter
              label="Bedrooms"
              min={filters.minBedrooms}
              max={filters.maxBedrooms}
              onMinChange={(v) => updateFilter('minBedrooms', v)}
              onMaxChange={(v) => updateFilter('maxBedrooms', v)}
              order={sort.by === 'bedrooms' ? sort.order : null}
              onOrderChange={(o) => updateSort('bedrooms', o)}
            />
            <th>Bathrooms</th>
            <th>Sqft</th>
            <CityFilter
              value={filters.city}
              cities={cities}
              unavailable={citiesFailed}
              onChange={(v) => updateFilter('city', v)}
            />
            <ColumnFilter
              label="Price"
              min={filters.minPrice}
              max={filters.maxPrice}
              onMinChange={(v) => updateFilter('minPrice', v)}
              onMaxChange={(v) => updateFilter('maxPrice', v)}
              order={sort.by === 'price' ? sort.order : null}
              onOrderChange={(o) => updateSort('price', o)}
            />
            <th className="score-header" title="Relevance to your target budget">
              Score
            </th>
          </tr>
        </thead>
        <tbody>{renderRows()}</tbody>
      </table>

      {data && !error && (
        <Pagination page={data.page} totalPages={data.totalPages} onPageChange={setPage} />
      )}
    </main>
  )
}

export default App
