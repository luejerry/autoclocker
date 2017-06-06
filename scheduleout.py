"""Module that schedules a clock-out job using the platform-native job scheduler (Task Scheduler
on Windows, `at` on Mac/Linux).
"""
import subprocess
import os

def schedule(time):
    """Schedule a clock-out job at the specified time today. Clock-out will be executed at the
    scheduled machine-local time.

    Parameters:
    * `time`: time string in HH:mm format.

    Returns: None.

    Side effects:
    * Spawns subprocess.
    * Adds job to OS job scheduler.
    * Prints to standard output.
    """
    if os.name == 'nt': # Use external PS script to add Task Scheduler task
        print('Windows platform detected. Creating Task Scheduler task...')
        subprocess.run(['powershell.exe', './scheduleout.ps1', time])
    elif os.name == 'posix': # Invoke `at` directly
        print('POSIX platform detected. Scheduling atjob...')
        cmd = 'python3 autotimecalc.py out'
        attime = time + ' today'
        subprocess.run(['at', attime], input=cmd, encoding='utf-8')
