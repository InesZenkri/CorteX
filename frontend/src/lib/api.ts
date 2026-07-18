import type { Dossier, DossierSummary, DocumentRecord, Finding, FindingDetail, GraphData, ReviewInput } from '../types'
import type { UploadedFolder } from './folderUpload'

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
export const llmRequested = import.meta.env.VITE_USE_LLM?.trim().toLowerCase() === 'true'
export interface InvestigationActivity { id: string; label: string; detail: string; kind: 'document' | 'stage'; status: 'active' | 'complete' }
export interface InvestigationStatus { status: 'idle' | 'processing' | 'ready' | 'failed'; dossier_status: string; progress: number; phase: string; processed_files: number; progress_total: number; activity: InvestigationActivity[]; error?: string; file_count: number; llm_requested: boolean; llm_available: boolean; llm_used: boolean; llm_unavailable_reason?: string; llm_attempted_requests: number; llm_successful_requests: number; llm_input_tokens: number; llm_output_tokens: number; llm_errors: string[] }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => undefined) as { detail?: string } | undefined
    throw new Error(body?.detail ?? `API request failed (${response.status})`)
  }
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
  investigationSummary: () => request<InvestigationStatus>('/api/investigation/summary'),
  uploadScope: async (folder: UploadedFolder) => {
    const form = new FormData()
    folder.files.forEach((item) => form.append('files', item.file, `CortexScope/${item.relativePath}`))
    const response = await fetch(`${baseUrl}/api/upload`, { method: 'POST', body: form })
    if (!response.ok) throw new Error(await response.text() || `Upload failed (${response.status})`)
    return response.json() as Promise<{ ok: boolean; files: number; dossierId: string }>
  },
  clearScope: () => request<{ ok: boolean }>('/api/upload', { method: 'DELETE' }),
  investigate: () => request<{ ok: boolean; status: string; dossierId: string }>('/api/investigate', { method: 'POST', body: JSON.stringify({ use_llm: llmRequested }) }),
}
