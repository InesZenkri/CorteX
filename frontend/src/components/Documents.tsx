import { CheckCircle2, FileText, Search } from 'lucide-react'
import type { DocumentRecord } from '../types'

export function Documents({ documents }: { documents: DocumentRecord[] }) {
  return <section className="page documents-page"><div className="page-heading"><div><p className="eyebrow">Evidence ledger</p><h1>Source documents</h1><p className="lede">Every extracted fact is anchored to its original passage.</p></div></div><div className="document-toolbar"><label><Search size={15}/><input placeholder="Search 20 documents…"/></label><button>All types</button><button>Verified</button></div><div className="document-table"><div className="table-head"><span>Document</span><span>Type</span><span>Language</span><span>Extracted facts</span><span>Status</span></div>{documents.map((doc) => <div className="table-row" key={doc.id}><div><span className="file-tile"><FileText size={17}/></span><div><strong>{doc.name}</strong><small>{doc.pages} pages</small></div></div><span>{doc.type}</span><span>{doc.language}</span><span>{doc.extractedFacts}</span><span className="verified-status"><CheckCircle2 size={14}/>Verified</span></div>)}</div></section>
}

