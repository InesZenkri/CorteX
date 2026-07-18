import { AlertTriangle, ArrowRight, CheckCircle2, FileText, Network, ShieldCheck } from 'lucide-react'
import type { DossierSummary, Finding } from '../types'
import { kindLabel } from '../lib/format'

export function Overview({ summary, findings, onInvestigate }: { summary: DossierSummary; findings: Finding[]; onInvestigate: () => void }) {
  const stats = [
    { label: 'Dossier health', value: `${summary.health}/100`, note: 'Attention required', icon: ShieldCheck },
    { label: 'Documents', value: summary.documents, note: 'All processed', icon: FileText },
    { label: 'Verified findings', value: summary.verifiedFindings, note: 'Evidence-gated', icon: CheckCircle2 },
    { label: 'Review queue', value: summary.reviewQueue, note: 'Awaiting decision', icon: AlertTriangle },
    { label: 'Unresolved entities', value: summary.unresolvedEntities, note: 'Across the graph', icon: Network },
  ]
  return <section className="page overview-page">
    <div className="page-heading"><div><p className="eyebrow">Meridian Payments · FY 2023</p><h1>Good afternoon, Anna.</h1><p className="lede">The analysis found three verified contradictions that require your attention.</p></div><button className="primary" onClick={onInvestigate}>Open investigation <ArrowRight size={16}/></button></div>
    <div className="stats-grid">{stats.map(({ label, value, note, icon: Icon }) => <article className="stat-card" key={label}><div className="stat-icon"><Icon size={18}/></div><span>{label}</span><strong>{value}</strong><small>{note}</small></article>)}</div>
    <div className="overview-grid">
      <article className="panel"><div className="panel-header"><div><p className="eyebrow">Priority review</p><h2>Top findings</h2></div><button className="text-button" onClick={onInvestigate}>View all <ArrowRight size={14}/></button></div>
        <div className="overview-findings">{findings.slice(0, 3).map((finding) => <button key={finding.id} onClick={onInvestigate}><span className={`severity-dot ${finding.severity}`}/><div><strong>{finding.title}</strong><span>{kindLabel[finding.kind]} · {finding.sourceCount} sources</span></div><b>{finding.confidence}%</b><ArrowRight size={15}/></button>)}</div>
      </article>
      <article className="panel activity-panel"><div className="panel-header"><div><p className="eyebrow">Audit trail</p><h2>Recent activity</h2></div></div>
        <ol className="activity-list"><li><span/><div><strong>Cash discrepancy promoted</strong><small>Verification gate · 12 min ago</small></div></li><li><span/><div><strong>20 documents processed</strong><small>Evidence ledger · 18 min ago</small></div></li><li><span/><div><strong>1,284 citations anchored</strong><small>Source verifier · 21 min ago</small></div></li><li><span/><div><strong>Dossier analysis started</strong><small>Anna Müller · 26 min ago</small></div></li></ol>
      </article>
    </div>
  </section>
}

