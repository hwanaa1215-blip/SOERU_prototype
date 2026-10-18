param([int]$WebPort=5195,[int]$ApiPort=8035,[switch]$LiveExtraction,[switch]$NoOpen)
$ErrorActionPreference='Stop'
$projectPath=$PSScriptRoot
$backendPath=Join-Path $projectPath 'backend'
$frontendPath=Join-Path $projectPath 'frontend'
$pythonPath=Join-Path $backendPath '.venv/Scripts/python.exe'
# Convenience on this workstation only. Sources never import the parent project.
if(-not(Test-Path -LiteralPath $pythonPath)){$pythonPath=Join-Path (Split-Path -Parent $projectPath) 'backend/.venv/Scripts/python.exe'}
if(-not(Test-Path -LiteralPath $pythonPath)){throw 'Create backend/.venv and install backend/requirements.txt first. See README.md.'}
if(-not(Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules/vite/bin/vite.js'))){throw 'Run npm ci in frontend first.'}
$runtimePath=Join-Path $projectPath '.local'
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
if($LiveExtraction -and -not $env:GEMINI_API_KEY){
    $keyPath=Join-Path $runtimePath 'gemini-key.txt'
    if(Test-Path -LiteralPath $keyPath){$env:GEMINI_API_KEY=[System.IO.File]::ReadAllText($keyPath).Trim()}
    if(-not $env:GEMINI_API_KEY -and $env:GOOGLE_API_KEY){$env:GEMINI_API_KEY=$env:GOOGLE_API_KEY}
    if(-not $env:GEMINI_API_KEY){throw 'Paste only your Gemini API key into .local/gemini-key.txt, save, then restart with -LiveExtraction. Do not send the key in chat. Calls can incur charges.'}
}
$tokenPath=Join-Path $runtimePath 'access-token.txt'
if(-not(Test-Path -LiteralPath $tokenPath)){
    [System.IO.File]::WriteAllText($tokenPath,([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')))
}
$env:LOCAL_ACCESS_TOKEN=[System.IO.File]::ReadAllText($tokenPath).Trim()
$env:VITE_LOCAL_ACCESS_TOKEN=$env:LOCAL_ACCESS_TOKEN
$env:LOCAL_DATA_DIR=Join-Path $projectPath 'data'
$env:EXTRACTION_MODE=if($LiveExtraction){'gemini'}else{'sample'}
$env:DEMO_CLOCK='true'
$env:API_TARGET="http://127.0.0.1:$ApiPort"
$nodePath=(Get-Command node -ErrorAction Stop).Source
$apiProcess=$null;$webProcess=$null
try {
    $apiProcess=Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','server:create_app','--factory','--host','127.0.0.1','--port',"$ApiPort",'--no-access-log' -WorkingDirectory $backendPath -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'api.log') -RedirectStandardError (Join-Path $runtimePath 'api-error.log')
    $webProcess=Start-Process -FilePath $nodePath -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',"$WebPort",'--strictPort' -WorkingDirectory $frontendPath -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'web.log') -RedirectStandardError (Join-Path $runtimePath 'web-error.log')
    $ready=$false
    for($attempt=0;$attempt -lt 40;$attempt++){
        if($apiProcess.HasExited -or $webProcess.HasExited){throw 'A process stopped. Check dose-timer/.local logs for port or dependency errors.'}
        try{
            $apiResponse=Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$ApiPort/health" -TimeoutSec 1
            $webResponse=Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$WebPort/" -TimeoutSec 1
            if($apiResponse.StatusCode -eq 200 -and $webResponse.StatusCode -eq 200){$ready=$true;break}
        }catch{Start-Sleep -Milliseconds 500}
    }
    if(-not $ready){throw 'Local startup timed out. Check .local logs.'}
    Write-Host "Dose Timer: http://127.0.0.1:$WebPort/"
    Write-Host "Reading mode: $env:EXTRACTION_MODE. Synthetic data only. Keep this terminal open; press Enter to stop."
    if(-not $NoOpen){Start-Process "http://127.0.0.1:$WebPort/"}
    [void](Read-Host)
}finally{
    if($null -ne $webProcess -and -not $webProcess.HasExited){Stop-Process -Id $webProcess.Id}
    if($null -ne $apiProcess -and -not $apiProcess.HasExited){Stop-Process -Id $apiProcess.Id}
}
