// Previous / Next buttons and "Page X of Y".
// Hidden when there is only one page. The parent owns the current page.
function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  return (
    <nav className="pagination">
      <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
        ← Previous
      </button>
      <span>
        Page {page} of {totalPages}
      </span>
      <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
        Next →
      </button>
    </nav>
  )
}

export default Pagination
