import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getParity } from '../api/client';
import StepTable, { Step } from '../components/StepTable';

export default function ReportPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const [parity, setParity] = useState(0); const [pass, setPass] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]); const [err, setErr] = useState('');
  useEffect(() => { async function load(): Promise<void> { try { const j = await getParity(id ?? ''); setParity(j.parity); setPass(j.pass); setSteps(j.steps as Step[]); } catch (e) { setErr(e instanceof Error ? e.message : 'Could not load report'); } } void load(); }, [id]);
  return <div className="report-page">
    <div className="back-row"><Link to={`/jobs/${id}`}>← Back to project</Link><span>REPORT / {id?.slice(0, 8).toUpperCase()}</span></div>
    <div className="job-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> VERIFICATION RESULTS</div><h1>Parity report</h1><p className="page-lead">A step-by-step comparison of the original experience and its reconstruction.</p></div><a className="button button-secondary" href={`/jobs/${id}/export.zip`}>Export project <span>↓</span></a></div>
    {err && <div className="inline-alert" role="alert">{err}</div>}
    {!err && <><section className="report-summary panel"><div className="parity-score"><strong>{Number(parity).toFixed(1)}<small>%</small></strong><span>OVERALL PARITY</span></div><div className="report-summary-copy"><span className={'result-chip ' + (pass ? 'result-pass' : 'result-fail')}>{pass ? '✓ Acceptance passed' : '× Acceptance not met'}</span><h2>{pass ? 'Reconstruction verified.' : 'More work is needed.'}</h2><p>Scores are based on observed state, data, flow, and visual evidence — not estimates.</p></div><div className="report-metric"><strong>{steps.length}</strong><span>Journey steps</span></div></section>
    <section className="report-table-section"><div className="projects-heading"><div><div className="section-kicker">DETAILED BREAKDOWN</div><h2>Journey evidence</h2></div><span className="updated-label">WEIGHTED SCORING</span></div><StepTable steps={steps} jobId={id ?? ''} /></section></>}
    <div className="report-links"><a href={`/jobs/${id}/report.html`}>Open full HTML report ↗</a><Link to={`/jobs/${id}`}>Return to pipeline →</Link></div>
  </div>;
}