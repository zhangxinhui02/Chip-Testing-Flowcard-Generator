import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Edit3, Eye, FilePlus2, RefreshCw, Save, Trash2, X } from 'lucide-react';
import { flowcardsApi } from '../api';
import { createDefaultRagSettings, RagControls } from '../components/RagControls';
import type { Doc, Flowcard, RagSettings } from '../types';
import { openFlowcardTable, validateRag } from '../utils';

interface FlowcardsProps {
  docs: Doc[];
}

type OrderMode = 'doc' | 'manual';

export function Flowcards({ docs }: FlowcardsProps) {
  const [flowcards, setFlowcards] = useState<Record<string, Flowcard>>({});
  const [orderMode, setOrderMode] = useState<OrderMode>('doc');
  const [title, setTitle] = useState('');
  const [orderDocId, setOrderDocId] = useState('');
  const [orderMessage, setOrderMessage] = useState('');
  const [chipCode, setChipCode] = useState('');
  const [rag, setRag] = useState<RagSettings>(() => createDefaultRagSettings());
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const flowcardItems = useMemo(
    () =>
      Object.entries(flowcards).map(([id, flowcard]) => ({
        id,
        flowcard,
        displayTitle: flowcard.title || '未命名流程卡'
      })),
    [flowcards]
  );

  const usableDocs = useMemo(() => docs.filter((doc) => doc.status === 'ok'), [docs]);

  const loadFlowcards = async () => {
    setLoading(true);
    setError(null);
    try {
      setFlowcards(await flowcardsApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : '流程卡列表加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFlowcards();
  }, []);

  useEffect(() => {
    if (!orderDocId && usableDocs.length > 0) {
      setOrderDocId(usableDocs[0].id);
    }
  }, [orderDocId, usableDocs]);

  const deleteFlowcard = async (flowcardId: string) => {
    if (!window.confirm(`删除流程卡「${flowcards[flowcardId]?.title || flowcardId}」？`)) {
      return;
    }
    setDeletingId(flowcardId);
    setError(null);
    setNotice(null);
    try {
      const ok = await flowcardsApi.remove(flowcardId);
      if (!ok) {
        throw new Error('流程卡删除被后端拒绝');
      }
      setFlowcards((current) => {
        const next = { ...current };
        delete next[flowcardId];
        return next;
      });
      setNotice('流程卡已删除');
    } catch (err) {
      setError(err instanceof Error ? err.message : '流程卡删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  const startEditTitle = (flowcardId: string, flowcard: Flowcard) => {
    setEditingId(flowcardId);
    setEditingTitle(flowcard.title || '');
    setError(null);
    setNotice(null);
  };

  const saveTitle = async (flowcardId: string) => {
    const nextTitle = editingTitle.trim();
    if (!nextTitle) {
      setError('请输入流程卡标题');
      return;
    }

    setSavingId(flowcardId);
    setError(null);
    setNotice(null);
    try {
      const ok = await flowcardsApi.updateTitle(flowcardId, nextTitle);
      if (!ok) {
        throw new Error('标题更新被后端拒绝');
      }
      setFlowcards((current) => ({
        ...current,
        [flowcardId]: {
          ...current[flowcardId],
          title: nextTitle
        }
      }));
      setEditingId(null);
      setNotice('流程卡标题已更新');
    } catch (err) {
      setError(err instanceof Error ? err.message : '标题更新失败');
    } finally {
      setSavingId(null);
    }
  };

  const viewFlowcard = (flowcardId: string, flowcard: Flowcard) => {
    setError(null);
    try {
      openFlowcardTable(flowcardId, flowcard);
    } catch (err) {
      setError(err instanceof Error ? err.message : '流程卡打开失败');
    }
  };

  const submitFlowcard = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const ragError = validateRag(rag.k, rag.rerankingEnabled, rag.rerankingK);
    if (ragError) {
      setError(ragError);
      return;
    }
    if (orderMode === 'doc' && !orderDocId.trim()) {
      setError('请选择订单文档 ID');
      return;
    }
    if (orderMode === 'manual' && !orderMessage.trim()) {
      setError('请输入订单要求');
      return;
    }
    if (orderMode === 'manual' && !chipCode.trim()) {
      setError('请输入芯片型号');
      return;
    }

    setGenerating(true);
    try {
      const [flowcardId, flowcard] = await flowcardsApi.create({
        title: title.trim() || null,
        orderDocId: orderMode === 'doc' ? orderDocId.trim() : null,
        orderMessage: orderMode === 'manual' ? orderMessage.trim() : null,
        chipCode: orderMode === 'manual' ? chipCode.trim() : null,
        usingDocIds: rag.usingDocIds,
        k: rag.k,
        rerankingK: rag.rerankingEnabled ? rag.rerankingK : null
      });
      setTitle('');
      setFlowcards((current) => ({ [flowcardId]: flowcard, ...current }));
      setNotice('流程卡已生成');
      openFlowcardTable(flowcardId, flowcard);
    } catch (err) {
      setError(err instanceof Error ? err.message : '流程卡生成失败');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="split-layout flowcard-layout">
      <aside className="panel side-panel">
        <div className="panel-header compact">
          <h2>流程卡</h2>
          <button className="icon-button" type="button" title="刷新" onClick={loadFlowcards} disabled={loading}>
            <RefreshCw size={16} aria-hidden />
          </button>
        </div>
        <div className="list-stack">
          {flowcardItems.length === 0 ? (
            <div className="empty-inline">{loading ? '加载中' : '暂无流程卡'}</div>
          ) : (
            flowcardItems.map((item) => {
              const editing = editingId === item.id;
              return (
                <div className="list-item passive" key={item.id}>
                  <span>
                    {editing ? (
                      <input
                        value={editingTitle}
                        onChange={(event) => setEditingTitle(event.target.value)}
                        disabled={savingId === item.id}
                      />
                    ) : (
                      <strong>{item.displayTitle}</strong>
                    )}
                    <code>{item.id}</code>
                    <small>{item.flowcard.jobs.length} 道工序</small>
                  </span>
                  <span className="row-actions">
                    {editing ? (
                      <>
                        <button
                          className="icon-button"
                          type="button"
                          title="保存"
                          onClick={() => saveTitle(item.id)}
                          disabled={savingId === item.id}
                        >
                          <Save size={15} aria-hidden />
                        </button>
                        <button
                          className="icon-button"
                          type="button"
                          title="取消"
                          onClick={() => setEditingId(null)}
                          disabled={savingId === item.id}
                        >
                          <X size={15} aria-hidden />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="icon-button"
                          type="button"
                          title="编辑标题"
                          onClick={() => startEditTitle(item.id, item.flowcard)}
                        >
                          <Edit3 size={15} aria-hidden />
                        </button>
                        <button
                          className="icon-button"
                          type="button"
                          title="查看"
                          onClick={() => viewFlowcard(item.id, item.flowcard)}
                        >
                          <Eye size={15} aria-hidden />
                        </button>
                        <button
                          className="icon-button danger"
                          type="button"
                          title="删除"
                          onClick={() => deleteFlowcard(item.id)}
                          disabled={deletingId === item.id}
                        >
                          <Trash2 size={15} aria-hidden />
                        </button>
                      </>
                    )}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </aside>

      <section className="panel generator-panel">
        <div className="panel-header">
          <div>
            <h2>生成流程卡</h2>
            <p>{orderMode === 'doc' ? '订单文档' : '手动订单'}</p>
          </div>
        </div>
        {error && <div className="alert danger">{error}</div>}
        {notice && <div className="alert success">{notice}</div>}
        <form className="flowcard-form" onSubmit={submitFlowcard}>
          <label className="field">
            <span>流程卡标题</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="留空则自动生成标题"
              disabled={generating}
            />
          </label>

          <div className="segmented wide">
            <button
              type="button"
              className={orderMode === 'doc' ? 'active' : ''}
              onClick={() => setOrderMode('doc')}
            >
              订单文档 ID
            </button>
            <button
              type="button"
              className={orderMode === 'manual' ? 'active' : ''}
              onClick={() => setOrderMode('manual')}
            >
              手动输入
            </button>
          </div>

          {orderMode === 'doc' ? (
            <label className="field">
              <span>订单文档 ID</span>
              <select value={orderDocId} onChange={(event) => setOrderDocId(event.target.value)}>
                {usableDocs.length === 0 ? (
                  <option value="">暂无可用文档</option>
                ) : (
                  usableDocs.map((doc) => (
                    <option value={doc.id} key={doc.id}>
                      {doc.title} ({doc.id})
                    </option>
                  ))
                )}
              </select>
            </label>
          ) : (
            <div className="field-grid">
              <label className="field">
                <span>芯片型号</span>
                <input value={chipCode} onChange={(event) => setChipCode(event.target.value)} />
              </label>
              <label className="field span-all">
                <span>订单要求</span>
                <textarea value={orderMessage} onChange={(event) => setOrderMessage(event.target.value)} />
              </label>
            </div>
          )}

          <button className="icon-text-button primary" type="submit" disabled={generating}>
            <FilePlus2 size={16} aria-hidden />
            {generating ? '生成中' : '生成流程卡'}
          </button>
        </form>
      </section>

      <aside className="panel controls-panel">
        <RagControls docs={docs} value={rag} onChange={setRag} />
      </aside>
    </div>
  );
}
