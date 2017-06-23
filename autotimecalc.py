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
from excepts import ParseFailure

CONF_PATH = 'config.ini'
LOG_PATH = 'errors.log'

def read_config() -> (str, str):
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
    config.read(CONF_PATH)
    if 'user' not in config['DEFAULT'] or 'key' not in config['DEFAULT']:
        print('Saved credentials not found.')
        print('Your username and password will be saved.',
              'Exit and run timecalc.py instead if you do not want this.')
        (user, key) = timecalc.login_prompt()
        config['DEFAULT']['user'] = user
        config['DEFAULT']['key'] = key
        with open(CONF_PATH, 'w') as conf_file:
            config.write(conf_file)
        return (user, key)
    else:
        user = config['DEFAULT']['user']
        key = config['DEFAULT']['key']
        return (user, key)


def main() -> None:
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
    try:
        main()
    except ParseFailure as ex:
        with open(LOG_PATH, 'a', encoding='utf-8') as log:
            log.write('{}\n{}\n'.format(str(ex), ex.log()))
        raise ex
    except Exception as ex:
        with open(LOG_PATH, 'a', encoding='utf-8') as log:
            log.write(str(ex) + '\n')
        raise ex
