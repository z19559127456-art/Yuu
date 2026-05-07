const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { autoUpdater } = require('electron-updater')
const { execFile } = require('child_process')
const path = require('path')
const http = require('http')

autoUpdater.autoDownload = true
autoUpdater.autoInstallOnAppQuit = true
let updateDownloading = false

let mainWindow = null
let backendProcess = null

// ── 清理旧进程 ────────────────────────────────────────
function cleanupOldBackend() {
  const { execSync } = require('child_process')
  try {
    // 杀掉所有旧版后端进程
    execSync('taskkill /F /IM vx-agent-backend.exe 2>nul & taskkill /F /IM yu-backend.exe 2>nul & exit 0', { timeout: 3000, windowsHide: true })
  } catch (_) { /* 忽略 */ }
  // 删除旧版 exe
  try {
    const oldPath = path.join(process.resourcesPath, 'backend', 'vx-agent-backend.exe')
    require('fs').unlinkSync(oldPath)
  } catch (_) { /* 不存在就算了 */ }
}

// ── 启动后端 ──────────────────────────────────────────
function spawnBackend() {
  cleanupOldBackend()
  const backendPath = path.join(process.resourcesPath, 'backend', 'yu-backend.exe')
  console.log('[backend] 启动:', backendPath)

  backendProcess = execFile(backendPath, [], {
    cwd: path.dirname(backendPath),
    windowsHide: true
  })

  backendProcess.stdout?.on('data', (d) => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr?.on('data', (d) => console.error('[backend]', d.toString().trim()))
  backendProcess.on('error', (err) => console.error('[backend] 启动失败:', err.message))
  backendProcess.on('close', (code) => console.log('[backend] 已退出, code:', code))
}

function waitForBackend(maxRetries = 20) {
  return new Promise((resolve) => {
    let tries = 0
    function check() {
      const req = http.get('http://localhost:7890/health', (res) => {
        if (res.statusCode === 200) {
          console.log('[backend] 就绪')
          resolve(true)
        } else {
          retry()
        }
      })
      req.on('error', () => retry())
      req.setTimeout(1000, () => { req.destroy(); retry() })
    }
    function retry() {
      tries++
      if (tries >= maxRetries) {
        console.log('[backend] 超时，继续加载界面')
        resolve(false)
      } else {
        setTimeout(check, 500)
      }
    }
    check()
  })
}

// ── 窗口 ──────────────────────────────────────────────
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
}

// ── 更新 ──────────────────────────────────────────────
function checkForUpdates() {
  if (process.env.NODE_ENV === 'development') {
    console.log('[updater] 开发模式，跳过更新检查')
    return
  }
  mainWindow?.webContents.send('update-status', { status: 'checking' })
  autoUpdater.checkForUpdates().catch((err) => {
    console.log('[updater] 检查更新失败:', err.message)
    mainWindow?.webContents.send('update-status', { status: 'error', error: err.message })
  })
}

// IPC: 渲染进程主动请求检查更新
ipcMain.on('check-for-update', () => {
  checkForUpdates()
})

autoUpdater.on('checking-for-update', () => {
  mainWindow?.webContents.send('update-status', { status: 'checking' })
})

autoUpdater.on('update-available', (info) => {
  updateDownloading = true
  mainWindow?.webContents.send('update-status', {
    status: 'downloading',
    version: info.version
  })
})

autoUpdater.on('download-progress', (progress) => {
  mainWindow?.webContents.send('update-status', {
    status: 'downloading',
    percent: progress.percent,
    speed: progress.bytesPerSecond
  })
})

autoUpdater.on('update-downloaded', (info) => {
  updateDownloading = false
  mainWindow?.webContents.send('update-status', {
    status: 'ready',
    version: info.version
  })
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: '发现新版本',
    message: `新版本 ${info.version} 已下载完成，是否立即重启安装？`,
    buttons: ['立即重启', '稍后']
  }).then(({ response }) => {
    if (response === 0) autoUpdater.quitAndInstall()
  })
})

autoUpdater.on('update-not-available', () => {
  mainWindow?.webContents.send('update-status', { status: 'up-to-date' })
})

autoUpdater.on('error', (err) => {
  updateDownloading = false
  console.log('[updater] 错误:', err.message)
  mainWindow?.webContents.send('update-status', { status: 'error', error: err.message })
})

// ── 生命周期 ──────────────────────────────────────────
app.whenReady().then(async () => {
  if (process.env.NODE_ENV !== 'development') {
    spawnBackend()
    await waitForBackend()
  }
  createWindow()
  checkForUpdates()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill()
  }
})
