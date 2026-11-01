import { useState } from 'react'

function Help() {
  const [tab, setTab] = useState('transportation')

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '1.75rem' }}>📚</span>
          <h1 className="page-title">
            <span className="page-title-gradient">Help</span> &amp; Documentation
          </h1>
        </div>
        <p className="page-subtitle">Method explanations, edge-case semantics, and how to use the system</p>
      </div>

      <div className="tabs">
        {[
          { id: 'transportation', label: '🚚 Transportation' },
          { id: 'assignment',     label: '📋 Assignment' },
          { id: 'guide',          label: '🛠️ How to Use' },
          { id: 'about',          label: 'ℹ️ About' },
        ].map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'transportation' && <TransportationHelp />}
      {tab === 'assignment'     && <AssignmentHelp />}
      {tab === 'guide'          && <GuideHelp />}
      {tab === 'about'          && <AboutHelp />}
    </div>
  )
}

/* ───────── Expandable accordion ─────────────────── */
function Expandable({ title, icon, children, accentColor }) {
  return (
    <div className="expander" style={{ borderLeft: `4px solid ${accentColor ?? 'var(--brand-purple)'}` }}>
      <details>
        <summary className="expander-header">
          {icon && <span style={{ marginRight: '0.5rem' }}>{icon}</span>}
          {title}
        </summary>
        <div className="expander-body">{children}</div>
      </details>
    </div>
  )
}

