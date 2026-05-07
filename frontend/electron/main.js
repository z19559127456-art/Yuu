const { app, BrowserWindow, dialog } = require('electron')
const { autoUpdater } = require('electron-updater')
const { execFile } = require('child_process')
const path = require('path')
const http = require('http')

autoUpdater.autoDownload = true
autoUpdater.autoInstallOnAppQuit = true

let mainWindow = null
let backendProcess = null

// ── 启动后端 ──────────────────────────────────────────
function spawnBackend() {
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
  if (process.env.NODE_ENV === 'development') return
  autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    console.log('[updater] 检查更新失败:', err.message)
  })
}

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
    if (response === 0) autoUpdater.quitAndInstall()
  })
})

autoUpdater.on('error', (err) => console.log('[updater] 错误:', err.message))

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
