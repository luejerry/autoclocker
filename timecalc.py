"""Utility to assist with calculating optimal clock-out times on the ADP web payroll platform.
Authenticates with the ADP web portal <https://workforcenow.adp.com> and scrapes timesheet
information for the current day. The user may then clock in or out without needing to use the
web application.

May be run in interactive mode by executing the script directly. Other semi-interactive and
noninteractive entry points are available for scripting use:

* `main_withlogin`: run interactively, but without prompting for credentials.
* `main_silent_clockin`: clock in silently.
* `main_silent_clockout`: clock out silently.

Two configurable constants are defined:
* `WORK_HOURS`: Desired hours of work per day. (Default: 8 hours)
* `HOURS_RESOLUTION`: Smallest increment of time that is counted for pay. (Default: 15 minutes)
"""

from datetime import datetime, timedelta
import configparser
import getpass
import re
from itertools import zip_longest
from typing import Optional, Sequence, Mapping, Dict, List, Tuple, Union
import requests
from lxml import html
import scheduleout
from excepts import ParseFailure, SessionExpired
import aws_adp_client.scheduler_client as aws_scheduler

CONF_PATH = 'config.ini'

# Default config values. These are overwritten by the config file if present
WORK_HOURS = timedelta(hours=8)
HOURS_RESOLUTION = timedelta(minutes=15)


def read_config() -> None:
    """Load settings from configuration file to global vars.

    Side effects:
    * Reads and writes to file system.
    * Writes to global vars.
    """
    # TODO: get rid of globals
    global WORK_HOURS, HOURS_RESOLUTION
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    if 'work_hours' not in config['DEFAULT'] or 'hours_resolution' not in config['DEFAULT']:
        print('Configuration not found. Initializing defaults.')
        config['DEFAULT']['work_hours'] = str(
            WORK_HOURS.total_seconds() / 3600)
        config['DEFAULT']['hours_resolution'] = str(
            HOURS_RESOLUTION.total_seconds() / 60)
        with open(CONF_PATH, 'w') as conf_file:
            config.write(conf_file)
    else:
        WORK_HOURS = timedelta(hours=config.getfloat('DEFAULT', 'work_hours'))
        HOURS_RESOLUTION = timedelta(
            minutes=config.getfloat('DEFAULT', 'hours_resolution'))
    print("You are working {} hours today.".format(
        WORK_HOURS.total_seconds() / 3600))


def login_prompt() -> Tuple[str, str]:
    """Prompt user for login credentials.

    Returns:
    * `user`: Username string.
    * `password`: Password string.
    """
    user = input("User: ")
    password = getpass.getpass()
    return (user, password)


def login_session(user: str, password: str) -> Tuple[requests.Session, requests.Response]:
    """Initiate an authenticated session with the supplied credentials. A failed login due to
    invalid credentials will not fail at this stage and must be checked by examining the contents
    of the returned session and response objects.

    Returns:
    * `session`: `requests.Session` object. On successful login, should contain the necessary
      authentication cookies.
    * `response`: `requests.Response` object of server response. On successful login, should
      be the main web application page.

    Side effects: None.
    """
    session = requests.Session()
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx'
    form = {
        'target': url,
        'USER': user,
        'PASSWORD': password
    }
    response = session.post(
        'https://workforcenow.adp.com/siteminderagent/forms/login.fcc', form)
    return (session, response)


def refresh_session(session: requests.Session) -> requests.Response:
    """GETs the web application page in the context of an authenticated session.

    Parameters:
    * `session`: An authenticated `requests.Session` object.

    Returns: `requests.Response` object of the server response.

    Side effects: None.
    """
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx'
    response = session.get(url)
    return response


def parse_ids(response_text: str) -> Tuple[str, str]:
    """Scrapes customer (employer) and employee IDs from the web application page. These are used
    to send clock-in/out requests.

    Parameters:
    * `response_text`: Text content of web application page.

    Returns:
    * `cust_id`: customer ID string.
    * `emp_id`: employee ID string.

    Side effects: None.
    """
    cust_id = re.search(r"var _custID = '(\w*)'", response_text).group(1)
    emp_id = re.search(r"var _employeeId = '(\w*)'", response_text).group(1)
    return (cust_id, emp_id)


