// Text box to search inside the listing descriptions.
// Controlled: receives the text and tells the parent when it changes.
function DescriptionFilter({ value, onChange }) {
  return (
    <div className="filter">
      <label htmlFor="description-filter">Search in description</label>
      <textarea
        id="description-filter"
        rows={2}
        placeholder="e.g. pet friendly, pool, renovated…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

export default DescriptionFilter
