import { useState } from 'react'
import EditableMatrix from '../components/EditableMatrix.jsx'
import DataTable from '../components/DataTable.jsx'
import ObjectiveSelector, { ObjectiveTrail } from '../components/ObjectiveSelector.jsx'
import { solveAssignment, explainAssignment } from '../api/client.js'
import { fmtUnit, withUnit, unitFor } from '../utils/units.js'

const fmt = (v) =>
  Number(v).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })

/* ───────── Main page ────────────────────────────── */
function Assignment() {
  const [tab, setTab] = useState('input')

  const [numRows,      setNumRows]      = useState(4)
  const [numCols,      setNumCols]      = useState(4)
  const [costMatrix,   setCostMatrix]   = useState(() =>
    Array.from({ length: 4 }, () => Array(4).fill(0)),
  )
  const [restrictedMask, setRestrictedMask] = useState(() =>
    Array.from({ length: 4 }, () => Array(4).fill(false)),
  )
  const [rowNamesInput, setRowNamesInput] = useState('')
  const [colNamesInput, setColNamesInput] = useState('')
  const [objective,    setObjective]    = useState(null)

  const problemType = objective?.intent === 'maximise' ? 'Maximization' : 'Minimization'

  const [result,      setResult]      = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')

  const defaultRowNames = Array.from({ length: numRows }, (_, i) => `Worker ${i+1}`)
  const defaultColNames = Array.from({ length: numCols }, (_, j) => `Job ${j+1}`)

  const parseNames = (str, defaults) => {
    const parsed = str.split(',').map((s) => s.trim()).filter(Boolean)
    return parsed.length === defaults.length ? parsed : defaults
  }

  const rowNames = parseNames(rowNamesInput, defaultRowNames)
  const colNames = parseNames(colNamesInput, defaultColNames)

  const changeNumRows = (val) => {
    const n = Math.min(20, Math.max(1, val))
    setNumRows(n)
    setCostMatrix((prev) => {
      const next = prev.slice(0, n)
      while (next.length < n) next.push(Array(numCols).fill(0))
      return next
    })
    setRestrictedMask((prev) => {
      const next = prev.slice(0, n)
      while (next.length < n) next.push(Array(numCols).fill(false))
      return next
    })
  }

  const changeNumCols = (val) => {
    const n = Math.min(20, Math.max(1, val))
    setNumCols(n)
    setCostMatrix((prev) =>
      prev.map((row) => {
        const next = row.slice(0, n)
        while (next.length < n) next.push(0)
        return next
      }),
    )
    setRestrictedMask((prev) =>
      prev.map((row) => {
        const next = row.slice(0, n)
        while (next.length < n) next.push(false)
        return next
      }),
    )
  }

  const toggleRestricted = (r, c) => {
    setRestrictedMask((prev) =>
      prev.map((row, i) =>
        i === r ? row.map((v, j) => (j === c ? !v : v)) : row,
      ),
    )
  }

  /* Cells that must be resolved before solving: blank or negative and not
     marked Restricted. Restricted cells may hold any placeholder value. */
  const invalidCells = []
  costMatrix.forEach((row, r) =>
    row.forEach((value, c) => {
      if (restrictedMask[r]?.[c]) return
      const s = String(value ?? '').trim()
      if (s === '' || (!Number.isNaN(Number(s)) && Number(s) < 0)) {
        invalidCells.push({ r, c })
      }
    }),
  )

  const markInvalidAsRestricted = () => {
    setRestrictedMask((prev) =>
      prev.map((row, r) =>
        row.map((v, c) => (invalidCells.some((ic) => ic.r === r && ic.c === c) ? true : v)),
      ),
    )
  }

  const handleSolve = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    setExplanation(null)

    if (invalidCells.length > 0) {
      setError(
        `${invalidCells.length} cell(s) are blank or negative, which is not allowed. ` +
        `Mark them as Restricted (click 🚫) or enter a valid cost of 0 or more.`,
      )
      setLoading(false)
      return
    }

    const restrictedCells = []
    costMatrix.forEach((row, r) =>
      row.forEach((_, c) => {
        if (restrictedMask[r]?.[c]) restrictedCells.push([r, c])
      }),
    )

    const payload = {
      cost_matrix:  costMatrix.map((row, r) =>
        row.map((v, c) => {
          if (restrictedMask[r]?.[c]) return null
          const s = String(v ?? '').trim()
          if (s === '' || Number.isNaN(Number(s))) return null
          return Number(v)
        }),
      ),
      problem_type: problemType,
      row_names:    rowNames,
      col_names:    colNames,
      restricted_cells: restrictedCells,
      objective,
    }

    try {
      const data = await solveAssignment(payload)
      setResult(data)
      try {
        const expl = await explainAssignment(payload)
        setExplanation(expl)
      } catch { /* optional */ }
      setTab('solution')
    } catch (err) {
      const detail = err.response?.data?.detail
      const status = err.response?.status
      let msg
      if (Array.isArray(detail?.errors)) {
        msg = detail.errors.join('; ')
      } else if (typeof detail === 'string') {
        msg = detail
      } else if (detail?.message) {
        msg = detail.message
      } else if (status === 500) {
        msg = 'Server error (500) — check that the backend is running and restart it.'
      } else if (!err.response) {
        msg = 'Cannot reach the backend. Make sure the FastAPI server is running on port 8000.'
      } else {
        msg = `Failed to solve the assignment problem. (HTTP ${status ?? 'unknown'})`
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Page header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '1.75rem' }}>📋</span>
          <h1 className="page-title">
            <span className="page-title-gradient">Assignment</span> Problem Solver
          </h1>
        </div>
        <p className="page-subtitle">
          Hungarian Method · Minimization &amp; Maximization · Rectangular Matrix Support
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'input',    label: '1 · Input',   icon: '📝' },
          { id: 'solution', label: '2 · Solution', icon: '✅' },
          { id: 'details',  label: '3 · Steps',    icon: '🔍' },
        ].map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ─── INPUT ─────────────────────────────────── */}
      {tab === 'input' && (
        <div className="tab-content">
          {/* Dimensions + type */}
          <div className="card">
            <div className="card-title">📐 Problem Setup</div>
            <div className="grid-2">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Workers / Resources</label>
                <input
                  type="number" className="form-control" min="1" max="20"
                  value={numRows}
                  onChange={(e) => changeNumRows(parseInt(e.target.value, 10) || 1)}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Jobs / Tasks</label>
                <input
                  type="number" className="form-control" min="1" max="20"
                  value={numCols}
                  onChange={(e) => changeNumCols(parseInt(e.target.value, 10) || 1)}
                />
              </div>
            </div>
          </div>

          {/* Objective selection */}
          <ObjectiveSelector mode="free" onChange={setObjective} />

          {/* Cost matrix */}
          <div className="card">
            <div className="card-title">
              {problemType === 'Minimization' ? '💰 Cost Matrix' : '🏆 Profit Matrix'}
            </div>
            <EditableMatrix
              rows={numRows} cols={numCols}
              rowNames={rowNames} colNames={colNames}
              values={costMatrix} onChange={setCostMatrix}
              restricted={restrictedMask} onToggleRestricted={toggleRestricted}
              cornerLabel="Workers / Jobs" relationNoun="assignment"
            />
            {invalidCells.length > 0 && (
              <div className="alert alert-warning" style={{ marginTop: '0.75rem' }}>
                <span className="alert-icon">🚫</span>
                <span>
                  <strong>{invalidCells.length} cell{invalidCells.length === 1 ? '' : 's'} is blank or negative</strong> — costs must be 0 or more.{' '}
                  {invalidCells
                    .map(({ r, c }) => `${rowNames[r] ?? `Worker ${r + 1}`} → ${colNames[c] ?? `Job ${c + 1}`}`)
                    .join(', ')}
                  .
                </span>
                <button
                  className="btn btn-sm btn-secondary"
                  style={{ marginLeft: '0.75rem' }}
                  onClick={markInvalidAsRestricted}
                >
                  🚫 Mark as Restricted{invalidCells.length > 1 ? ` (${invalidCells.length})` : ''}
                </button>
              </div>
            )}
          </div>

          {/* Custom names */}
          <div className="card">
            <div className="card-title">🏷️ Custom Labels (optional)</div>
            <div className="grid-2">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Row names (comma-separated)</label>
                <input
                  className="form-control"
                  value={rowNamesInput}
                  placeholder={defaultRowNames.join(', ')}
                  onChange={(e) => setRowNamesInput(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Column names (comma-separated)</label>
                <input
                  className="form-control"
                  value={colNamesInput}
                  placeholder={defaultColNames.join(', ')}
                  onChange={(e) => setColNamesInput(e.target.value)}
                />
              </div>
            </div>
          </div>

          {numRows !== numCols && (
            <div className="alert alert-warning">
              <span className="alert-icon">⚠️</span>
              Rectangular matrix ({numRows}×{numCols}): dummy{' '}
              {numRows < numCols ? 'rows' : 'columns'} will be added automatically.
            </div>
          )}

          {error && (
            <div className="alert alert-error">
              <span className="alert-icon">❌</span>{error}
            </div>
          )}

          <button
            className="btn btn-primary btn-block btn-lg"
            onClick={handleSolve}
            disabled={loading || invalidCells.length > 0}
            style={{ marginTop: '0.5rem' }}
          >
            {loading
              ? <><span className="spinner" /> Solving with Hungarian Method...</>
              : invalidCells.length > 0
                ? '🚫 Resolve invalid cells before solving'
                : '🧠  Solve Assignment Problem'}
          </button>
        </div>
      )}

      {/* ─── SOLUTION ──────────────────────────────── */}
      {tab === 'solution' && (
        <div className="tab-content">
          {loading ? (
            <div className="loading-box">
              <span className="spinner spinner-dark" /> Solving...
            </div>
          ) : !result ? (
            <div className="alert alert-info">
              <span className="alert-icon">ℹ️</span>
              Input your problem and click Solve to see results.
            </div>
          ) : (
            <SolutionView result={result} explanation={explanation} />
          )}
        </div>
      )}

      {/* ─── DETAILS ───────────────────────────────── */}
      {tab === 'details' && (
        <div className="tab-content">
          {loading ? (
            <div className="loading-box">
              <span className="spinner spinner-dark" /> Loading...
            </div>
          ) : !result ? (
            <div className="alert alert-info">
              <span className="alert-icon">ℹ️</span>
              Solve a problem first to see Hungarian Method steps.
            </div>
          ) : (
            <DetailsView result={result} />
          )}
        </div>
      )}
    </div>
  )
}

