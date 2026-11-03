import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getStatus, runStage, deleteJob, eventsUrl } from '../api/client';
import StageProgress from '../components/StageProgress';

const STAGES = ['ingest', 'observe', 'specify', 'generate', 'replay', 'score', 'repair', 'report'];

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
    async function poll(): Promise<void> {
      try {
        const status = await getStatus(jobId);
        if (alive) setStages(status.stages);
      } catch (error) {
        if (alive) setMessage(error instanceof Error ? error.message : 'Could not load job status');
      }
    }
    void poll();
    const interval = window.setInterval(() => void poll(), 1500);
    const events = new EventSource(eventsUrl(jobId));
    events.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as { stages: Record<string, boolean> };
        if (alive && payload.stages) setStages(payload.stages);
      } catch {
        // Ignore malformed event payloads; status polling remains authoritative.
      }
    };
    events.onerror = () => events.close();
    return () => {
      alive = false;
      window.clearInterval(interval);
      events.close();
    };
  }, [jobId]);

  async function refreshStatus(): Promise<void> {
    const status = await getStatus(jobId);
    setStages(status.stages);
  }

  async function runOne(stage: string): Promise<void> {
    if (running) return;
    setRunning(true);
    setRunningStage(stage);
    setMessage('Running ' + stage + '…');
    try {
      await runStage(jobId, stage);
      await refreshStatus();
      setMessage(stage + ' completed');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Stage failed');
    } finally {
      setRunning(false);
      setRunningStage('');
    }
  }

  async function runPipeline(): Promise<void> {
    if (running) return;
    setRunning(true);
    try {
      for (const stage of STAGES) {
        setRunningStage(stage);
        setMessage('Running ' + stage + '…');
        await runStage(jobId, stage);
        await refreshStatus();
        setMessage(stage + ' completed');
      }
      setMessage('Pipeline completed');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Pipeline stopped');
    } finally {
      setRunning(false);
      setRunningStage('');
    }
  }

  async function onDelete(): Promise<void> {
    if (running) return;
    try {
      await deleteJob(jobId);
      navigate('/');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Delete failed');
    }
  }

  return (
    <div>
      <h2>Job {jobId}</h2>
      <StageProgress stages={stages} />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <button disabled={running} onClick={() => void runPipeline()}>
          {running ? 'Pipeline running…' : 'Run full pipeline'}
        </button>
        {STAGES.map((stage) => (
          <button key={stage} disabled={running} onClick={() => void runOne(stage)}>
            {runningStage === stage ? 'Running…' : 'Run ' + stage}
          </button>
        ))}
      </div>
      <p role="status">{message}</p>
      <p>
        <Link to={`/jobs/${jobId}/report`}>View report</Link> |{' '}
        <a href={`/jobs/${jobId}/report.html`}>report.html</a> |{' '}
        <a href={`/jobs/${jobId}/export.zip`}>export.zip</a>
      </p>
      <button disabled={running} onClick={() => void onDelete()}>Delete job</button>
    </div>
  );
}
