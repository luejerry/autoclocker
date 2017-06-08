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
import requests
from lxml import html
import scheduleout

WORK_HOURS = timedelta(hours=8)
HOURS_RESOLUTION = timedelta(minutes=15)

CONF_PATH = 'config.ini'

def read_config():
    # TODO: get rid of globals
    global WORK_HOURS, HOURS_RESOLUTION
    config = configparser.ConfigParser()
    config.read(CONF_PATH)
    if 'work_hours' not in config['DEFAULT'] or 'hours_resolution' not in config['DEFAULT']:
        print('Configuration not found. Initializing defaults.')
        config['DEFAULT']['work_hours'] = str(WORK_HOURS.total_seconds() / 3600)
        config['DEFAULT']['hours_resolution'] = str(HOURS_RESOLUTION.total_seconds() / 60)
        with open(CONF_PATH, 'w') as conf_file:
            config.write(conf_file)
    else:
        WORK_HOURS = timedelta(hours=config.getfloat('DEFAULT', 'work_hours'))
        HOURS_RESOLUTION = timedelta(minutes=config.getfloat('DEFAULT', 'hours_resolution'))
    print("You are working {} hours today.".format(WORK_HOURS.total_seconds() / 3600))

def login_prompt():
    """Prompt user for login credentials.

    Returns: 2-tuple.
    * `user`: Username string.
    * `password`: Password string.
    """
    user = input("User: ")
    password = getpass.getpass()
    return (user, password)


def test_login(user, password):
    """Attempt login to ADP with user supplied credentials.

    Returns: Text content of server response. On successful login, should be main web application
    page.

    Side effects: Prints to standard output.
    """
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx?dojo.preventCache=1496267721438'
    form = {
        'target': url,
        'USER': user,
        'PASSWORD': password
    }
    print('Logging in to https://workforcenow.adp.com...', end=' ')
    response = requests.post('https://workforcenow.adp.com/siteminderagent/forms/login.fcc', form)
    print('Connected.')
    return response.text


def login_session(user, password):
    """Initiate an authenticated session with the supplied credentials. A failed login due to
    invalid credentials will not fail at this stage and must be checked by examining the contents
    of the returned session and response objects.

    Returns: 2-tuple.
    * `session`: `requests.Session` object. On successful login, should contain the necessary
      authentication cookies.
    * `response`: `requests.Response` object of server response. On successful login, should
      be the main web application page.

    Side effects: None.
    """
    session = requests.Session()
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx?dojo.preventCache=1496267721438'
    form = {
        'target': url,
        'USER': user,
        'PASSWORD': password
    }
    response = session.post('https://workforcenow.adp.com/siteminderagent/forms/login.fcc', form)
    return (session, response)


def refresh_session(session):
    """GETs the web application page in the context of an authenticated session.

    Parameters:
    * `session`: An authenticated `requests.Session` object.

    Returns: `requests.Response` object of the server response.

    Side effects: None.
    """
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/WFN/Portlet/MyTime.aspx?dojo.preventCache=1496267721438'
    response = session.get(url)
    return response


def parse_ids(response_text):
    """Scrapes customer (employer) and employee IDs from the web application page. These are used
    to send clock-in/out requests.

    Parameters:
    * `response_text`: Text content of web application page.

    Returns: 2-tuple.
    * `cust_id`: customer ID string.
    * `emp_id`: employee ID string.

    Side effects: None.
    """
    cust_id = re.search(r"var _custID = '(\w*)'", response_text).group(1)
    emp_id = re.search(r"var _employeeId = '(\w*)'", response_text).group(1)
    return (cust_id, emp_id)


def clock_inout(session, cust_id, emp_id, is_in):
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
    url = 'https://workforcenow.adp.com/ezLaborManagerNet/UI4/Common/TLMRevitServices.asmx/ProcessClockFunctionAndReturnMsg'
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


def clock_in(session, cust_id, emp_id):
    """Clocks user in. Requires an authenticated session. The customer and employee IDs must
    be scraped from the authenticated web application.

    Parameters:
    * `session`: An authenticated `request.Session` object.
    * `cust_id`: ID of ADP customer (employer).
    * `emp_id`: ID of employee.

    Returns: None.

    Side effects: Prints to standard output.
    """
    clock_inout(session, cust_id, emp_id, True)
    return


def clock_out(session, cust_id, emp_id):
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


def parse_response(response_text):
    """Parse the clock in/clock out data from ADP page and calculate remaining hours and time to
    clock out.

    Parameters:
    * `response_text`: text of ADP page.

    Returns: 2-tuple.
    * `parsed_in`: List of clock-in `datetime` objects.
    * `parsed_out`: List of clock-out `datetime` objects.

    Side effects: Prints to standard output.
    """
    if not response_text:
        print('Error accessing data. Response was empty.')
        return

    # Scrape the page for timesheet information
    htmltree = html.fromstring(response_text)
    div_activities = htmltree.get_element_by_id('divActivities', None)
    if div_activities is None:
        print('Error accessing time information. Login may be incorrect.')
        return ([], [])
    activities_text = div_activities.getchildren()[0].text_content()
    times_in = re.findall(r'In(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (?:AM|PM))', activities_text)
    if not times_in:
        print('You have not clocked in today.')
        print('You have {} hours remaining.'.format(WORK_HOURS.total_seconds() / 3600))
        return ([], [])
    times_out = re.findall(r'Out(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (?:AM|PM))', activities_text)
    parsed_in = [datetime.strptime(strtime, '%m/%d/%Y %I:%M %p') for strtime in times_in]
    parsed_out = [datetime.strptime(strtime, '%m/%d/%Y %I:%M %p') for strtime in times_out]

    # Display timesheet information
    # print_clocktable(parsed_in, parsed_out)

    return (parsed_in, parsed_out)


