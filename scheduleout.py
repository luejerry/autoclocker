import subprocess
import os

def schedule(time):
    if os.name == 'nt':
        print('Windows platform detected. Creating Task Scheduler task...')
        subprocess.run(['powershell.exe', './scheduleout.ps1', time])
    elif os.name == 'posix':
        print('POSIX platform detected. Scheduling atjob...')
        cmd = 'python3 autotimecalc.py out'
        attime = time + ' today'
        subprocess.run(['at', attime], input=cmd, encoding='utf-8')