import { useState } from 'react'
import EditableMatrix from '../components/EditableMatrix.jsx'
import DataTable from '../components/DataTable.jsx'
import ObjectiveSelector, { ObjectiveTrail } from '../components/ObjectiveSelector.jsx'
import { solveTransportation, explainTransportation } from '../api/client.js'
import { fmtUnit, withUnit, unitFor } from '../utils/units.js'

const METHODS = [
  { id: 'nwc',    label: 'North-West Corner',      short: 'NWC',    icon: '↖️' },
  { id: 'lc',     label: 'Least Cost Method',       short: 'LC',     icon: '💰' },
  { id: 'vogel',  label: "Vogel's Approximation",   short: 'VAM',    icon: '📐' },
]

const METHOD_MAP = {
  nwc:   'North-West Corner Method',
  lc:    'Least Cost Method',
  vogel: "Vogel's Approximation Method",
}

const fmt = (v) =>
  Number(v).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })

/* ───────── Main page ────────────────────────────── */
function Transportation() {
  const [tab, setTab] = useState('input')
  const [numSources, setNumSources] = useState(3)
  const [numDests,   setNumDests]   = useState(4)
  const [methodId,   setMethodId]   = useState('vogel')
  const [optimize,   setOptimize]   = useState(true)
  const [supply,     setSupply]     = useState([0, 0, 0])
  const [demand,     setDemand]     = useState([0, 0, 0, 0])
  const [costMatrix, setCostMatrix] = useState(() =>
    Array.from({ length: 3 }, () => Array(4).fill(0)),
  )
  const [restrictedMask, setRestrictedMask] = useState(() =>
    Array.from({ length: 3 }, () => Array(4).fill(false)),
  )
  const [result,      setResult]      = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')
  const [sourceNamesInput, setSourceNamesInput] = useState('')
  const [destNamesInput,   setDestNamesInput]   = useState('')
  const [objective,        setObjective]        = useState(null)

  const defaultSourceNames = Array.from({ length: numSources }, (_, i) => `S${i + 1}`)
  const defaultDestNames   = Array.from({ length: numDests },   (_, j) => `D${j + 1}`)

  const parseNames = (str, defaults) => {
    const parsed = str.split(',').map((s) => s.trim()).filter(Boolean)
    return parsed.length === defaults.length ? parsed : defaults
  }

  const sourceNames = parseNames(sourceNamesInput, defaultSourceNames)
  const destNames   = parseNames(destNamesInput, defaultDestNames)
  const totalSupply = supply.reduce((a, b) => a + Number(b || 0), 0)
  const totalDemand = demand.reduce((a, b) => a + Number(b || 0), 0)
  const isBalanced  = Math.abs(totalSupply - totalDemand) < 1e-9

  const changeNumSources = (val) => {
    const n = Math.min(20, Math.max(1, val))
    setNumSources(n)
    setSupply(Array.from({ length: n }, (_, i) => supply[i] ?? 0))
    setCostMatrix((prev) => {
      const next = prev.slice(0, n)
      while (next.length < n) next.push(Array(numDests).fill(0))
      return next
    })
    setRestrictedMask((prev) => {
      const next = prev.slice(0, n)
      while (next.length < n) next.push(Array(numDests).fill(false))
      return next
    })
  }

  const changeNumDests = (val) => {
    const n = Math.min(20, Math.max(1, val))
    setNumDests(n)
    setDemand(Array.from({ length: n }, (_, i) => demand[i] ?? 0))
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

    const method = METHOD_MAP[methodId]

    const restrictedCells = []
    costMatrix.forEach((row, r) =>
      row.forEach((_, c) => {
        if (restrictedMask[r]?.[c]) restrictedCells.push([r, c])
      }),
    )

    const payload = {
      cost_matrix: costMatrix.map((row) =>
        row.map((v) => {
          const s = String(v ?? '').trim()
          if (s === '' || Number.isNaN(Number(s))) return null
          return Number(v)
        }),
      ),
      supply:       supply.map((v) => Number(v)),
      demand:       demand.map((v) => Number(v)),
      method,
      optimize,
      source_names: sourceNames,
      dest_names:   destNames,
      objective,
      restricted_cells: restrictedCells,
    }

    try {
      const data = await solveTransportation(payload)
      setResult(data)
      try {
        const expl = await explainTransportation(payload)
        setExplanation(expl)
      } catch { /* explanation is optional */ }
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
        msg = `Failed to solve. (HTTP ${status ?? 'unknown'})`
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const balanceRatio = totalDemand === 0 ? 0 : Math.min(totalSupply / totalDemand, 1)

  return (
    <div>
      {/* Page header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '1.75rem' }}>🚚</span>
          <h1 className="page-title">
            <span className="page-title-gradient">Transportation</span> Problem Solver
          </h1>
        </div>
        <p className="page-subtitle">
          North-West Corner · Least Cost · Vogel's Approximation · Stepping Stone Optimization
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'input',    label: '1 · Input',    icon: '📝' },
          { id: 'solution', label: '2 · Solution',  icon: '✅' },
          { id: 'details',  label: '3 · Steps',     icon: '🔍' },
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

      {/* ─── INPUT TAB ─────────────────────────────── */}
      {tab === 'input' && (
        <div className="tab-content">
          {/* Dimensions */}
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="card-title">📐 Problem Dimensions</div>
            <div className="grid-2">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Sources (rows)</label>
                <input
                  type="number" className="form-control"
                  min="1" max="20" value={numSources}
                  onChange={(e) => changeNumSources(parseInt(e.target.value, 10) || 1)}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Destinations (cols)</label>
                <input
                  type="number" className="form-control"
                  min="1" max="20" value={numDests}
                  onChange={(e) => changeNumDests(parseInt(e.target.value, 10) || 1)}
                />
              </div>
            </div>
          </div>

          {/* Objective selection */}
          <ObjectiveSelector mode="locked-min" onChange={setObjective} />

          {/* Cost matrix */}
          <div className="card">
            <div className="card-title">💰 Cost Matrix</div>
            <EditableMatrix
              rows={numSources} cols={numDests}
              rowNames={sourceNames} colNames={destNames}
              values={costMatrix} onChange={setCostMatrix}
              restricted={restrictedMask} onToggleRestricted={toggleRestricted}
            />
            {invalidCells.length > 0 && (
              <div className="alert alert-warning" style={{ marginTop: '0.75rem' }}>
                <span className="alert-icon">🚫</span>
                <span>
                  <strong>{invalidCells.length} cell{invalidCells.length === 1 ? '' : 's'} is blank or negative</strong> — costs must be 0 or more.{' '}
                  {invalidCells
                    .map(({ r, c }) => `${sourceNames[r] ?? `S${r + 1}`} → ${destNames[c] ?? `D${c + 1}`}`)
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
                <label className="form-label">Source names (comma-separated)</label>
                <input
                  className="form-control"
                  value={sourceNamesInput}
                  placeholder={defaultSourceNames.join(', ')}
                  onChange={(e) => setSourceNamesInput(e.target.value)}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Destination names (comma-separated)</label>
                <input
                  className="form-control"
                  value={destNamesInput}
                  placeholder={defaultDestNames.join(', ')}
                  onChange={(e) => setDestNamesInput(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Supply + Demand */}
          <div className="grid-2">
            <div className="card">
              <div className="card-title">📦 Supply</div>
              <div
                className="grid-auto"
                style={{ gridTemplateColumns: `repeat(${Math.min(numSources, 3)}, 1fr)` }}
              >
                {sourceNames.map((name, i) => (
                  <div className="form-group" key={i} style={{ marginBottom: '0.5rem' }}>
                    <label className="form-label-muted">{name}</label>
                    <input
                      type="number" className="form-control" min="0" step="any"
                      value={supply[i]}
                      onChange={(e) => {
                        const next = [...supply]; next[i] = e.target.value; setSupply(next)
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-title">🎯 Demand</div>
              <div
                className="grid-auto"
                style={{ gridTemplateColumns: `repeat(${Math.min(numDests, 3)}, 1fr)` }}
              >
                {destNames.map((name, j) => (
                  <div className="form-group" key={j} style={{ marginBottom: '0.5rem' }}>
                    <label className="form-label-muted">{name}</label>
                    <input
                      type="number" className="form-control" min="0" step="any"
                      value={demand[j]}
                      onChange={(e) => {
                        const next = [...demand]; next[j] = e.target.value; setDemand(next)
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Balance indicator */}
          <div className="balance-indicator">
            <span className="balance-text">Supply: {fmt(totalSupply)}</span>
            <div className="balance-bar">
              <div
                className={`balance-fill ${isBalanced ? 'balance-fill-ok' : 'balance-fill-over'}`}
                style={{ width: `${Math.min(100, balanceRatio * 100)}%` }}
              />
            </div>
            <span className="balance-text">Demand: {fmt(totalDemand)}</span>
            <span className={`badge ${isBalanced ? 'badge-green' : 'badge-orange'}`}>
              {isBalanced ? '✓ Balanced' : 'Unbalanced'}
            </span>
          </div>

          {!isBalanced && totalSupply > 0 && totalDemand > 0 && (
            <div className="alert alert-warning">
              <span className="alert-icon">⚠️</span>
              {totalSupply > totalDemand
                ? `Supply exceeds demand by ${fmt(totalSupply - totalDemand)}. A dummy destination will be added automatically.`
                : `Demand exceeds supply by ${fmt(totalDemand - totalSupply)}. A dummy source will be added automatically.`}
            </div>
          )}

          {/* Method selector */}
          <div className="card" style={{ marginTop: '0.25rem' }}>
            <div className="card-title">⚙️ Solver Settings</div>

            <label className="form-label">Initial Solution Method</label>
            <div className="method-pills">
              {METHODS.map((m) => (
                <button
                  key={m.id}
                  className={`method-pill ${methodId === m.id ? 'selected' : ''}`}
                  onClick={() => setMethodId(m.id)}
                >
                  {m.icon} {m.label}
                </button>
              ))}
            </div>

            <label className="checkbox" style={{ marginTop: '1rem' }}>
              <input
                type="checkbox" checked={optimize}
                onChange={(e) => setOptimize(e.target.checked)}
              />
              Apply Stepping Stone optimization (recommended)
            </label>
          </div>

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
              ? <><span className="spinner" /> Solving...</>
              : invalidCells.length > 0
                ? '🚫 Resolve invalid cells before solving'
                : '🚀  Solve Transportation Problem'}
          </button>
        </div>
      )}

      {/* ─── SOLUTION TAB ─────────────────────────── */}
      {tab === 'solution' && (
        <div className="tab-content">
          {loading ? (
            <div className="loading-box">
              <span className="spinner spinner-dark" /> Solving...
            </div>
          ) : !result ? (
            <div className="alert alert-info">
              <span className="alert-icon">ℹ️</span>
              Input your problem and click Solve to see results here.
            </div>
          ) : (
            <SolutionView
              result={result}
              explanation={explanation}
              methodLabel={METHODS.find((m) => METHOD_MAP[m.id] === METHOD_MAP[methodId])?.label ?? ''}
            />
          )}
        </div>
      )}

      {/* ─── DETAILS TAB ──────────────────────────── */}
      {tab === 'details' && (
        <div className="tab-content">
          {loading ? (
            <div className="loading-box">
              <span className="spinner spinner-dark" /> Loading...
            </div>
          ) : !result ? (
            <div className="alert alert-info">
              <span className="alert-icon">ℹ️</span>
              Solve a problem first to see step-by-step details.
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
function SolutionView({ result, explanation, methodLabel }) {
  if (!result) return null

  if (!result.success) {
    return (
      <div className="alert alert-error">
        <span className="alert-icon">❌</span>
        {(result.errors || []).join('; ')}
      </div>
    )
  }

  const balanced          = result.balanced_problem
  const initial           = result.initial_solution
  const optimized         = result.optimized_solution
  const balancingEvents   = result.balancing?.events || []
  const needsBalancing    = !result.balancing?.is_balanced
  const initCost          = initial?.total_cost ?? 0
  const optCost           = optimized?.total_cost
  const reduction         = initCost - (optCost ?? initCost)
  const pct               = initCost > 0 ? ((reduction / initCost) * 100).toFixed(1) : '0'
  const namesR            = balanced?.source_names || []
  const namesC            = balanced?.dest_names   || []
  const unit              = unitFor(result.objective_selection)
  const restrictedCells   = result.problem?.restricted_cells || []
  const pNamesR           = result.problem?.source_names || namesR
  const pNamesC           = result.problem?.dest_names   || namesC

  const buildRows = (alloc) =>
    alloc.map((row, i) => [namesR[i] ?? `S${i+1}`, ...row.map(Number)])
  const cols = ['', ...namesC]

  return (
    <div>
      {/* Objective selection */}
      <ObjectiveTrail objective={result.objective_selection} />

      {/* Restricted routes */}
      {restrictedCells.length > 0 && (
        <div className="alert alert-warning">
          <span className="alert-icon">🚫</span>
          <strong>{restrictedCells.length} restricted route{restrictedCells.length === 1 ? '' : 's'}:</strong>{' '}
          {restrictedCells
            .map(([r, c]) => `${pNamesR[r] ?? `S${r + 1}`} → ${pNamesC[c] ?? `D${c + 1}`}`)
            .join(', ')}
          <span style={{ marginLeft: '0.5rem' }}>— these routes are forbidden and never allocated.</span>
        </div>
      )}

      {/* Balancing notice */}
      {needsBalancing && (
        <>
          <div className="section-divider">Balancing</div>
          {balancingEvents.map((evt, i) => (
            <div key={i} className="alert alert-info">
              <span className="alert-icon">⚖️</span>{evt.explanation}
            </div>
          ))}
        </>
      )}

      {/* Cost summary cards */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: '1.5rem' }}>
        <div className="stat-card stat-card-blue">
          <div className="stat-icon">📊</div>
          <div className="stat-value">{fmtUnit(initCost, unit)}</div>
          <div className="stat-label">Initial Cost · {methodLabel}</div>
        </div>
        {optimized && (
          <>
            <div className="stat-card stat-card-purple">
              <div className="stat-icon">⚡</div>
              <div className="stat-value gradient">{fmtUnit(optCost, unit)}</div>
              <div className="stat-label">Optimized Cost</div>
            </div>
            <div className="stat-card stat-card-green">
              <div className="stat-icon">📉</div>
              <div className="stat-value">{pct}%</div>
              <div className="stat-label">Cost Reduction</div>
            </div>
          </>
        )}
      </div>

      {/* Initial allocation */}
      <div className="section-divider">Initial Solution — {methodLabel}</div>
      <DataTable columns={cols} rows={buildRows(initial.allocation)} highlightZeros />

      {/* Optimized allocation */}
      {optimized && (
        <>
          <div className="section-divider">Optimized Solution — Stepping Stone</div>
          {reduction > 1e-9 ? (
            <div className="alert alert-success">
              <span className="alert-icon">🎉</span>
              Cost reduced from <strong>{fmtUnit(initCost, unit)}</strong> → <strong>{fmtUnit(optCost, unit)}</strong>
              &nbsp;(saved {fmtUnit(reduction, unit)}, {pct}% improvement)
              {optimized.is_optimal && (
                <span className="badge badge-green" style={{ marginLeft: '0.75rem' }}>
                  ✓ Globally Optimal
                </span>
              )}
            </div>
          ) : (
            <div className="alert alert-info">
              <span className="alert-icon">✅</span>
              Initial solution was already optimal — no further improvement possible.
            </div>
          )}
          <DataTable columns={cols} rows={buildRows(optimized.allocation)} highlightZeros />
        </>
      )}

      {/* Cost matrix for reference */}
      {balanced && (
        <>
          <div className="section-divider">Balanced Cost Matrix</div>
          <DataTable
            columns={['', ...namesC]}
            rows={balanced.cost_matrix.map((row, i) => [namesR[i] ?? `S${i+1}`, ...row.map(Number)])}
            restrictedCells={balanced.restricted_cells || []}
          />
          {restrictedCells.length > 0 && (
            <span className="cell-hint">🚫 Hatched cells are restricted (forbidden) routes.</span>
          )}
        </>
      )}

      {/* Verification */}
      {result.verification && (
        result.verification.passed ? (
          <div className="alert alert-success">
            <span className="alert-icon">✔️</span>
            Verification passed — all supply and demand constraints satisfied.
          </div>
        ) : (
          <div className="alert alert-error">
            <span className="alert-icon">❌</span>
            Verification failed: {(result.verification.issues || []).join('; ')}
          </div>
        )
      )}

      {/* Explanations */}
      <div className="section-divider">XAI Explanations</div>
      {explanation ? (
        <>
          <div className="card card-purple">
            <div className="card-title">💬 Summary</div>
            <p style={{ fontSize: '0.9rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
              {explanation.summary}
            </p>
          </div>

          {explanation.key_decisions?.length > 0 && (
            <div className="expander">
              <details>
                <summary className="expander-header">📌 Key Allocation Decisions</summary>
                <div className="expander-body">
                  <ul>
                    {explanation.key_decisions.map((d, i) => (
                      <li key={i} style={{ marginBottom: '0.5rem' }}>{d}</li>
                    ))}
                  </ul>
                </div>
              </details>
            </div>
          )}

          {explanation.optimality_reason && (
            <div className="expander">
              <details>
                <summary className="expander-header">🏆 Why is this solution optimal?</summary>
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
      <PlainEnglishInterpretation
        initial={initial}
        optimized={optimized}
        namesR={namesR}
        namesC={namesC}
        finalCost={optCost ?? result.final_cost}
        isOptimized={Boolean(optimized)}
        unit={unit}
        objective={result.objective_selection}
      />
    </div>
  )
}

/* ───────── Plain-English interpretation ────────── */
function PlainEnglishInterpretation({ initial, optimized, namesR, namesC, finalCost, isOptimized, unit, objective }) {
  const alloc = optimized?.allocation || initial?.allocation
  if (!alloc) {
    return <div className="alert alert-info"><span className="alert-icon">ℹ️</span>No allocation available to interpret.</div>
  }

  const obj = objective
  const fallback = 'cost'
  const vt = obj?.value_type === 'other'
    ? (obj?.other_description || fallback)
    : (obj?.value_type || fallback)

  const routes = []
  let realRoutes = []
  let dummyNotes = []
  for (let i = 0; i < alloc.length; i++) {
    for (let j = 0; j < alloc[i].length; j++) {
      const qty = Number(alloc[i][j] || 0)
      if (qty === 0) continue
      const src = namesR[i] ?? `S${i+1}`
      const dst = namesC[j] ?? `D${j+1}`
      const isSrcDummy = src.toLowerCase().includes('dummy')
      const isDstDummy = dst.toLowerCase().includes('dummy')
      if (isSrcDummy || isDstDummy) {
        dummyNotes.push(
          `${qty.toLocaleString()} unit${qty === 1 ? '' : 's'} left unfulfilled` +
          (isDstDummy ? ` from ${src}` : ` at ${dst}`),
        )
        continue
      }
      realRoutes.push({ src, dst, qty })
      routes.push(`${qty.toLocaleString()} units from ${src} to ${dst}`)
    }
  }

  const finalLabel = isOptimized ? 'best (lowest)' : 'best-known'
  const totalText = withUnit(fmt(finalCost), unit)
  const routeText = routes.length > 0
    ? routes.slice(0, -1).join(', ') + (routes.length > 1 ? ', and ' : '') + routes[routes.length - 1]
    : 'no shipments were made'

  return (
    <div className="card card-teal">
      <p style={{ fontSize: '0.92rem', color: 'var(--gray-800)', lineHeight: 1.85 }}>
        To achieve the {finalLabel} total {vt} of <strong>{totalText}</strong>, the
        best plan is to ship {routeText}.
      </p>
      {realRoutes.length > 1 && (
        <p style={{ fontSize: '0.88rem', color: 'var(--gray-700)', lineHeight: 1.8, marginTop: '0.5rem' }}>
          In other words: {realRoutes.map((r) => `${r.src} supplies ${r.dst} with ${r.qty.toLocaleString()} units`).join(', ')}.
        </p>
      )}
      {dummyNotes.length > 0 && (
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-600)', lineHeight: 1.7, marginTop: '0.5rem' }}>
          Note: {dummyNotes.join('; ')} (the problem was not fully balanced, so some supply/demand is not used).
        </p>
      )}
    </div>
  )
}

/* ───────── Details / step-by-step view ─────────── */
function DetailsView({ result }) {
  const initial   = result.initial_solution
  const optimized = result.optimized_solution
  const namesR    = result.balanced_problem?.source_names || []
  const namesC    = result.balanced_problem?.dest_names   || []
  const srcName   = (r) => namesR[r] ?? `S${r + 1}`
  const dstName   = (c) => namesC[c] ?? `D${c + 1}`
  const cellName  = (r, c) => `${srcName(r)} → ${dstName(c)}`
  const colHeader = ['Row', ...namesC.map((d, j) => dstName(j))]

  return (
    <div>
      {/* Initial decisions */}
      {initial?.decisions?.length > 0 && (
        <>
          <div className="section-divider">Initial Allocation Steps</div>
          {initial.decisions.map((d, i) => (
            <div className="expander" key={i}>
              <details>
                <summary className="expander-header">
                  <span style={{ color: 'var(--brand-purple)', marginRight: '0.5rem' }}>
                    Step {i + 1}
                  </span>
                  Cell ({cellName(d.row, d.col)}) — Allocate{' '}
                  <strong style={{ marginLeft: '0.25rem' }}>{fmt(d.quantity)} units</strong>
                </summary>
                <div className="expander-body">{d.explanation}</div>
              </details>
            </div>
          ))}
        </>
      )}

      {/* Intermediate states */}
      {initial?.intermediate_states?.length > 0 && (
        <>
          <div className="section-divider">Intermediate States</div>
          {initial.intermediate_states.map((state, i) => (
            <div className="expander" key={i}>
              <details>
                <summary className="expander-header">
                  After Step {state.step} — Cost so far:{' '}
                  <strong style={{ marginLeft: '0.25rem' }}>{fmt(state.total_cost_so_far)}</strong>
                </summary>
                <div className="expander-body">
                  <DataTable
                    columns={colHeader}
                    rows={state.allocation.map((row, r) => [srcName(r), ...row.map(Number)])}
                    highlightZeros
                  />
                  <p style={{ marginTop: '0.5rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Remaining supply: {state.supply.map((v, i) => `${srcName(i)}=${fmt(v)}`).join(', ')}
                    &nbsp;|&nbsp;
                    Remaining demand: {state.demand.map((v, j) => `${dstName(j)}=${fmt(v)}`).join(', ')}
                  </p>
                </div>
              </details>
            </div>
          ))}
        </>
      )}

      {/* Stepping stone iterations */}
      {optimized?.iterations?.length > 0 && (
        <>
          <div className="section-divider">Stepping Stone Iterations</div>
          {optimized.iterations.map((it) => (
            <div className="expander" key={it.iteration}>
              <details>
                <summary className="expander-header">
                  <span style={{ color: 'var(--brand-blue)', marginRight: '0.5rem' }}>
                    Iteration {it.iteration}
                  </span>
                  Cost: {fmt(it.old_cost)} →{' '}
                  <strong style={{ color: 'var(--brand-green)', marginLeft: '0.25rem' }}>
                    {fmt(it.new_cost)}
                  </strong>
                  <span className="improvement-chip" style={{ marginLeft: '0.75rem' }}>
                    −{fmt(it.old_cost - it.new_cost)}
                  </span>
                </summary>
                <div className="expander-body">
                  {it.best_candidate && (
                    <div
                      className="card card-blue"
                      style={{ marginBottom: '0.75rem', padding: '0.875rem' }}
                    >
                      <p style={{ marginBottom: '0.3rem' }}>
                        <strong>Entering cell:</strong> ({cellName(it.best_candidate.row, it.best_candidate.col)})
                        &nbsp;·&nbsp;
                        <strong>Improvement index:</strong> {fmt(it.best_candidate.improvement_index)}
                        &nbsp;·&nbsp;
                        <strong>Adjustment:</strong> {fmt(it.adjustment_quantity)}
                      </p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem', color: 'var(--brand-blue)' }}>
                        Loop: {it.best_candidate.loop.map(([r, c]) => `(${cellName(r, c)})`).join(' → ')}
                      </p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem' }}>
                        Signs: {it.best_candidate.signs.join(' ')}
                      </p>
                    </div>
                  )}

                  <p style={{ marginBottom: '0.5rem', fontSize: '0.83rem' }}>{it.explanation}</p>

                  <p style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--gray-600)', marginBottom: '0.35rem' }}>
                    All candidates evaluated:
                  </p>
                  <ul style={{ paddingLeft: '1.25rem' }}>
                    {it.candidates.map((c, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: '0.82rem',
                          marginBottom: '0.2rem',
                          color: it.best_candidate && c.row === it.best_candidate.row && c.col === it.best_candidate.col
                            ? 'var(--brand-purple)'
                            : 'var(--gray-600)',
                          fontWeight: it.best_candidate && c.row === it.best_candidate.row && c.col === it.best_candidate.col
                            ? 700
                            : 400,
                        }}
                      >
                        Cell ({cellName(c.row, c.col)}): index = {fmt(c.improvement_index)}
                        {it.best_candidate && c.row === it.best_candidate.row && c.col === it.best_candidate.col
                          && <span className="badge badge-purple" style={{ marginLeft: '0.5rem' }}>ENTERING</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              </details>
            </div>
          ))}
        </>
      )}

      {/* Final optimality indices */}
      {optimized?.final_improvement_indices?.length > 0 && (
        <>
          <div className="section-divider">Final Improvement Indices (Optimality Check)</div>
          <div className="card">
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              All indices ≥ 0 confirms the solution is globally optimal.
            </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {optimized.final_improvement_indices.map((c, i) => (
                      <span
                        key={i}
                        className={`badge ${c.improvement_index < -1e-6 ? 'badge-orange' : 'badge-green'}`}
                      >
                        ({cellName(c.row, c.col)}) = {fmt(c.improvement_index)}
                      </span>
                    ))}
                  </div>
          </div>
        </>
      )}

      {/* Event log */}
      <div className="section-divider">Full Event Log</div>
      {(result.events || []).filter((e) => e.explanation).map((evt, i) => (
        <div className="expander" key={i}>
          <details>
            <summary className="expander-header">
              <span
                className="badge badge-purple"
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

export default Transportation
