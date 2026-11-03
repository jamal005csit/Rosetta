import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import JobPage from './pages/JobPage';
import ReportPage from './pages/ReportPage';

export default function App(): JSX.Element {
  return (
    <div style={{ fontFamily: 'system-ui', maxWidth: 1000, margin: '0 auto', padding: 16 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/">Upload</Link>
        <span>Rosetta — Record the old app. Get the new one, with proof.</span>
      </nav>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/jobs/:id" element={<JobPage />} />
        <Route path="/jobs/:id/report" element={<ReportPage />} />
      </Routes>
    </div>
  );
}