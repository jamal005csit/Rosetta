import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getStatus, runStage, deleteJob, eventsUrl } from '../api/client';
import StageProgress from '../components/StageProgress';

const STAGES = ['ingest', 'observe', 'specify', 'generate', 'replay', 'score', 'repair', 'report'];

export default function JobPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [stages, setStages] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState('');
  const jobId = id ?? '';

  useEffect(() => {
    let alive = true;
    async function poll(): Promise<void> {
      try {
        const s = await getStatus(jobId);
        if (alive) setStages(s.stages);
      } catch {
        /* backend may be down in dev */
      }
    }
    void poll();
    const t = window.setInterval(() => void poll(), 1000);
    const es = new EventSource(eventsUrl(jobId));
    es.onmessage = (ev) => {
      try {
        const j = JSON.parse(ev.data as string) as { stages: Record<string, boolean> };
        if (alive && j.stages) setStages(j.stages);
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => es.close();
    return () => {
      alive = false;
      window.clearInterval(t);
      es.close();
    };
  }, [jobId]);

  async function run(s: string): Promise<void> {
    try {
      setMsg('running ' + s);
      await runStage(jobId, s);
      const st = await getStatus(jobId);
      setStages(st.stages);
      setMsg(s + ' done');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'run error');
    }
  }

  async function onDelete(): Promise<void> {
    await deleteJob(jobId);
    nav('/');
  }

  return (
    <div>
      <h2>Job {jobId}</h2>
      <StageProgress stages={stages} />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {STAGES.map((s) => (
          <button key={s} onClick={() => void run(s)}>
            Run {s}
          </button>
        ))}
      </div>
      <p>{msg}</p>
      <p>
        <Link to={`/jobs/${jobId}/report`}>View report</Link> |{' '}
        <a href={`/jobs/${jobId}/report.html`}>report.html</a> |{' '}
        <a href={`/jobs/${jobId}/export.zip`}>export.zip</a>
      </p>
      <button onClick={() => void onDelete()}>Delete job</button>
    </div>
  );
}