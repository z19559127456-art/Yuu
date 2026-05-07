const { app, BrowserWindow, dialog } = require('electron')
const { autoUpdater } = require('electron-updater')
const path = require('path')

// 自动更新配置
autoUpdater.autoDownload = true
autoUpdater.autoInstallOnAppQuit = true

let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 启动后端（生产模式）
  if (process.env.NODE_ENV !== 'development') {
    spawnBackend()
  }
}

// 启动 Python 后端（已用 PyInstaller 编译为 exe）
function spawnBackend() {
  const { execFile } = require('child_process')
  const backendPath = path.join(process.resourcesPath, 'backend', 'yu-backend.exe')

  const child = execFile(backendPath, [], { cwd: path.dirname(backendPath) })
  child.stdout?.on('data', (d) => console.log('[backend]', d.toString()))
  child.stderr?.on('data', (d) => console.error('[backend]', d.toString()))
  child.on('error', (err) => console.error('[backend] 启动失败:', err.message))
}

// 检查更新
function checkForUpdates() {
  if (process.env.NODE_ENV === 'development') return

  autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    console.log('[updater] 检查更新失败:', err.message)
  })
}

// 更新事件
autoUpdater.on('update-available', () => {
  mainWindow?.webContents.send('update-status', { status: 'downloading' })
})

autoUpdater.on('update-downloaded', () => {
  mainWindow?.webContents.send('update-status', { status: 'ready' })
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: '发现新版本',
    message: '新版本已下载完成，是否立即重启安装？',
    buttons: ['立即重启', '稍后']
  }).then(({ response }) => {
    if (response === 0) {
      autoUpdater.quitAndInstall()
    }
  })
})

autoUpdater.on('error', (err) => {
  console.log('[updater] 错误:', err.message)
})

app.whenReady().then(() => {
  createWindow()
  checkForUpdates()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