def print_clocktable(parsed_in, parsed_out):
    """Display timesheet for the present day. Also calculates remaining hours and displays
    recommended clock out time.

    Parameters:
    * `parsed_in` : list of datetime objects corresponding to clock-in times.
    * `parsed_out`: list of datetime objects corresponding to clock-out times.

    Returns: Recommended clock out `datetime`.

    Side effects:
    * Prints to standard output.
    * Reads variables `WORK_HOURS` and `HOURS_RESOLUTION`.
    """
    # Utility to stringify a datetime as 'HH:mm AM/PM'
    tformatter = lambda t: t.strftime('%I:%M %p')
    # Utility to round a timedelta down to the nearest resolution
    floor_delta = lambda t: t // HOURS_RESOLUTION * HOURS_RESOLUTION
    # Utility to convert a timedelta to numeric hours
    hours_delta = lambda t: round(t.total_seconds() / 3600, 2)

    print('The current time is: {}'.format(tformatter(datetime.now())))
    format_str = '{:12} {:12} {:>6}'
    print('')
    print(format_str.format('Clocked in', 'Clocked out', 'Hours'))
    time_worked = timedelta()
    iter_in = iter(parsed_in)

    # Print the timesheet
    for time_out in parsed_out:
        # Assume that len(time_in) is always len(time_out) or len(time_out) + 1
        time_in = next(iter_in)
        time_worked += floor_delta(time_out - time_in)
        print(format_str.format(tformatter(time_in), tformatter(time_out),
                                round(time_worked.total_seconds() / 3600, 2)))
    time_remaining = WORK_HOURS - time_worked

    # If currently clocked in, calculate clock out time
    try:
        time_in = next(iter_in)
        # Next soonest clock-out time that will get counted
        time_next_out = floor_delta(datetime.now() - time_in + HOURS_RESOLUTION) + time_in
        time_next_worked = time_next_out - time_in

        # Time to clock-out that completes remaining hours for the day
        time_to_out = time_in + time_remaining
        time_remaining -= floor_delta(datetime.now() - time_in)

        print(format_str.format(tformatter(time_in),
                                '('+tformatter(time_next_out)+')',
                                '('+str(hours_delta(time_next_worked))+')'))
        print('')
        print('You should clock out at {}.'.format(tformatter(time_to_out)))
        return time_to_out
    # If not currently clocked in, done
    except StopIteration:
        print('')
        return None
    finally:
        print('You have {} hours remaining.'.format(hours_delta(time_remaining)))


def main_silent_clockin(username, password):
    """Noninteractive entry point. Clocks in the user with the supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    clock_in(session, cust_id, emp_id)
    response = refresh_session(session)
    (times_in, times_out) = parse_response(response.text)
    print_clocktable(times_in, times_out)
    input('Press enter to exit...')


def main_silent_clockout(username, password):
    """Noninteractive entry point. Clocks out the user with the supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    (cust_id, emp_id) = parse_ids(response.text)
    clock_out(session, cust_id, emp_id)
    response = refresh_session(session)
    (times_in, times_out) = parse_response(response.text)
    print_clocktable(times_in, times_out)
    input('Press enter to exit...')


def main_withlogin(username, password):
    """Entry point for interactive use with supplied credentials."""
    read_config()
    (session, response) = login_session(username, password)
    while True:
        response = refresh_session(session)
        (times_in, times_out) = parse_response(response.text)
        time_to_out = print_clocktable(times_in, times_out)
        print('')
        (cust_id, emp_id) = parse_ids(response.text)
        command = input('Type "in" to clock in, "out" to clock out, "auto" to auto-clockout, or anything else to exit: ')
        if command == 'in':
            if time_to_out:
                print('Cannot clock in: you are already clocked in.')
                return
            clock_in(session, cust_id, emp_id)
        elif command == 'out':
            if not time_to_out:
                print('Cannot clock out: you are not clocked in.')
                return
            clock_out(session, cust_id, emp_id)
        elif command == 'auto':
            if not time_to_out:
                print('Cannot auto-clockout: you have not clocked in.')
                return
            adj_time_out = time_to_out + timedelta(minutes=2) # Add a buffer to be safe
            scheduleout.schedule(adj_time_out.strftime('%H:%M'))
            print('Automatic clock-out scheduled for {0:%I:%M %p}.'.format(adj_time_out))
        else:
            return
    # input('Press enter to continue...')


def main():
    """Main entry point for interactive use. Prompts user for credentials."""
    read_config()
    (username, password) = login_prompt()
    main_withlogin(username, password)


if __name__ == '__main__':
    main()
