import { useState } from 'react'
import { ChevronDown, File, FileSpreadsheet, FileText, Folder, FolderOpen } from 'lucide-react'

export interface FileTreeItem {
  id: string
  name: string
  kind: 'folder' | 'file'
  status?: 'ready' | 'missing' | 'processing'
  meta?: string
  bytes?: number
  children?: FileTreeItem[]
}

function FileIcon({ name }: { name: string }) {
  const extension = name.split('.').pop()?.toLowerCase()
  if (extension === 'csv' || extension === 'xls' || extension === 'xlsx') return <FileSpreadsheet size={16}/>
  if (extension === 'doc' || extension === 'docx' || extension === 'pdf') return <FileText size={16}/>
  return <File size={16}/>
}

function TreeItem({ item, depth = 0, compact = false, onFileSelect }: { item: FileTreeItem; depth?: number; compact?: boolean; onFileSelect?: (id: string) => void }) {
  const [open, setOpen] = useState(true)
  const hasChildren = item.kind === 'folder' && Boolean(item.children?.length)
  return <div className="tree-item-wrap">
    <div className={`tree-item ${item.kind} ${item.kind === 'file' && onFileSelect ? 'selectable' : ''}`} style={{ paddingLeft: `${depth * (compact ? 18 : 22) + 8}px` }} role={item.kind === 'file' && onFileSelect ? 'button' : undefined} tabIndex={item.kind === 'file' && onFileSelect ? 0 : undefined} onClick={() => item.kind === 'file' && onFileSelect?.(item.id)} onKeyDown={(event) => { if (item.kind === 'file' && onFileSelect && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onFileSelect(item.id) } }}>
      {item.kind === 'folder' ? <>{hasChildren ? <button className="tree-toggle" onClick={() => setOpen(!open)} aria-label={`${open ? 'Collapse' : 'Expand'} ${item.name}`} aria-expanded={open}><ChevronDown className={`tree-chevron ${open ? '' : 'collapsed'}`} size={13}/></button> : <span className="tree-toggle-placeholder"/>}{hasChildren && open ? <FolderOpen size={17}/> : <Folder size={17}/>}</> : <><span className="tree-indent"/><FileIcon name={item.name}/></>}
      <span className="tree-name">{item.name}</span>
      {item.meta && <span className="tree-meta">{item.meta}</span>}
      {item.status && <span className={`tree-status ${item.status}`}>{item.status === 'ready' ? 'Verified' : item.status === 'processing' ? 'Processing' : 'Missing'}</span>}
    </div>
    {hasChildren && open && <div className="tree-children">{item.children!.map((child) => <TreeItem key={child.id} item={child} depth={depth + 1} compact={compact} onFileSelect={onFileSelect}/>)}</div>}
  </div>
}

export function FileTree({ items, compact = false, onFileSelect }: { items: FileTreeItem[]; compact?: boolean; onFileSelect?: (id: string) => void }) {
  return <div className={`file-tree ${compact ? 'compact' : ''}`}>{items.map((item) => <TreeItem item={item} key={item.id} compact={compact} onFileSelect={onFileSelect}/>)}</div>
}
