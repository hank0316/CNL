from salmon.routing import route, route_like
from salmon.mail import MailResponse
from salmon.server import Relay

from .filter import classifier

import json
from collections import defaultdict
from datetime import date
import os
from pathlib import Path


ADMIN = 'admin@cnlteam7.com'


def removeBracket(s):
    start_pos = s.find('<') + 1
    end_pos = s.find('>', start_pos)
    return s if start_pos == 0 else s[start_pos: end_pos]


def email2id(s):
    key_end = s.find('@')
    name = s[:key_end]
    return name


@route("(address)@(host)", address=".+")
def START(message, address=None, host=None):
    with open('/home/team7/lists.json', 'r') as listfp:
        lists = json.load(listfp)
        lists = defaultdict(lambda: defaultdict(list), lists)
        print(lists)

    with open('/home/team7/users.json', 'r') as userfp:
        users = json.load(userfp)
        users = defaultdict(dict, users)

    message['From'] = removeBracket(message['From'])
    message['To'] = removeBracket(message['To'])

    userTo, userFrom = email2id(message['To']), email2id(message['From'])
    if len(message['subject']) >= 11 and message['subject'][:11] == 'ADD TO LIST':
        print('ADD TO LIST')
        with open('/home/team7/lists.json', 'w') as listfp:
            # find list key
            key_start = message['subject'].find('"') + 1
            key_end = message['subject'].find('"', key_start)
            if key_end == -1:
                return START
            key = message['subject'][key_start: key_end]
            if key not in lists[userFrom].keys():
                lists[userFrom][key] = [userTo]
            else:
                lists[userFrom][key].append(userTo)
            json.dump(lists, listfp, indent=4)
            return START
    elif len(message['subject']) >= 16 and message['subject'][:16] == 'REMOVE FROM LIST':
        print('REMOVE FROM LIST')
        with open('/home/team7/lists.json', 'w') as listfp:
            # find list key
            key_start = message['subject'].find('"') + 1
            key_end = message['subject'].find('"', key_start)
            if key_end == -1:
                return START
            key = message['subject'][key_start: key_end]
            if key not in lists[userFrom].keys():
                return START
            else:
                if userTo in lists[userFrom][key]:
                    lists[userFrom][key].remove(userTo)
            json.dump(lists, listfp, indent=4)
            return START
    elif message['subject'] == 'BAN':
        print(f'BAN {userTo}')
        with open('/home/team7/lists.json', 'w') as listfp:
            if 'BLACKLIST' in lists[userFrom].keys():
                lists[userFrom]['BLACKLIST'].append(userTo)
            else:
                lists[userFrom]['BLACKLIST'] = [userTo]
            json.dump(lists, listfp, indent=4)
            return START
    elif message['subject'] == 'UNBAN':
        print(f'UNBAN {userTo}')
        with open('/home/team7/lists.json', 'w') as listfp:
            if 'BLACKLIST' not in lists[userFrom].keys() or userTo not in lists[userFrom]['BLACKLIST']:
                return START
            lists[userFrom]['BLACKLIST'].remove(userTo)
            json.dump(lists, listfp, indent=4)
            return START
    elif message['To'] == ADMIN and message['subject'] == 'REGISTER':
        with open('/home/team7/users.json', 'w') as userfp:
            if userFrom in users['register']:
                # already registered
                response = MailResponse(
                    Body='Already registered.',
                    To=message['From'],
                    From=ADMIN,
                    Subject="Admin's reply for registeration.",
                    Html=f'<html><body><div style="color: red">Already registered.</div></body></html>'
                )
            else:
                users['register'][userFrom] = message['From']
                content = 'Registeration success.'
                with open("/etc/postfix/virtual", "a") as postfixRegister:
                    print(f"{userFrom}@cnlteam7 {userFrom}",
                          file=postfixRegister)
                os.system("postmap /etc/postfix/virtual")
                response = MailResponse(
                    Body=content,
                    To=message['From'],
                    From=ADMIN,
                    Subject="Admin's reply for registeration.",
                    Html=f'<html><body><div style="color: green">Registeration success.</div><div>Your protected email is: {userFrom}@cnlteam7</div></body></html>'
                )
            json.dump(users, userfp, indent=4)
            relay = Relay()
            relay.deliver(response)
            return START

    if len(message['From']) >= 13 and message['From'][-13:] != '@cnlteam7':
        with open('/home/team7/users.json', 'w') as userfp:
            exist = False
            if message['From'].replace('@', '+') in users['register'].keys():
                exist = True
            users['register'][message['From'].replace(
                '@', '+')] = message['From']
            json.dump(users, userfp, indent=4)
        if not exist:
            with open("/etc/postfix/virtual", "a") as postfixRegister:
                print(f"{message['From'].replace('@', '+')}@cnlteam7 {message['From'].replace('@', '+')}",
                    file=postfixRegister)
            os.system("postmap /etc/postfix/virtual")
        message['From'] = message['From'].replace('@', '+') + '@cnlteam7'
        userFrom = email2id(message['From'])

    prefixs = []
    for k in lists[userTo].keys():
        print(f"prefixs: {k}")
        if userFrom in lists[userTo][k]:
            if k == "BLACKLIST":
                print("DISCARDED")
                return START
            prefixs.append(f"[{k}]")

    label = classifier(message)
    if label == 1:
        prefixs.insert(0, "[SPAM]")

    subject_prefix = '' if (len(prefixs) == 0) else ' '.join(prefixs) + ' '
    message['subject'] = subject_prefix + message['subject']
    body = message.body().encode().decode('unicode-escape')
    response = MailResponse(
        Body=body,
        To=users['register'][userTo],
        From=message['From'],
        Subject=message['subject'],
        Html=f'<html><body>{body}</body></html>'
    )
    relay = Relay()
    relay.deliver(response)

    # Save mail to MailBox
    today = date.today()
    d4 = today.strftime("%b-%d-%Y")

    for prefix in prefixs:
        print(f"prefixs: {prefix}")
        _path = Path(f"/home/team7/Maildir/{userTo}/{prefix[1:-1]}/")
        _path.mkdir(parents=True, exist_ok=True)
        _path = os.path.join(
            _path, f"{d4}-{message['subject'].replace(' ', '')}")
        with open(_path, 'w') as f:
            print(f"From: {message['From']}", file=f)
            print(f"To: {users['register'][userTo]}", file=f)
            print(f"Subject: {message['subject']}", file=f)
            print("-------------------------\n", file=f)
            print(message.body().encode().decode('utf-8', "ignore"), file=f)

    return START


@route_like(START)
def NEW_USER(message, address=None, host=None):
    with open("/home/team7/test_project/NEWUSER.log", 'w') as f:
        print(message, file=f)
    return NEW_USER


@route_like(START)
def END(message, address=None, host=None):
    return START