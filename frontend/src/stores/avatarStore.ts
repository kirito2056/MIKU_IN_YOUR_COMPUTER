import { create } from 'zustand'

export type LipSyncShape = {
  aa: number
  ih: number
  ou: number
  ee: number
  oh: number
}

export const NEUTRAL_LIPS: LipSyncShape = {
  aa: 0,
  ih: 0,
  ou: 0,
  ee: 0,
  oh: 0,
}

type AvatarState = {
  isSpeaking: boolean
  lipSync: LipSyncShape
  motionBoost: number
  setSpeaking: (speaking: boolean) => void
  setLipSync: (lipSync: LipSyncShape) => void
  resetLipSync: () => void
  triggerSpeakingMotion: () => void
}

export const useAvatarStore = create<AvatarState>((set) => ({
  isSpeaking: false,
  lipSync: NEUTRAL_LIPS,
  motionBoost: 0,
  setSpeaking: (isSpeaking) => set({ isSpeaking }),
  setLipSync: (lipSync) => set({ lipSync }),
  resetLipSync: () => set({ lipSync: NEUTRAL_LIPS }),
  triggerSpeakingMotion: () =>
    set((state) => ({ motionBoost: state.motionBoost + 1 })),
}))
