import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getStatus, runStage, deleteJob, eventsUrl } from '../api/client';
import StageProgress from '../components/StageProgress';

const STAGES = ['ingest', 'observe', 'specify', 'generate', 'replay', 'score', 'repair', 'report'];
const TITLES: Record<string, string> = { ingest: 'Capture frames', observe: 'Understand UI', specify: 'Define interface', generate: 'Build application', replay: 'Replay journey', score: 'Measure parity', repair: 'Refine result', report: 'Create report' };
const DESCRIPTIONS: Record<string, string> = { ingest: 'Extract frames from the source recording.', observe: 'Identify screens, controls, and user actions.', specify: 'Create a structured application specification.', generate: 'Generate the React application.', replay: 'Run the journey in a real browser.', score: 'Compare behavior and visual fidelity.', repair: 'Apply evidence-based improvements.', report: 'Package findings and supporting evidence.' };

export default function JobPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [stages, setStages] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState('');
  const [running, setRunning] = useState(false);
  const [runningStage, setRunningStage] = useState('');
  const jobId = id ?? '';
  useEffect(() => {
    let alive = true;
    async function poll(): Promise<void> { try { const status = await getStatus(jobId); if (alive) setStages(status.stages); } catch (error) { if (alive) setMessage(error instanceof Error ? error.message : 'Could not load project status'); } }
    void poll(); const interval = window.setInterval(() => void poll(), 2000);
    const events = new EventSource(eventsUrl(jobId));
    events.onmessage = (event) => { try { const payload = JSON.parse(event.data as string) as { stages: Record<string, boolean> }; if (alive && payload.stages) setStages(payload.stages); } catch { /* status polling remains authoritative */ } };
    events.onerror = () => events.close();
    return () => { alive = false; window.clearInterval(interval); events.close(); };
  }, [jobId]);
  async function refreshStatus(): Promise<void> { const status = await getStatus(jobId); setStages(status.stages); }
  async function runOne(stage: string): Promise<void> {
    if (running) return; setRunning(true); setRunningStage(stage); setMessage('Running ' + TITLES[stage] + '…');
    try { await runStage(jobId, stage); await refreshStatus(); setMessage(TITLES[stage] + ' completed'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Stage failed'); }
    finally { setRunning(false); setRunningStage(''); }
  }
  async function runPipeline(): Promise<void> {
    if (running) return; setRunning(true);
    try { for (const stage of STAGES) { setRunningStage(stage); setMessage('Running ' + TITLES[stage] + '…'); await runStage(jobId, stage); await refreshStatus(); setMessage(TITLES[stage] + ' completed'); } setMessage('Pipeline completed'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Pipeline stopped'); }
    finally { setRunning(false); setRunningStage(''); }
  }
  async function onDelete(): Promise<void> { if (running || !window.confirm('Delete this project and its generated artifacts?')) return; try { await deleteJob(jobId); navigate('/'); } catch (error) { setMessage(error instanceof Error ? error.message : 'Delete failed'); } }
  const completed = STAGES.filter((stage) => stages[stage]).length;
  const percent = Math.round((completed / STAGES.length) * 100);
  return <div className="job-page">
    <div className="back-row"><Link to="/">← All projects</Link><span>PROJECT / {jobId.slice(0, 8).toUpperCase()}</span></div>
    <div className="job-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> PROJECT WORKFLOW</div><h1>Your reconstruction</h1><p className="page-lead">Run each stage independently or let Rosetta take the full journey.</p></div><button className="button button-danger-ghost" disabled={running} onClick={() => void onDelete()}>Delete project</button></div>
    <section className="progress-panel panel"><div className="progress-top"><div><div className="section-kicker">PIPELINE PROGRESS</div><h2>{completed} <span>/ {STAGES.length} stages complete</span></h2></div><strong className="progress-percent">{percent}%</strong></div><div className="progress-track"><span style={{width: percent + '%'}} /></div><StageProgress stages={stages} runningStage={runningStage} /></section>
    <section className="stage-section"><div className="projects-heading"><div><div className="section-kicker">EXECUTION</div><h2>Pipeline stages</h2></div><button className="button button-primary" disabled={running} onClick={() => void runPipeline()}>{running ? 'Pipeline running…' : 'Run full pipeline'} <span>↗</span></button></div>
      <div className="stage-grid">{STAGES.map((stage, index) => <article className={'stage-card panel' + (stages[stage] ? ' stage-done' : '') + (runningStage === stage ? ' stage-running' : '')} key={stage}><div className="stage-card-top"><span className="stage-index">{String(index + 1).padStart(2, '0')}</span><span className={'stage-status' + (stages[stage] ? ' done' : '')}>{stages[stage] ? 'Completed' : runningStage === stage ? 'Running' : 'Pending'}</span></div><h3>{TITLES[stage]}</h3><p>{DESCRIPTIONS[stage]}</p><button className="button button-secondary stage-run-button" disabled={running} onClick={() => void runOne(stage)}>{runningStage === stage ? 'Running…' : stages[stage] ? 'Run again' : 'Run stage'} <span>→</span></button></article>)}</div>
    </section>
    {message && <div className="execution-message" role="status"><span className="message-pulse" />{message}</div>}
    <section className="deliverables panel"><div><div className="section-kicker">OUTPUTS</div><h2>Evidence & deliverables</h2><p>Inspect the parity report or export the generated project and its evidence.</p></div><div className="deliverable-actions"><Link className="button button-secondary" to={`/jobs/${jobId}/report`}>View parity report <span>↗</span></Link><a className="button button-secondary" href={`/jobs/${jobId}/export.zip`}>Download project <span>↓</span></a></div></section>
  </div>;
}