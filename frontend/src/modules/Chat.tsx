import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Edit3, MessageSquarePlus, RefreshCw, Save, Send, Trash2, X } from 'lucide-react';
import { chatsApi } from '../api';
import { createDefaultRagSettings, RagControls } from '../components/RagControls';
import type { ChatMessage, ChatSummary, Doc, RagSettings } from '../types';
import { validateRag } from '../utils';

interface ChatProps {
  docs: Doc[];
}

export function Chat({ docs }: ChatProps) {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [transientChatIds, setTransientChatIds] = useState<Set<string>>(() => new Set());
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [rag, setRag] = useState<RagSettings>(() => createDefaultRagSettings());
  const [loadingChats, setLoadingChats] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');

  const selectedChat = useMemo(
    () => chats.find((chat) => chat.id === selectedChatId) || null,
    [chats, selectedChatId]
  );

  const visibleMessages = useMemo(
    () => messages.filter((message) => message.type !== 'SystemMessage'),
    [messages]
  );

  const loadChats = async () => {
    setLoadingChats(true);
    setError(null);
    try {
      const remoteChats = await chatsApi.list();
      setChats((current) => {
        const remoteIds = new Set(remoteChats.map((chat) => chat.id));
        const transient = current.filter((chat) => transientChatIds.has(chat.id) && !remoteIds.has(chat.id));
        return [...transient, ...remoteChats];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '对话列表加载失败');
    } finally {
      setLoadingChats(false);
    }
  };

  useEffect(() => {
    void loadChats();
  }, []);

  useEffect(() => {
    if (!selectedChatId) {
      setMessages([]);
      return;
    }
    if (transientChatIds.has(selectedChatId)) {
      setMessages([]);
      return;
    }

    setLoadingMessages(true);
    setError(null);
    chatsApi
      .get(selectedChatId)
      .then(setMessages)
      .catch((err) => setError(err instanceof Error ? err.message : '对话加载失败'))
      .finally(() => setLoadingMessages(false));
  }, [selectedChatId, transientChatIds]);

  const createChat = async () => {
    setError(null);
    try {
      const id = await chatsApi.create();
      setTransientChatIds((current) => new Set(current).add(id));
      setChats((current) => [{ id, title: '新对话' }, ...current]);
      setSelectedChatId(id);
      setMessages([]);
      setDraft('');
      setEditingTitle(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '对话创建失败');
    }
  };

  const deleteChat = async (chat: ChatSummary) => {
    if (!window.confirm(`删除对话「${chat.title}」？`)) {
      return;
    }
    setError(null);
    try {
      if (!transientChatIds.has(chat.id)) {
        const ok = await chatsApi.remove(chat.id);
        if (!ok) {
          throw new Error('对话删除被后端拒绝');
        }
      }
      setChats((current) => current.filter((item) => item.id !== chat.id));
      setTransientChatIds((current) => {
        const next = new Set(current);
        next.delete(chat.id);
        return next;
      });
      if (selectedChatId === chat.id) {
        setSelectedChatId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '对话删除失败');
    }
  };

  const saveTitle = async () => {
    if (!selectedChatId || !titleDraft.trim()) {
      return;
    }
    setError(null);
    try {
      if (!transientChatIds.has(selectedChatId)) {
        const ok = await chatsApi.updateTitle(selectedChatId, titleDraft.trim());
        if (!ok) {
          throw new Error('标题更新被后端拒绝');
        }
      }
      setChats((current) =>
        current.map((chat) => (chat.id === selectedChatId ? { ...chat, title: titleDraft.trim() } : chat))
      );
      setEditingTitle(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '标题更新失败');
    }
  };

  const submitMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    const ragError = validateRag(rag.k, rag.rerankingEnabled, rag.rerankingK);
    if (!message) {
      setError('请输入消息');
      return;
    }
    if (ragError) {
      setError(ragError);
      return;
    }

    setSending(true);
    setError(null);
    try {
      let chatId = selectedChatId;
      if (!chatId) {
        chatId = await chatsApi.create();
        setSelectedChatId(chatId);
        setTransientChatIds((current) => new Set(current).add(chatId as string));
        setChats((current) => [{ id: chatId as string, title: '新对话' }, ...current]);
      }

      setDraft('');
      setMessages((current) => [...current, { type: 'HumanMessage', content: message }]);
      const response = await chatsApi.send(chatId, {
        message,
        usingDocs: rag.usingDocIds,
        k: rag.k,
        rerankingK: rag.rerankingEnabled ? rag.rerankingK : null
      });
      setMessages((current) => [...current, { type: 'AIMessage', content: response }]);
      setTransientChatIds((current) => {
        const next = new Set(current);
        next.delete(chatId as string);
        return next;
      });
      await loadChats();
    } catch (err) {
      setError(err instanceof Error ? err.message : '消息发送失败');
    } finally {
      setSending(false);
    }
  };

  const beginTitleEdit = () => {
    if (!selectedChat) {
      return;
    }
    setTitleDraft(selectedChat.title);
    setEditingTitle(true);
  };

  return (
    <div className="split-layout">
      <aside className="panel side-panel">
        <div className="panel-header compact">
          <h2>对话</h2>
          <div className="header-actions">
            <button className="icon-button" type="button" title="刷新" onClick={loadChats} disabled={loadingChats}>
              <RefreshCw size={16} aria-hidden />
            </button>
            <button className="icon-button primary-soft" type="button" title="新建" onClick={createChat}>
              <MessageSquarePlus size={16} aria-hidden />
            </button>
          </div>
        </div>
        <div className="list-stack">
          {chats.length === 0 ? (
            <div className="empty-inline">{loadingChats ? '加载中' : '暂无对话'}</div>
          ) : (
            chats.map((chat) => (
              <div
                key={chat.id}
                className={`list-item selectable ${selectedChatId === chat.id ? 'active' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => {
                  setSelectedChatId(chat.id);
                  setEditingTitle(false);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setSelectedChatId(chat.id);
                    setEditingTitle(false);
                  }
                }}
              >
                <span>
                  <strong>{chat.title}</strong>
                  <code>{chat.id}</code>
                </span>
                <button
                  className="inline-icon"
                  title="删除"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void deleteChat(chat);
                  }}
                >
                  <Trash2 size={15} aria-hidden />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <section className="panel conversation-panel">
        <div className="panel-header">
          <div>
            {editingTitle ? (
              <div className="title-edit-row">
                <input value={titleDraft} onChange={(event) => setTitleDraft(event.target.value)} />
                <button className="icon-button" type="button" title="保存" onClick={saveTitle}>
                  <Save size={16} aria-hidden />
                </button>
                <button className="icon-button" type="button" title="取消" onClick={() => setEditingTitle(false)}>
                  <X size={16} aria-hidden />
                </button>
              </div>
            ) : (
              <>
                <h2>{selectedChat?.title || '新对话'}</h2>
                <p>{selectedChatId || '尚未创建 ID'}</p>
              </>
            )}
          </div>
          {selectedChat && !editingTitle && (
            <button className="icon-button" type="button" title="重命名" onClick={beginTitleEdit}>
              <Edit3 size={16} aria-hidden />
            </button>
          )}
        </div>
        {error && <div className="alert danger">{error}</div>}
        <div className="messages">
          {loadingMessages ? (
            <div className="empty-inline">加载中</div>
          ) : visibleMessages.length === 0 ? (
            <div className="empty-inline">暂无消息</div>
          ) : (
            visibleMessages.map((message, index) => {
              const isUser = message.type === 'HumanMessage';
              return (
                <article className={`message ${isUser ? 'user' : 'assistant'}`} key={`${message.type}-${index}`}>
                  <div className="message-role">{isUser ? '用户' : '模型'}</div>
                  <div className="message-content">{message.content}</div>
                </article>
              );
            })
          )}
        </div>
        <form className="composer" onSubmit={submitMessage}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="输入消息"
            disabled={sending}
          />
          <button className="icon-text-button primary" type="submit" disabled={sending}>
            <Send size={16} aria-hidden />
            {sending ? '发送中' : '发送'}
          </button>
        </form>
      </section>

      <aside className="panel controls-panel">
        <RagControls docs={docs} value={rag} onChange={setRag} />
      </aside>
    </div>
  );
}
