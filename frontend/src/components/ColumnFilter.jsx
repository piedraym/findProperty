// Table header cell with a title, sort arrows and min/max inputs.
// It is controlled: the values come from the parent and every change is reported back.
// Used for both the Price and Bedrooms columns.
function ColumnFilter({ label, min, max, onMinChange, onMaxChange, order, onOrderChange }) {
  // Activates a sort direction, or turns it off if it was already active
  function toggle(direction) {
    onOrderChange(order === direction ? null : direction)
  }

  return (
    <th className="column-filter">
      <div className="column-title">
        <span>{label}</span>
        <button
          type="button"
          className={order === 'asc' ? 'active' : ''}
          onClick={() => toggle('asc')}
          title="Low to high"
        >
          ↑
        </button>
        <button
          type="button"
          className={order === 'desc' ? 'active' : ''}
          onClick={() => toggle('desc')}
          title="High to low"
        >
          ↓
        </button>
      </div>
      <div className="column-range">
        <input
          type="number"
          min="0"
          placeholder="Min"
          aria-label={`Minimum ${label}`}
          value={min}
          onChange={(e) => onMinChange(e.target.value)}
        />
        <input
          type="number"
          min="0"
          placeholder="Max"
          aria-label={`Maximum ${label}`}
          value={max}
          onChange={(e) => onMaxChange(e.target.value)}
        />
      </div>
    </th>
  )
}

export default ColumnFilter
