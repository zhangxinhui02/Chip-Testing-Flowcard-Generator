export type DocStatus = 'ok' | 'creating' | 'failed';
export type DocFileType = 'image' | 'pdf' | 'markdown';
export type ModuleKey = 'docs' | 'docSearch' | 'chat' | 'flowcards';

export interface Doc {
  title: string;
  id: string;
  status: DocStatus;
  note: string;
  is_built_in: boolean;
}

export interface SemanticSearchHit {
  documentTitle: string;
  hierarchy: string[];
  content: string;
}

export interface ChatResponse {
  answer: string;
  ragHits: SemanticSearchHit[];
}

export interface ChatSummary {
  id: string;
  title: string;
}

export type ChatMessageType = 'SystemMessage' | 'HumanMessage' | 'AIMessage';

export interface ChatMessage {
  type: ChatMessageType;
  content: string;
  ragHits?: SemanticSearchHit[];
}

export interface Job {
  name: string;
  requirement: string;
  start_and_end_time?: string;
  result: string;
  operator: string;
  note?: string;
}

export interface Flowcard {
  title: string;
  jobs: Job[];
}

export interface RagSettings {
  usingDocIds: string[];
  k: number;
  rerankingEnabled: boolean;
  rerankingK: number;
}
