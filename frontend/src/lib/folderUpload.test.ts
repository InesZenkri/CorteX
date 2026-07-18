import { describe, expect, it } from 'vitest'
import { buildFolder, folderFromFileList } from './folderUpload'

describe('folder ingestion', () => {
  it('preserves duplicate filenames when their relative paths differ', () => {
    const first = new File(['one'], 'invoice.pdf')
    const second = new File(['two'], 'invoice.pdf')
    const folder = buildFolder([
      { id: 'a', file: first, name: first.name, relativePath: 'Audit/Supplier A/invoice.pdf', extension: 'pdf', size: first.size, modifiedAt: 1 },
      { id: 'b', file: second, name: second.name, relativePath: 'Audit/Supplier B/invoice.pdf', extension: 'pdf', size: second.size, modifiedAt: 2 },
    ])
    expect(folder.rootName).toBe('Audit')
    expect(folder.files).toHaveLength(2)
    expect(folder.tree[0].children).toHaveLength(2)
    expect(folder.tree[0]).toMatchObject({ bytes: 6, meta: '6 B' })
  })

  it('retains empty folders exposed during recursive drag and drop', () => {
    const folder = buildFolder([], ['Audit/Empty controls'])
    expect(folder.tree[0].children?.[0]).toMatchObject({ name: 'Empty controls', kind: 'folder', children: [], bytes: 0, meta: '0 B' })
  })

  it('falls back to filenames when relative paths are unavailable', () => {
    const file = new File(['data'], 'ledger.csv')
    const folder = folderFromFileList({ 0: file, length: 1, item: () => file } as unknown as FileList)
    expect(folder.files[0].relativePath).toBe('ledger.csv')
  })
})