/* ───────── Transportation help ──────────────────── */
function TransportationHelp() {
  return (
    <div>
      {/* Intro card */}
      <div className="card card-purple" style={{ marginBottom: '1.25rem' }}>
        <div className="card-title">🚚 What is a Transportation Problem?</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
          A transportation problem determines the cheapest way to ship goods from
          <strong> m sources</strong> (with known supply) to <strong>n destinations</strong>{' '}
          (with known demand), minimizing total transportation cost.
        </p>
        <div
          className="mono"
          style={{ marginTop: '0.875rem', fontSize: '0.78rem', padding: '0.875rem 1rem' }}
        >
          {`Minimize  Z = Σᵢ Σⱼ  cᵢⱼ · xᵢⱼ\n\nSubject to:\n  Σⱼ xᵢⱼ = sᵢ   (supply at source i)\n  Σᵢ xᵢⱼ = dⱼ   (demand at dest j)\n     xᵢⱼ ≥ 0`}
        </div>
      </div>

      <h2 style={{ marginTop: '0' }}>Concepts &amp; Input Semantics</h2>

      <Expandable title="Balancing the Problem (Dummy Rows / Columns)" icon="⚖️" accentColor="var(--brand-purple)">
        <StepList items={[
          'Compare total supply vs total demand.',
          'If supply &lt; demand → a <strong>dummy source</strong> with the missing units and 0 cost is added.',
          'If demand &lt; supply → a <strong>dummy destination</strong> with the surplus units and 0 cost is added.',
          'Dummy routes cost 0 and are never restricted — the solver always stays feasible.',
          'The UI shows exactly which dummy was added in the solution explainer and the event log.',
        ]} />
      </Expandable>

      <Expandable title="Restricted Routes (forbidden cells)" icon="🚫" accentColor="var(--brand-orange)">
        <p style={{ fontSize: '0.88rem', lineHeight: 1.7, marginBottom: '0.5rem' }}>
          A route can be <strong>forbidden entirely</strong> — no material may ever flow on it.
          Click the 🚫 toggle on any cell to mark it <strong>Restricted</strong> (the cell turns hatched).
        </p>
        <StepList items={[
          'Restricted is a <em>separate cell state</em> — it is never encoded as 0, a negative value, or a big number.',
          'Restricted cells are excluded from every method: NW Corner, Least Cost, VAM, and Stepping Stone.',
          'Restricted cells are <strong>exempt from value validation</strong> — they may hold any placeholder.',
          '<strong>0 is a valid cost</strong> and is never treated as blank.',
          'Blank or negative values are rejected — mark the cell Restricted instead.',
          'Feasibility is checked: a source with supply but no open route, a destination unreachable, capacity shortfalls, or a table split into disconnected components all produce clear errors.',
        ]} />
      </Expandable>

      <Expandable title="Edge-Case Semantics" icon="⚠️" accentColor="var(--brand-teal)">
        <InfoRow label="0 supply / 0 demand" value="Accepted — treated as dummy entries, they get no allocation. You are always warned" />
        <InfoRow label="Negative costs" value="Rejected with guidance — costs must be ≥ 0; use Restricted to forbid a route" />
        <InfoRow label="Degenerate initial BFS" value="Detected and fixed with ε-perturbations; reported, never silent" />
        <InfoRow label="Degenerate pivots" value="Detected and counted (degenerate_pivot_count); ε keeps a valid basis" />
        <InfoRow label="Unbalanced problems" value="Automatically balanced with dummy rows/columns (see above)" />
        <div style={{ fontSize: '0.85rem', color: 'var(--gray-700)', lineHeight: 1.75, marginTop: '0.5rem' }}>
          <strong>Degeneracy:</strong> a basis needs <strong>m+n−1</strong> basic cells. A degenerate pivot happens when two
          (or more) cells tie at the minimum θ, so more than one basic cell drops to zero at once.
          The engine then adds tiny ε-permutations to keep a valid spanning-tree basis — never altering
          real shipments (ε cells always report as 0). Every occurrence is surfaced as a warning and in
          the event log.
        </div>
      </Expandable>

      <h2>Initial Solution Methods</h2>

      <Expandable title="North-West Corner Method" icon="↖️" accentColor="var(--brand-purple)">
        <InfoRow label="Purpose" value="Find an initial basic feasible solution (BFS)" />
        <InfoRow label="Considers costs?" value="No — purely positional" />
        <InfoRow label="Solution quality" value="Often poor; serves as a starting point for optimization" />
        <div className="section-divider" style={{ margin: '0.75rem 0' }}>Algorithm</div>
        <ol style={{ paddingLeft: '1.25rem', lineHeight: 2 }}>
          <li>Start at cell (1,1) — the top-left corner.</li>
          <li>Allocate min(supply<sub>i</sub>, demand<sub>j</sub>).</li>
          <li>If supply exhausted → move down. If demand satisfied → move right.</li>
          <li>If both exhausted → move diagonally (degenerate step).</li>
          <li>Repeat until all supply and demand are fulfilled.</li>
        </ol>
      </Expandable>

      <Expandable title="Least Cost Method" icon="💰" accentColor="var(--brand-blue)">
        <InfoRow label="Purpose" value="Cost-guided initial BFS" />
        <InfoRow label="Considers costs?" value="Yes — always picks the cheapest available cell" />
        <InfoRow label="Solution quality" value="Better than NWC; usually close to optimal" />
        <div className="section-divider" style={{ margin: '0.75rem 0' }}>Algorithm</div>
        <ol style={{ paddingLeft: '1.25rem', lineHeight: 2 }}>
          <li>Find the cell with the minimum cost among all available cells.</li>
          <li>Allocate min(supply, demand) to that cell.</li>
          <li>Remove exhausted row/column; repeat.</li>
          <li>Tie-break: smallest row index, then smallest column index.</li>
        </ol>
      </Expandable>

      <Expandable title="Vogel's Approximation Method (VAM)" icon="📐" accentColor="var(--brand-teal)">
        <InfoRow label="Purpose" value="Near-optimal initial BFS using opportunity costs" />
        <InfoRow label="Considers costs?" value="Yes — with penalty (regret) analysis" />
        <InfoRow label="Solution quality" value="Usually very close to optimal; best of the three methods" />
        <div className="section-divider" style={{ margin: '0.75rem 0' }}>Algorithm</div>
        <ol style={{ paddingLeft: '1.25rem', lineHeight: 2 }}>
          <li>For each row: penalty = 2nd smallest cost − smallest cost.</li>
          <li>For each column: same calculation.</li>
          <li>Select the row/column with the highest penalty.</li>
          <li>Allocate to the cheapest cell in that row/column.</li>
          <li>Update and repeat until complete.</li>
        </ol>
      </Expandable>

      <h2>Optimization</h2>
      <Expandable title="Stepping Stone / MODI Method" icon="🪨" accentColor="var(--brand-green)">
        <InfoRow label="Purpose" value="Optimize any BFS to global optimality" />
        <InfoRow label="Basis" value="Maintains a spanning-tree basis (transportation simplex)" />
        <InfoRow label="Guarantee" value="Provably optimal when all improvement indices ≥ 0" />
        <div className="section-divider" style={{ margin: '0.75rem 0' }}>Algorithm</div>
        <ol style={{ paddingLeft: '1.25rem', lineHeight: 2 }}>
          <li>Build a spanning-tree basis from the current BFS.</li>
          <li>Compute dual potentials u, v via the basis tree.</li>
          <li>Compute reduced costs: c̄ᵢⱼ = cᵢⱼ − uᵢ − vⱼ for each non-basic cell.</li>
          <li>If all c̄ᵢⱼ ≥ 0, solution is <strong>optimal</strong>. Stop.</li>
          <li>Enter the non-basic cell with the most negative c̄ᵢⱼ.</li>
          <li>Find its unique loop in the basis tree; adjust allocations.</li>
          <li>Rebuild the basis and repeat.</li>
        </ol>
        <div className="alert alert-warning" style={{ marginTop: '0.75rem' }}>
          <span className="alert-icon">⚠️</span>
          <span>
            <strong>Degeneracy</strong> is handled automatically with ε-perturbations and is always
            reported: the warning banner, the <em>Solution</em> summary, and the event log tell you when
            the initial solution or specific pivots were degenerate. It is expected behaviour, not an error.
          </span>
        </div>
      </Expandable>

      <Expandable title="Alternative Optimal Solutions" icon="🎯" accentColor="var(--brand-blue)">
        <p style={{ fontSize: '0.88rem', lineHeight: 1.7 }}>
          If a non-basic cell has an improvement index of exactly <strong>0</strong> at optimality, the
          same total cost can be achieved by a different allocation. The engine lists those cells and
          shows them in the XAI summary ("Alternative optimal solutions exist at cells …"), and the
          event log records every zero-index cell for the final iteration.
        </p>
      </Expandable>
    </div>
  )
}

