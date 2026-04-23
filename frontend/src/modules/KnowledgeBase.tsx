import { FormEvent, useMemo, useState } from 'react';
import { Download, Edit3, RefreshCw, Save, Trash2, Upload, X } from 'lucide-react';
import { docsApi } from '../api';
import { StatusPill } from '../components/StatusPill';
import type { Doc, DocFileType } from '../types';

interface KnowledgeBaseProps {
  docs: Doc[];
  loading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
}

const fileTypes: Array<{ value: DocFileType; label: string; accept: string }> = [
  { value: 'image', label: 'Image', accept: 'image/*' },
  { value: 'pdf', label: 'PDF', accept: 'application/pdf,.pdf' },
  { value: 'markdown', label: 'Markdown', accept: '.md,.markdown,text/markdown,text/plain' }
];

export function KnowledgeBase({ docs, loading, error, onRefresh }: KnowledgeBaseProps) {
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [fileType, setFileType] = useState<DocFileType>('pdf');
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editDocId, setEditDocId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editNote, setEditNote] = useState('');
  const [savingDocId, setSavingDocId] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);

  const selectedAccept = useMemo(
    () => fileTypes.find((item) => item.value === fileType)?.accept || '',
    [fileType]
  );

  const startEdit = (doc: Doc) => {
    setEditDocId(doc.id);
    setEditTitle(doc.title);
    setEditNote(doc.note || '');
    setLocalError(null);
    setNotice(null);
  };

  const resetCreateForm = () => {
    setTitle('');
    setNote('');
    setFile(null);
    setFileType('pdf');
    setFileInputKey((value) => value + 1);
  };

  const submitCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    setNotice(null);

    if (!title.trim()) {
      setLocalError('请输入文档标题');
      return;
    }
    if (!file) {
      setLocalError('请选择文件');
      return;
    }

    setUploading(true);
    try {
      const ok = await docsApi.create({
        title: title.trim(),
        note: note.trim(),
        fileType,
        file
      });
      if (!ok) {
        throw new Error('后端未接受文档创建请求');
      }
      resetCreateForm();
      setNotice('文档已提交');
      await onRefresh();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : '文档创建失败');
    } finally {
      setUploading(false);
    }
  };

  const saveEdit = async (doc: Doc) => {
    setLocalError(null);
    setNotice(null);

    const nextTitle = doc.is_built_in ? doc.title : editTitle.trim();
    if (!nextTitle) {
      setLocalError('请输入文档标题');
      return;
    }

    setSavingDocId(doc.id);
    try {
      const ok = await docsApi.update(doc.id, {
        title: nextTitle,
        note: editNote.trim()
      });
      if (!ok) {
        throw new Error('文档更新被后端拒绝');
      }
      setEditDocId(null);
      setNotice('文档已更新');
      await onRefresh();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : '文档更新失败');
    } finally {
      setSavingDocId(null);
    }
  };

  const deleteDoc = async (doc: Doc) => {
    if (doc.is_built_in || !window.confirm(`删除文档「${doc.title}」？`)) {
      return;
    }

    setDeletingDocId(doc.id);
    setLocalError(null);
    setNotice(null);
    try {
      const ok = await docsApi.remove(doc.id);
      if (!ok) {
        throw new Error('文档删除被后端拒绝');
      }
      setNotice('文档已删除');
      await onRefresh();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : '文档删除失败');
    } finally {
      setDeletingDocId(null);
    }
  };

  return (
    <div className="module-layout">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>知识库</h2>
            <p>{docs.length} 个文档</p>
          </div>
          <button className="icon-text-button secondary" type="button" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={16} aria-hidden />
            刷新
          </button>
        </div>
        {(error || localError) && <div className="alert danger">{localError || error}</div>}
        {notice && <div className="alert success">{notice}</div>}

        <form className="create-doc-form" onSubmit={submitCreate}>
          <div className="field-grid">
            <label className="field">
              <span>标题</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={uploading} />
            </label>
            <label className="field">
              <span>备注</span>
              <input value={note} onChange={(event) => setNote(event.target.value)} disabled={uploading} />
            </label>
          </div>
          <div className="field-row">
            <div className="field">
              <span>文件类型</span>
              <div className="segmented">
                {fileTypes.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    className={fileType === item.value ? 'active' : ''}
                    onClick={() => setFileType(item.value)}
                    disabled={uploading}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <label className="field file-field">
              <span>文件</span>
              <input
                key={fileInputKey}
                type="file"
                accept={selectedAccept}
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                disabled={uploading}
              />
            </label>
            <button className="icon-text-button primary" type="submit" disabled={uploading}>
              <Upload size={16} aria-hidden />
              {uploading ? '提交中' : '新建文档'}
            </button>
          </div>
        </form>
      </section>

      <section className="panel table-panel">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>ID</th>
                <th>状态</th>
                <th>来源</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-cell">
                    {loading ? '加载中' : '暂无文档'}
                  </td>
                </tr>
              ) : (
                docs.map((doc) => {
                  const editing = editDocId === doc.id;
                  return (
                    <tr key={doc.id}>
                      <td>
                        {editing ? (
                          <input
                            className="table-input"
                            value={doc.is_built_in ? doc.title : editTitle}
                            disabled={doc.is_built_in}
                            onChange={(event) => setEditTitle(event.target.value)}
                          />
                        ) : (
                          <strong>{doc.title}</strong>
                        )}
                      </td>
                      <td>
                        <code>{doc.id}</code>
                      </td>
                      <td>
                        <StatusPill status={doc.status} />
                      </td>
                      <td>{doc.is_built_in ? <span className="pill neutral">内建</span> : '用户上传'}</td>
                      <td>
                        {editing ? (
                          <textarea
                            className="table-textarea"
                            value={editNote}
                            onChange={(event) => setEditNote(event.target.value)}
                          />
                        ) : (
                          <span className="note-text">{doc.note || '-'}</span>
                        )}
                      </td>
                      <td>
                        <div className="row-actions">
                          {editing ? (
                            <>
                              <button
                                className="icon-button"
                                type="button"
                                title="保存"
                                onClick={() => saveEdit(doc)}
                                disabled={savingDocId === doc.id}
                              >
                                <Save size={16} aria-hidden />
                              </button>
                              <button
                                className="icon-button"
                                type="button"
                                title="取消"
                                onClick={() => setEditDocId(null)}
                                disabled={savingDocId === doc.id}
                              >
                                <X size={16} aria-hidden />
                              </button>
                            </>
                          ) : (
                            <>
                              <button className="icon-button" type="button" title="编辑" onClick={() => startEdit(doc)}>
                                <Edit3 size={16} aria-hidden />
                              </button>
                              <a
                                className="icon-button"
                                title="下载"
                                href={`/api/docs/${encodeURIComponent(doc.id)}/file`}
                                target="_blank"
                                rel="noreferrer"
                              >
                                <Download size={16} aria-hidden />
                              </a>
                              <button
                                className="icon-button danger"
                                type="button"
                                title={doc.is_built_in ? '内建文档不可删除' : '删除'}
                                onClick={() => deleteDoc(doc)}
                                disabled={doc.is_built_in || deletingDocId === doc.id}
                              >
                                <Trash2 size={16} aria-hidden />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
