import { Check, FileText, Network, ScanSearch, Search, ShieldCheck } from 'lucide-react'
import type { InvestigationStatus } from '../lib/api'

function StageIcon({ label, document }: { label: string; document: boolean }) {
  if (document) return <FileText size={17}/>
  if (label.includes('graph')) return <Network size={17}/>
  if (label.includes('check')) return <ScanSearch size={17}/>
  if (label.includes('Challenging')) return <Search size={17}/>
  return <ShieldCheck size={17}/>
}

export function InvestigationJourney({ status }: { status: InvestigationStatus }) {
  return <section className="investigation-journey" aria-live="polite">
    <div className="journey-intro">
      <span>LIVE INVESTIGATION</span>
      <h2>CorteX is following the evidence</h2>
      <p>Every extracted fact is being linked back to its exact source before it can enter the audit.</p>
    </div>
    <div className="journey-flow">
      {status.activity.map((item) => <div className={`journey-event ${item.status}`} key={item.id}>
        <div className="journey-card">
          <span className="journey-icon"><StageIcon label={item.label} document={item.kind === 'document'}/></span>
          <div><strong>{item.label}</strong><small>{item.detail}</small></div>
          {item.status === 'complete' ? <span className="journey-check"><Check size={13}/></span> : <span className="journey-spinner"/>}
        </div>
      </div>)}
    </div>
    <footer><span>{status.processed_files} of {status.progress_total} documents examined</span><span>Only source-anchored facts move forward</span></footer>
  </section>
}
