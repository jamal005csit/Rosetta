import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getParity } from '../api/client';
import StepTable, { Step } from '../components/StepTable';

export default function ReportPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const [parity, setParity] = useState(0);
  const [pass, setPass] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => {
    async function load(): Promise<void> {
      try {
        const j = await getParity(id ?? '');
        setParity(j.parity);
        setPass(j.pass);
        setSteps(j.steps as Step[]);
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'load error');
      }
    }
    void load();
  }, [id]);

  return (
    <div>
      <h2>Parity report {id}</h2>
      {err && <div role="alert">{err}</div>}
      <p>
        Parity: {parity} Pass: {String(pass)}
      </p>
      <StepTable steps={steps} />
      <p>
        <a href={`/jobs/${id}/report.html`}>Full report.html</a> | <a href={`/jobs/${id}/export.zip`}>export.zip</a>
      </p>
    </div>
  );
}