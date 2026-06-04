import { Pin } from './types'

const DB_NAME = 'bosai-map-db'
const DB_VERSION = 1
const PINS_STORE = 'pins'
const META_STORE = 'meta'

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(PINS_STORE)) {
        db.createObjectStore(PINS_STORE, { keyPath: 'id' })
      }
      if (!db.objectStoreNames.contains(META_STORE)) {
        db.createObjectStore(META_STORE)
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function savePins(pins: Pin[]): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(PINS_STORE, 'readwrite')
  const store = tx.objectStore(PINS_STORE)
  for (const pin of pins) {
    store.put(pin)
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getPins(): Promise<Pin[]> {
  const db = await openDB()
  const tx = db.transaction(PINS_STORE, 'readonly')
  const store = tx.objectStore(PINS_STORE)
  return new Promise((resolve, reject) => {
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function saveLastUpdated(date: string): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(META_STORE, 'readwrite')
  tx.objectStore(META_STORE).put(date, 'lastUpdated')
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getLastUpdated(): Promise<string | null> {
  const db = await openDB()
  const tx = db.transaction(META_STORE, 'readonly')
  return new Promise((resolve, reject) => {
    const req = tx.objectStore(META_STORE).get('lastUpdated')
    req.onsuccess = () => resolve(req.result ?? null)
    req.onerror = () => reject(req.error)
  })
}
