import { useEffect, useState } from 'react'
import './App.css'
import BudgetFilter from './components/BudgetFilter'
import CityFilter from './components/CityFilter'
import ColumnFilter from './components/ColumnFilter'
import DescriptionFilter from './components/DescriptionFilter'
import Pagination from './components/Pagination'

const PAGE_SIZE = 5
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

// Builds the query string for /api/listings, skipping the empty filters
function buildParams(filters, sort, page) {
  const params = new URLSearchParams({ page, pageSize: PAGE_SIZE })
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
  const [cities, setCities] = useState([])
 

  // Loads the list of cities once, when the page opens, to fill the selector
  useEffect(() => {
    fetch('/api/cities')
      .then((res) => (res.ok ? res.json() : []))
      .then(setCities)
      .catch(() => setCities([]))
  }, [])

  // Fetches the listings every time the filters, the sort or the page change
  useEffect(() => {
    const controller = new AbortController()

    setLoading(true)
    setError(null)

    fetch(`/api/listings?${buildParams(filters, sort, page)}`, { signal: controller.signal })
      .then(async (res) => {
        const body = await res.json()
        if (!res.ok) throw new Error(errorMessage(body, res.status))
        return body
      })
      .then(setData)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    // Cancels this request if a new search starts before it finishes
    return () => controller.abort()
  }, [filters, sort, page])

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

  const hasActiveFilters =
    Object.values(filters).some((v) => v.trim() !== '') || sort.by !== null

  // Decides what goes in the table body: an error, loading, no results, or the rows
  function renderRows() {
    if (error) {
      return (
        <tr>
          <td colSpan={COLUMN_COUNT} className="status error">Could not load listings: {error}</td>
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
        <button
          type="button"
          className="clear-button"
          onClick={clearFilters}
          disabled={!hasActiveFilters}
        >
          Clear filters
        </button>
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
