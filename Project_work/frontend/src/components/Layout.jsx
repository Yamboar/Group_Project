import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Home',            icon: '🏠', to: '/',               end: true  },
  { label: 'Transportation',  icon: '🚚', to: '/transportation',  end: false },
  { label: 'Assignment',      icon: '📋', to: '/assignment',      end: false },
  { label: 'Saved Problems',  icon: '💾', to: '/saved',           end: false },
  { label: 'Help',            icon: '❓', to: '/help',            end: false },
]

function Layout() {
  return (
    <div className="layout">
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-logo">
            <div className="sidebar-brand-icon">⚡</div>
            <div>
              <h2>XAI-OR</h2>
            </div>
          </div>
          <p>Explainable AI · Operations Research</p>
        </div>

        <div className="sidebar-divider" />

        {/* Nav */}
        <nav>
          <div className="nav-section-label">Navigation</div>
          <ul className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => (isActive ? 'active' : '')}
                >
                  {({ isActive }) => (
                    <>
                      <span className="nav-icon">{item.icon}</span>
                      <span>{item.label}</span>
                      {isActive && <span className="nav-active-pill" />}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <p className="sidebar-footer-text">
            XAI-OR System<br />
            Powered by Pure Python Algorithms
          </p>
        </div>
      </aside>

      <main className="main-content">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default Layout
