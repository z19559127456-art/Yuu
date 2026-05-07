interface Window {
  electronAPI?: {
    checkForUpdate: () => void
    onUpdateStatus: (callback: (data: { status: string; version?: string; percent?: number; error?: string }) => void) => void
    getVersion: () => string
  }
}
