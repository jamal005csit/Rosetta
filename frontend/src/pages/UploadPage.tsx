import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { uploadVideo, listJobs, deleteJob } from '../api/client';

export default function UploadPage(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<string[]>([]);
  const [err, setErr] = useState('');

  async function refresh(): Promise<void> {
    try {
      setJobs(await listJobs());
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'list error');
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onUpload(): Promise<void> {
    if (!file) {
      setErr('choose a video file first');
      return;
    }
    try {
      const id = await uploadVideo(file);
      setErr('');
      setJobs([...jobs, id]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'upload error');
    }
  }

  async function onDelete(id: string): Promise<void> {
    try {
      await deleteJob(id);
      setJobs(jobs.filter((j) => j !== id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'delete error');
    }
  }

  return (
    <div>
      <h2>Upload screen recording</h2>
      <input
        type="file"
        accept=".mp4,.mov,.mkv,.webm"
        onChange={(e) => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
      />
      <button onClick={() => void onUpload()}>Upload</button>
      {err && <div role="alert">{err}</div>}
      <h3>Jobs</h3>
      <ul>
        {jobs.map((j) => (
          <li key={j}>
            <Link to={`/jobs/${j}`}>{j}</Link>{' '}
            <button onClick={() => void onDelete(j)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}