import { useMemo, useState } from 'react'
import { Background, Controls, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react'
import { Building2, FileText, Landmark, Search, UserRound } from 'lucide-react'
import type { GraphData, GraphEdge, GraphNode } from '../types'

const icons = { company: Building2, person: UserRound, account: Landmark, document: FileText }
const positions: Record<string, { x: number; y: number }> = { meridian: { x: 65, y: 185 }, cfo: { x: 55, y: 390 }, account: { x: 365, y: 185 }, northstar: { x: 690, y: 75 }, trustee: { x: 690, y: 265 }, bankdoc: { x: 365, y: 420 } }

function EntityNode({ data, selected }: NodeProps<Node<GraphNode>>) {
  const Icon = icons[data.kind]
  return <div className={`entity-node ${data.risk} ${selected ? 'selected' : ''}`}><Handle type="target" position={Position.Left}/><div className="node-icon"><Icon size={17}/></div><div><strong>{data.label}</strong><span>{data.subtitle}</span></div>{data.risk === 'alert' && <i/>}<Handle type="source" position={Position.Right}/></div>
}

export function InvestigationGraph({ data, selected, onSelect }: { data: GraphData; selected?: GraphNode | GraphEdge; onSelect: (item: GraphNode | GraphEdge) => void }) {
  const [query, setQuery] = useState('')
  const [riskOnly, setRiskOnly] = useState(false)
  const nodes = useMemo<Node<GraphNode>[]>(() => data.nodes.map((node) => ({ id: node.id, type: 'entity', position: positions[node.id] ?? { x: 0, y: 0 }, data: node, hidden: (riskOnly && node.risk === 'clear') || (!!query && !node.label.toLowerCase().includes(query.toLowerCase())) })), [data, query, riskOnly])
  const edges = useMemo<Edge<GraphEdge>[]>(() => data.edges.map((edge) => ({ ...edge, type: 'smoothstep', data: edge, label: edge.label, markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15 }, className: `graph-edge ${edge.risk}`, style: { strokeWidth: edge.risk === 'alert' ? 2.5 : 1.3 } })), [data])
  return <div className="graph-wrap">
    <div className="graph-toolbar"><label><Search size={15}/><input aria-label="Search entities" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search entities…"/></label><button className={riskOnly ? 'active' : ''} onClick={() => setRiskOnly(!riskOnly)}><span className="severity-dot critical"/> Risk paths</button><div className="graph-legend"><span><i className="company"/> Company</span><span><i className="person"/> Person</span><span><i className="account"/> Account</span></div></div>
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={{ entity: EntityNode }} onNodeClick={(_, node) => onSelect(node.data)} onEdgeClick={(_, edge) => edge.data && onSelect(edge.data)} fitView minZoom={0.55} maxZoom={1.6} proOptions={{ hideAttribution: true }}><Background color="#d7d3c9" gap={24} size={1}/><Controls showInteractive={false}/></ReactFlow>
    {!selected && <div className="graph-hint"><span>01</span><div><strong>Start with the red relationship</strong><p>Select an entity or connection to inspect its evidence and linked findings.</p></div></div>}
  </div>
}

