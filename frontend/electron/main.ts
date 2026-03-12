import { app, BrowserWindow } from 'electron';
import * as path from 'path';

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function createWindow() {
  const { width, height } = require('electron').screen.getPrimaryDisplay().workAreaSize;

  const mainWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    transparent: true, // 투명 윈도우 설정
    frame: false,      // 창 테두리 없애기
    alwaysOnTop: true, // 항상 최상단
    skipTaskbar: true, // 작업 표시줄에서 숨기기
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  // 클릭 통과 설정 (배경을 클릭하면 뒤에 있는 창이 클릭됨)
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  // 렌더러 console.log → 터미널로 전달
  mainWindow.webContents.on('console-message', (_event, _level, message, _line, _sourceId) => {
    console.log('[Renderer]', message);
  });

  if (isDev) {
    // 개발 환경에서는 로컬 서버(Vite) URL 로드
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools();
  } else {
    // 프로덕션 빌드에서는 파일 로드
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
