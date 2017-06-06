import sys
import configparser
import getpass
import timecalc

CONF_PATH = 'config.ini'

def read_config():
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