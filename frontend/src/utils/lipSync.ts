import type { LipSyncShape } from '../stores/avatarStore'

/** TTS 오디오 AnalyserNode → VRM 모음(aa/ih/ou/ee/oh) 가중치 */
export function computeLipSync(analyser: AnalyserNode): LipSyncShape {
  const timeData = new Uint8Array(analyser.fftSize)
  const freqData = new Uint8Array(analyser.frequencyBinCount)

  analyser.getByteTimeDomainData(timeData)
  let sumSq = 0
  for (let i = 0; i < timeData.length; i += 1) {
    const sample = (timeData[i] - 128) / 128
    sumSq += sample * sample
  }
  const rms = Math.sqrt(sumSq / timeData.length)
  const volume = Math.min(1, rms * 6)

  if (volume < 0.03) {
    return { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }
  }

  analyser.getByteFrequencyData(freqData)
  let weighted = 0
  let total = 0
  for (let i = 0; i < freqData.length; i += 1) {
    weighted += i * freqData[i]
    total += freqData[i]
  }
  const centroid = total > 0 ? weighted / total / freqData.length : 0.35

  const shape: LipSyncShape = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }

  if (centroid < 0.28) {
    shape.oh = volume * 0.85
    shape.ou = volume * 0.45
  } else if (centroid < 0.48) {
    shape.aa = volume
  } else if (centroid < 0.62) {
    shape.ee = volume * 0.75
    shape.ih = volume * 0.35
  } else {
    shape.ih = volume * 0.9
    shape.ee = volume * 0.4
  }

  return shape
}
