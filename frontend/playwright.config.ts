import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

const ownPython = path.resolve('../backend/.venv/Scripts/python.exe')
const python = process.env.PYTHON_EXECUTABLE || (existsSync(ownPython) ? ownPython : path.resolve('../../backend/.venv/Scripts/python.exe'))
const token = 'synthetic-browser-test-token-at-least-32-characters'
export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 45000,
  use: {baseURL: 'http://127.0.0.1:5196', browserName: 'chromium', trace: 'retain-on-failure'},
  webServer: [
    {command: `"${python}" -m uvicorn server:create_app --factory --host 127.0.0.1 --port 8036 --no-access-log`, cwd: '../backend', url:'http://127.0.0.1:8036/health', reuseExistingServer: false,
      env: {LOCAL_ACCESS_TOKEN: token, LOCAL_DATA_DIR: `../.local/e2e-${randomUUID()}`, EXTRACTION_MODE: 'sample', DEMO_CLOCK: 'true'}},
    {command: 'npm run dev -- --port 5196 --strictPort', url:'http://127.0.0.1:5196', reuseExistingServer: false,
      env: {VITE_LOCAL_ACCESS_TOKEN: token, API_TARGET: 'http://127.0.0.1:8036'}},
  ],
})
