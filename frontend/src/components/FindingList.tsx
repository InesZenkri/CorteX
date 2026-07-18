import { CheckCircle2, ChevronRight, CircleAlert, Eye, XCircle } from 'lucide-react'
import type { Finding } from '../types'
import { formatMoney, kindLabel, reviewLabel } from '../lib/format'

const statusIcon = { confirmed: CheckCircle2, rejected: XCircle, needs_review: Eye }

export function FindingList({ findings, activeId, onSelect }: { findings: Finding[]; activeId?: string; onSelect: (id: string) => void }) {
  return <aside className="findings-panel"><div className="findings-heading"><div><p className="eyebrow">Ranked by evidence strength</p><h2>Findings</h2></div><span>{findings.length}</span></div>
    <div className="finding-tabs"><button className="active">All</button><button>Findings</button><button>Observations</button></div>
    <div className="finding-list">{findings.map((finding) => { const StatusIcon = statusIcon[finding.reviewStatus]; return <button key={finding.id} className={`finding-card ${finding.kind} ${activeId === finding.id ? 'active' : ''}`} onClick={() => onSelect(finding.id)}>
      <div className="finding-card-top"><span className={`rank rank-${finding.severity}`}>0{finding.rank}</span><span className={`kind kind-${finding.kind}`}>{kindLabel[finding.kind]}</span><span className="confidence">{finding.confidence}%</span></div>
      <strong>{finding.title}</strong><p>{finding.summary}</p>
      {finding.amount && <div className="amount"><CircleAlert size={14}/>{formatMoney(finding.amount.amount, finding.amount.currency)}</div>}
      <div className="finding-meta"><span><StatusIcon size={13}/>{reviewLabel[finding.reviewStatus]}</span><span>{finding.sourceCount} sources</span><ChevronRight size={15}/></div>
    </button>})}</div>
  </aside>
}

