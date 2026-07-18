import type { FileTreeItem } from '../components/FileTree'

export interface UploadedFile {
  id: string
  file: File
  name: string
  relativePath: string
  extension: string
  size: number
  modifiedAt: number
}

export interface UploadedFolder {
  rootName: string
  files: UploadedFile[]
  tree: FileTreeItem[]
  totalBytes: number
}

interface BrowserFileEntry {
  isFile: true
  isDirectory: false
  name: string
  fullPath: string
  file: (success: (file: File) => void, error?: (error: DOMException) => void) => void
}

interface BrowserDirectoryReader {
  readEntries: (success: (entries: BrowserEntry[]) => void, error?: (error: DOMException) => void) => void
}

interface BrowserDirectoryEntry {
  isFile: false
  isDirectory: true
  name: string
  fullPath: string
  createReader: () => BrowserDirectoryReader
}

type BrowserEntry = BrowserFileEntry | BrowserDirectoryEntry

const idFor = (path: string) => `upload-${path.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`
const extensionFor = (name: string) => name.includes('.') ? name.split('.').pop()!.toLowerCase() : ''

function uploadedFile(file: File, relativePath: string): UploadedFile {
  return { id: idFor(relativePath), file, name: file.name, relativePath, extension: extensionFor(file.name), size: file.size, modifiedAt: file.lastModified }
}

function insertPath(root: FileTreeItem[], path: string, uploaded?: UploadedFile) {
  const segments = path.split('/').filter(Boolean)
  let level = root
  segments.forEach((segment, index) => {
    const isFile = index === segments.length - 1 && Boolean(uploaded)
    let node = level.find((item) => item.name === segment && item.kind === (isFile ? 'file' : 'folder'))
    if (!node) {
      node = { id: idFor(segments.slice(0, index + 1).join('/')), name: segment, kind: isFile ? 'file' : 'folder', ...(isFile ? { bytes: uploaded!.size, meta: formatFileSize(uploaded!.size) } : { children: [] }) }
      level.push(node)
    }
    if (!isFile) level = node.children ?? (node.children = [])
  })
}

export function buildFolder(files: UploadedFile[], emptyFolders: string[] = []): UploadedFolder {
  const tree: FileTreeItem[] = []
  emptyFolders.forEach((path) => insertPath(tree, path))
  files.sort((a, b) => a.relativePath.localeCompare(b.relativePath)).forEach((item) => insertPath(tree, item.relativePath, item))
  const calculateSizes = (items: FileTreeItem[]): number => items.reduce((total, item) => {
    const bytes = item.kind === 'folder' ? calculateSizes(item.children ?? []) : (item.bytes ?? 0)
    item.bytes = bytes
    item.meta = formatFileSize(bytes)
    return total + bytes
  }, 0)
  calculateSizes(tree)
  const firstPath = files[0]?.relativePath ?? emptyFolders[0] ?? 'Uploaded folder'
  return { rootName: firstPath.split('/')[0], files, tree, totalBytes: files.reduce((sum, item) => sum + item.size, 0) }
}

export function folderFromFileList(list: FileList): UploadedFolder {
  const files = Array.from(list).map((file) => uploadedFile(file, file.webkitRelativePath || file.name))
  return buildFolder(files)
}

const fileFromEntry = (entry: BrowserFileEntry) => new Promise<File>((resolve, reject) => entry.file(resolve, reject))
const readDirectoryBatch = (reader: BrowserDirectoryReader) => new Promise<BrowserEntry[]>((resolve, reject) => reader.readEntries(resolve, reject))

async function allDirectoryEntries(entry: BrowserDirectoryEntry): Promise<BrowserEntry[]> {
  const reader = entry.createReader()
  const entries: BrowserEntry[] = []
  while (true) {
    const batch = await readDirectoryBatch(reader)
    if (!batch.length) break
    entries.push(...batch)
  }
  return entries
}

async function walkEntry(entry: BrowserEntry, files: UploadedFile[], folders: string[]) {
  const relativePath = entry.fullPath.replace(/^\//, '')
  if (entry.isFile) {
    const file = await fileFromEntry(entry)
    files.push(uploadedFile(file, relativePath))
    return
  }
  folders.push(relativePath)
  const children = await allDirectoryEntries(entry)
  await Promise.all(children.map((child) => walkEntry(child, files, folders)))
}

export async function folderFromDrop(dataTransfer: DataTransfer): Promise<UploadedFolder> {
  const entries = Array.from(dataTransfer.items)
    .map((item) => item.webkitGetAsEntry?.() as BrowserEntry | null)
    .filter((entry): entry is BrowserEntry => Boolean(entry))
  if (!entries.length) return folderFromFileList(dataTransfer.files)
  const files: UploadedFile[] = []
  const folders: string[] = []
  await Promise.all(entries.map((entry) => walkEntry(entry, files, folders)))
  return buildFolder(files, folders)
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
}
