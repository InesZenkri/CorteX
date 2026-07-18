import { useState } from 'react'
import { Files, LayoutDashboard, Network, PanelLeftClose, PanelLeftOpen, Search } from 'lucide-react'

type View = 'overview' | 'investigate' | 'documents'

export function Shell({ children, folderName, documentCount, view, onViewChange }: { children: React.ReactNode; folderName?: string; documentCount?: number; view: View; onViewChange: (view: View) => void }) {
  const [collapsed, setCollapsed] = useState(false)
  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <aside className="sidebar">
      <div className="sidebar-head"><div className="brand">corteX</div><button className="collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>{collapsed ? <PanelLeftOpen size={17}/> : <PanelLeftClose size={17}/>}</button></div>
      <p className="eyebrow sidebar-label">Workspace</p>
      <nav className="main-nav" aria-label="Primary">
        <button title="Overview" className={view === 'overview' ? 'active' : ''} onClick={() => onViewChange('overview')}><LayoutDashboard size={17} /><span className="nav-label">Overview</span></button>
        <button title="Investigate" className={view === 'investigate' ? 'active' : ''} onClick={() => onViewChange('investigate')}><Network size={17} /><span className="nav-label">Investigate</span></button>
        <button title="Documents" className={view === 'documents' ? 'active' : ''} onClick={() => onViewChange('documents')}><Files size={17} /><span className="nav-label">Documents</span>{documentCount !== undefined && <span className="nav-count">{documentCount}</span>}</button>
      </nav>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div className="dossier-picker"><span className={`dossier-dot ${folderName ? '' : 'inactive'}`}/><div><span className="eyebrow">Uploaded folder</span><strong>{folderName ?? 'No folder selected'}</strong></div></div>
        <div className="top-actions"><button className="search-button"><Search size={16}/> Search dossier <kbd>⌘ K</kbd></button></div>
      </header>
      {children}
    </main>
  </div>
}