/* ───────── Assignment help ──────────────────────── */
function AssignmentHelp() {
  return (
    <div>
      <div className="card card-blue" style={{ marginBottom: '1.25rem' }}>
        <div className="card-title">📋 What is an Assignment Problem?</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
          An assignment problem assigns <strong>n workers</strong> to <strong>n jobs</strong>{' '}
          (one-to-one) minimizing total cost. It is a special balanced transportation problem
          where every supply and demand equals 1.
        </p>
        <div
          className="mono"
          style={{ marginTop: '0.875rem', fontSize: '0.78rem', padding: '0.875rem 1rem' }}
        >
          {`Minimize  Z = Σᵢ Σⱼ  cᵢⱼ · xᵢⱼ\n\nSubject to:\n  Σⱼ xᵢⱼ = 1   (each worker does one job)\n  Σᵢ xᵢⱼ = 1   (each job gets one worker)\n     xᵢⱼ ∈ {0,1}`}
        </div>
      </div>

      <h2 style={{ marginTop: '0' }}>Concepts &amp; Input Semantics</h2>

      <Expandable title="Restricted Assignments (forbidden pairings)" icon="🚫" accentColor="var(--brand-orange)">
        <p style={{ fontSize: '0.88rem', lineHeight: 1.7, marginBottom: '0.5rem' }}>
          Click any cell's 🚫 toggle to forbid that worker→job pairing. The cell becomes{' '}
          <strong>Restricted</strong> (hatched) and can never end up in the final assignment.
        </p>
        <StepList items={[
          'Restricted is a separate cell state — never encoded as 0, a negative value, or a big number.',
          'Restricted cells are excluded from row/column reduction, zero covering, matrix adjustment, and the final matching.',
          'Restricted cells are exempt from value validation — they may hold any placeholder.',
          '<strong>0 is a valid cost</strong> and is never treated as blank.',
          'Blank or negative values are rejected — mark the cell Restricted instead (the UI offers a bulk "Mark as Restricted" button).',
          'Feasibility is verified via bipartite matching: if too many pairings are forbidden, you get a clear error (cell cut-off or Hall shortfall).',
        ]} />
      </Expandable>

      <Expandable title="Balancing &amp; Maximization" icon="⚖️" accentColor="var(--brand-blue)">
        <StepList items={[
          '<strong>Rectangular matrices</strong> are supported — dummy rows or columns with cost 0 are added automatically to square the table.',
          '<strong>Maximization</strong> (profit) is transformed to minimization with M − cᵢⱼ using the largest value in the matrix.',
          'Dummy rows/columns are never restricted and never affect the reported cost/profit.',
          'The final reported total always uses the <em>original</em> values — you never see transformed numbers in the result.',
        ]} />
      </Expandable>

      <Expandable title="All Optimal Plans (enumeration)" icon="🎯" accentColor="var(--brand-green)">
        <p style={{ fontSize: '0.88rem', lineHeight: 1.7, marginBottom: '0.5rem' }}>
          After the Hungarian Method finishes, every <strong>perfect matching on the zero cells</strong>{' '}
          of the final reduced matrix is also optimal. The engine <strong>counts and enumerates</strong>{' '}
          the full set — a classic exam question ("how many different optimal plans are there?").
        </p>
        <StepList items={[
          'The result shows e.g. "There are 4 different optimal assignment plans".',
          'Every distinct plan is listed in the Solution tab as its own table.',
          'Plans that differ only in which <em>dummy</em> placeholder fills a slot are collapsed into one real plan.',
          'When many plans exist, the listing is capped (first 100 shown); the count stays exact for square problems.',
          'The XAI summary and the event log also mention the count and the alternative cells.',
        ]} />
      </Expandable>

      <h2>Algorithm</h2>

      <Expandable title="Hungarian Method" icon="🇭🇺" accentColor="var(--brand-purple)">
        <InfoRow label="Complexity" value="O(n³)" />
        <InfoRow label="Guarantee" value="Globally optimal" />
        <InfoRow label="Rectangular support" value="Yes — dummy rows/columns added automatically" />
        <InfoRow label="Maximization" value="Transformed to minimization via max − cᵢⱼ" />
        <div className="section-divider" style={{ margin: '0.75rem 0' }}>Algorithm</div>
        <ol style={{ paddingLeft: '1.25rem', lineHeight: 2 }}>
          <li><strong>Balance</strong> — add dummy rows/cols if rectangular.</li>
          <li><strong>Row reduction</strong> — subtract minimum of each row.</li>
          <li><strong>Column reduction</strong> — subtract minimum of each column.</li>
          <li><strong>Cover zeros</strong> — find minimum number of lines to cover all zeros (König's theorem: equals max matching).</li>
          <li>If lines = n → optimal assignment found. Go to step 7.</li>
          <li><strong>Adjust</strong> — subtract smallest uncovered value; add it at line intersections. Repeat from step 4.</li>
          <li><strong>Extract</strong> — find a complete assignment of independent zeros.</li>
          <li>Compute cost using the <em>original</em> matrix.</li>
          <li><strong>Enumerate</strong> — count and list all perfect matchings on the final zero cells (all optimal plans).</li>
        </ol>
      </Expandable>

      <div className="alert alert-info" style={{ marginBottom: 0 }}>
        <span className="alert-icon">ℹ️</span>
        <span>
          Every Hungarian step (reduction, covering, adjustment, final assignment) is shown in the{' '}
          <em>Steps</em> tab, along with the zero cells after each step and the covering lines used.
        </span>
      </div>
    </div>
  )
}

/* ───────── How to Use guide ─────────────────────── */
function GuideHelp() {
  return (
    <div>
      <div className="card card-teal" style={{ marginBottom: '1.25rem' }}>
        <div className="card-title">🛠️ How to Use the System</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-700)', lineHeight: 1.7 }}>
          Both solvers follow the same flow: <strong>Input</strong> → <strong>Solution</strong> →{' '}
          <strong>Steps</strong> → <strong>Saved</strong>. Below are the exact steps for each page.
        </p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">🚚 Solving a Transportation Problem</div>
          <StepList items={[
            'Open the Transportation page and set the number of <strong>Sources</strong> and <strong>Destinations</strong>.',
            'Enter the cost per unit for every route. <strong>0 is a valid cost</strong>.',
            'To forbid a route, click its 🚫 so the cell turns hatched (Restricted).',
            'Optionally set custom Source/Destination names.',
            'Pick an initial method: North-West Corner, Least Cost, or VAM.',
            'Tick <strong>Optimize with Stepping Stone</strong> to reach global optimality.',
            'Click <strong>Solve</strong> → review the Solution tab, then the Steps tab for the full event log.',
          ]} />
        </div>

        <div className="card">
          <div className="card-title">📋 Solving an Assignment Problem</div>
          <StepList items={[
            'Open the Assignment page and set the number of <strong>Workers</strong> and <strong>Jobs</strong>.',
            'Enter costs (or profits) for every worker→job pairing. <strong>0 is a valid cost</strong>.',
            'To forbid a pairing, click its 🚫 (hatched = Restricted).',
            'Optionally set custom names and choose an objective (minimize cost or maximize profit).',
            'For rectangular matrices, dummy rows/columns are added automatically.',
            'Click <strong>Solve</strong> → the Solution tab shows the optimal assignment and — if more than one optimum exists — <strong>all optimal plans</strong>.',
            'The Steps tab walks through row reduction, column reduction, zero covering, and adjustments.',
          ]} />
        </div>
      </div>

      <h2>Reading the Results</h2>
      <Expandable title="Solution Tab" icon="✅" accentColor="var(--brand-green)">
        <StepList items={[
          '<strong>Stat cards</strong>: initial/optimized or final cost, number of assignments/allocations, and verification status (Passed/Failed).',
          '<strong>Restricted cells</strong> are listed up front so you can confirm every forbidden pairing is present.',
          '<strong>Warnings</strong> (amber) are shown for edge cases: 0-supply/0-demand rows, degeneracy, alternatives, iteration-limit — warnings never silently hide.',
          '<strong>XAI Explanations</strong>: a plain-language summary, the key decisions made step by step, and why the solution is optimal.',
          '<strong>Plain-English interpretation</strong> restates the result in words ("assign Worker 1 to do Job 3 …").',
        ]} />
      </Expandable>

      <Expandable title="Steps / Details Tab" icon="🔍" accentColor="var(--brand-blue)">
        <StepList items={[
          '<strong>Get the detailed algorithm trace</strong>: every matrix snapshot before/after each operation.',
          'Transportation: every allocation decision (with alternatives considered and tie-breaking reasons), every Stepping Stone iteration (loop, θ, entering cell, improvement index), and the final reduced costs.',
          'Assignment: every Hungarian step with the covering lines and the zero positions.',
          '<strong>Event Log</strong>: a chronological list of everything the solver did, including degeneracy events and alternative-optimum detection.',
        ]} />
      </Expandable>

      <Expandable title="Saved Problems &amp; History" icon="💾" accentColor="var(--brand-purple)">
        <StepList items={[
          'Every solved problem is stored automatically in the database (see the <strong>Saved</strong> page).',
          'Transportation records keep the problem, the initial and optimized allocations, and degeneracy/optimality flags.',
          'Assignment records keep the problem, the balanced matrix, restricted cells, and the final assignment.',
          'Open any record to re-view the full details — the same tables and explanations as immediately after solving.',
          'If the database is unavailable, the result is still returned with a warning; nothing is silently lost.',
        ]} />
      </Expandable>

      <h2>Conventions &amp; Tips</h2>
      <div className="grid-2">
        <div className="card card-purple">
          <div className="card-title">💡 Cell Semantics</div>
          <StepList items={[
            '<strong>0</strong> = a valid zero-cost cell, never treated as blank.',
            '<strong>Positive</strong> = a valid cost/profit.',
            '<strong>Blank / negative / non-numeric</strong> = rejected with guidance; mark the cell Restricted instead.',
            '<strong>Restricted (🚫, hatched)</strong> = the route/pairing is forbidden and excluded from every step.',
          ]} />
        </div>
        <div className="card card-teal">
          <div className="card-title">✅ Verification</div>
          <StepList items={[
            'Every solution is independently re-checked: constraints, cost, and (for assignment) the one-to-one property.',
            'Restricted cells can never be selected — the verifier asserts this explicitly.',
            'Mismatches are surfaced as warnings, never silently corrected.',
            'Feasibility errors (cut-off rows, capacity shortfalls, disconnected tables) stop the solve with a clear message.',
          ]} />
        </div>
      </div>
    </div>
  )
}

