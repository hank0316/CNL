from salmon.routing import route, route_like
from salmon.utils import settings
# from salmon.testing import RouterConversation, queue, relay
from salmon.mail import MailResponse
from salmon.server import Relay

from .filter import classifier

import json
import re
from collections import defaultdict
import os

ADMIN = 'admin@example.com'


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
    elif message['subject'] == 'BAN':
        with open('/home/team7/lists.json', 'w') as listfp:
            if 'BLACKLIST' in lists[userFrom].keys():
                lists[userFrom]['BLACKLIST'].append(userTo)
            else:
                lists[userFrom]['BLACKLIST'] = [userTo]
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
                    Html=f'<html><body style="color: red">Already registered.</body></html>'
                )
            else:
                users['register'][userFrom] = message['From']
                content     = 'Registeration success.'
                with open("/etc/postfix/virtual", "a") as postfixRegister:
                    print(f"{userFrom}@example.com {userFrom}",
                          file=postfixRegister)
                os.system("postmap /etc/postfix/virtual")
                response = MailResponse(
                    Body=content,
                    To=message['From'],
                    From=ADMIN,
                    Subject="Admin's reply for registeration.",
                    Html=f'<html><body><p style="color: green">Registeration success.</p><p>Your protected email is: {userFrom}@example.com</p></body></html>'
                )
            json.dump(users, userfp, indent=4)
            relay = Relay()
            relay.deliver(response)

            return START

    if message['From'][-12:] != '@example.com':
        with open('/home/team7/users.json', 'w') as userfp:
            users['register'][message['From'].replace('@', '+')] = message['From']
            json.dump(users, userfp, indent=4)
        with open("/etc/postfix/virtual", "a") as postfixRegister:
            print(f"{message['From'].replace('@', '+')}@example.com {message['From'].replace('@', '+')}",
                    file=postfixRegister)
        os.system("postmap /etc/postfix/virtual")
        message['From'] = message['From'].replace('@', '+') + '@example.com'

    prefix = ""
    for k in lists[userTo].keys():
        if userFrom in lists[userTo][k]:
            if k == "BLACKLIST":
                print("DISCARDED")
                return START
            prefix = f"[{k}] " + prefix

    # print(type(message.body()))
    # decoding = message.body().encode().decode('utf-8')
    # print(message.body(), decoding)
    label = classifier(message)
    if label == 1:
        prefix = "[SPAM] " + prefix
    print("LABELLLLLL:", label)

    message['subject'] = prefix + message['subject']
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

    with open(f"/home/team7/Maildir/{message['Message-Id']}", 'w') as f:
        msg = message.to_message()
        print(msg, file=f)

    return START


@route_like(START)
def NEW_USER(message, address=None, host=None):
    with open("/home/team7/test_project/NEWUSER.log", 'w') as f:
        print(message, file=f)
    return NEW_USER


@route_like(START)
def END(message, address=None, host=None):
    return START
