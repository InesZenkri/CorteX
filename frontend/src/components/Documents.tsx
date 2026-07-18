import { useState } from 'react'
import { FileUp, Grid2X2, List, Search, SlidersHorizontal } from 'lucide-react'
import { FileTree } from './FileTree'
import { formatFileSize, type UploadedFile, type UploadedFolder } from '../lib/folderUpload'
import { FilePreview } from './FilePreview'
import { EvidenceViewer } from './EvidenceViewer'
import type { Citation, DocumentRecord } from '../types'

const kindFor = (extension: string) => ({ pdf: 'PDF document', csv: 'CSV data', xls: 'Spreadsheet', xlsx: 'Spreadsheet', doc: 'Word document', docx: 'Word document', png: 'Image', jpg: 'Image', jpeg: 'Image' }[extension] ?? (extension ? `${extension.toUpperCase()} file` : 'File'))

export function Documents({ folder, documents, onUpload }: { folder?: UploadedFolder; documents: DocumentRecord[]; onUpload: () => void }) {
  const [preview, setPreview] = useState<UploadedFile>()
  const [backendPreview, setBackendPreview] = useState<DocumentRecord>()
  if (!folder) return <section className="page documents-page document-empty"><div><span><FileUp size={22}/></span><p className="eyebrow">No folder uploaded</p><h1>Documents will appear here.</h1><p>Upload a root folder first. Its complete nested structure will be preserved.</p><button onClick={onUpload}>Go to upload</button></div></section>
  return <section className="page documents-page"><div className="page-heading"><div><p className="eyebrow">Uploaded evidence</p><h1>{folder.rootName}</h1><p className="lede">The directory structure below comes directly from the selected folder.</p></div><div className="document-summary"><div><strong>{folder.files.length} files</strong><span>{formatFileSize(folder.totalBytes)} total</span></div></div></div>
    <div className="document-workspace">
      <aside className="folder-browser"><div className="folder-browser-head"><h2>Folders</h2><span>{documents.length} files</span></div><FileTree items={folder.tree} onFileSelect={(id) => { const local = folder.files.find((item) => item.id === id); const backend = local && documents.find((item) => item.relativePath === local.relativePath); if (backend) setBackendPreview(backend); else if (local) setPreview(local) }}/></aside>
      <div className="document-content"><div className="document-toolbar"><label><Search size={15}/><input placeholder="Search uploaded files…"/></label><button><SlidersHorizontal size={14}/> Filter</button><div className="view-switch"><button className="active"><List size={14}/></button><button><Grid2X2 size={14}/></button></div></div>
        <div className="folder-path"><span>{folder.rootName}</span><b>/</b><span>All files</span></div>
        <div className="document-table"><div className="table-head uploaded-table-head"><span>File</span><span>Type</span><span>Location</span><span>Size</span><span>Modified</span></div>{documents.map((item) => { const extension = item.relativePath.split('.').pop()?.toLowerCase() ?? ''; return <button className="table-row uploaded-table-row" key={item.id} onClick={() => setBackendPreview(item)}><div><span className="file-type-badge">{extension.slice(0, 4).toUpperCase() || 'FILE'}</span><div><strong>{item.relativePath.split('/').pop()}</strong><small>{item.relativePath}</small></div></div><span>{kindFor(extension)}</span><span className="path-cell">{item.relativePath.split('/').slice(0,-1).join(' / ') || 'Root'}</span><span>{formatFileSize(item.size)}</span><span>{new Intl.DateTimeFormat(undefined,{ dateStyle:'medium' }).format(item.modifiedAt)}</span></button> })}</div>
      </div>
    </div>
    {preview && <FilePreview item={preview} onClose={() => setPreview(undefined)}/>} 
    {backendPreview && <EvidenceViewer
      document={backendPreview}
      citation={{ id: `document-${backendPreview.id}`, documentId: backendPreview.id, documentName: backendPreview.relativePath, page: 1, quote: '' } satisfies Citation}
      onClose={() => setBackendPreview(undefined)}
    />}
  </section>
}
