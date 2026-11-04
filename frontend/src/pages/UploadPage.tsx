import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { uploadVideo, listJobs, deleteJob } from '../api/client';

export default function UploadPage(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<string[]>([]);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh(): Promise<void> {
    try { setJobs(await listJobs()); }
    catch (e) { setErr(e instanceof Error ? e.message : 'Could not load projects'); }
  }
  useEffect(() => { void refresh(); }, []);

  async function onUpload(): Promise<void> {
    if (!file) { setErr('Choose a screen recording to continue.'); return; }
    setBusy(true); setErr('');
    try {
      const id = await uploadVideo(file);
      setJobs((current) => [id, ...current.filter((job) => job !== id)]);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (e) { setErr(e instanceof Error ? e.message : 'Upload failed'); }
    finally { setBusy(false); }
  }
  async function onDelete(id: string): Promise<void> {
    try { await deleteJob(id); setJobs((current) => current.filter((j) => j !== id)); }
    catch (e) { setErr(e instanceof Error ? e.message : 'Delete failed'); }
  }
  function chooseFile(next: File | undefined): void {
    if (!next) return;
    const allowed = /\.(mp4|mov|mkv|webm)$/i.test(next.name);
    if (!allowed) { setErr('Use an MP4, MOV, MKV, or WebM recording.'); return; }
    setErr(''); setFile(next);
  }
  const formatDate = (): string => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date());

  return (
    <div className="overview-page">
      <div className="page-heading">
        <div><div className="eyebrow"><span className="eyebrow-line" /> REVERSE-ENGINEERING WORKSPACE</div><h1>Bring any interface<br /><span>back to life.</span></h1>
          <p className="page-lead">Turn a screen recording into a working application — with evidence at every step.</p></div>
        <div className="heading-orbit" aria-hidden="true"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><div className="orbit-core"><span>R</span></div><i className="orbit-node node-one" /><i className="orbit-node node-two" /></div>
      </div>

      <section className="upload-panel panel">
        <div className="section-top"><div><div className="section-kicker">START A NEW PROJECT</div><h2>Upload a screen recording</h2><p>Give Rosetta a walkthrough of the original application.</p></div><div className="step-pill"><span>01</span> SOURCE VIDEO</div></div>
        <div className={'dropzone' + (dragging ? ' dragging' : '') + (file ? ' has-file' : '')}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); chooseFile(e.dataTransfer.files[0]); }}>
          <input ref={inputRef} className="file-input" type="file" accept=".mp4,.mov,.mkv,.webm,video/mp4,video/quicktime,video/x-matroska,video/webm" onChange={(e) => chooseFile(e.target.files?.[0])} />
          <div className="upload-symbol"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4.5 15.5v3A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5v-3" /></svg></div>
          {file ? <><strong className="drop-title">{file.name}</strong><span className="drop-subtitle">{(file.size / (1024 * 1024)).toFixed(1)} MB · Ready to upload</span></> :
            <><strong className="drop-title">Drop your recording here</strong><span className="drop-subtitle">or <button className="text-button" type="button" onClick={() => inputRef.current?.click()}>browse files</button> from your computer</span></>}
          <span className="file-types">MP4 · MOV · MKV · WEBM <i /> MAX 500 MB</span>
        </div>
        <div className="upload-actions"><span className="privacy-note"><span className="lock-icon">⌑</span> Your recordings stay in your local workspace.</span><button className="button button-primary" disabled={!file || busy} onClick={() => void onUpload()}>{busy ? 'Uploading…' : 'Create project'} <span>↗</span></button></div>
        {err && <div className="inline-alert" role="alert">{err}</div>}
      </section>

      <section className="projects-section">
        <div className="projects-heading"><div><div className="section-kicker">YOUR WORKSPACE</div><h2>Recent projects <span className="count-badge">{jobs.length}</span></h2></div><span className="updated-label">UPDATED {formatDate().toUpperCase()}</span></div>
        {jobs.length ? <div className="project-list">{jobs.map((job, index) => (
          <div className="project-row" key={job}><div className="project-file-icon">◫</div><div className="project-meta"><Link to={`/jobs/${job}`} className="project-name">Recording project</Link><span className="project-id">{job}</span></div><span className="project-state"><i /> Ready to process</span><Link className="row-open" to={`/jobs/${job}`}>Open project <span>↗</span></Link><button className="icon-button" aria-label="Delete project" title="Delete project" onClick={() => void onDelete(job)}>×</button></div>
        ))}</div> : <div className="empty-state"><div className="empty-icon">⌁</div><strong>No projects yet</strong><span>Your uploaded recordings will appear here.</span></div>}
      </section>
      <div className="workflow-strip"><div className="workflow-title"><span className="mini-spark">✳</span><div><strong>From recording to reconstruction</strong><small>A transparent, evidence-first workflow.</small></div></div><div className="workflow-steps"><span>01 <b>Capture</b></span><i>→</i><span>02 <b>Understand</b></span><i>→</i><span>03 <b>Rebuild</b></span><i>→</i><span>04 <b>Verify</b></span></div></div>
    </div>
  );
}