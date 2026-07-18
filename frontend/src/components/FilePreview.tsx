import { useEffect, useState } from 'react'
import { Download, FileQuestion, X } from 'lucide-react'
import { formatFileSize, type UploadedFile } from '../lib/folderUpload'

const textExtensions = new Set(['txt','csv','tsv','xml','json','md','log','dtd','html','css','js','ts','tsx','jsx','yaml','yml','ini','sql'])

export function FilePreview({ item, onClose }: { item: UploadedFile; onClose: () => void }) {
  const [url, setUrl] = useState('')
  const [text, setText] = useState<string>()
  const [textError, setTextError] = useState(false)
  const isText = item.file.type.startsWith('text/') || textExtensions.has(item.extension)
  const isPdf = item.file.type === 'application/pdf' || item.extension === 'pdf'
  const isImage = item.file.type.startsWith('image/')
  const isAudio = item.file.type.startsWith('audio/')
  const isVideo = item.file.type.startsWith('video/')

  useEffect(() => {
    const objectUrl = URL.createObjectURL(item.file)
    setUrl(objectUrl)
    if (isText) item.file.text().then(setText).catch(() => setTextError(true))
    return () => URL.revokeObjectURL(objectUrl)
  }, [item, isText])

  return <div className="file-preview-overlay" role="dialog" aria-modal="true" aria-label={`Preview ${item.name}`} onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="file-preview-modal"><header><div><span className="file-preview-type">{item.extension.toUpperCase() || 'FILE'}</span><div><strong>{item.name}</strong><span>{item.relativePath} · {formatFileSize(item.size)}</span></div></div><div><a href={url} download={item.name} title="Download original"><Download size={16}/></a><button onClick={onClose} title="Close preview"><X size={18}/></button></div></header>
      <div className="file-preview-body">
        {isPdf && url && <iframe src={url} title={item.name}/>} 
        {isImage && url && <div className="image-preview"><img src={url} alt={item.name}/></div>}
        {isAudio && url && <div className="media-preview"><audio src={url} controls/></div>}
        {isVideo && url && <div className="media-preview"><video src={url} controls/></div>}
        {isText && !textError && <pre>{text ?? 'Loading file…'}</pre>}
        {(textError || (!isPdf && !isImage && !isAudio && !isVideo && !isText)) && <div className="binary-preview"><span><FileQuestion size={27}/></span><h2>Preview unavailable for this format</h2><p>The original file is safely cached. Download it to open it in its native application.</p><a href={url} download={item.name}><Download size={14}/> Download {item.name}</a></div>}
      </div>
    </section>
  </div>
}

