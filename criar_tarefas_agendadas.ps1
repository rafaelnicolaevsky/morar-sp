# Cria as 3 tarefas agendadas do pipeline Morar SP (turnos manha/tarde/noite).
# Rode este script num PowerShell aberto como Administrador
# (clique direito no PowerShell > "Executar como administrador").
#
# Usa logon S4U: roda mesmo com o Windows deslogado/bloqueado, sem precisar
# guardar sua senha.

$usuario = "$env:COMPUTERNAME\$env:USERNAME"
$python = 'C:\Users\nikol\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$pasta = 'C:\Users\nikol\projetos\morar-sp'

Write-Output "Usuario: $usuario"

# Turno manha: 08:00 + ate 2h25 de atraso aleatorio (janela 08:00-10:25)
$action_manha = New-ScheduledTaskAction -Execute $python -Argument 'scripts\agendador.py manha' -WorkingDirectory $pasta
$trigger_manha = New-ScheduledTaskTrigger -Daily -At 08:00
$trigger_manha.RandomDelay = 'PT2H25M'
$principal_manha = New-ScheduledTaskPrincipal -UserId $usuario -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName 'MorarSP_Turno_Manha' -Action $action_manha -Trigger $trigger_manha -Principal $principal_manha -Description 'Pipeline Morar SP - turno manha (08:00-10:25)' -Force | Out-Null
Write-Output "Tarefa manha criada"

# Turno tarde: 13:45 + ate 2h25 (janela 13:45-16:10)
$action_tarde = New-ScheduledTaskAction -Execute $python -Argument 'scripts\agendador.py tarde' -WorkingDirectory $pasta
$trigger_tarde = New-ScheduledTaskTrigger -Daily -At 13:45
$trigger_tarde.RandomDelay = 'PT2H25M'
$principal_tarde = New-ScheduledTaskPrincipal -UserId $usuario -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName 'MorarSP_Turno_Tarde' -Action $action_tarde -Trigger $trigger_tarde -Principal $principal_tarde -Description 'Pipeline Morar SP - turno tarde (13:45-16:10)' -Force | Out-Null
Write-Output "Tarefa tarde criada"

# Turno noite: 19:15 + ate 2h10 (janela 19:15-21:25)
$action_noite = New-ScheduledTaskAction -Execute $python -Argument 'scripts\agendador.py noite' -WorkingDirectory $pasta
$trigger_noite = New-ScheduledTaskTrigger -Daily -At 19:15
$trigger_noite.RandomDelay = 'PT2H10M'
$principal_noite = New-ScheduledTaskPrincipal -UserId $usuario -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName 'MorarSP_Turno_Noite' -Action $action_noite -Trigger $trigger_noite -Principal $principal_noite -Description 'Pipeline Morar SP - turno noite (19:15-21:25)' -Force | Out-Null
Write-Output "Tarefa noite criada"

Write-Output "`nPronto! Conferindo as 3 tarefas:"
Get-ScheduledTask -TaskName 'MorarSP_Turno_*' | Select-Object TaskName, State
