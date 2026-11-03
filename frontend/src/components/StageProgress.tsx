import React from 'react';

const ORDER = ['ingest', 'observe', 'specify', 'generate', 'replay', 'score', 'repair', 'report'];

export default function StageProgress(props: { stages: Record<string, boolean> }): JSX.Element {
  return (
    <ul>
      {ORDER.map((s) => (
        <li key={s}>
          {s}: {props.stages[s] ? 'done' : 'pending'}
        </li>
      ))}
    </ul>
  );
}