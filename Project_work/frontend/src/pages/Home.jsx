import { Link } from 'react-router-dom'

function Home() {
  return (
    <div>
      {/* Hero */}
      <div className="hero-banner">
        <div className="hero-badge">⚡ Explainable AI · Operations Research</div>
        <h1>XAI-OR Solver System</h1>
        <p>
          Solve <strong>Transportation</strong> and <strong>Assignment</strong>{' '}
          optimization problems with full transparency into every algorithmic decision.
          Every calculation is traceable, every step is explained.
        </p>
      </div>

      {/* Quick stats */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4,1fr)', marginBottom: '1.5rem' }}>
        {[
          { icon: '🚚', value: '3', label: 'Initial Methods',  cls: 'stat-card-purple' },
          { icon: '⚙️', value: '1', label: 'Optimizer',        cls: 'stat-card-blue'   },
          { icon: '📋', value: '1', label: 'Assignment Solver', cls: 'stat-card-green'  },
          { icon: '🔍', value: '100%', label: 'Traceable Steps', cls: 'stat-card-warm'   },
        ].map((s) => (
          <div key={s.label} className={`stat-card ${s.cls}`}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Feature cards */}
      <div className="grid-2">
        <div className="feature-card feature-card-purple">
          <div className="feature-card-icon">🚚</div>
          <h3>Transportation Problems</h3>
          <ul className="feature-list">
            {[
              ['North-West Corner', 'Initial feasible solution'],
              ['Least Cost Method', 'Cost-guided initial allocation'],
              ["Vogel's Approximation", 'Penalty-based, near-optimal start'],
              ['Stepping Stone',    'Optimize to global optimality'],
            ].map(([name, desc]) => (
              <li key={name}>
                <span className="feature-list-bullet">●</span>
                <span>
                  <strong>{name}</strong>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', display: 'block' }}>
                    {desc}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <Link to="/transportation" className="btn btn-primary btn-sm" style={{ marginTop: '1.25rem' }}>
            Open Solver →
          </Link>
        </div>

        <div className="feature-card feature-card-teal">
          <div className="feature-card-icon">📋</div>
          <h3>Assignment Problems</h3>
          <ul className="feature-list">
            {[
              ['Hungarian Method',        'Provably optimal assignment'],
              ['Minimization & Max',      'Both objective types supported'],
              ['Rectangular Matrices',    'Auto-balanced with dummy rows/cols'],
              ['Full Matrix Tracking',    'Every reduction step recorded'],
            ].map(([name, desc]) => (
              <li key={name}>
                <span className="feature-list-bullet" style={{ color: 'var(--brand-teal)' }}>●</span>
                <span>
                  <strong>{name}</strong>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', display: 'block' }}>
                    {desc}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <Link to="/assignment" className="btn btn-primary btn-sm" style={{ marginTop: '1.25rem' }}>
            Open Solver →
          </Link>
        </div>
      </div>

      {/* Architecture */}
      <h2 style={{ marginTop: '2rem' }}>System Architecture</h2>
      <div className="arch-diagram">
        {[
          { label: 'Presentation', content: 'React + Vite  ·  Component UI', tag: 'Frontend', tagColor: '#7c3aed' },
          { arrow: true },
          { label: 'API Gateway',  content: 'FastAPI  ·  REST Endpoints',     tag: 'Backend',  tagColor: '#2563eb' },
          { arrow: true },
          { label: 'OR Engine',    content: 'Transportation  ·  Assignment  ·  Pure Python', tag: 'Core', tagColor: '#0891b2' },
          { arrow: true },
          { label: 'XAI Engine',   content: 'Event capture  ·  Explanation generation',      tag: 'Explainability', tagColor: '#059669' },
          { arrow: true },
          { label: 'Data Layer',   content: 'SQLAlchemy ORM  ·  MySQL Database',             tag: 'Persistence', tagColor: '#ea580c' },
        ].map((layer, i) =>
          layer.arrow ? (
            <div key={i} className="arch-arrow">  └──▶</div>
          ) : (
            <div key={i} className="arch-layer">
              <span className="arch-layer-label">{layer.label}</span>
              <span className="arch-layer-content">{layer.content}</span>
              <span
                className="arch-layer-tag"
                style={{
                  background: `${layer.tagColor}22`,
                  color: layer.tagColor,
                  border: `1px solid ${layer.tagColor}44`,
                }}
              >
                {layer.tag}
              </span>
            </div>
          ),
        )}
      </div>

      {/* XAI callout */}
      <div className="card card-purple" style={{ marginTop: '1.5rem' }}>
        <div className="card-title">🔍 Why Explainable?</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-600)', lineHeight: 1.7 }}>
          Every algorithmic decision — from the initial allocation choice to each stepping stone pivot —
          is captured as a structured event and converted into a human-readable explanation.
          You can inspect <em>why</em> every unit was allocated to every cell, and
          <em> why</em> the solution is guaranteed to be optimal.
        </p>
      </div>
    </div>
  )
}

export default Home
