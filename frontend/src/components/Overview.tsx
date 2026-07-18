import { useMemo, useRef, useState } from 'react'
import { AlertCircle, ArrowRight, FileCheck2, FileSearch, Folder, Network, RefreshCw, ScanLine, UploadCloud } from 'lucide-react'
import { FileTree } from './FileTree'
import { folderFromDrop, folderFromFileList, formatFileSize, type UploadedFolder } from '../lib/folderUpload'

export function Overview({ folder, onFolderChange, onOpenDocuments }: { folder?: UploadedFolder; onFolderChange: (folder: UploadedFolder) => void; onOpenDocuments: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [reading, setReading] = useState(false)
  const [error, setError] = useState<string>()
  const typeCounts = useMemo(() => folder?.files.reduce<Record<string, number>>((counts, file) => { const type = file.extension.toUpperCase() || 'FILE'; counts[type] = (counts[type] ?? 0) + 1; return counts }, {}) ?? {}, [folder])

  const acceptFolder = async (read: () => UploadedFolder | Promise<UploadedFolder>) => {
    setReading(true); setError(undefined)
    try {
      const next = await read()
      if (!next.files.length && !next.tree.length) throw new Error('This folder is empty.')
      onFolderChange(next)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The folder could not be read.')
    } finally { setReading(false) }
  }

  return <section className="page intake-page">
    <div className="intake-heading"><div><p className="eyebrow">New audit engagement</p><h1>{folder ? folder.rootName : 'Bring your evidence together.'}</h1><p>{folder ? 'Your original folder hierarchy is ready for review.' : 'Drop the complete client folder. Cortex preserves its structure and every nested file.'}</p></div><div className="intake-steps" aria-label="Cortex workflow"><div className="active"><span>1</span><small>Upload</small></div><i/><div><span>2</span><small>Verify</small></div><i/><div><span>3</span><small>Investigate</small></div></div></div>
    {!folder ? <div className="intake-grid upload-empty-grid">
      <div className="intake-left">
        <div className={`dropzone ${dragging ? 'dragging' : ''} ${reading ? 'reading' : ''}`} role="button" tabIndex={0} aria-label="Choose or drop a root folder" onClick={() => !reading && inputRef.current?.click()} onKeyDown={(event) => { if ((event.key === 'Enter' || event.key === ' ') && !reading) { event.preventDefault(); inputRef.current?.click() } }} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); setDragging(false); void acceptFolder(() => folderFromDrop(event.dataTransfer)) }}>
          <div className="dropzone-action">
            <div className="dropzone-content"><h2>{reading ? 'Reading folder structure…' : 'Upload the complete audit folder'}</h2><p>Keep the client’s original hierarchy intact. Every nested directory and file is reconstructed exactly as selected.</p><span className="click-hint"><Folder size={14}/>{reading ? 'Reading folder…' : 'Click anywhere or drop a folder'}<ArrowRight size={13}/></span></div>
            <span className="upload-scene" aria-hidden="true"><span className="scene-grid"/><span className="connection connection-a"/><span className="connection connection-b"/><span className="connection connection-c"/><span className="connection connection-d"/><span className="floating-file file-pdf"><b>PDF</b><i/><i/></span><span className="floating-file file-sheet"><b>XLSX</b><i/><i/></span><span className="floating-file file-doc"><b>DOCX</b><i/><i/></span><span className="floating-file file-text"><b>TXT</b><i/><i/></span><span className="upload-core"><span className="core-ring"/>{reading ? <RefreshCw className="spin" size={25}/> : <UploadCloud size={25}/>}<span className="scan-beam"/></span><span className="any-format">+ any file type</span></span>
          </div><input ref={inputRef} hidden type="file" multiple onChange={(event) => event.target.files && void acceptFolder(() => folderFromFileList(event.target.files!))} {...{ webkitdirectory: '' }}/>
        </div>
        {error && <div className="upload-error"><AlertCircle size={15}/><span>{error}</span></div>}
      </div>
      <aside className="upload-guidance"><div className="guidance-visual"><Folder size={25}/><span/><span/><span/></div><p className="eyebrow">What happens next</p><h2>Your structure, unchanged.</h2><p>Cortex reads the directory paths provided by your browser and rebuilds the hierarchy without renaming or regrouping anything.</p><ol><li><span>01</span>Choose one root folder</li><li><span>02</span>Review every nested item</li><li><span>03</span>Continue to the document workspace</li></ol></aside>
    </div> : <div className="uploaded-layout">
      <section className="uploaded-tree-card"><header><div><span className="uploaded-folder-icon"><Folder size={20}/></span><div><p className="eyebrow">Uploaded folder</p><h2>{folder.rootName}</h2></div></div><button onClick={() => inputRef.current?.click()}><RefreshCw size={13}/> Replace folder</button><input ref={inputRef} hidden type="file" multiple onChange={(event) => event.target.files && void acceptFolder(() => folderFromFileList(event.target.files!))} {...{ webkitdirectory: '' }}/></header><div className="uploaded-tree-scroll"><FileTree items={folder.tree}/></div></section>
      <aside className="upload-inspector"><p className="eyebrow">Folder summary</p><div className="upload-metric"><strong>{folder.files.length}</strong><span>files discovered</span></div><div className="upload-metric"><strong>{formatFileSize(folder.totalBytes)}</strong><span>total size</span></div><div className="type-breakdown">{Object.entries(typeCounts).sort((a,b) => b[1] - a[1]).map(([type,count]) => <div key={type}><span>{type}</span><i><b style={{ width: `${Math.max(12, count / folder.files.length * 100)}%` }}/></i><strong>{count}</strong></div>)}</div><button className="open-documents" onClick={onOpenDocuments}>Review documents <ArrowRight size={15}/></button></aside>
    </div>}
    <div className="trust-strip"><div><FileSearch size={16}/><span><strong>Structure-aware</strong>Folder hierarchy preserved</span></div><i/><div><ScanLine size={16}/><span><strong>Browser-native</strong>No sample data or renaming</span></div><i/><div><Network size={16}/><span><strong>Nested paths</strong>Subfolders remain connected</span></div><i/><div><FileCheck2 size={16}/><span><strong>Review first</strong>Inspect before processing</span></div></div>
  </section>
}
