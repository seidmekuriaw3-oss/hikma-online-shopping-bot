import assert from 'node:assert/strict'
import test from 'node:test'
import { api } from './api.js'

test('api returns parsed response data', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response('{"status":"ok"}', { status: 200 })

  try {
    assert.deepEqual(await api('/api/health'), { status: 'ok' })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('api exposes server validation errors', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response('{"error":"Bad request"}', { status: 400 })

  try {
    await assert.rejects(api('/api/orders'), { message: 'Bad request' })
  } finally {
    globalThis.fetch = originalFetch
  }
})
