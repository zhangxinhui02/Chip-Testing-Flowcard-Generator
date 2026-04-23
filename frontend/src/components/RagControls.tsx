import { Settings2 } from 'lucide-react';
import type { Doc, RagSettings } from '../types';
import { validateRag } from '../utils';
import { DocumentSelector } from './DocumentSelector';

interface RagControlsProps {
  docs: Doc[];
  value: RagSettings;
  onChange: (value: RagSettings) => void;
}

export function createDefaultRagSettings(): RagSettings {
  return {
    usingDocIds: [],
    k: 10,
    rerankingEnabled: false,
    rerankingK: 20
  };
}

export function RagControls({ docs, value, onChange }: RagControlsProps) {
  const validation = validateRag(value.k, value.rerankingEnabled, value.rerankingK);

  return (
    <div className="rag-panel">
      <div className="section-heading">
        <Settings2 size={16} aria-hidden />
        <span>RAG 参数</span>
      </div>
      <div className="field-grid two">
        <label className="field">
          <span>每个文档检索数量 k</span>
          <input
            type="number"
            min={1}
            value={value.k}
            onChange={(event) => onChange({ ...value, k: Number(event.target.value) })}
          />
        </label>
        <label className="toggle-field">
          <input
            type="checkbox"
            checked={value.rerankingEnabled}
            onChange={(event) => onChange({ ...value, rerankingEnabled: event.target.checked })}
          />
          <span>启用重排序</span>
        </label>
        {value.rerankingEnabled && (
          <label className="field">
            <span>reranking_k</span>
            <input
              type="number"
              min={value.k}
              value={value.rerankingK}
              onChange={(event) => onChange({ ...value, rerankingK: Number(event.target.value) })}
            />
          </label>
        )}
      </div>
      {validation && <div className="form-error">{validation}</div>}
      <DocumentSelector
        docs={docs}
        selectedIds={value.usingDocIds}
        onChange={(usingDocIds) => onChange({ ...value, usingDocIds })}
      />
    </div>
  );
}
