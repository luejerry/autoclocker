# ADP Autoclocker

Having to manually clock in exactly 8 hours a day for work is tedious and
error-prone, especially if workplace policy requires clocking out for lunch
break. This tool automates the process of clocking your exact desired number
of hours in [ADP](http://workforcenow.adp.com) each day. No longer must you
(or your manager) suffer the anxiety of logging accidental overtime.

## Features

* Calculates exact clock-out time to log exactly 8 hours across all shifts.
* Accounts for pay hours being counted in 15 minute increments.
* Hours per day and minimum paid increment are configurable via config file.
* Schedule an automatic clock out at the completion of daily hours or the next
paid increment, using the platform native job scheduler (Task Scheduler on
Windows, `at` on Linux/MacOS).

## Requirements
* Python 3
    * `requests`
    * `lxml`
* Powershell with unsigned script execution enabled (on Windows)

## Setup and run in interactive mode
1. Install `requests` and `lxml`.

`pip install requests lxml`

2. Run `timecalc.sh` (Linux/Mac) or `timecalc.bat` (Windows).

3. If prompted, enter your ADP credentials. Your username and password will
be stored in plain text in `config.ini` to allow automatic login. See below
if this is not desired.

## Other startup modes

### Interactive mode, without saving credentials

Run `python timecalc.py` from terminal, or run `timecalc.py` with the Python
launcher. This behaves as normal interactive mode, except login credentials
will not be saved.

### Noninteractive mode

Clocking in/out can be performed noninteractively via the command line.
Noninteractive functions are only available if credentials have been saved.

* Clock in: `python autotimecalc.py in`
* Clock out: `python autotimecalc.py out`

## Canceling automatic clockout

To cancel a scheduled automatic clockout:

* Windows: delete the `ClockOut` task from Task Scheduler.
* Linux/Mac: run `atq` to find the clock out job, then `atrm` to delete it.

## Todo
* Add error checking for failure adding job.
* Remove use of mutable global variables.
* ~~Add support for configuration file.~~
* ~~Add feature to auto-clockout after next time interval.~~
* ~~Document auxiliary scripts.~~
