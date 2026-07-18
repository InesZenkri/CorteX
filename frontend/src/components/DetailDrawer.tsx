import { ArrowRight, Building2, FileText, Landmark, Link2, UserRound, X } from 'lucide-react'
import type { Finding, GraphEdge, GraphNode } from '../types'

function isNode(item: GraphNode | GraphEdge): item is GraphNode { return 'kind' in item }

export function DetailDrawer({ item, findings, onClose, onFinding, onCitation }: { item: GraphNode | GraphEdge; findings: Finding[]; onClose: () => void; onFinding: (id: string) => void; onCitation: (citationId: string) => void }) {
  const Icon = isNode(item) ? { company: Building2, person: UserRound, account: Landmark, document: FileText }[item.kind] : Link2
  return <aside className="detail-drawer"><div className="drawer-top"><span className={`drawer-icon ${item.risk}`}><Icon size={18}/></span><button onClick={onClose} aria-label="Close details"><X size={18}/></button></div>
    <p className="eyebrow">{isNode(item) ? item.kind : 'Relationship'}</p><h2>{isNode(item) ? item.label : item.label}</h2><p className="drawer-subtitle">{isNode(item) ? item.subtitle : item.explanation}</p>
    <div className="risk-block"><span>Risk assessment</span><strong className={item.risk}>{item.risk === 'alert' ? 'Elevated risk' : item.risk === 'watch' ? 'Review suggested' : 'No issue found'}</strong></div>
    <section><div className="section-title"><span>Linked findings</span><b>{item.findingIds.length}</b></div>{item.findingIds.length ? item.findingIds.map((id) => { const finding = findings.find((candidate) => candidate.id === id); return <button className="drawer-link" key={id} onClick={() => onFinding(id)}><div><strong>{finding?.title ?? id}</strong><span>{finding ? `${finding.severity} · ${finding.confidence}% confidence` : 'Open finding details'}</span></div><ArrowRight size={15}/></button> }) : <p className="empty-copy">No findings are linked to this entity.</p>}</section>
    <section><div className="section-title"><span>Source evidence</span><b>{item.citations.length}</b></div>{item.citations.map((citation) => <button className="citation-row" key={citation.id} onClick={() => onCitation(citation.id)}><FileText size={16}/><div><strong>{citation.documentName}</strong><span>Page {citation.page} · “{citation.quote.slice(0, 48)}…”</span></div><ArrowRight size={14}/></button>)}</section>
  </aside>
}
