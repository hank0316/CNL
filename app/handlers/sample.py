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

    with open('/home/team7/users.json', 'r') as userfp:
        users = json.load(userfp)
        users = defaultdict(dict, users)

    message['From'] = removeBracket(message['From'])
    message['To'] = removeBracket(message['To'])
    userTo, userFrom = email2id(message['To']), email2id(message['From'])

    if len(message['subject']) >= 11 and message['subject'][:11] == 'ADD TO LIST':
        with open('/home/team7/lists.json', 'w') as listfp:
            # find list key
            key_start = message['subject'].find('"') + 1
            key_end = message['subject'].find('"', key_start)
            if key_end == -1:
                return START
            key = message['subject'][key_start: key_end]
            lists[userFrom][key].append(userTo)
            json.dump(lists, listfp, indent=4)
            return START
    elif message['subject'] == 'BAN':
        with open('/home/team7/lists.json', 'w') as listfp:
            lists[userFrom]['BLACKLIST'].append(userTo)
            json.dump(lists, listfp, indent=4)
            return START
    elif message['To'] == ADMIN and message['subject'] == 'REGISTER':
        with open('/home/team7/users.json', 'w') as userfp:
            if userFrom in users['register']:
                # already registered
                content = 'Already registered.'
            else:
                users['register'][userFrom] = message['From']
                content = 'Registeration success.'
                with open("/etc/postfix/virtual", "a") as postfixRegister:
                    print(f"{userFrom}@example.com {userFrom}", file=postfixRegister)
                os.system("postmap /etc/postfix/virtual")
            json.dump(users, userfp, indent=4)
            response = MailResponse(
                Body=content,
                To=message['From'],
                From=ADMIN,
                Subject="Admin's reply for registeration.",
                Html=f'<html><body style="color: red">{content}</body></html>'
            )
            relay = Relay()
            relay.deliver(response)

            return START

    prefix = ""
    for k in lists[userTo].keys():
        if userFrom in lists[userTo][k]:
            if k == "BLACKLIST":
                print("DISCARDED")
                return START
            prefix = f"[{k}] " + prefix
            # message['subject'] = f"[{k}] " + message['subject']

    print(type(message.body()))
    decoding = message.body().encode().decode('utf-8')
    print(message.body(), decoding)
    # label = classifier(message)
    # if label == 0:
    #     prefix = "[SPAM] " + prefix
    
    message['subject'] = prefix + message['subject']
    body = message.body().encode('uft-8').decode('unicode-escape')
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
