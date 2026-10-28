// Table header cell with a dropdown to filter by city.
// Controlled: the parent passes the selected city and the list of options.
// The empty option ("All cities") means no city filter.
function CityFilter({ value, cities, onChange }) {
  return (
    <th className="column-filter">
      <div className="column-title">
        <span>City</span>
      </div>
      <select
        className="city-select"
        aria-label="Filter by city"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={cities.length === 0}
      >
        <option value="">All cities</option>
        {cities.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </th>
  )
}

export default CityFilter
