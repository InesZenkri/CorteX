import { useEffect, useMemo, useState } from 'react'
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
import { InvestigationJourney } from './components/InvestigationJourney'
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
  const [folderCacheLoaded, setFolderCacheLoaded] = useState(false)
  const [activeDossierId, setActiveDossierId] = useState('')
  const uploadedFolder = useMemo(() => combineFolders(uploadedFolders), [uploadedFolders])
  useEffect(() => { void loadFoldersFromCache().then(setUploadedFolders).catch(() => undefined).finally(() => setFolderCacheLoaded(true)) }, [])
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
      await queryClient.cancelQueries({ queryKey: ['documents'] })
      await queryClient.cancelQueries({ queryKey: ['summary'] })
      await queryClient.cancelQueries({ queryKey: ['graph'] })
      await queryClient.cancelQueries({ queryKey: ['findings'] })
      const uploaded = await api.uploadScope(scope)
      setActiveDossierId(uploaded.dossierId)
      await api.investigate()
      setInvestigationScope(scope); setFindingId(undefined); setSelectedGraphItem(undefined); setView('investigate')
      await queryClient.invalidateQueries({ queryKey: ['dossiers'] })
    } catch (reason) {
      setIntegrationError(reason instanceof Error ? reason.message : 'The backend investigation could not be started.')
    } finally { setInvestigationStarting(false) }
  }
  const dossierQuery = useQuery({ queryKey: ['dossiers'], queryFn: api.dossiers })
  const dossierId = activeDossierId || dossierQuery.data?.[0]?.id || ''
  const summaryQuery = useQuery({ queryKey: ['summary', dossierId], queryFn: () => api.summary(dossierId), enabled: !!dossierId })
  const graphQuery = useQuery({ queryKey: ['graph', dossierId], queryFn: () => api.graph(dossierId), enabled: !!dossierId })
  const findingsQuery = useQuery({ queryKey: ['findings', dossierId], queryFn: () => api.findings(dossierId), enabled: !!dossierId })
  const documentsQuery = useQuery({ queryKey: ['documents', dossierId], queryFn: () => api.documents(dossierId), enabled: !!dossierId })
  const findingQuery = useQuery({ queryKey: ['finding', findingId], queryFn: () => api.finding(findingId!), enabled: !!findingId })
  const investigationStatusQuery = useQuery({ queryKey: ['investigation-status'], queryFn: api.investigationSummary, enabled: view === 'investigate', refetchInterval: (query) => query.state.data?.dossier_status === 'processing' ? 750 : false })
  const reviewMutation = useMutation({ mutationFn: ({ status }: { status: ReviewStatus }) => api.review(findingId!, { status }), onSuccess: (updated) => { queryClient.setQueryData(['finding', findingId], updated); queryClient.invalidateQueries({ queryKey: ['findings', dossierId] }) } })
  const allQueries = [dossierQuery, graphQuery, findingsQuery, documentsQuery]
  const error = allQueries.find((query) => query.isError)?.error

  useEffect(() => { if (findingId) setSelectedGraphItem(undefined) }, [findingId])
  useEffect(() => {
    if (!folderCacheLoaded || !uploadedFolder || view !== 'documents' || investigationStarting) return
    let cancelled = false
    const synchronizeDocuments = async () => {
      try {
        await queryClient.cancelQueries({ queryKey: ['documents'] })
        const uploaded = await api.uploadScope(uploadedFolder)
        if (cancelled) return
        setActiveDossierId(uploaded.dossierId)
        await queryClient.invalidateQueries({ queryKey: ['documents', uploaded.dossierId] })
        await queryClient.invalidateQueries({ queryKey: ['dossiers'] })
      } catch (reason) {
        if (cancelled) return
        setIntegrationError(reason instanceof Error ? reason.message : 'Could not synchronize folders with the backend.')
      }
    }
    void synchronizeDocuments()
    return () => { cancelled = true }
  }, [folderCacheLoaded, uploadedFolder, view, investigationStarting, queryClient])
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

  return <Shell folderName={uploadedFolder?.rootName} documentCount={uploadedFolder?.files.length} view={view} onViewChange={(next) => { setView(next); setFindingId(undefined); setSelectedGraphItem(undefined) }}>
    {view === 'overview' && <Overview
      folder={uploadedFolder}
      folders={uploadedFolders}
      onFolderAdd={addUploadedFolder}
      onFolderDelete={deleteUploadedFolder}
      onInvestigate={(scope) => void openInvestigation(scope)}
      onOpenDocuments={() => setView('documents')}
    />}
    {view === 'documents' && <Documents
      folder={uploadedFolder}
      documents={documentsQuery.data ?? []}
      onUpload={() => setView('overview')}
    />}
    {view === 'investigate' && <div className="investigation-page">
      {findingId && findingQuery.data ? <FindingDetail finding={findingQuery.data} isUpdating={reviewMutation.isPending} onBack={() => setFindingId(undefined)} onReview={(status) => reviewMutation.mutate({ status })} onCitation={openCitation}/>
      : <><div className="investigation-main"><div className="investigation-heading"><div><p className="eyebrow">Entity intelligence · {investigationScope?.rootName ?? dossierQuery.data?.[0]?.name ?? 'No active dossier'}</p><h1>{investigationStatusQuery.data?.dossier_status === 'processing' ? 'Analyzing evidence…' : 'Follow the money.'}</h1></div><div><span className="live-dot"/> {investigationStatusQuery.data?.dossier_status === 'processing' ? investigationStatusQuery.data.stage : `${graphQuery.data?.nodes.length ?? 0} entities · ${graphQuery.data?.edges.length ?? 0} relationships`}</div></div>{investigationStatusQuery.data?.dossier_status === 'processing' ? <InvestigationJourney status={investigationStatusQuery.data}/> : graphQuery.data ? <InvestigationGraph data={graphQuery.data} selected={selectedGraphItem} onSelect={setSelectedGraphItem}/> : <div className="panel-loader"><LoaderCircle className="spin"/>Building entity graph…</div>}{selectedGraphItem && <DetailDrawer item={selectedGraphItem} findings={findingsQuery.data ?? []} onClose={() => setSelectedGraphItem(undefined)} onFinding={setFindingId} onCitation={openCitation}/>}</div>{findingsQuery.data && <FindingList findings={findingsQuery.data} activeId={findingId} onSelect={setFindingId}/>}</>}
    </div>}
    {citation && <EvidenceViewer citation={citation} document={documentsQuery.data?.find((doc) => doc.id === citation.documentId)} onClose={() => setCitation(undefined)}/>} 
    {investigationStarting && <div className="integration-toast"><LoaderCircle className="spin"/><span>Uploading selected scope to AuditPipe…</span></div>}
    {integrationError && <button className="integration-toast error" onClick={() => setIntegrationError(undefined)}><AlertTriangle size={15}/><span>{integrationError}</span></button>}
  </Shell>
}
