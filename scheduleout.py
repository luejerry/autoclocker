import subprocess
import os

def schedule(time):
    if os.name == 'nt':
        print('Windows platform detected. Creating Task Scheduler task...')
        subprocess.call(['powershell.exe', './scheduleout.ps1', time])
    else:
        print('TODO: handle Unix')