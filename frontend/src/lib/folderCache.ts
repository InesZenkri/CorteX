import type { UploadedFolder } from './folderUpload'

const DATABASE = 'cortex-local-evidence'
const STORE = 'folder-cache'
const ACTIVE_KEY = 'active-folder'

function openDatabase() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) request.result.createObjectStore(STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveFoldersToCache(folders: UploadedFolder[]) {
  const database = await openDatabase()
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE, 'readwrite')
    transaction.objectStore(STORE).put(folders, ACTIVE_KEY)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error)
  })
  database.close()
}

export async function loadFoldersFromCache() {
  const database = await openDatabase()
  const cached = await new Promise<UploadedFolder[] | UploadedFolder | undefined>((resolve, reject) => {
    const transaction = database.transaction(STORE, 'readonly')
    const request = transaction.objectStore(STORE).get(ACTIVE_KEY)
    request.onsuccess = () => resolve(request.result as UploadedFolder[] | UploadedFolder | undefined)
    request.onerror = () => reject(request.error)
  })
  database.close()
  if (!cached) return []
  const folders = Array.isArray(cached) ? cached : [cached]
  return folders.map((folder) => ({ ...folder, id: folder.id || globalThis.crypto?.randomUUID?.() || `folder-${Date.now()}-${Math.random().toString(36).slice(2)}` }))
}
