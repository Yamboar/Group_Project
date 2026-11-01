import { useEffect, useState } from 'react'
import DataTable from '../components/DataTable.jsx'
import {
  getTransportationHistory,
  getAssignmentHistory,
  deleteTransportationProblem,
  deleteAssignmentProblem,
  getTransportationDetails,
  getAssignmentDetails,
} from '../api/client.js'

const fmtDate = (iso) => {
  if (!iso) return 'unknown date'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : d.toLocaleString()
}

function Saved() {
  const [tab,        setTab]    = useState('transportation')
  const [transport,  setTransport] = useState([])
  const [assignment, setAssignment] = useState([])
  const [loading,    setLoading]   = useState(false)
  const [dbError,    setDbError]   = useState('')
  const [transportDetail,  setTransportDetail]  = useState(null)
  const [assignmentDetail, setAssignmentDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError,   setDetailError]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [t, a] = await Promise.all([
        getTransportationHistory(),
        getAssignmentHistory(),
      ])
      setTransport(t)
      setAssignment(a)
    } catch (err) {
      setDbError(
        err.response?.data?.detail ||
          'Database not available. Ensure the backend database is configured.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  const handleDeleteTransport = async (id) => {
    try {
      await deleteTransportationProblem(id)
      setTransport((prev) => prev.filter((p) => p.id !== id))
      if (transportDetail?.id === id) setTransportDetail(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete.')
    }
  }

  const handleDeleteAssignment = async (id) => {
    try {
      await deleteAssignmentProblem(id)
      setAssignment((prev) => prev.filter((p) => p.id !== id))
      if (assignmentDetail?.id === id) setAssignmentDetail(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete.')
    }
  }

  const toggleTransportDetail = async (id) => {
    if (transportDetail?.id === id) {
      setTransportDetail(null)
      return
    }
    setDetailLoading(true)
    setDetailError('')
    try {
      const data = await getTransportationDetails(id)
      setTransportDetail({ id, data })
    } catch (err) {
      setDetailError(err.response?.data?.detail || 'Failed to load problem details.')
    } finally {
      setDetailLoading(false)
    }
  }

  const toggleAssignmentDetail = async (id) => {
    if (assignmentDetail?.id === id) {
      setAssignmentDetail(null)
      return
    }
    setDetailLoading(true)
    setDetailError('')
    try {
      const data = await getAssignmentDetails(id)
      setAssignmentDetail({ id, data })
    } catch (err) {
      setDetailError(err.response?.data?.detail || 'Failed to load problem details.')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '1.75rem' }}>💾</span>
          <h1 className="page-title">
            <span className="page-title-gradient">Saved</span> Problems
          </h1>
        </div>
        <p className="page-subtitle">Solution history and saved problem records</p>
      </div>

      {dbError && (
        <div className="alert alert-warning">
          <span className="alert-icon">⚠️</span>
          {dbError}
        </div>
      )}

      {detailError && (
        <div className="alert alert-warning">
          <span className="alert-icon">⚠️</span>
          {detailError}
        </div>
      )}

      {!dbError && loading ? (
        <div className="loading-box">
          <span className="spinner spinner-dark" /> Loading history…
        </div>
      ) : !dbError && (
        <>
          {/* Summary stats */}
          <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(2,1fr)', marginBottom: '1.5rem' }}>
            <div className="stat-card stat-card-purple">
              <div className="stat-icon">🚚</div>
              <div className="stat-value">{transport.length}</div>
              <div className="stat-label">Transportation Problems</div>
            </div>
            <div className="stat-card stat-card-blue">
              <div className="stat-icon">📋</div>
              <div className="stat-value">{assignment.length}</div>
              <div className="stat-label">Assignment Problems</div>
            </div>
          </div>

          <div className="tabs">
            {[
              { id: 'transportation', label: '🚚 Transportation', count: transport.length },
              { id: 'assignment',     label: '📋 Assignment',     count: assignment.length },
            ].map((t) => (
              <button
                key={t.id}
                className={`tab-btn ${tab === t.id ? 'active' : ''}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
                <span
                  className={`badge ${tab === t.id ? 'badge-purple' : 'badge-blue'}`}
                  style={{ marginLeft: '0.5rem' }}
                >
                  {t.count}
                </span>
              </button>
            ))}
          </div>

          {tab === 'transportation' &&
            (transport.length === 0 ? (
              <EmptyState
                icon="🚚"
                title="No saved transportation problems"
                desc="Solve a transportation problem and it will appear here."
              />
            ) : (
              transport.map((p) => (
                <div className="card" key={p.id} style={{ marginBottom: '0.75rem' }}>
                  <div className="d-flex-between" style={{ marginBottom: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div
                          className="stat-icon"
                          style={{
                            width: 36, height: 36,
                            background: 'linear-gradient(135deg, #ede9fe, #dbeafe)',
                            borderRadius: 8,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '1rem',
                          }}
                        >🚚</div>
                        <div>
                          <strong>Problem #{p.id}</strong>
                          {p.name && (
                            <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                              — {p.name}
                            </span>
                          )}
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                            {fmtDate(p.created_at)}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className={`btn btn-sm ${transportDetail?.id === p.id ? 'btn-primary' : 'btn-secondary'}`}
                          onClick={() => toggleTransportDetail(p.id)}
                          disabled={detailLoading}
                        >
                          {transportDetail?.id === p.id ? '✕ Close' : '👁 View'}
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteTransport(p.id)}
                        >
                          🗑 Delete
                        </button>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span className="badge badge-purple">{p.num_sources} sources</span>
                      <span className="badge badge-blue">{p.num_destinations} destinations</span>
                      <span className={`badge ${p.is_balanced ? 'badge-green' : 'badge-orange'}`}>
                        {p.is_balanced ? '✓ Balanced' : 'Unbalanced'}
                      </span>
                    </div>
                    {detailLoading && transportDetail === null && (
                      <div className="loading-box" style={{ marginTop: '1rem' }}>
                        <span className="spinner spinner-dark" /> Loading details…
                      </div>
                    )}
                    {transportDetail?.id === p.id && (
                      <TransportDetail data={transportDetail.data} />
                    )}
                  </div>
                ))
              ))}

          {tab === 'assignment' &&
            (assignment.length === 0 ? (
              <EmptyState
                icon="📋"
                title="No saved assignment problems"
                desc="Solve an assignment problem and it will appear here."
              />
            ) : (
              assignment.map((p) => (
                <div className="card" key={p.id} style={{ marginBottom: '0.75rem' }}>
                  <div className="d-flex-between" style={{ marginBottom: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div
                          style={{
                            width: 36, height: 36,
                            background: 'linear-gradient(135deg, #ecfeff, #e0f2fe)',
                            borderRadius: 8,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '1rem',
                          }}
                        >📋</div>
                        <div>
                          <strong>Problem #{p.id}</strong>
                          {p.name && (
                            <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                              — {p.name}
                            </span>
                          )}
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                            {fmtDate(p.created_at)}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className={`btn btn-sm ${assignmentDetail?.id === p.id ? 'btn-primary' : 'btn-secondary'}`}
                          onClick={() => toggleAssignmentDetail(p.id)}
                          disabled={detailLoading}
                        >
                          {assignmentDetail?.id === p.id ? '✕ Close' : '👁 View'}
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteAssignment(p.id)}
                        >
                          🗑 Delete
                        </button>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span className="badge badge-purple">{p.num_rows}×{p.num_cols} matrix</span>
                      <span className={`badge ${p.problem_type === 'Minimization' ? 'badge-blue' : 'badge-orange'}`}>
                        {p.problem_type}
                      </span>
                    </div>
                    {detailLoading && assignmentDetail === null && (
                      <div className="loading-box" style={{ marginTop: '1rem' }}>
                        <span className="spinner spinner-dark" /> Loading details…
                      </div>
                    )}
                    {assignmentDetail?.id === p.id && (
                      <AssignmentDetail data={assignmentDetail.data} />
                    )}
                  </div>
                ))
              ))}
        </>
      )}
    </div>
  )
}

function TransportDetail({ data }) {
  const { problem } = data
  const solutions = data.solutions || []

  const costMatrix = problem.cost_matrix || []
  const supply     = problem.supply || []
  const demand     = problem.demand || []
  const restricted = problem.restricted_cells || []
  const n = costMatrix.length
  const m = costMatrix[0]?.length || 0
  const srcNames = problem.source_names || Array.from({ length: n }, (_, i) => `S${i + 1}`)
  const dstNames = problem.dest_names || Array.from({ length: m }, (_, j) => `D${j + 1}`)

  const costColumns = ['', ...dstNames, 'Supply']
  const costRows = srcNames.map((s, i) => [s, ...costMatrix[i], supply[i]])
  costRows.push(['Demand', ...demand, ''])

  return (
    <div
      style={{
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '1px solid var(--border-strong)',
      }}
    >
      <div className="d-flex-between" style={{ marginBottom: '0.6rem' }}>
        <h4 style={{ margin: 0 }}>Problem Input</h4>
        {restricted.length > 0 && (
          <span className="badge badge-orange">🚫 {restricted.length} restricted route{restricted.length === 1 ? '' : 's'}</span>
        )}
      </div>
      <DataTable columns={costColumns} rows={costRows} restrictedCells={restricted} />
      {restricted.length > 0 && (
        <span className="cell-hint">🚫 Hatched cells are restricted (forbidden) routes.</span>
      )}

      {solutions.length === 0 ? (
        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
          No saved solutions for this problem.
        </p>
      ) : (
        solutions.map((s) => (
          <div key={s.id} style={{ marginTop: '1.25rem' }}>
            <div className="d-flex-between" style={{ marginBottom: '0.4rem' }}>
              <strong>{s.method}</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {fmtDate(s.created_at)}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
              <span className="badge badge-purple">Initial: {fmtNum(s.initial_total_cost)}</span>
              <span className="badge badge-blue">
                {s.is_optimized ? `Optimal: ${fmtNum(s.optimized_total_cost)}` : 'Not optimized'}
              </span>
              <span className={`badge ${s.is_optimal ? 'badge-green' : 'badge-orange'}`}>
                {s.is_optimal ? '✓ Optimal' : 'Not proven optimal'}
              </span>
              <span className={`badge ${s.verification_passed ? 'badge-green' : 'badge-orange'}`}>
                {s.verification_passed ? '✓ Verified' : 'Verification failed'}
              </span>
            </div>
            {s.optimized_allocation && (
              <p style={{ margin: '0 0 0.35rem', fontSize: '0.85rem', fontWeight: 600 }}>
                Optimized allocation
              </p>
            )}
            <AllocationTable
              allocation={s.optimized_allocation || s.initial_allocation}
              sourceNames={srcNames}
              destNames={dstNames}
            />
            {s.events?.length > 0 && (
              <details className="expander" style={{ marginTop: '0.75rem' }}>
                <summary className="expander-header">
                  Solution events ({s.events.length})
                </summary>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                  {s.events.map((e, i) => (
                    <li key={i} style={{ marginBottom: '0.3rem' }}>
                      <strong>{e.operation || 'event'}:</strong>{' '}
                      {e.explanation || e.concise || e.detailed || ''}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))
      )}
    </div>
  )
}

function AssignmentDetail({ data }) {
  const { problem } = data
  const solutions = data.solutions || []

  const costMatrix = problem.cost_matrix || []
  const n = costMatrix.length
  const m = costMatrix[0]?.length || 0
  const rowNames = problem.row_names || Array.from({ length: n }, (_, i) => `Worker ${i + 1}`)
  const colNames = problem.col_names || Array.from({ length: m }, (_, j) => `Job ${j + 1}`)
  const restricted = problem.restricted_cells || []

  const columns = ['', ...colNames]
  const rows = rowNames.map((r, i) => [r, ...costMatrix[i]])

  return (
    <div
      style={{
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '1px solid var(--border-strong)',
      }}
    >
      <div className="d-flex-between" style={{ marginBottom: '0.5rem' }}>
        <h4 style={{ margin: 0 }}>Problem Input</h4>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {restricted.length > 0 && (
            <span className="badge badge-orange">🚫 {restricted.length} restricted {restricted.length === 1 ? 'assignment' : 'assignments'}</span>
          )}
          <span className={`badge ${problem.problem_type === 'Minimization' ? 'badge-blue' : 'badge-orange'}`}>
            {problem.problem_type}
          </span>
        </div>
      </div>
      <DataTable columns={columns} rows={rows} restrictedCells={restricted} />
      {restricted.length > 0 && (
        <span className="cell-hint">🚫 Hatched cells are Restricted (forbidden) assignments.</span>
      )}

      {solutions.length === 0 ? (
        <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
          No saved solutions for this problem.
        </p>
      ) : (
        solutions.map((s) => (
          <div key={s.id} style={{ marginTop: '1.25rem' }}>
            <div className="d-flex-between" style={{ marginBottom: '0.4rem' }}>
              <strong>Hungarian Method</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {fmtDate(s.created_at)}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
              <span className="badge badge-purple">Total cost: {fmtNum(s.total_cost)}</span>
              <span className={`badge ${s.verification_passed ? 'badge-green' : 'badge-orange'}`}>
                {s.verification_passed ? '✓ Verified' : 'Verification failed'}
              </span>
              {(s.dummy_rows_added > 0 || s.dummy_cols_added > 0) && (
                <span className="badge badge-orange">
                  +{s.dummy_rows_added} dummy row(s), +{s.dummy_cols_added} dummy col(s)
                </span>
              )}
            </div>

            <p style={{ margin: '0 0 0.35rem', fontSize: '0.85rem', fontWeight: 600 }}>Assignments</p>
            <DataTable
              columns={['Worker', 'Job', 'Original Cost', 'Reduced Cost']}
              rows={(s.assignments || []).map((a) => [
                a.row_name || `Worker ${a.row + 1}`,
                a.col_name || `Job ${a.col + 1}`,
                a.original_cost ?? '—',
                a.is_dummy ? '—' : (a.reduced_cost ?? '—'),
              ])}
            />

            {s.steps?.length > 0 && (
              <details className="expander" style={{ marginTop: '0.75rem' }}>
                <summary className="expander-header">
                  Algorithm steps ({s.steps.length})
                </summary>
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                  {s.steps.map((st, i) => (
                    <li key={i} style={{ marginBottom: '0.3rem' }}>
                      <strong>Step {st.step} — {st.operation}:</strong> {st.explanation || ''}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))
      )}
    </div>
  )
}

function AllocationTable({ allocation, sourceNames, destNames }) {
  const rowsData = allocation || []
  const n = rowsData.length
  const m = rowsData[0]?.length || 0
  const src = sourceNames && sourceNames.length === n
    ? sourceNames
    : Array.from({ length: n }, (_, i) => `S${i + 1}`)
  const dst = destNames && destNames.length >= m
    ? destNames.slice(0, m)
    : Array.from({ length: m }, (_, j) => `D${j + 1}`)
  const columns = ['', ...dst]
  const rows = src.map((s, i) => [s, ...rowsData[i]])
  return <DataTable columns={columns} rows={rows} highlightZeros />
}

const fmtNum = (v) =>
  Number(v ?? 0).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })

function EmptyState({ icon, title, desc }) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '3rem 2rem',
        color: 'var(--text-muted)',
        background: 'var(--bg-white)',
        border: '1.5px dashed var(--border-strong)',
        borderRadius: 'var(--radius-lg)',
        marginTop: '0.5rem',
      }}
    >
      <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>{icon}</div>
      <p style={{ fontWeight: 700, color: 'var(--gray-600)', marginBottom: '0.35rem' }}>{title}</p>
      <p style={{ fontSize: '0.875rem' }}>{desc}</p>
    </div>
  )
}

export default Saved
