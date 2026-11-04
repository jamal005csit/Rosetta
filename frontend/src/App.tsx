import React from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import JobPage from './pages/JobPage';
import ReportPage from './pages/ReportPage';
import Icon from './components/Icon';

function Mark(): JSX.Element {
  return <div className="brand-mark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

export default function App(): JSX.Element {
  const location = useLocation();
  const inJob = location.pathname.startsWith('/jobs/');
  return (
    <div className="app-shell">
      <a className="skip-link" href="#content">Skip to Content</a>
      <aside className="sidebar glass">
        <div className="brand"><Mark /><span className="brand-name">Rosetta</span><span className="brand-beta">Beta</span></div>
        <div className="side-label">Workspace</div>
        <nav className="side-nav" aria-label="Primary">
          <NavLink to="/" end aria-label="Overview" className={({isActive}) => 'nav-item' + (isActive ? ' active' : '')}>
            <span className="nav-icon"><Icon name="house" size={20} /></span><span className="nav-text">Overview</span>
          </NavLink>
          <Link to="/" aria-label="Projects" aria-current={inJob ? 'page' : undefined} className={'nav-item' + (inJob ? ' active' : '')}>
            <span className="nav-icon"><Icon name="stack" size={20} /></span><span className="nav-text">Projects</span>
          </Link>
        </nav>
        <div className="side-bottom">
          <div className="status-dot" />
          <div className="side-bottom-text"><strong>Local Workspace</strong><small>Running on this device</small></div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-brand"><Mark /><span>Rosetta</span></div>
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron-right" size={12} /><strong>{inJob ? 'Project' : 'Overview'}</strong></div>
          <div className="topbar-right"><span className="secure-indicator"><i /> Local environment</span><div className="avatar" aria-hidden="true">R</div></div>
        </header>
        <div className="page-content" id="content" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/jobs/:id" element={<JobPage />} />
            <Route path="/jobs/:id/report" element={<ReportPage />} />
          </Routes>
        </div>
        <footer className="app-footer"><span>Rosetta</span><span>Rebuild interfaces. Verify every detail.</span><span>v1.0</span></footer>
      </main>
    </div>
  );
}
