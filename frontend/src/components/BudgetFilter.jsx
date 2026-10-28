// Number input for the user's target budget.
// It does not remove listings: it is used to rank them by relevance score.
// Controlled: receives the value and tells the parent when it changes.
function BudgetFilter({ value, onChange }) {
  return (
    <div className="budget-filter">
      <label htmlFor="budget-filter">Target budget (USD)</label>
      <input
        id="budget-filter"
        type="number"
        min="1"
        placeholder="e.g. 500000"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

export default BudgetFilter
