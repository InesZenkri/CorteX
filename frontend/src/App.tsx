import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, LoaderCircle } from 'lucide-react'
import { api } from './lib/api'
import type { Citation, GraphEdge, GraphNode, ReviewStatus } from './types'
import { Shell } from './components/Shell'
import { Overview } from './components/Overview'
import { InvestigationGraph } from './components/InvestigationGraph'
import { FindingList } from './components/FindingList'
import { DetailDrawer } from './components/DetailDrawer'
import { FindingDetail } from './components/FindingDetail'
import { EvidenceViewer } from './components/EvidenceViewer'
import { Documents } from './components/Documents'
import { combineFolders, type UploadedFolder } from './lib/folderUpload'
import { loadFoldersFromCache, saveFoldersToCache } from './lib/folderCache'

type View = 'overview' | 'investigate' | 'documents'

export default function App() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<View>('overview')
  const [selectedGraphItem, setSelectedGraphItem] = useState<GraphNode | GraphEdge>()
  const [findingId, setFindingId] = useState<string>()
  const [citation, setCitation] = useState<Citation>()
  const [uploadedFolders, setUploadedFolders] = useState<UploadedFolder[]>([])
  const [investigationScope, setInvestigationScope] = useState<UploadedFolder>()
  const uploadedFolder = combineFolders(uploadedFolders)
  useEffect(() => { void loadFoldersFromCache().then(setUploadedFolders).catch(() => undefined) }, [])
  const addUploadedFolder = (folder: UploadedFolder) => { setUploadedFolders((current) => { const next = [...current, folder]; void saveFoldersToCache(next).catch(() => undefined); return next }) }
  const deleteUploadedFolder = (id: string) => {
    const target = uploadedFolders.find((folder) => folder.id === id)
    if (!target || !window.confirm(`Delete “${target.rootName}” from this engagement? The original files on your computer will not be affected.`)) return
    setUploadedFolders((current) => { const next = current.filter((folder) => folder.id !== id); void saveFoldersToCache(next).catch(() => undefined); return next })
    if (investigationScope?.id === id) setInvestigationScope(undefined)
  }
  const openInvestigation = (scope?: UploadedFolder) => { setInvestigationScope(scope); setFindingId(undefined); setSelectedGraphItem(undefined); setView('investigate') }
  const dossierQuery = useQuery({ queryKey: ['dossiers'], queryFn: api.dossiers })
  const dossierId = dossierQuery.data?.[0]?.id ?? ''
  const summaryQuery = useQuery({ queryKey: ['summary', dossierId], queryFn: () => api.summary(dossierId), enabled: !!dossierId })
  const graphQuery = useQuery({ queryKey: ['graph', dossierId], queryFn: () => api.graph(dossierId), enabled: !!dossierId })
  const findingsQuery = useQuery({ queryKey: ['findings', dossierId], queryFn: () => api.findings(dossierId), enabled: !!dossierId })
  const documentsQuery = useQuery({ queryKey: ['documents', dossierId], queryFn: () => api.documents(dossierId), enabled: !!dossierId })
  const findingQuery = useQuery({ queryKey: ['finding', findingId], queryFn: () => api.finding(findingId!), enabled: !!findingId })
  const reviewMutation = useMutation({ mutationFn: ({ status }: { status: ReviewStatus }) => api.review(findingId!, { status }), onSuccess: (updated) => { queryClient.setQueryData(['finding', findingId], updated); queryClient.invalidateQueries({ queryKey: ['findings', dossierId] }) } })
  const allQueries = [dossierQuery, graphQuery, findingsQuery, documentsQuery]
  const error = allQueries.find((query) => query.isError)?.error

  useEffect(() => { if (findingId) setSelectedGraphItem(undefined) }, [findingId])
  const openCitation = (id: string) => {
    const all = [...(findingQuery.data?.citations ?? []), ...(selectedGraphItem?.citations ?? []), ...(graphQuery.data?.nodes.flatMap((node) => node.citations) ?? [])]
    const found = all.find((item) => item.id === id)
    if (found) setCitation(found)
  }
  if (error) return <div className="state-page"><AlertTriangle/><h1>Workspace unavailable</h1><p>{error.message}</p><button onClick={() => window.location.reload()}>Try again</button></div>
  if (dossierQuery.isLoading) return <div className="state-page"><LoaderCircle className="spin"/><p>Opening evidence ledger…</p></div>

  return <Shell folderName={uploadedFolder?.rootName} documentCount={uploadedFolder?.files.length} view={view} onViewChange={(next) => { setView(next); setFindingId(undefined); setSelectedGraphItem(undefined) }}>
    {view === 'overview' && <Overview folder={uploadedFolder} folders={uploadedFolders} onFolderAdd={addUploadedFolder} onFolderDelete={deleteUploadedFolder} onInvestigate={openInvestigation} onOpenDocuments={() => setView('documents')}/>} 
    {view === 'documents' && <Documents folder={uploadedFolder} onUpload={() => setView('overview')}/>} 
    {view === 'investigate' && <div className="investigation-page">
      {findingId && findingQuery.data ? <FindingDetail finding={findingQuery.data} isUpdating={reviewMutation.isPending} onBack={() => setFindingId(undefined)} onReview={(status) => reviewMutation.mutate({ status })} onCitation={openCitation}/>
      : <><div className="investigation-main"><div className="investigation-heading"><div><p className="eyebrow">Entity intelligence · {investigationScope?.rootName ?? 'No folder scope selected'}</p><h1>Follow the money.</h1></div><div><span className="live-dot"/> {investigationScope ? `${investigationScope.files.length} source files in scope` : 'Select a scope from Overview'}</div></div>{graphQuery.data ? <InvestigationGraph data={graphQuery.data} selected={selectedGraphItem} onSelect={setSelectedGraphItem}/> : <div className="panel-loader"><LoaderCircle className="spin"/>Building entity graph…</div>}{selectedGraphItem && <DetailDrawer item={selectedGraphItem} onClose={() => setSelectedGraphItem(undefined)} onFinding={setFindingId} onCitation={openCitation}/>}</div>{findingsQuery.data && <FindingList findings={findingsQuery.data} activeId={findingId} onSelect={setFindingId}/>}</>}
    </div>}
    {citation && <EvidenceViewer citation={citation} document={documentsQuery.data?.find((doc) => doc.id === citation.documentId)} onClose={() => setCitation(undefined)}/>} 
  </Shell>
}
