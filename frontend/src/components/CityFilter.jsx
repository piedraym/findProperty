// Table header cell with a dropdown to filter by city.
// Controlled: the parent passes the selected city and the list of options.
// The empty option ("All cities") means no city filter.
// If the list could not be loaded, the dropdown is disabled and says so.
function CityFilter({ value, cities, unavailable, onChange }) {
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
        <option value="">{unavailable ? 'Cities unavailable' : 'All cities'}</option>
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
