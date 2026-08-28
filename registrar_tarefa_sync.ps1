# registrar_tarefa_sync.ps1
# Cria a tarefa agendada que roda a sincronização periodicamente,
# com reinício automático em caso de falha.
#
# Rode este script UMA VEZ como Administrador para registrar a tarefa.

$nomeTarefa = "Sync_Supabase_TFSEVEN"
$scriptWrapper = "C:\api_rcs\run_sync.ps1"

# --- Ação: o que a tarefa executa ---
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$scriptWrapper`""

# --- Gatilho: roda a cada 4 horas, indefinidamente ---
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 4) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# --- Configurações: reinício automático se falhar, sem depender de login ---
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

# --- Executa como SYSTEM: roda mesmo sem ninguém logado no servidor ---
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" `
    -LogonType ServiceAccount -RunLevel Highest

# Remove versão anterior da tarefa, se existir (permite rodar este script de novo para atualizar)
Unregister-ScheduledTask -TaskName $nomeTarefa -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $nomeTarefa `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Sincroniza dados de vendas do SQL Server local para o Supabase (cliente TFSEVEN)."

Write-Host "Tarefa '$nomeTarefa' registrada com sucesso."
Write-Host "Rodando a cada 4 horas, com ate 3 tentativas automaticas em caso de falha."
