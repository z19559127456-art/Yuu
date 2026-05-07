const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // 更新相关
  checkForUpdate: () => ipcRenderer.send('check-for-update'),
  onUpdateStatus: (callback) => {
    ipcRenderer.on('update-status', (_event, data) => callback(data))
  },
  getVersion: () => '0.1.7'
})
