import React from 'react';
import { NavLink, Route, Routes, useLocation } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import JobPage from './pages/JobPage';
import ReportPage from './pages/ReportPage';

function Mark(): JSX.Element {
  return <div className="brand-mark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

export default function App(): JSX.Element {
  const location = useLocation();
  const inJob = location.pathname.startsWith('/jobs/');
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Mark /><span>rosetta</span><span className="brand-beta">BETA</span></div>
        <div className="side-label">WORKSPACE</div>
        <NavLink to="/" end className={({isActive}) => 'nav-item' + (isActive ? ' active' : '')}>
          <span className="nav-icon">⌂</span><span>Overview</span>
        </NavLink>
        <div className={'nav-item' + (inJob ? ' active' : '')}><span className="nav-icon">◈</span><span>Projects</span></div>
        <div className="side-bottom">
          <div className="status-dot" />
          <div><strong>Local workspace</strong><small>Running on this device</small></div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{inJob ? 'Project' : 'Overview'}</strong></div>
          <div className="topbar-right"><span className="secure-indicator"><i /> Local environment</span><div className="avatar">R</div></div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/jobs/:id" element={<JobPage />} />
            <Route path="/jobs/:id/report" element={<ReportPage />} />
          </Routes>
        </div>
        <footer className="app-footer"><span>ROSETTA</span><span>Rebuild interfaces. Verify every detail.</span><span>v1.0</span></footer>
      </main>
    </div>
  );
}