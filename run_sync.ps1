# run_sync.ps1
# Wrapper que executa o script de sincronização Python e registra logs com timestamp.
# Usado como ação do Agendador de Tarefas do Windows.

$ErrorActionPreference = "Continue"

$pastaLogs = "C:\api_rcs\logs"
if (-not (Test-Path $pastaLogs)) {
    New-Item -ItemType Directory -Path $pastaLogs | Out-Null
}

$logFile = Join-Path $pastaLogs "sync_$(Get-Date -Format 'yyyyMMdd').log"
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

"[$timestamp] ===== Iniciando sincronização =====" | Out-File -Append -FilePath $logFile -Encoding utf8

& "C:\api_rcs\venv\Scripts\python.exe" "C:\api_rcs\script_sincroniza_supabase.py" *>> $logFile
$exitCode = $LASTEXITCODE

$timestampFim = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"[$timestampFim] ===== Sincronização finalizada (exit code $exitCode) =====" | Out-File -Append -FilePath $logFile -Encoding utf8

exit $exitCode
