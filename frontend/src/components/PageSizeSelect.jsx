// Dropdown to choose how many results are shown per page.
// Controlled: the parent owns the page size and the list of allowed options.
function PageSizeSelect({ value, options, onChange }) {
  return (
    <label className="page-size">
      Per page
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {options.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </label>
  )
}

export default PageSizeSelect