/* ───────── About ────────────────────────────────── */
function AboutHelp() {
  return (
    <div>
      <div className="hero-banner" style={{ marginBottom: '1.5rem' }}>
        <div className="hero-badge">Academic Research Project</div>
        <h1 style={{ fontSize: '1.4rem' }}>
          Explainable AI Operations Research System
        </h1>
        <p style={{ marginTop: '0.5rem' }}>
          Every calculation is traceable. Every decision is explained.
        </p>
      </div>

      <div className="grid-2">
        <div className="card card-purple">
          <div className="card-title">🔬 Core Principles</div>
          <ul className="feature-list">
            {[
              'No black-box solvers — pure Python implementations',
              'Every step captured as a structured event',
              'XAI engine converts events to natural-language explanations',
              'Full verification of all solutions',
              'Alternative optima counted and enumerated, not just flagged',
              'Restricted cells and degeneracy handled as first-class, explained states',
              'Solution history stored in relational database',
            ].map((item) => (
              <li key={item}>
                <span className="feature-list-bullet">●</span>
                <span style={{ fontSize: '0.875rem', color: 'var(--gray-600)' }}>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card card-teal">
          <div className="card-title">⚙️ Technology Stack</div>
          <ul className="feature-list">
            {[
              ['React 19 + Vite', 'Frontend'],
              ['FastAPI', 'REST API'],
              ['Python 3.10+', 'OR + XAI Engines'],
              ['SQLAlchemy + MySQL', 'Persistence'],
              ['pytest', 'Automated Testing'],
            ].map(([tech, role]) => (
              <li key={tech}>
                <span className="feature-list-bullet" style={{ color: 'var(--brand-teal)' }}>●</span>
                <span style={{ fontSize: '0.875rem' }}>
                  <strong>{tech}</strong>
                  <span style={{ color: 'var(--text-muted)', marginLeft: '0.4rem' }}>{role}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <h2>Implemented Algorithms</h2>
      <div className="grid-2" style={{ marginTop: '0' }}>
        {[
          { name: 'North-West Corner',     type: 'Transportation initial', color: 'badge-purple' },
          { name: 'Least Cost Method',     type: 'Transportation initial', color: 'badge-purple' },
          { name: "Vogel's Approximation", type: 'Transportation initial', color: 'badge-purple' },
          { name: 'Stepping Stone / MODI', type: 'Transportation optimize', color: 'badge-blue' },
          { name: 'Hungarian Method',      type: 'Assignment optimal',     color: 'badge-teal'   },
          { name: 'All-optimal-plans enumeration', type: 'Assignment results', color: 'badge-green' },
          { name: 'Restricted-cell handling',       type: 'Both modules',        color: 'badge-orange' },
          { name: 'Degeneracy ε-handling',          type: 'Transportation',      color: 'badge-orange' },
          { name: 'Bipartite feasibility check',    type: 'Both modules',        color: 'badge-blue'   },
          { name: 'What-if re-solving (API)',       type: 'Both modules',        color: 'badge-purple' },
        ].map((alg) => (
          <div
            key={alg.name}
            className="card"
            style={{ padding: '0.875rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}
          >
            <span className={`badge ${alg.color}`} style={{ flexShrink: 0 }}>●</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.875rem' }}>{alg.name}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{alg.type}</div>
            </div>
          </div>
        ))}
      </div>

      <h2>Pages &amp; Routes</h2>
      <div className="grid-2" style={{ marginTop: '0' }}>
        {[
          { name: 'Home',           route: '/',               desc: 'Overview, quick stats, feature highlights' },
          { name: 'Transportation', route: '/transportation', desc: '3xN-any-size shipping solver with optimization' },
          { name: 'Assignment',     route: '/assignment',     desc: 'Hungarian Method with all-optimal-plan listing' },
          { name: 'Saved',          route: '/saved',          desc: 'Saved problems, history, details, deletion' },
          { name: 'Help',           route: '/help',           desc: 'This page — methods, semantics, and guides' },
        ].map((p) => (
          <div
            key={p.name}
            className="card"
            style={{ padding: '0.875rem', marginBottom: '0.5rem' }}
          >
            <div style={{ fontWeight: 700, fontSize: '0.875rem' }}>
              {p.name} <code style={{ fontSize: '0.75rem', color: 'var(--brand-blue)' }}>{p.route}</code>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{p.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ───────── Utility: info row ─────────────────────── */
function InfoRow({ label, value }) {
  return (
    <div
      style={{
        display: 'flex',
        gap: '0.75rem',
        padding: '0.35rem 0',
        borderBottom: '1px solid var(--border)',
        fontSize: '0.875rem',
      }}
    >
      <span style={{ color: 'var(--text-secondary)', width: 160, flexShrink: 0 }}>{label}</span>
      <span style={{ color: 'var(--gray-800)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

/* ───────── Utility: step list ────────────────────── */
function StepList({ items }) {
  return (
    <ol style={{ paddingLeft: '1.4rem', lineHeight: 1.9, fontSize: '0.875rem', margin: 0 }}>
      {items.map((item, i) => (
        <li key={i} style={{ color: 'var(--gray-800)' }}>
          <span
            dangerouslySetInnerHTML={{ __html: item }}
            style={{ color: 'var(--gray-800)' }}
          />
        </li>
      ))}
    </ol>
  )
}

export default Help