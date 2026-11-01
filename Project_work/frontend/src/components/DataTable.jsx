/**
 * DataTable — renders a two-dimensional array as a styled table.
 *
 * Props
 *   columns         string[]        header labels (first is usually row-label col)
 *   rows            any[][]         row data (first element used as row header)
 *   highlightZeros  boolean         highlight non-zero numeric cells (allocations)
 *   cellFormatter   (v) => string   optional custom formatter
 *   restrictedCells array<[r,c]>    forbidden (restricted) routes to hatch, in
 *                                   matrix coords (c is the data column index)
 */
function DataTable({ columns, rows, highlightZeros, cellFormatter, restrictedCells }) {
  const fmt = (v) =>
    Number(v).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })

  const isRestricted = (r, c) =>
    restrictedCells && restrictedCells.some(([rr, cc]) => rr === r && cc === c)

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} className={i === 0 ? 'col-header' : ''}>
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => {
                const isAllocated =
                  highlightZeros && typeof cell === 'number' && cell !== 0 && j > 0
                const restricted = isRestricted(i, j - 1)
                const cellClass = isAllocated
                  ? 'allocated'
                  : restricted
                    ? 'cell-restricted'
                    : j === 0
                      ? 'row-header'
                      : ''
                return (
                  <td key={j} className={cellClass}>
                    {restricted && (
                      <span className="restricted-flag" role="img" aria-label="restricted">🚫</span>
                    )}
                    {cellFormatter
                      ? cellFormatter(cell)
                      : typeof cell === 'number'
                        ? fmt(cell)
                        : cell}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default DataTable
