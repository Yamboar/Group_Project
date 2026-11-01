/**
 * EditableMatrix — an interactive cost-matrix input grid.
 *
 * Props
 *   values             string[][]          cell values (from <input>)
 *   restricted         boolean[][]         forbidden-route mask (same shape)
 *   onToggleRestricted (r, c) => void      mark/unmark a cell as Restricted
 *   cornerLabel        string              label for the top-left corner cell
 *   relationNoun       string              noun describing a forbidden pairing
 *                                          ("route", "assignment", …)
 */
function EditableMatrix({
  rowNames, colNames, values, onChange, restricted, onToggleRestricted,
  cornerLabel = 'Sources / Destinations', relationNoun = 'route',
}) {
  const handleChange = (r, c, value) => {
    const next = values.map((row, i) =>
      i === r ? row.map((v, j) => (j === c ? value : v)) : row,
    )
    onChange(next)
  }

  const isRestricted = (r, c) => Boolean(restricted?.[r]?.[c])

  return (
    <>
      <div className="table-wrapper">
        <table className="data-table matrix-input">
          <thead>
            <tr>
              <th className="col-header" style={{ fontSize: '0.72rem', color: 'var(--gray-400)' }}>
                ↓ {cornerLabel} →
              </th>
              {colNames.map((name, j) => (
                <th key={j}>{name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowNames.map((rname, r) => (
              <tr key={r}>
                <td className="row-header">{rname}</td>
                {colNames.map((_, c) => {
                  const restrictedCell = isRestricted(r, c)
                  return (
                    <td key={c} style={{ padding: '0.3rem 0.4rem' }}>
                      <div className="matrix-cell">
                        <input
                          type="number"
                          step="any"
                          className={restrictedCell ? 'restricted-input' : ''}
                          value={restrictedCell ? '' : values[r][c]}
                          placeholder={restrictedCell ? '—' : ''}
                          disabled={restrictedCell}
                          onChange={(e) => handleChange(r, c, e.target.value)}
                          aria-label={`Cost from ${rname} to ${colNames[c]}`}
                        />
                        <button
                          type="button"
                          className={`matrix-toggle ${restrictedCell ? 'active' : ''}`}
                          onClick={() => onToggleRestricted && onToggleRestricted(r, c)}
                          title={
                            restrictedCell
                              ? `Allow ${relationNoun} ${rname} → ${colNames[c]} again`
                              : `Forbid ${relationNoun} ${rname} → ${colNames[c]} (Restricted)`
                          }
                          aria-label={
                            restrictedCell
                              ? `Unrestrict ${relationNoun} from ${rname} to ${colNames[c]}`
                              : `Restrict ${relationNoun} from ${rname} to ${colNames[c]}`
                          }
                          aria-pressed={restrictedCell}
                        >
                          🚫
                        </button>
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {onToggleRestricted && (
        <span className="cell-hint">
          💡 <strong>0 is a valid cost</strong> — it is never treated as blank. To forbid a {relationNoun},
          click its 🚫 so the cell turns <strong>Restricted</strong> (hatched); that {relationNoun} is
          excluded from every method. Blank or negative values are not allowed — mark them
          Restricted instead.
        </span>
      )}
    </>
  )
}

export default EditableMatrix