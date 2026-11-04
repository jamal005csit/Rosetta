import React from 'react';

/**
 * A small, weight-matched line-icon set in the spirit of SF Symbols:
 * one 24-pt grid, one 1.75 stroke, round caps and joins, inherits currentColor.
 */
export type IconName =
  | 'house' | 'stack' | 'film' | 'upload' | 'lock' | 'sparkles' | 'exclamation'
  | 'arrow-up-right' | 'arrow-down' | 'arrow-right' | 'chevron-right' | 'chevron-left'
  | 'check' | 'xmark' | 'trash' | 'play' | 'reload'
  | 'eye' | 'doc' | 'cube' | 'gauge' | 'chart';

const PATHS: Record<IconName, JSX.Element> = {
  house: <path d="M4 11.2 12 4l8 7.2V19a1 1 0 0 1-1 1h-4v-5.2H9V20H5a1 1 0 0 1-1-1z" />,
  stack: <><rect x="4" y="9" width="16" height="11" rx="2.6" /><path d="M7 6h10M9.5 3h5" /></>,
  film: <><rect x="3.5" y="6" width="17" height="12" rx="3" /><path d="m10.5 9.6 3.9 2.4-3.9 2.4z" /></>,
  upload: <path d="M12 15V4m0 0L8 8m4-4 4 4M6.5 11H6a2 2 0 0 0-2 2v4.5A1.5 1.5 0 0 0 5.5 19h13a1.5 1.5 0 0 0 1.5-1.5V13a2 2 0 0 0-2-2h-.5" />,
  lock: <><rect x="5" y="11" width="14" height="9" rx="2.6" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  sparkles: <><path d="m11 4 1.7 4.6L17.3 10l-4.6 1.7L11 16.3l-1.7-4.6L4.7 10l4.6-1.4z" /><path d="M18 15v4M16 17h4" /></>,
  exclamation: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.8v5M12 16.2v.1" /></>,
  'arrow-up-right': <path d="M7.5 16.5 16.5 7.5M9 7.5h7.5V15" />,
  'arrow-down': <path d="M12 5v14m0 0 5-5m-5 5-5-5" />,
  'arrow-right': <path d="M5 12h14m0 0-5-5m5 5-5 5" />,
  'chevron-right': <path d="m9.5 6 6 6-6 6" />,
  'chevron-left': <path d="m14.5 6-6 6 6 6" />,
  check: <path d="m5.5 12.6 4.2 4.2L18.5 8" />,
  xmark: <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />,
  trash: <path d="M5 7h14M10 7V5h4v2M7 7l.8 12h8.4L17 7M10.2 11v5M13.8 11v5" />,
  play: <path d="M8.5 6.2v11.6L18 12z" />,
  reload: <path d="M19 12a7 7 0 1 1-2.2-5.1M19 4.8v4.4h-4.4" />,
  eye: <><path d="M2.8 12S6.2 5.8 12 5.8 21.2 12 21.2 12 17.8 18.2 12 18.2 2.8 12 2.8 12z" /><circle cx="12" cy="12" r="2.8" /></>,
  doc: <path d="M7 3.5h6.8L18.5 8v11a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5zM13.5 3.8V8.5h4.7M8.8 12.8h6.4M8.8 16.2h4.2" />,
  cube: <path d="M12 3.2 4.6 7.1v9.8L12 20.8l7.4-3.9V7.1zM4.6 7.1 12 11l7.4-3.9M12 11v9.8" />,
  gauge: <path d="M4.6 16.2a8 8 0 1 1 14.8 0M12 14l3.4-4.2" />,
  chart: <path d="M6 20v-9M12 20V5M18 20v-6" />,
};

export default function Icon(props: { name: IconName; size?: number }): JSX.Element {
  const size = props.size ?? 18;
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {PATHS[props.name]}
    </svg>
  );
}
