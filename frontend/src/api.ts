import type { ChatMessage, ChatSummary, Doc, DocFileType, Flowcard, SemanticSearchHit } from './types';

const API_BASE = '/api';

interface BackendSemanticSearchHit {
  document_title: string;
  hierarchy: string[];
  content: string;
}

async function readError(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`;

  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join('；') || fallback;
    }
    return JSON.stringify(body);
  } catch {
    return fallback;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...init?.headers
    }
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.json() as Promise<T>;
}

export const docsApi = {
  list: () => requestJson<Doc[]>('/docs'),
  create: (input: { title: string; fileType: DocFileType; note: string; file: File }) => {
    const formData = new FormData();
    formData.append('title', input.title);
    formData.append('file_type', input.fileType);
    formData.append('note', input.note);
    formData.append('file', input.file);

    return requestJson<boolean>('/docs', {
      method: 'POST',
      body: formData
    });
  },
  update: (docId: string, input: { title: string; note: string }) =>
    requestJson<boolean>(`/docs/${encodeURIComponent(docId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        new_title: input.title,
        new_note: input.note
      })
    }),
  remove: (docId: string) =>
    requestJson<boolean>(`/docs/${encodeURIComponent(docId)}`, {
      method: 'DELETE'
    }),
  search: async (input: {
    query: string;
    usingDocIds: string[];
    k: number;
    rerankingK: number | null;
  }) => {
    const results = await requestJson<BackendSemanticSearchHit[]>('/docs/search', {
      method: 'POST',
      body: JSON.stringify({
        query: input.query,
        using_doc_ids: input.usingDocIds,
        k: input.k,
        reranking_k: input.rerankingK
      })
    });

    return results.map((result) => ({
      documentTitle: result.document_title,
      hierarchy: result.hierarchy,
      content: result.content
    })) as SemanticSearchHit[];
  }
};

export const chatsApi = {
  list: () => requestJson<ChatSummary[]>('/chats'),
  create: () =>
    requestJson<string>('/chats', {
      method: 'POST'
    }),
  get: (chatId: string) => requestJson<ChatMessage[]>(`/chats/${encodeURIComponent(chatId)}`),
  updateTitle: (chatId: string, title: string) =>
    requestJson<boolean>(`/chats/${encodeURIComponent(chatId)}`, {
      method: 'PUT',
      body: JSON.stringify({ new_title: title })
    }),
  remove: (chatId: string) =>
    requestJson<boolean>(`/chats/${encodeURIComponent(chatId)}`, {
      method: 'DELETE'
    }),
  send: (
    chatId: string,
    input: {
      message: string;
      usingDocs: string[];
      k: number;
      rerankingK: number | null;
    }
  ) =>
    requestJson<string>(`/chats/${encodeURIComponent(chatId)}/chat`, {
      method: 'POST',
      body: JSON.stringify({
        message: input.message,
        using_docs: input.usingDocs,
        k: input.k,
        reranking_k: input.rerankingK
      })
    })
};

export const flowcardsApi = {
  list: () => requestJson<Record<string, Flowcard>>('/flowcards'),
  create: (input: {
    title: string | null;
    orderDocId: string | null;
    orderMessage: string | null;
    chipCode: string | null;
    usingDocIds: string[];
    k: number;
    rerankingK: number | null;
  }) =>
    requestJson<[string, Flowcard]>('/flowcards', {
      method: 'POST',
      body: JSON.stringify({
        title: input.title,
        order_doc_id: input.orderDocId,
        order_message: input.orderMessage,
        chip_code: input.chipCode,
        using_doc_ids: input.usingDocIds,
        k: input.k,
        reranking_k: input.rerankingK
      })
    }),
  updateTitle: (flowcardId: string, title: string) =>
    requestJson<boolean>(`/flowcards/${encodeURIComponent(flowcardId)}`, {
      method: 'PUT',
      body: JSON.stringify({ new_title: title })
    }),
  remove: (flowcardId: string) =>
    requestJson<boolean>(`/flowcards/${encodeURIComponent(flowcardId)}`, {
      method: 'DELETE'
    })
};
