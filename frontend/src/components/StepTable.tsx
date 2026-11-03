import React from 'react';

export type Step = {
  step: number;
  weight: number;
  state: number;
  data: number;
  flow: number;
  visual: number;
  s: number;
  verdict: string;
  reason: string;
  action_success?: boolean;
  active_screen?: string | null;
  replay_error?: string | null;
  legacy_frame?: string;
  new_screenshot?: string;
};

export default function StepTable(props: { steps: Step[]; jobId: string }): JSX.Element {
  const evidenceUrl = (path?: string): string =>
    path ? `/jobs/${props.jobId}/files/${path}` : '#';

  return (
    <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
      <thead>
        <tr>
          <th>Step</th>
          <th>Weight</th>
          <th>State</th>
          <th>Data</th>
          <th>Flow</th>
          <th>Visual</th>
          <th>Score</th>
          <th>Verdict</th>
          <th>Browser action</th>
          <th>Active screen</th>
          <th>Legacy evidence</th>
          <th>Replay screenshot</th>
          <th>Replay error</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody>
        {props.steps.map((step) => (
          <tr key={step.step}>
            <td>{step.step}</td>
            <td>{step.weight}</td>
            <td>{step.state}</td>
            <td>{step.data}</td>
            <td>{step.flow}</td>
            <td>{step.visual}</td>
            <td>{step.s}</td>
            <td>{step.verdict}</td>
            <td>{step.action_success ? 'succeeded' : 'failed'}</td>
            <td>{step.active_screen ?? 'unknown'}</td>
            <td>{step.legacy_frame ? <a href={evidenceUrl(step.legacy_frame)}>Open frame</a> : 'missing'}</td>
            <td>{step.new_screenshot ? <a href={evidenceUrl(step.new_screenshot)}>Open screenshot</a> : 'missing'}</td>
            <td>{step.replay_error ?? ''}</td>
            <td>{step.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
