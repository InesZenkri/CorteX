import { useEffect, useState } from 'react'
import { Check, FileText, Network, ScanSearch, Search, ShieldCheck } from 'lucide-react'
import type { InvestigationStatus } from '../lib/api'

interface JourneyEvent { id: string; label: string; detail: string; status: 'active' | 'complete' }

const workPulses = [
  'Reading source passages and table structures',
  'Normalizing German and English financial values',
  'Resolving companies, accounts and counterparties',
  'Comparing facts across independent documents',
  'Testing plausible innocent explanations',
  'Pinning claims back to verbatim source quotes',
]

function StageIcon({ label }: { label: string }) {
  if (label.includes('evidence batch')) return <FileText size={17}/>
  if (label.includes('graph')) return <Network size={17}/>
  if (label.includes('check')) return <ScanSearch size={17}/>
  if (label.includes('Challenging')) return <Search size={17}/>
  return <ShieldCheck size={17}/>
}

export function InvestigationJourney({ status }: { status: InvestigationStatus }) {
  const [events, setEvents] = useState<JourneyEvent[]>([])
  const [pulse, setPulse] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setPulse((current) => (current + 1) % workPulses.length), 1400)
    return () => window.clearInterval(timer)
  }, [])
  useEffect(() => {
    if (!status.stage || status.stage === 'Ready') return
    setEvents((current) => {
      if (current.at(-1)?.label === status.stage) return current
      const completed = current.map((item) => item.status === 'active' ? { ...item, status: 'complete' as const } : item)
      const detail = status.stage.includes('completed:') ? 'A verified evidence batch has returned from GPT-5.6'
        : status.stage.includes('synthesis') ? 'Connecting facts and testing cross-document contradictions'
        : status.stage.includes('Verifying') ? 'Rechecking every quotation against its original source'
        : status.stage.includes('Submitting') ? 'Securely dispatching source-preserving evidence batches'
        : 'Preparing source documents for evidence-first analysis'
      return [...completed, { id: `${status.progress}-${status.stage}`, label: status.stage, detail, status: 'active' as const }].slice(-6)
    })
  }, [status.stage, status.progress])

  return <section className="investigation-journey" aria-live="polite">
    <div className="journey-intro">
      <span>LIVE INVESTIGATION</span>
      <h2>CorteX is following the evidence</h2>
      <p>Every extracted fact is being linked back to its exact source before it can enter the audit.</p>
    </div>
    <div className="journey-flow">
      {events.map((item) => <div className={`journey-event ${item.status}`} key={item.id}>
        <div className="journey-card">
          <span className="journey-icon"><StageIcon label={item.label}/></span>
          <div><strong>{item.label}</strong><small key={item.status === 'active' ? pulse : item.id} className={item.status === 'active' ? 'pulse-copy' : ''}>{item.status === 'active' ? workPulses[pulse] : item.detail}</small></div>
          {item.status === 'complete' ? <span className="journey-check"><Check size={13}/></span> : <span className="journey-spinner"/>}
        </div>
      </div>)}
    </div>
    <footer><span>{status.file_count} source files in scope</span><span>Only source-verified claims move forward</span></footer>
  </section>
}
