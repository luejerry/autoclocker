# ADP Autoclocker

Automatically clock out of ADP Workforce after a set number of hours has been
clocked for the day across all shifts. Uses platform native job scheduler to
execute the auto clock-out (Task Scheduler on Windows, `at` on POSIX).

# Requirements
* Python 3
    * `lxml` package
    * `requests` package

