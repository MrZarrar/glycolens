# Registers "glycolens weekly": Sundays 20:00, runs late if the PC was off. Owner runs this once.
# Runs the venv's python (allowed by Smart App Control) rather than the unsigned glycolens.exe launcher.
$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "no venv at ${python}; create it first (see README)" }
$action = New-ScheduledTaskAction -Execute $python -Argument "-m glycolens.cli run" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 8pm
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "glycolens weekly" -Action $action -Trigger $trigger -Settings $settings