/* ───────── Solution view ────────────────────────── */
function SolutionView({ result, explanation }) {
  if (!result) return null

  if (!result.success) {
    return (
      <div className="alert alert-error">
        <span className="alert-icon">❌</span>
        {(result.errors || []).join('; ')}
      </div>
    )
  }

  const nonDummy = (result.result?.assignments || []).filter(
    (a) => !a.row_name?.startsWith('Dummy') && !a.col_name?.startsWith('Dummy'),
  )

  const obj = result.objective_selection
  const isMax = (obj?.resolved_direction || obj?.intent) === 'maximise'
  const fallback = isMax ? 'profit' : 'cost'
  const valueLabel = obj?.value_type === 'other'
    ? (obj?.other_description || fallback)
    : (obj?.value_type || fallback)
  const unit = unitFor(result.objective_selection)
  const restrictedCells = result.problem?.restricted_cells || []

  return (
    <div>
      {/* Objective selection */}
      <ObjectiveTrail objective={result.objective_selection} />

      {/* Restricted assignments */}
      {restrictedCells.length > 0 && (
        <div className="alert alert-warning">
          <span className="alert-icon">🚫</span>
          <strong>{restrictedCells.length} restricted assignment{restrictedCells.length === 1 ? '' : 's'}:</strong>{' '}
          {restrictedCells
            .map(([r, c]) => `${result.problem?.row_names?.[r] ?? `Worker ${r + 1}`} → ${result.problem?.col_names?.[c] ?? `Job ${c + 1}`}`)
            .join(', ')}
          <span style={{ marginLeft: '0.5rem' }}>— these cells are forbidden and never assigned.</span>
        </div>
      )}

      {/* Cost highlight */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: '1.5rem' }}>
        <div className="stat-card stat-card-purple" style={{ gridColumn: '1 / 2' }}>
          <div className="stat-icon">🏆</div>
          <div className="stat-value gradient">{fmtUnit(result.final_cost, unit)}</div>
          <div className="stat-label">Optimal Total {valueLabel[0].toUpperCase() + valueLabel.slice(1)}</div>
        </div>
        <div className="stat-card stat-card-blue">
          <div className="stat-icon">👥</div>
          <div className="stat-value">{nonDummy.length}</div>
          <div className="stat-label">Assignments Made</div>
        </div>
        <div className="stat-card stat-card-green">
          <div className="stat-icon">✅</div>
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {result.verification?.passed ? 'Passed' : 'Failed'}
          </div>
          <div className="stat-label">Verification</div>
        </div>
      </div>

      {/* Assignment table */}
      {nonDummy.length > 0 && (
        <>
          <div className="section-divider">Optimal Assignment</div>
          <DataTable
            columns={['#', 'Worker / Resource', 'Job / Task', valueLabel[0].toUpperCase() + valueLabel.slice(1)]}
            rows={nonDummy.map((a, i) => [
              i + 1,
              a.row_name,
              a.col_name,
              withUnit(fmt(a.original_cost), unit),
            ])}
          />
        </>
      )}

      {/* All optimal plans */}
      {(result.number_of_optimal_assignments || 0) > 1 && (
        <AllOptimalPlans
          count={result.number_of_optimal_assignments}
          plans={result.all_optimal_assignments || []}
          truncated={result.optimal_assignments_truncated}
          problem={result.problem}
        />
      )}

      {/* Verification */}
      {result.verification && (
        result.verification.passed ? (
          <div className="alert alert-success">
            <span className="alert-icon">✔️</span>
            Valid one-to-one assignment — each worker assigned to exactly one unique job.
          </div>
        ) : (
          <div className="alert alert-error">
            <span className="alert-icon">❌</span>
            Verification failed: {(result.verification.issues || []).join('; ')}
          </div>
        )
      )}

      {/* XAI */}
      <div className="section-divider">XAI Explanations</div>
      {explanation ? (
        <>
          <div className="card card-teal">
            <div className="card-title">💬 Summary</div>
            <p style={{ fontSize: '0.9rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
              {explanation.summary}
            </p>
          </div>

          {explanation.key_decisions?.length > 0 && (
            <div className="expander">
              <details>
                <summary className="expander-header">📌 Assignment Details</summary>
                <div className="expander-body">
                  <ul>
                    {explanation.key_decisions.map((d, i) => (
                      <li key={i} style={{ marginBottom: '0.4rem' }}>{d}</li>
                    ))}
                  </ul>
                </div>
              </details>
            </div>
          )}

          {explanation.optimality_reason && (
            <div className="expander">
              <details>
                <summary className="expander-header">🏆 Why is this optimal?</summary>
                <div className="expander-body">{explanation.optimality_reason}</div>
              </details>
            </div>
          )}
        </>
      ) : (
        <div className="alert alert-info">
          <span className="alert-icon">ℹ️</span>
          Re-solve to regenerate explanations.
        </div>
      )}

      {/* Plain-English interpretation */}
      <div className="section-divider">📝 Plain-English Interpretation</div>
      <PlainEnglishInterpretation result={result} />
    </div>
  )
}

/* ───────── All optimal plans ─────────────────────── */
function AllOptimalPlans({ count, plans, truncated, problem }) {
  const origRows = problem?.row_names || []
  const origCols = problem?.col_names || []
  const rowName = (r) => origRows[r] ?? `Row ${r + 1}`
  const colName = (c) => origCols[c] ?? `Col ${c + 1}`

  // Each plan covers the balanced matrix; present only the real assignments.
  const realAssigns = (plan) =>
    plan.filter(([r, c]) => r < origRows.length && c < origCols.length)

  return (
    <div className="expander">
      <details>
        <summary className="expander-header" style={{ color: 'var(--brand-green)' }}>
          🎯 {count} Optimal Plan{count === 1 ? '' : 's'}
          {truncated ? ' (showing first ' + plans.length + ')' : ''}
        </summary>
        <div className="expander-body">
          <p style={{ fontSize: '0.88rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
            Every plan below gives the same optimal total — pick whichever suits
            your situation best (e.g. avoid a particular pairing, or spread work
            differently). The trade-off is free: the total cost stays identical.
          </p>
          {truncated && (
            <div className="alert alert-warning" style={{ marginBottom: '0.75rem' }}>
              <span className="alert-icon">⚠️</span>
              Many alternative optimal plans exist; showing the first {plans.length}.
              The true count is reported in the summary above.
            </div>
          )}
          {plans.map((plan, i) => (
            <div key={i} style={{ marginBottom: '1rem' }}>
              <div
                className="badge"
                style={{ marginBottom: '0.4rem', fontStyle: 'normal', background: 'var(--brand-green)' }}
              >
                Plan {i + 1}
              </div>
              <DataTable
                columns={['#', 'Worker / Resource', 'Job / Task']}
                rows={realAssigns(plan).map(([r, c], j) => [j + 1, rowName(r), colName(c)])}
              />
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}

/* ───────── Plain-English interpretation ────────── */
function PlainEnglishInterpretation({ result }) {
  const assignments = (result.result?.assignments || []).filter(
    (a) => !a.row_name?.startsWith('Dummy') && !a.col_name?.startsWith('Dummy'),
  )
  const total = result.final_cost ?? result.result?.total_cost ?? 0

  if (assignments.length === 0) {
    return <div className="alert alert-info"><span className="alert-icon">ℹ️</span>No assignment available to interpret.</div>
  }

  const obj = result.objective_selection
  const direction = obj?.resolved_direction || obj?.intent || 'minimise'
  const isMax = direction === 'maximise'
  const fallback = isMax ? 'profit' : 'cost'
  const vt = obj?.value_type === 'other'
    ? (obj?.other_description || fallback)
    : (obj?.value_type || fallback)
  const verb = isMax ? 'maximise' : 'minimise'
  const unit = unitFor(result.objective_selection)

  const totalText = withUnit(fmt(total), unit)
  const assignText = assignments
    .map((a) => `assign ${a.row_name} to do ${a.col_name}`)
    .join(', and ')

  const pieces = assignments.map(
    (a, i) =>
      `${a.row_name} → ${a.col_name} (${vt} ${withUnit(fmt(a.original_cost), unit)})` +
      (i === assignments.length - 1 ? '.' : '; '),
  )

  return (
    <div className="card card-teal">
      <p style={{ fontSize: '0.92rem', color: 'var(--gray-800)', lineHeight: 1.85 }}>
        To achieve the best results — {verb} the total {vt} to <strong>{totalText}</strong> —
        {assignText}.
      </p>
      <p style={{ fontSize: '0.88rem', color: 'var(--gray-700)', lineHeight: 1.8, marginTop: '0.5rem' }}>
        More precisely: {pieces.join(' ')}
      </p>
    </div>
  )
}

/* ───────── Details / Hungarian steps ───────────── */
function DetailsView({ result }) {
  const hungarian = result.result
  if (!hungarian) {
    return <div className="alert alert-info"><span className="alert-icon">ℹ️</span>No solution data.</div>
  }

  // Reconstruct the balanced (square, dummy-filled) row/column names so the
  // step tables reflect the user's labels.
  const prob = result.problem
  const origRows = prob?.row_names || []
  const origCols = prob?.col_names || []
  const balancedN = hungarian.final_matrix?.length || Math.max(origRows.length, origCols.length)
  const balRows = [...origRows]
  const balCols = [...origCols]
  while (balRows.length < balancedN) balRows.push(`Dummy Row ${balRows.length - origRows.length + 1}`)
  while (balCols.length < balancedN) balCols.push(`Dummy Col ${balCols.length - origCols.length + 1}`)
  const matrixCols = ['', ...balCols]
  const restrictedCells = prob?.restricted_cells || []

  /* Keep null (Restricted) cells as null so they render hatched & empty,
     never as a number. */
  const fmtMatrix = (v) =>
    v === null || v === undefined || Number.isNaN(Number(v)) ? null : Number(v)
  const matrixRow = (row, r) => [balRows[r] ?? `R${r+1}`, ...row.map(fmtMatrix)]

  const STEP_COLORS = {
    row_reduction:    'var(--brand-purple)',
    column_reduction: 'var(--brand-blue)',
    cover_zeros:      'var(--brand-teal)',
    matrix_adjustment:'var(--brand-orange)',
    final_assignment: 'var(--brand-green)',
    initial_matrix:   'var(--gray-500)',
  }

  return (
    <div>
      {hungarian.steps?.length > 0 && (
        <>
          <div className="section-divider">Hungarian Method Steps</div>
          {hungarian.steps.map((step, i) => (
            <div className="expander" key={i}>
              <details>
                <summary className="expander-header">
                  <span
                    className="badge"
                    style={{
                      marginRight: '0.625rem',
                      background: `${STEP_COLORS[step.operation] ?? 'var(--gray-500)'}22`,
                      color: STEP_COLORS[step.operation] ?? 'var(--gray-600)',
                      border: `1px solid ${STEP_COLORS[step.operation] ?? 'var(--gray-300)'}44`,
                    }}
                  >
                    {step.operation.replace(/_/g, ' ')}
                  </span>
                  Step {step.step_number}
                  {step.min_uncovered != null && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginLeft: '0.5rem' }}>
                      · min = {fmt(step.min_uncovered)}
                    </span>
                  )}
                </summary>
                <div className="expander-body">
                  <p style={{ marginBottom: '0.75rem' }}>{step.explanation}</p>

                  {step.matrix_after?.length > 0 && (
                    <DataTable
                      columns={matrixCols}
                      rows={step.matrix_after.map(matrixRow)}
                      restrictedCells={restrictedCells}
                    />
                  )}

                  {step.lines_covering_zeros?.length > 0 && (
                    <p style={{ marginTop: '0.5rem', fontSize: '0.83rem' }}>
                      <strong>Covering lines:</strong>{' '}
                      {step.lines_covering_zeros
                        .map((l) => `${l.type === 'row' ? balRows[l.index] : balCols[l.index]}`)
                        .join(', ')}
                    </p>
                  )}
                </div>
              </details>
            </div>
          ))}
        </>
      )}

      {hungarian.final_matrix?.length > 0 && (
        <>
          <div className="section-divider">Final Reduced Matrix</div>
          <DataTable
            columns={matrixCols}
            rows={hungarian.final_matrix.map(matrixRow)}
            restrictedCells={restrictedCells}
          />
          {restrictedCells.length > 0 && (
            <span className="cell-hint">🚫 Hatched cells are Restricted (forbidden) and are excluded from every Hungarian step.</span>
          )}
        </>
      )}

      <div className="section-divider">Event Log</div>
      {(result.events || []).filter((e) => e.explanation).map((evt, i) => (
        <div className="expander" key={i}>
          <details>
            <summary className="expander-header">
              <span
                className="badge badge-blue"
                style={{ marginRight: '0.625rem', textTransform: 'none', fontSize: '0.72rem' }}
              >
                {evt.operation}
              </span>
              {evt.explanation?.split('.')[0]}.
            </summary>
            <div className="expander-body">{evt.explanation}</div>
          </details>
        </div>
      ))}
    </div>
  )
}

export default Assignment
