"""Scriptable entry point for running the autoclocker program. On first run, user is prompted for
credentials to be saved. Subsequent executions will login automatically. Note that credentials
will be stored in plaintext in the configuration file. If this is not desired, use `timecalc.py`
instead.

Usage:

`python autotimecalc.py [in|out]`

If run with no arguments, the program runs in interactive mode.

Arguments:
* `in`: clock user in noninteractively.
* `out`: clock user out noninteractively.
"""
import sys
import configparser
import timecalc

CONF_PATH = 'config.ini'

def read_config():
    """Retrieve credentials from configuration file. If no configuration file is present, creates
    one and saves user-supplied credentials to it.

    Returns: 2-tuple.
    * `user`: Username.
    * `key`: Password.

    Side effects:
    * Reads global variable `CONF_PATH`.
    * Reads and writes configuration file.
    * Prints to standard output.
    * Reads from standard input.
    """
    config = configparser.ConfigParser()
    conf_list = config.read(CONF_PATH)
    if not conf_list:
        print(CONF_PATH + ' not found. Initializing new configuration.')
        print('Your username and password will be saved. Exit and run timecalc.py instead if you do not want this.')
        (user, key) = timecalc.login_prompt()
        config['DEFAULT'] = {
            'user': user,
            'key': key
        }
        with open(CONF_PATH, 'w') as conf_file:
            config.write(conf_file)
        return (user, key)
    else:
        user = config['DEFAULT']['user']
        key = config['DEFAULT']['key']
        return (user, key)


def main():
    """Main entry point."""
    (user, key) = read_config()
    if len(sys.argv) < 2:
        timecalc.main_withlogin(user, key)
    elif sys.argv[1] == 'in':
        # print("IN RECEIVED")
        timecalc.main_silent_clockin(user, key)
    elif sys.argv[1] == 'out':
        # print("OUT received")
        timecalc.main_silent_clockout(user, key)

if __name__ == '__main__':
    main()
