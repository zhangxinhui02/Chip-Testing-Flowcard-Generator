import { statusLabel, statusTone } from '../utils';
import type { DocStatus } from '../types';

interface StatusPillProps {
  status: DocStatus;
}

export function StatusPill({ status }: StatusPillProps) {
  return <span className={`pill ${statusTone(status)}`}>{statusLabel(status)}</span>;
}
