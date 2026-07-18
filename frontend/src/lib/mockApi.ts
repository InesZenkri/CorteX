import { dossiers, documents, findings, graph, summary } from './fixtures'
import type { ReviewInput } from '../types'

const wait = (ms = 220) => new Promise((resolve) => setTimeout(resolve, ms))

export async function mockRequest(path: string, init?: RequestInit): Promise<unknown> {
  await wait()
  if (path === '/api/dossiers') return dossiers
  if (path.endsWith('/summary')) return summary
  if (path.endsWith('/documents')) return documents
  if (path.endsWith('/graph')) return graph
  if (path.endsWith('/findings')) return findings.map(({ claim: _claim, checks: _checks, contradictions: _contradictions, defenses: _defenses, ...finding }) => finding)
  const findingMatch = path.match(/^\/api\/findings\/([^/]+)$/)
  if (findingMatch) {
    const finding = findings.find((item) => item.id === findingMatch[1])
    if (!finding) throw new Error('Finding not found')
    if (init?.method === 'PATCH') {
      const update = JSON.parse(String(init.body)) as ReviewInput
      finding.reviewStatus = update.status
      finding.auditorNote = update.note
    }
    return finding
  }
  const documentMatch = path.match(/^\/api\/documents\/([^/]+)$/)
  if (documentMatch) {
    const document = documents.find((item) => item.id === documentMatch[1])
    if (!document) throw new Error('Document not found')
    return document
  }
  throw new Error(`Mock endpoint not implemented: ${path}`)
}

