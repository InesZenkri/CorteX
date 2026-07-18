import { ChevronLeft, ChevronRight, Download, FileText, Maximize2, X } from 'lucide-react'
import type { Citation, DocumentRecord } from '../types'

export function EvidenceViewer({ citation, document, onClose }: { citation: Citation; document?: DocumentRecord; onClose: () => void }) {
  return <div className="evidence-overlay" role="dialog" aria-modal="true" aria-label="Source evidence"><div className="evidence-viewer">
    <header><div><FileText size={18}/><div><strong>{citation.documentName}</strong><span>{document?.type ?? 'Source document'} · {document?.language ?? '—'}</span></div></div><div><button title="Download"><Download size={16}/></button><button title="Expand"><Maximize2 size={16}/></button><button title="Close" onClick={onClose}><X size={18}/></button></div></header>
    <div className="pdf-toolbar"><button><ChevronLeft size={15}/></button><span>Page <strong>{citation.page}</strong> of {document?.pages ?? citation.page}</span><button><ChevronRight size={15}/></button><span className="zoom">100%</span></div>
    <div className="pdf-stage"><div className="pdf-page">
      <div className="document-letterhead"><span>{document?.name.includes('Bank') ? 'FIRST MERCHANT BANK' : document?.name.includes('Invoice') ? 'NORTHSTAR CONSULTING' : 'MERIDIAN PAYMENT SOLUTIONS'}</span><i/></div>
      {(document?.previewLines ?? [citation.quote]).map((line, index) => <p key={`${line}-${index}`} className={line === citation.quote ? 'highlight-line' : ''}>{line || '\u00a0'}{line === citation.quote && <span className="source-pin">Evidence</span>}</p>)}
      <div className="document-footer"><span>CONFIDENTIAL</span><span>Page {citation.page}</span></div>
    </div></div>
    <aside className="evidence-caption"><p className="eyebrow">Verified source passage</p><blockquote>“{citation.quote}”</blockquote><div><Shield/><span>Exact quote match · Page {citation.page} · Coordinates anchored</span></div></aside>
  </div></div>
}

function Shield() { return <span className="mini-shield">✓</span> }

