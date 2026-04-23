import { FileText } from 'lucide-react';
import type { Doc } from '../types';
import { StatusPill } from './StatusPill';

interface DocumentSelectorProps {
  docs: Doc[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  title?: string;
}

export function DocumentSelector({ docs, selectedIds, onChange, title = '检索文档' }: DocumentSelectorProps) {
  const toggle = (docId: string) => {
    if (selectedIds.includes(docId)) {
      onChange(selectedIds.filter((id) => id !== docId));
      return;
    }
    onChange([...selectedIds, docId]);
  };

  return (
    <section className="control-section">
      <div className="section-heading">
        <FileText size={16} aria-hidden />
        <span>{title}</span>
      </div>
      <div className="doc-selector">
        {docs.length === 0 ? (
          <div className="empty-inline">暂无文档</div>
        ) : (
          docs.map((doc) => {
            const disabled = doc.status !== 'ok';
            return (
              <label className={`doc-option ${disabled ? 'muted' : ''}`} key={doc.id}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(doc.id)}
                  disabled={disabled}
                  onChange={() => toggle(doc.id)}
                />
                <span className="doc-option-body">
                  <span className="doc-option-title">{doc.title}</span>
                  <span className="doc-option-meta">{doc.id}</span>
                </span>
                <StatusPill status={doc.status} />
              </label>
            );
          })
        )}
      </div>
    </section>
  );
}
