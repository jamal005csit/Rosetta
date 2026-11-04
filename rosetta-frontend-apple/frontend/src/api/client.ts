export async function uploadVideo(file: File): Promise<string> {
    const fd = new FormData();
    fd.append('f', file, file.name);
    const r = await fetch('/jobs', { method: 'POST', body: fd });
    if (!r.ok) throw new Error('upload failed ' + r.status + ': ' + await r.text());
    const j = await r.json();
    return j.id as string;
  }
  
  export async function listJobs(): Promise<string[]> {
    const r = await fetch('/jobs');
    if (!r.ok) throw new Error('list failed');
    const j = await r.json();
    return j.jobs as string[];
  }
  
  export async function getStatus(jobId: string): Promise<{ stages: Record<string, boolean>; files: string[] }> {
    const r = await fetch(`/jobs/${jobId}/status`);
    if (!r.ok) throw new Error('status failed ' + r.status + ': ' + await r.text());
    return r.json();
  }
  
  export async function runStage(jobId: string, stage: string): Promise<unknown> {
    const r = await fetch(`/jobs/${jobId}/run/${stage}`, { method: 'POST' });
    if (!r.ok) throw new Error('run ' + stage + ' failed ' + r.status + ': ' + await r.text());
    return r.json();
  }
  
  export async function deleteJob(jobId: string): Promise<void> {
    const r = await fetch(`/jobs/${jobId}`, { method: 'DELETE' });
    if (!r.ok) throw new Error('delete failed');
  }
  
  export async function getParity(jobId: string): Promise<{ parity: number; pass: boolean; steps: unknown[] }> {
    const r = await fetch(`/jobs/${jobId}/parity.json`);
    if (!r.ok) throw new Error('no parity');
    return r.json();
  }
  
  export function eventsUrl(jobId: string): string {
    return `/jobs/${jobId}/events`;
  }