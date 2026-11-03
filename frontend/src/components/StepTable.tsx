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
};

export default function StepTable(props: { steps: Step[] }): JSX.Element {
  return (
    <table style={{ borderCollapse: 'collapse', width: '100%' }}>
      <thead>
        <tr>
          <th>step</th>
          <th>w</th>
          <th>state</th>
          <th>data</th>
          <th>flow</th>
          <th>visual</th>
          <th>s</th>
          <th>verdict</th>
          <th>reason</th>
        </tr>
      </thead>
      <tbody>
        {props.steps.map((s) => (
          <tr key={s.step}>
            <td>{s.step}</td>
            <td>{s.weight}</td>
            <td>{s.state}</td>
            <td>{s.data}</td>
            <td>{s.flow}</td>
            <td>{s.visual}</td>
            <td>{s.s}</td>
            <td>{s.verdict}</td>
            <td>{s.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}