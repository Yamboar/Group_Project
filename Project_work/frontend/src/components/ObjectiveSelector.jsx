import { useState } from 'react'

const VALUE_TYPES = [
  { id: 'cost',     label: 'Cost',      icon: '💰' },
  { id: 'time',     label: 'Time',      icon: '⏱️' },
  { id: 'distance', label: 'Distance',  icon: '📏' },
  { id: 'profit',   label: 'Profit',    icon: '📈' },
  { id: 'revenue',  label: 'Revenue',   icon: '💵' },
  { id: 'other',    label: 'Other',     icon: '✏️' },
]

const DIR_LABEL = {
  minimise: { verb: 'minimise', plain: 'reduce' },
  maximise: { verb: 'maximise', plain: 'increase' },
}

function labelForValueType(valueType) {
  return VALUE_TYPES.find((v) => v.id === valueType)?.label ?? 'value'
}

export default function ObjectiveSelector({
  mode = 'free', // 'free' (can maximise) or 'locked-min' (minimise-only engine)
  onChange,
}) {
  const [valueType, setValueType] = useState('cost')
  const [otherDesc, setOtherDesc] = useState('')
  const [intent, setIntent] = useState(null)

  const lockedMin = mode === 'locked-min'
  const recommendable = valueType !== 'other'
  const recommended = lockedMin
    ? 'minimise'
    : (recommendable ? (valueType === 'profit' || valueType === 'revenue' ? 'maximise' : 'minimise') : null)
  const opposite = recommended === 'maximise' ? 'minimise' : 'maximise'
  const vtLabel = valueType === 'other' ? (otherDesc.trim() || 'value') : labelForValueType(valueType)

  const push = (partial) => {
    onChange({
      value_type: valueType,
      other_description: valueType === 'other' ? otherDesc : null,
      intent: partial.intent ?? intent,
      recommended,
      confirmed: partial.confirmed ?? false,
      overridden: partial.overridden ?? false,
    })
  }

  const choose = (dir, overridden) => {
    setIntent(dir)
    push({ intent: dir, confirmed: true, overridden })
  }

  const changeValueType = (id) => {
    setValueType(id)
    setIntent(null)
    const rec = lockedMin
      ? 'minimise'
      : (id === 'other' ? null : (id === 'profit' || id === 'revenue' ? 'maximise' : 'minimise'))
    onChange({
      value_type: id,
      other_description: id === 'other' ? otherDesc : null,
      intent: null,
      recommended: rec,
      confirmed: false,
      overridden: false,
    })
  }

  const changeOther = (text) => {
    setOtherDesc(text)
    push({})
  }

  const reset = () => {
    setIntent(null)
    onChange({
      value_type: valueType,
      other_description: valueType === 'other' ? otherDesc : null,
      intent: null,
      recommended,
      confirmed: false,
      overridden: false,
    })
  }

  return (
    <div className="card" style={{ marginBottom: '1.25rem' }}>
      <div className="card-title">🎯 What are we trying to achieve?</div>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
        Tell us what the numbers in the table represent and which way to optimise.
        The solver converts your choice into the correct mathematical objective, and
        the explanation records exactly what you asked for.
      </p>

      {/* Step 1: what do the values represent */}
      <label className="form-label">1 · What do these numbers represent?</label>
      <div className="method-pills" style={{ flexWrap: 'wrap' }}>
        {VALUE_TYPES.map((v) => (
          <button
            key={v.id}
            className={`method-pill ${valueType === v.id ? 'selected' : ''}`}
            onClick={() => changeValueType(v.id)}
          >
            {v.icon} {v.label}
          </button>
        ))}
      </div>

      {valueType === 'other' && (
        <div className="form-group" style={{ marginTop: '0.75rem', marginBottom: 0 }}>
          <input
            className="form-control"
            placeholder="Describe what the values represent (e.g. carbon emissions)"
            value={otherDesc}
            onChange={(e) => changeOther(e.target.value)}
          />
        </div>
      )}

      {/* Step 2: confirmation / override */}
      {!intent && (
        <div style={{ marginTop: '1rem' }}>
          <label className="form-label">2 · How should the solver optimise the total?</label>

          {lockedMin ? (
            <div className="alert alert-info" style={{ marginBottom: '0.5rem' }}>
              <span className="alert-icon">ℹ️</span>
              This solver works with transportation costs, so it always{' '}
              <strong>minimises</strong> the total.
            </div>
          ) : recommendable ? (
            <div className="alert alert-info" style={{ marginBottom: '0.5rem' }}>
              <span className="alert-icon">💡</span>
              Since these numbers represent <strong>{vtLabel}</strong>, I recommend we{' '}
              <strong>{DIR_LABEL[recommended].plain} the total {vtLabel}</strong>
              {' '}({DIR_LABEL[recommended].verb}).
            </div>
          ) : (
            <div className="alert alert-info" style={{ marginBottom: '0.5rem' }}>
              <span className="alert-icon">❓</span>
              Since you described the values yourself, please tell us the direction directly.
            </div>
          )}

          <div className="method-pills" style={{ marginTop: '0.25rem' }}>
            {recommendable && (
              <button className="method-pill selected" onClick={() => choose(recommended, false)}>
                ✓ Yes, {DIR_LABEL[recommended].plain}
              </button>
            )}
            {recommendable && !lockedMin && (
              <button className="method-pill" onClick={() => choose(opposite, true)}>
                No, {DIR_LABEL[opposite].plain} instead
              </button>
            )}
            {!recommendable && (
              <>
                <button className="method-pill selected" onClick={() => choose('minimise', false)}>
                  Minimise (reduce) the total
                </button>
                <button className="method-pill" onClick={() => choose('maximise', false)}>
                  Maximise (increase) the total
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Confirmation chip */}
      {intent && (
        <div
          className="alert alert-success"
          style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'space-between' }}
        >
          <span>
            <span className="alert-icon">✅</span>
            Goal: {DIR_LABEL[intent].plain} the total {vtLabel}
            {recommended && intent !== recommended && (
              <span className="badge badge-purple" style={{ marginLeft: '0.5rem' }}>Overridden recommendation</span>
            )}
            {recommended && intent === recommended && (
              <span className="badge badge-green" style={{ marginLeft: '0.5rem' }}>Confirmed</span>
            )}
          </span>
          <button className="btn btn-sm" onClick={reset}>Change</button>
        </div>
      )}
    </div>
  )
}

export function ObjectiveTrail({ objective }) {
  if (!objective) return null

  const rawVt = objective.value_type
  const vt = rawVt === 'other'
    ? (objective.other_description || 'value')
    : (rawVt || '')
  const direction = objective.resolved_direction || objective.intent
  const dirLabel = direction === 'maximise' ? 'maximise (increase)' : 'minimise (reduce)'
  const overridden = objective.overridden

  return (
    <div className="card card-purple" style={{ marginBottom: '1.5rem' }}>
      <div className="card-title">🎯 Objective</div>
      <p style={{ fontSize: '0.9rem', color: 'var(--gray-800)', lineHeight: 1.7 }}>
        The solver was asked to{' '}
        <strong>{vt ? dirLabel : 'minimise (reduce) the objective value'}</strong>
        {vt && <><strong> the total {vt}</strong></>}.
        {overridden && (
          <span className="badge badge-purple" style={{ marginLeft: '0.5rem' }}>
            You overrode the recommendation
          </span>
        )}
        {!overridden && objective.confirmed && (
          <span className="badge badge-green" style={{ marginLeft: '0.5rem' }}>
            Recommendation confirmed
          </span>
        )}
      </p>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginTop: '0.25rem' }}>
        This choice was recorded and reflected in the explanation below.
      </p>
    </div>
  )
}