def clock_inout(session: requests.Session, cust_id: str, emp_id: str, is_in: bool) -> None:
    """Clocks user in or out. Requires an authenticated session. The customer and employee IDs
    must be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.
    * `is_in`: `True` to clock in, `False` to clock out.

    Returns: None.

    Side effects: Prints to standard output.
    """
    url = (
        'https://workforcenow.adp.com/ezLaborManagerNet/UI4/Common/TLMRevitServices.asmx'
        '/ProcessClockFunctionAndReturnMsg')
    payload = {
        'iCustID': cust_id,
        'sEmployeeID': emp_id,
        'sEvent': 'IN' if is_in else 'OUT',
        'sCulture': 'en-US'
    }
    response = session.post(url, json=payload)
    if 'Operation Successful' in response.text:
        print('You have clocked {}.'.format('in' if is_in else 'out'))
    else:
        print('Error clocking {}.'.format('in' if is_in else 'out'))
    return


def clock_in(session: requests.Session, cust_id: str, emp_id: str) -> None:
    """Clocks user in. Requires an authenticated session. The customer and employee IDs must
    be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `requests.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.

    Returns: None.

    Side effects: Prints to standard output.
    """
    clock_inout(session, cust_id, emp_id, True)
    return


def clock_out(session: requests.Session, cust_id: str, emp_id: str) -> None:
    """Clocks user out. Requires an authenticated session. The customer and employee IDs must
    be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.

    Returns: None.

    Side effects: Prints to standard output.
    """
    clock_inout(session, cust_id, emp_id, False)
    return


def parse_response(response_text: str) -> Tuple[List[datetime], List[datetime], datetime]:
    """Parse the clock in/clock out data from ADP page and calculate remaining hours and time to
    clock out.

    Parameters:
    * `response_text`: text of ADP page.

    Returns:
    * `parsed_in`: List of clock-in `datetime` objects.
    * `parsed_out`: List of clock-out `datetime` objects.
    * `parsed_time`: Current `datetime` from server.

    Throws:
    * `SessionExpired` if response text indicates that server terminated the authenticated session.
    * `ParseFailure` if timesheet data could not be parsed from text.

    Side effects: Prints to standard output.
    """
    if not response_text:
        print('Error accessing data. Response was empty.')
        return

    # Scrape the page for timesheet information
    htmltree = html.fromstring(response_text)
    div_activities = htmltree.get_element_by_id('divActivities', None)
    if len(div_activities) == 0:
        div_login = htmltree.get_element_by_id('mainLoginWrapper', None)
        if div_login:
            print('Login session expired.')
            raise SessionExpired('Login session expired.')
        print('Error accessing time information. Login may be incorrect.')
        raise ParseFailure('Error accessing time information. Login may be incorrect.',
                           response_text)
    activities_text = div_activities.getchildren()[0].text_content()
    current_time = re.search(
        r"""var sDate = ['"]([^'"]+)['"];""", response_text)
    if current_time is None:
        print('Error getting server time. The server application may have changed.')
        raise ParseFailure(
            'Error getting server time. The server application may have changed.',
            response_text)
    parsed_time = datetime.strptime(
        current_time.group(1), '%B %d, %Y %H:%M:%S')
    print('Current server time:', parsed_time.strftime('%I:%M %p'))
    times_in = re.findall(
        r'In(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (?:AM|PM))', activities_text)
    if not times_in:
        print('You have not clocked in today.')
        return ([], [], parsed_time)
    times_out = re.findall(
        r'Out(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (?:AM|PM))', activities_text)
    parsed_in = [datetime.strptime(strtime, '%m/%d/%Y %I:%M %p')
                 for strtime in times_in]
    parsed_out = [datetime.strptime(strtime, '%m/%d/%Y %I:%M %p')
                  for strtime in times_out]
    return (parsed_in, parsed_out, parsed_time)


