import type { Dossier, DossierSummary, DocumentRecord, Finding, FindingDetail, GraphData, ReviewInput } from '../types'
import type { UploadedFolder } from './folderUpload'
import { mockRequest } from './mockApi'

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const useMock = import.meta.env.VITE_USE_MOCK_API === 'true'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (useMock) return mockRequest(path, init) as Promise<T>
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  dossiers: () => request<Dossier[]>('/api/dossiers'),
  summary: (id: string) => request<DossierSummary>(`/api/dossiers/${id}/summary`),
  documents: (id: string) => request<DocumentRecord[]>(`/api/dossiers/${id}/documents`),
  graph: (id: string) => request<GraphData>(`/api/dossiers/${id}/graph`),
  findings: (id: string) => request<Finding[]>(`/api/dossiers/${id}/findings`),
  finding: (id: string) => request<FindingDetail>(`/api/findings/${id}`),
  review: (id: string, input: ReviewInput) => request<FindingDetail>(`/api/findings/${id}`, { method: 'PATCH', body: JSON.stringify(input) }),
  document: (id: string) => request<DocumentRecord>(`/api/documents/${id}`),
  documentFileUrl: (id: string) => `${baseUrl}/api/documents/${id}/file`,
  investigationSummary: () => request<{ status: 'idle' | 'processing' | 'ready' | 'failed'; dossier_status: string; progress: number; error?: string; file_count: number }>('/api/investigation/summary'),
  uploadScope: async (folder: UploadedFolder) => {
    const form = new FormData()
    folder.files.forEach((item) => form.append('files', item.file, `CortexScope/${item.relativePath}`))
    const response = await fetch(`${baseUrl}/api/upload`, { method: 'POST', body: form })
    if (!response.ok) throw new Error(await response.text() || `Upload failed (${response.status})`)
    return response.json() as Promise<{ ok: boolean; files: number; dossierId: string }>
  },
  investigate: () => request<{ ok: boolean; status: string; dossierId: string }>('/api/investigate', { method: 'POST', body: JSON.stringify({ use_llm: import.meta.env.VITE_USE_LLM === 'true' }) }),
}
