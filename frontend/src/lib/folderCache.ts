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

export async function saveFolderToCache(folder: UploadedFolder) {
  const database = await openDatabase()
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE, 'readwrite')
    transaction.objectStore(STORE).put(folder, ACTIVE_KEY)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error)
  })
  database.close()
}

export async function loadFolderFromCache() {
  const database = await openDatabase()
  const folder = await new Promise<UploadedFolder | undefined>((resolve, reject) => {
    const transaction = database.transaction(STORE, 'readonly')
    const request = transaction.objectStore(STORE).get(ACTIVE_KEY)
    request.onsuccess = () => resolve(request.result as UploadedFolder | undefined)
    request.onerror = () => reject(request.error)
  })
  database.close()
  return folder
}