def round_datetime(time_date: datetime, time_resolution: timedelta) -> datetime:
    """Round a `datetime` to the nearest clock interval.

    Parameters:
    * `time_date`: `datetime` to round.
    * `time_resolution`: Clock interval to round to, e.g. 15 minutes.

    Returns: rounded `datetime`.
    """
    minute_res = time_resolution.total_seconds() / 60
    minute_rounded = round(time_date.minute / minute_res) * minute_res
    hour_adj = time_date.hour + minute_rounded // 60
    minute_adj = minute_rounded % 60
    datetime_adj = datetime(time_date.year, time_date.month, time_date.day,
                            hour=int(hour_adj), minute=int(minute_adj))
    return datetime_adj


def calculate_time_table(
        parsed_in: Sequence[datetime],
        parsed_out: Sequence[datetime],
        current_time: datetime
) -> Dict[str, List[Union[datetime, timedelta]]]:
    """Generate timesheet table data given list of clockin and clockout times.

    Parameters:
    * `parsed_in`: List of clock-in times.
    * `parsed_out`: List of clock-out times.
    * `current_time`: Current time, in same timezone as clock-in/out times.
    
    Returns: timesheet data in the following format

        ```python
        {
            'in': [clockin datetimes],
            'out': [clockout datetimes],
            'duration': [clockout - clockin times]
        }
        ```
    """
    rounded_in = [round_datetime(dt, HOURS_RESOLUTION) for dt in parsed_in]
    rounded_out = [round_datetime(dt, HOURS_RESOLUTION) for dt in parsed_out]

    def time_or_next(t): return t or round_datetime(
        current_time + HOURS_RESOLUTION, HOURS_RESOLUTION)

    times_table = [
        list(col) for col in zip(*[
            (time_in, time_or_next(time_out), time_or_next(time_out) - time_in)
            for (time_in, time_out) in zip_longest(rounded_in, rounded_out)
        ])
    ]
    table_headers = ['in', 'out', 'duration']
    times_dict = dict(zip(table_headers, times_table))
    return times_dict


def hours_delta(t: timedelta) -> float:
    """Converts a `timedelta` to decimal hours."""
    return round(t.total_seconds() / 3600, 2)


def tformatter(t: datetime) -> str:
    """Format a `datetime` as "08:05 PM"."""
    return t.strftime('%I:%M %p')


def display_clocktable(
        times_dict: Mapping[str, Sequence[Union[datetime, timedelta]]],
        current_time: datetime
) -> None:
    """Formats and prints timesheet data as a text table."""
    if not times_dict:
        return
    format_str = '{:12} {:12} {:>6}'
    print('')
    print(format_str.format('Clocked in', 'Clocked out', 'Hours'))

    for (time_in, time_out, duration) in zip(*times_dict.values()):
        future_fmtstr = '{}' if time_out < current_time else '({})'
        print(format_str.format(
            tformatter(time_in), future_fmtstr.format(tformatter(
                time_out)), future_fmtstr.format(hours_delta(duration))
        ))
    print(format_str.format('', '', hours_delta(
        sum(times_dict['duration'], timedelta()))))


def calculate_summary(
        times_dict: Mapping[str, Sequence[Union[datetime, timedelta]]],
        current_time: datetime
) -> Tuple[bool, timedelta, Optional[datetime]]:
    """Generates summary information from the supplied timesheet data.

    Parameters:
    * `times_dict`: timesheet data in the following format

        ```python
        {
            'in': [clockin datetimes],
            'out': [clockout datetimes],
            'duration': [clockout - clockin times]
        }
        ```

    * `current_time`: current time, in the same timezone as the timesheet data.

    Returns:
    * `is_in`: `True` if currently clocked in.
    * `time_remaining`: remaining time to work today, starting from the next clock interval.
    * `time_to_out`: time to clock out to complete remaining hours, or `None` if not currently
      clocked in.
    """
    if not times_dict:
        return (False, WORK_HOURS, None)
    time_remaining = WORK_HOURS - sum(times_dict['duration'], timedelta())
    is_in = times_dict['out'][-1] > current_time

    def lazy_time_to_out(): return times_dict['out'][-1] + time_remaining

    return (is_in, time_remaining, lazy_time_to_out() if is_in else None)


