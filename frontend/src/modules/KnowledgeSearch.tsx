import { FormEvent, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { docsApi } from '../api';
import { createDefaultRagSettings, RagControls } from '../components/RagControls';
import type { Doc, RagSettings, SemanticSearchHit } from '../types';
import { validateRag } from '../utils';

interface KnowledgeSearchProps {
  docs: Doc[];
}

export function KnowledgeSearch({ docs }: KnowledgeSearchProps) {
  const [query, setQuery] = useState('');
  const [rag, setRag] = useState<RagSettings>(() => createDefaultRagSettings());
  const [results, setResults] = useState<SemanticSearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableDocsCount = useMemo(() => docs.filter((doc) => doc.status === 'ok').length, [docs]);

  const submitSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const ragError = validateRag(rag.k, rag.rerankingEnabled, rag.rerankingK);
    if (!query.trim()) {
      setError('请输入检索内容');
      return;
    }
    if (rag.usingDocIds.length === 0) {
      setError('请至少选择一个文档');
      return;
    }
    if (ragError) {
      setError(ragError);
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const hits = await docsApi.search({
        query: query.trim(),
        usingDocIds: rag.usingDocIds,
        k: rag.k,
        rerankingK: rag.rerankingEnabled ? rag.rerankingK : null
      });
      setResults(hits);
    } catch (err) {
      setResults([]);
      setError(err instanceof Error ? err.message : '语义搜索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-layout">
      <section className="panel search-main-panel">
        <div className="panel-header">
          <div>
            <h2>知识库语义搜索</h2>
            <p>选择多个文档后执行一次性语义检索，结果不会被保存</p>
          </div>
          <div className="search-summary">{searched ? `${results.length} 条结果` : `${availableDocsCount} 个可检索文档`}</div>
        </div>

        {error && <div className="alert danger">{error}</div>}

        <form className="search-form" onSubmit={submitSearch}>
          <label className="field">
            <span>检索内容</span>
            <textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="输入想要检索的测试标准、工艺要求或芯片相关问题"
              disabled={loading}
            />
          </label>
          <div className="search-actions">
            <button className="icon-text-button primary" type="submit" disabled={loading}>
              <Search size={16} aria-hidden />
              {loading ? '检索中' : '开始检索'}
            </button>
          </div>
        </form>

        <div className="search-results">
          {!searched ? (
            <div className="search-empty">输入检索内容并选择文档后开始搜索</div>
          ) : loading ? (
            <div className="search-empty">正在检索语义相近片段</div>
          ) : results.length === 0 ? (
            <div className="search-empty">未找到相关片段</div>
          ) : (
            results.map((hit, index) => (
              <article className="search-result-card" key={`${hit.documentTitle}-${index}`}>
                <div className="search-result-header">
                  <span className="search-result-rank">{index + 1}</span>
                  <div className="search-result-title-block">
                    <h3>{hit.documentTitle || '未命名文档'}</h3>
                    {hit.hierarchy.length > 0 ? (
                      <div className="search-result-breadcrumb">
                        {hit.hierarchy.map((item, itemIndex) => (
                          <span className="search-result-chip" key={`${item}-${itemIndex}`}>
                            {item}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="search-result-meta">未提供目录层级</div>
                    )}
                  </div>
                </div>
                <div className="search-result-content">{hit.content}</div>
              </article>
            ))
          )}
        </div>
      </section>

      <aside className="panel controls-panel">
        <RagControls docs={docs} value={rag} onChange={setRag} />
      </aside>
    </div>
  );
}
