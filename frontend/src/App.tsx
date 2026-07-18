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
  const [investigationStarting, setInvestigationStarting] = useState(false)
  const [integrationError, setIntegrationError] = useState<string>()
  const uploadedFolder = combineFolders(uploadedFolders)
  useEffect(() => { void loadFoldersFromCache().then(setUploadedFolders).catch(() => undefined) }, [])
  const addUploadedFolder = (folder: UploadedFolder) => { setUploadedFolders((current) => { const next = [...current, folder]; void saveFoldersToCache(next).catch(() => undefined); return next }) }
  const deleteUploadedFolder = (id: string) => {
    const target = uploadedFolders.find((folder) => folder.id === id)
    if (!target || !window.confirm(`Delete “${target.rootName}” from this engagement? The original files on your computer will not be affected.`)) return
    setUploadedFolders((current) => { const next = current.filter((folder) => folder.id !== id); void saveFoldersToCache(next).catch(() => undefined); return next })
    if (investigationScope?.id === id) setInvestigationScope(undefined)
  }
  const openInvestigation = async (scope?: UploadedFolder) => {
    if (!scope || investigationStarting) return
    setInvestigationStarting(true); setIntegrationError(undefined)
    try {
      await api.uploadScope(scope)
      await queryClient.invalidateQueries({ queryKey: ['dossiers'] })
      await api.investigate()
      setInvestigationScope(scope); setFindingId(undefined); setSelectedGraphItem(undefined); setView('investigate')
      await queryClient.invalidateQueries({ queryKey: ['investigation-status'] })
    } catch (reason) {
      setIntegrationError(reason instanceof Error ? reason.message : 'The backend investigation could not be started.')
    } finally { setInvestigationStarting(false) }
  }
  const dossierQuery = useQuery({ queryKey: ['dossiers'], queryFn: api.dossiers })
  const dossierId = dossierQuery.data?.[0]?.id ?? ''
  const summaryQuery = useQuery({ queryKey: ['summary', dossierId], queryFn: () => api.summary(dossierId), enabled: !!dossierId })
  const investigationStatusQuery = useQuery({ queryKey: ['investigation-status'], queryFn: api.investigationSummary, enabled: view === 'investigate', refetchInterval: (query) => query.state.data?.dossier_status === 'processing' ? 1500 : false })
  const resultsReady = investigationStatusQuery.data?.status === 'ready' && investigationStatusQuery.data?.dossier_status === 'ready'
  const graphQuery = useQuery({ queryKey: ['graph', dossierId], queryFn: () => api.graph(dossierId), enabled: !!dossierId && view === 'investigate' && resultsReady })
  const findingsQuery = useQuery({ queryKey: ['findings', dossierId], queryFn: () => api.findings(dossierId), enabled: !!dossierId && view === 'investigate' && resultsReady })
  const documentsQuery = useQuery({ queryKey: ['documents', dossierId], queryFn: () => api.documents(dossierId), enabled: !!dossierId })
  const findingQuery = useQuery({ queryKey: ['finding', findingId], queryFn: () => api.finding(findingId!), enabled: !!findingId })
  const reviewMutation = useMutation({ mutationFn: ({ status }: { status: ReviewStatus }) => api.review(findingId!, { status }), onSuccess: (updated) => { queryClient.setQueryData(['finding', findingId], updated); queryClient.invalidateQueries({ queryKey: ['findings', dossierId] }) } })
  const allQueries = [dossierQuery]
  const error = allQueries.find((query) => query.isError)?.error

  useEffect(() => { if (findingId) setSelectedGraphItem(undefined) }, [findingId])
  useEffect(() => {
    if (investigationStatusQuery.data?.dossier_status === 'ready' && investigationStatusQuery.data.progress === 100) {
      void queryClient.invalidateQueries({ queryKey: ['graph', dossierId] })
      void queryClient.invalidateQueries({ queryKey: ['findings', dossierId] })
      void queryClient.invalidateQueries({ queryKey: ['summary', dossierId] })
    }
  }, [investigationStatusQuery.data?.dossier_status, investigationStatusQuery.data?.progress, dossierId, queryClient])
  const openCitation = (id: string) => {
    const all = [...(findingQuery.data?.citations ?? []), ...(selectedGraphItem?.citations ?? []), ...(graphQuery.data?.nodes.flatMap((node) => node.citations) ?? [])]
    const found = all.find((item) => item.id === id)
    if (found) setCitation(found)
  }
  if (error) return <div className="state-page"><AlertTriangle/><h1>Workspace unavailable</h1><p>{error.message}</p><button onClick={() => window.location.reload()}>Try again</button></div>
  if (dossierQuery.isLoading) return <div className="state-page"><LoaderCircle className="spin"/><p>Opening evidence ledger…</p></div>
  const investigationFailed = investigationStatusQuery.data?.dossier_status === 'failed' || investigationStatusQuery.isError
  const investigationError = investigationStatusQuery.data?.error || (investigationStatusQuery.error as Error | null)?.message
  const investigationProcessing = investigationStatusQuery.data?.dossier_status === 'processing'

  return <Shell folderName={uploadedFolder?.rootName} documentCount={uploadedFolder?.files.length} view={view} onViewChange={(next) => { setView(next); setFindingId(undefined); setSelectedGraphItem(undefined) }}>
    {view === 'overview' && <Overview
      folder={uploadedFolder}
      folders={uploadedFolders}
      onFolderAdd={addUploadedFolder}
      onFolderDelete={deleteUploadedFolder}
      onInvestigate={(scope) => void openInvestigation(scope)}
      onOpenDocuments={() => setView('documents')}
    />}
    {view === 'documents' && <Documents folder={uploadedFolder} onUpload={() => setView('overview')}/>} 
    {view === 'investigate' && <div className="investigation-page">
      {findingId && findingQuery.data ? <FindingDetail finding={findingQuery.data} isUpdating={reviewMutation.isPending} onBack={() => setFindingId(undefined)} onReview={(status) => reviewMutation.mutate({ status })} onCitation={openCitation}/>
      : <><div className="investigation-main"><div className="investigation-heading"><div><p className="eyebrow">Entity intelligence · {investigationScope?.rootName ?? 'No folder scope selected'}</p><h1>{investigationProcessing ? 'Analyzing evidence…' : investigationFailed ? 'Investigation stopped.' : 'Follow the money.'}</h1></div><div><span className="live-dot"/> {investigationProcessing ? `${investigationStatusQuery.data?.progress}% · ${investigationStatusQuery.data?.file_count} files` : investigationScope ? `${investigationScope.files.length} source files in scope` : 'Select a scope from Overview'}</div></div>{investigationProcessing ? <div className="analysis-progress"><LoaderCircle className="spin"/><strong>{investigationStatusQuery.data?.stage ?? 'GPT-5.6 is analyzing the evidence'}</strong><span>Each evidence batch is processed before dossier-level synthesis and quote verification.</span><i><b style={{ width: `${investigationStatusQuery.data?.progress ?? 0}%` }}/></i></div> : investigationFailed ? <div className="analysis-progress error"><AlertTriangle/><strong>GPT-5.6 investigation failed</strong><span>{investigationError ?? 'The backend worker stopped before producing an attested report.'}</span><button onClick={() => setView('overview')}>Return to Overview</button></div> : resultsReady && graphQuery.data ? <InvestigationGraph data={graphQuery.data} selected={selectedGraphItem} onSelect={setSelectedGraphItem}/> : <div className="panel-loader">No completed investigation is available for this scope.</div>}{selectedGraphItem && <DetailDrawer item={selectedGraphItem} onClose={() => setSelectedGraphItem(undefined)} onFinding={setFindingId} onCitation={openCitation}/>}</div>{resultsReady && findingsQuery.data && <FindingList findings={findingsQuery.data} activeId={findingId} onSelect={setFindingId}/>}</>}
    </div>}
    {citation && <EvidenceViewer citation={citation} document={documentsQuery.data?.find((doc) => doc.id === citation.documentId)} onClose={() => setCitation(undefined)}/>} 
    {investigationStarting && <div className="integration-toast"><LoaderCircle className="spin"/><span>Uploading selected scope to AuditPipe…</span></div>}
    {integrationError && <button className="integration-toast error" onClick={() => setIntegrationError(undefined)}><AlertTriangle size={15}/><span>{integrationError}</span></button>}
  </Shell>
}
