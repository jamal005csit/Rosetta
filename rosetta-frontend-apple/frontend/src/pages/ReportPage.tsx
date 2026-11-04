import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getParity } from '../api/client';
import StepTable, { Step } from '../components/StepTable';
import Icon from '../components/Icon';

const RING = 2 * Math.PI * 52;

export default function ReportPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const [parity, setParity] = useState(0); const [pass, setPass] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]); const [err, setErr] = useState('');
  useEffect(() => { async function load(): Promise<void> { try { const j = await getParity(id ?? ''); setParity(j.parity); setPass(j.pass); setSteps(j.steps as Step[]); } catch (e) { setErr(e instanceof Error ? e.message : 'Could not load report'); } } void load(); }, [id]);
  const shown = Number(parity);
  const filled = (Math.max(0, Math.min(100, shown)) / 100) * RING;
  return <div className="report-page">
    <div className="back-row"><Link to={`/jobs/${id}`}><Icon name="chevron-left" size={18} /> Back to Project</Link><span>Report / {id?.slice(0, 8).toUpperCase()}</span></div>
    <div className="job-heading"><div><div className="eyebrow"><Icon name="sparkles" size={15} /> Verification results</div><h1>Parity report</h1><p className="page-lead">A step-by-step comparison of the original experience and its reconstruction.</p></div><a className="button button-secondary" href={`/jobs/${id}/export.zip`}>Export Project <Icon name="arrow-down" size={15} /></a></div>
    {err && <div className="inline-alert" role="alert"><Icon name="exclamation" size={18} /><span>{err}</span></div>}
    {!err && <><section className="report-summary panel"><div className="parity-score" role="img" aria-label={'Overall parity ' + shown.toFixed(1) + ' percent'}><svg viewBox="0 0 120 120" aria-hidden="true"><circle className="ring-bg" cx="60" cy="60" r="52" /><circle className={'ring-fg ' + (pass ? 'ok' : 'bad')} cx="60" cy="60" r="52" strokeDasharray={filled + ' ' + RING} /></svg><div className="parity-value"><strong>{shown.toFixed(1)}<small>%</small></strong><span>Overall parity</span></div></div><div className="report-summary-copy"><span className={'result-chip ' + (pass ? 'result-pass' : 'result-fail')}><Icon name={pass ? 'check' : 'xmark'} size={14} /> {pass ? 'Acceptance passed' : 'Acceptance not met'}</span><h2>{pass ? 'Reconstruction verified.' : 'More work is needed.'}</h2><p>Scores are based on observed state, data, flow, and visual evidence — not estimates.</p></div><div className="report-metric"><strong>{steps.length}</strong><span>Journey steps</span></div></section>
    <section className="report-table-section"><div className="projects-heading"><div><div className="section-kicker">Detailed breakdown</div><h2>Journey evidence</h2></div><span className="updated-label">Weighted scoring</span></div><StepTable steps={steps} jobId={id ?? ''} /></section></>}
    <div className="report-links"><a href={`/jobs/${id}/report.html`}>Open full HTML report <Icon name="arrow-up-right" size={15} /></a><Link to={`/jobs/${id}`}>Return to pipeline <Icon name="arrow-right" size={15} /></Link></div>
  </div>;
}
