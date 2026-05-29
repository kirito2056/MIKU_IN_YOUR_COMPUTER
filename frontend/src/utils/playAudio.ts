function base64ToBytes(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

/** WebSocket TTS 청크(base64)를 합쳐 OGG 재생 */
export async function playOggFromBase64Chunks(chunks: string[]): Promise<void> {
  if (chunks.length === 0) return

  const parts = chunks.map(base64ToBytes)
  const total = parts.reduce((sum, part) => sum + part.length, 0)
  const merged = new Uint8Array(total)
  let offset = 0
  for (const part of parts) {
    merged.set(part, offset)
    offset += part.length
  }

  const blob = new Blob([merged], { type: 'audio/ogg' })
  const ctx = new AudioContext()
  try {
    const arrayBuffer = await blob.arrayBuffer()
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer)
    const source = ctx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(ctx.destination)
    source.start(0)
    await new Promise<void>((resolve) => {
      source.onended = () => resolve()
    })
  } finally {
    void ctx.close()
  }
}
