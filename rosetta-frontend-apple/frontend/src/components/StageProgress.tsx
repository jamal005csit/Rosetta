import React from 'react';
import Icon from './Icon';
const ORDER = ['ingest', 'observe', 'specify', 'generate', 'replay', 'score', 'repair', 'report'];
const LABELS: Record<string, string> = { ingest: 'Capture', observe: 'Observe', specify: 'Specify', generate: 'Generate', replay: 'Replay', score: 'Score', repair: 'Repair', report: 'Report' };
export default function StageProgress(props: { stages: Record<string, boolean>; runningStage?: string }): JSX.Element {
  return <div className="stage-progress">{ORDER.map((stage, index) => <div className={'progress-step' + (props.stages[stage] ? ' complete' : '') + (props.runningStage === stage ? ' current' : '')} key={stage}><span className="progress-step-icon">{props.stages[stage] ? <Icon name="check" size={14} /> : String(index + 1).padStart(2, '0')}</span><span>{LABELS[stage]}</span></div>)}</div>;
}
