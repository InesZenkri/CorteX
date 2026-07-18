import { Activity, Bell, Files, LayoutDashboard, Network, Search, ShieldCheck } from 'lucide-react'
import type { Dossier } from '../types'

type View = 'overview' | 'investigate' | 'documents'

export function Shell({ children, dossier, view, onViewChange }: { children: React.ReactNode; dossier?: Dossier; view: View; onViewChange: (view: View) => void }) {
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">C</span><span>Corte<span className="brand-x">X</span></span></div>
      <p className="eyebrow sidebar-label">Workspace</p>
      <nav className="main-nav" aria-label="Primary">
        <button className={view === 'overview' ? 'active' : ''} onClick={() => onViewChange('overview')}><LayoutDashboard size={17} /> Overview</button>
        <button className={view === 'investigate' ? 'active' : ''} onClick={() => onViewChange('investigate')}><Network size={17} /> Investigate <span className="nav-count">4</span></button>
        <button className={view === 'documents' ? 'active' : ''} onClick={() => onViewChange('documents')}><Files size={17} /> Documents <span className="nav-count">20</span></button>
      </nav>
      <div className="sidebar-bottom">
        <div className="verified-box"><ShieldCheck size={18}/><div><strong>Evidence gate active</strong><span>All claims source-verified</span></div></div>
        <div className="profile"><div className="avatar">AM</div><div><strong>Anna Müller</strong><span>Lead auditor</span></div><button aria-label="Notifications"><Bell size={17}/></button></div>
      </div>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div className="dossier-picker"><span className="dossier-dot"/><div><span className="eyebrow">Active dossier</span><strong>{dossier?.name ?? 'Loading dossier…'}</strong></div><span className="chevron">⌄</span></div>
        <div className="top-actions"><button className="search-button"><Search size={16}/> Search dossier <kbd>⌘ K</kbd></button><div className="processing"><Activity size={15}/><span>Analysis complete</span><strong>{dossier?.progress ?? 0}%</strong></div></div>
      </header>
      {children}
    </main>
  </div>
}

