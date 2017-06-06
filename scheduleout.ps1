# Adds a Task Scheduler task to clock-out at the time specified by an argument.
param([string]$outtime='17:00')
$taskname = 'ClockOut'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c python.exe autotimecalc.py out' -WorkingDirectory $PWD
$trigger = New-ScheduledTaskTrigger -Once -At $outtime
Unregister-ScheduledTask -TaskName $taskname -Confirm:$false
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $taskname -Description 'Clock out of ADP'
