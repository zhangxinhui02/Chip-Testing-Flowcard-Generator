import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, ClipboardList, MessageSquareText, Search } from 'lucide-react';
import { docsApi } from './api';
import { Chat } from './modules/Chat';
import { Flowcards } from './modules/Flowcards';
import { KnowledgeBase } from './modules/KnowledgeBase';
import { KnowledgeSearch } from './modules/KnowledgeSearch';
import type { Doc, ModuleKey } from './types';

const navItems: Array<{
  key: ModuleKey;
  label: string;
  icon: typeof BookOpen;
}> = [
  { key: 'docs', label: '知识库管理', icon: BookOpen },
  { key: 'docSearch', label: '知识库语义搜索', icon: Search },
  { key: 'chat', label: '对话', icon: MessageSquareText },
  { key: 'flowcards', label: '芯片测试流程卡', icon: ClipboardList }
];

export default function App() {
  const [activeModule, setActiveModule] = useState<ModuleKey>('docs');
  const [docs, setDocs] = useState<Doc[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    setDocsLoading(true);
    try {
      setDocs(await docsApi.list());
      setDocsError(null);
    } catch (err) {
      setDocsError(err instanceof Error ? err.message : '文档列表加载失败');
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocs();
    const timer = window.setInterval(() => {
      void loadDocs();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [loadDocs]);

  const activeContent = useMemo(() => {
    if (activeModule === 'docs') {
      return <KnowledgeBase docs={docs} loading={docsLoading} error={docsError} onRefresh={loadDocs} />;
    }
    if (activeModule === 'docSearch') {
      return <KnowledgeSearch docs={docs} />;
    }
    if (activeModule === 'chat') {
      return <Chat docs={docs} />;
    }
    return <Flowcards docs={docs} />;
  }, [activeModule, docs, docsError, docsLoading, loadDocs]);

  return (
    <div className="app-shell">
      <aside className="main-nav">
        <div className="brand">
          <div className="brand-mark">CT</div>
          <div>
            <h1>芯片测试流程卡生成器</h1>
            <p>Chip Testing Flowcard Generator</p>
          </div>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={activeModule === item.key ? 'active' : ''}
                type="button"
                onClick={() => setActiveModule(item.key)}
              >
                <Icon size={18} aria-hidden />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="workspace">{activeContent}</main>
    </div>
  );
}
