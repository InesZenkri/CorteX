import { useEffect, useState } from 'react'
import { Download, FileQuestion, FileText, X } from 'lucide-react'
import type { Citation, DocumentRecord } from '../types'
import { api } from '../lib/api'

const textTypes = new Set(['txt','csv','tsv','xml','json','md','log','dtd','html','css','js','ts','yaml','yml','ini','sql'])

function QuotedText({ content, quote }: { content: string; quote: string }) {
  const index = quote ? content.indexOf(quote) : -1
  if (index < 0) return <pre>{content}</pre>
  return <pre>{content.slice(0,index)}<mark>{content.slice(index,index + quote.length)}</mark>{content.slice(index + quote.length)}</pre>
}

export function EvidenceViewer({ citation, document, onClose }: { citation: Citation; document?: DocumentRecord; onClose: () => void }) {
  const [content, setContent] = useState<string>()
  const [loadError, setLoadError] = useState(false)
  const fileUrl = api.documentFileUrl(citation.documentId)
  const extension = (document?.relativePath ?? citation.documentName).split('.').pop()?.toLowerCase() ?? ''
  const mime = document?.mimeType ?? ''
  const isPdf = extension === 'pdf' || mime === 'application/pdf'
  const isImage = mime.startsWith('image/') || ['png','jpg','jpeg','gif','webp','svg'].includes(extension)
  const isText = mime.startsWith('text/') || textTypes.has(extension)

  useEffect(() => {
    setContent(undefined); setLoadError(false)
    if (isText) fetch(fileUrl).then((response) => { if (!response.ok) throw new Error('Source unavailable'); return response.text() }).then(setContent).catch(() => setLoadError(true))
  }, [fileUrl, isText])

  return <div className="evidence-overlay" role="dialog" aria-modal="true" aria-label="Source evidence" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><div className="evidence-viewer live-evidence">
    <header><div><FileText size={18}/><div><strong>{document?.relativePath ?? citation.documentName}</strong><span>{document?.type ?? extension.toUpperCase()} · {document ? `${document.size.toLocaleString()} bytes` : 'Backend source'}</span></div></div><div><a href={fileUrl} download title="Download original"><Download size={16}/></a><button title="Close" onClick={onClose}><X size={18}/></button></div></header>
    <div className="live-evidence-body">
      {isPdf && (
        <iframe src={`${fileUrl}#page=${citation.page}`} title={citation.documentName}/>
      )}
      {isImage && <div className="live-image"><img src={fileUrl} alt={citation.documentName}/></div>}
      {isText && !loadError && (
        <QuotedText content={content ?? 'Loading source…'} quote={citation.quote}/>
      )}
      {(loadError || (!isPdf && !isImage && !isText)) && <div className="binary-preview"><span><FileQuestion size={27}/></span><h2>Native preview unavailable</h2><p>This source comes directly from the backend. Download it to inspect it in its native application.</p><a href={fileUrl} download><Download size={14}/> Download source</a></div>}
    </div>
    <aside className="evidence-caption"><p className="eyebrow">Backend evidence passage</p><blockquote>“{citation.quote}”</blockquote><div><span className="mini-shield">✓</span><span>{citation.documentName} · Page {citation.page}</span></div></aside>
  </div></div>
}
