export type ReviewStatus = 'confirmed' | 'rejected' | 'needs_review'
export type FindingKind = 'finding' | 'observation' | 'clean'
export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface Citation {
  id: string
  documentId: string
  documentName: string
  page: number
  quote: string
  boundingBox?: { x: number; y: number; width: number; height: number }
}

export interface Money {
  amount: string
  currency: string
  originalText: string
  citation: Citation
}

export interface Dossier {
  id: string
  name: string
  company: string
  period: string
  status: 'ready' | 'processing' | 'failed'
  progress: number
}

export interface DossierSummary {
  health: number
  documents: number
  verifiedFindings: number
  reviewQueue: number
  unresolvedEntities: number
  lastUpdated: string
}

export interface DocumentRecord {
  id: string
  name: string
  type: string
  language: 'DE' | 'EN'
  pages: number
  status: 'verified' | 'processing' | 'unavailable'
  extractedFacts: number
  previewLines: string[]
}

export interface GraphNode {
  id: string
  label: string
  kind: 'company' | 'person' | 'account' | 'document'
  subtitle: string
  risk: 'alert' | 'watch' | 'clear'
  sourceCount: number
  findingIds: string[]
  citations: Citation[]
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  risk: 'alert' | 'watch' | 'clear'
  explanation: string
  findingIds: string[]
  citations: Citation[]
}

export interface Finding {
  id: string
  rank: number
  title: string
  summary: string
  kind: FindingKind
  severity: Severity
  confidence: number
  reviewStatus: ReviewStatus
  amount?: Money
  sourceCount: number
  citations: Citation[]
}

export interface Contradiction {
  id: string
  label: string
  statement: string
  citation: Citation
}

export interface FindingDetail extends Finding {
  claim: string
  checks: { label: string; result: 'passed' | 'failed'; detail: string }[]
  contradictions: Contradiction[]
  defenses: { explanation: string; verdict: 'refuted' | 'plausible'; detail: string }[]
  auditorNote?: string
}

export interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }
export interface ReviewInput { status: ReviewStatus; note?: string }