def display_summary(time_remaining: timedelta, time_to_out: datetime) -> None:
    """Formats and prints supplied timesheet summary information."""
    print(
        'You have {} hours remaining.'.format(hours_delta(time_remaining)),
        'You should clock out at {}.'.format(
            tformatter(time_to_out)) if time_to_out else ''
    )


def print_clocktable(
        times_in: List[datetime],
        times_out: List[datetime],
        current_time: datetime
) -> None:
    """Convenience method to display timesheet table and summary information."""
    times_dict = calculate_time_table(times_in, times_out, current_time)
    (_, time_remaining, time_to_out) = calculate_summary(times_dict, current_time)
    display_clocktable(times_dict, current_time)
    display_summary(time_remaining, time_to_out)


def main_silent_clockin(username: str, password: str) -> None:
    """Noninteractive entry point. Clocks in the user with the supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    clock_in(session, cust_id, emp_id)
    response = refresh_session(session)
    (times_in, times_out, server_time) = parse_response(response.text)
    print_clocktable(times_in, times_out, server_time)
    input('Press enter to exit...')


def main_silent_clockout(username: str, password: str) -> None:
    """Noninteractive entry point. Clocks out the user with the supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    clock_out(session, cust_id, emp_id)
    response = refresh_session(session)
    (times_in, times_out, server_time) = parse_response(response.text)
    print_clocktable(times_in, times_out, server_time)
    input('Press enter to exit...')


def main_withlogin(username: str, password: str) -> None:
    """Entry point for interactive use with supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    while True:
        response = refresh_session(session)
        try:
            (times_in, times_out, server_time) = parse_response(response.text)
        except SessionExpired:
            print('Session expired, reauthenticating...')
            (session, response) = login_session(username, password)
            (times_in, times_out, server_time) = parse_response(response.text)
        times_dict = calculate_time_table(times_in, times_out, server_time)
        display_clocktable(times_dict, server_time)
        print('')
        (is_in, time_remaining, time_to_out) = calculate_summary(
            times_dict, server_time)
        display_summary(time_remaining, time_to_out)
        time_next_out = times_dict['out'][-1] if times_dict else None
        (cust_id, emp_id) = parse_ids(response.text)
        command = input(
            'Type "in" to clock in, "out" to clock out, "auto" to auto-clockout,'
            ' "next" to auto-clockout at the next interval, "r" to refresh,'
            ' or anything else to exit: ')
        command_map = {
            'in': lambda: handle_in(session, cust_id, emp_id, is_in),
            'out': lambda: handle_out(session, cust_id, emp_id, is_in),
            'auto': lambda: handle_auto(time_to_out, server_time, username, is_in),
            'next': lambda: handle_auto(time_next_out, server_time, username, is_in),
        }
        if command == 'r':
            (session, response) = login_session(username, password)
            continue
        elif command not in command_map.keys():
            return
        command_map[command]()


def handle_in(session, cust_id, emp_id, is_in):
    if is_in:
        print('Cannot clock in: you are already clocked in.')
        return
    clock_in(session, cust_id, emp_id)


def handle_out(session, cust_id, emp_id, is_in):
    if not is_in:
        print('Cannot clock out: you are not clocked in.')
        return
    clock_out(session, cust_id, emp_id)


def handle_auto(time_to_out: datetime, current_time: datetime, user: str, is_in: bool):
    if not is_in:
        print('Cannot auto-clockout: you have not clocked in.')
        return
    exact_remaining = time_to_out - current_time
    scheduled_time = aws_scheduler.execute_saved_scheduler(
        user, exact_remaining)
    print('AWS auto-clockout scheduled for {}.'.format(
        tformatter(scheduled_time.astimezone(tz=None))))


def main() -> None:
    """Main entry point for interactive use. Prompts user for credentials."""
    read_config()
    (username, password) = login_prompt()
    main_withlogin(username, password)


if __name__ == '__main__':
    main()
