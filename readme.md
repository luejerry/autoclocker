# ADP Autoclocker

Automatically clock out of ADP Workforce after a set number of hours has been
clocked for the day across all shifts. Uses platform native job scheduler to
execute the auto clock-out (Task Scheduler on Windows, `at` on Linux/MacOS).

# Requirements
* Python 3
    * `lxml` package
    * `requests` package
* Powershell (on Windows)

# Setup and run
1. Install `requests` and `lxml`.

`pip3 install requests lxml`

2. Run `timecalc.sh` (Linux/Mac) or `timecalc.bat`.

# Todo
* Add error checking for failure adding job.
* ~~Add support for configuration file.~~
* ~~Add feature to auto-clockout after next time interval.~~
* ~~Document auxiliary scripts.~~
