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


def email2id(s, users):
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

    if len(message['subject']) >= 11 and message['subject'][:11] == 'ADD TO LIST':
        with open('/home/team7/lists.json', 'w') as listfp:
            # get user
            user_end = message['From'].find('@')
            user = message['From'][: user_end]
            # find list key
            key_start = message['subject'].find('"') + 1
            key_end = message['subject'].find('"', key_start)
            if key_end == -1:
                return START
            key = message['subject'][key_start: key_end]
            lists[user][key].append(email2id(message['To']))
            json.dump(lists, listfp, indent=4)
            return START
    elif message['subject'] == 'BAN':
        with open('/home/team7/lists.json', 'w') as listfp:
            # get user
            user_end = message['From'].find('@')
            user = message['From'][: user_end]
            lists[user]['BLACKLIST'].append(email2id(message['To']))
            json.dump(lists, listfp, indent=4)
            return START
    elif message['To'] == ADMIN and message['subject'] == 'REGISTER':
        with open('/home/team7/users.json', 'w') as userfp:
            key_end = message['From'].find('@')
            if key_end == -1:
                return START
            user = message['From'][: key_end]
            if user in users['register']:
                # already registered
                content = 'Already registered.'
            else:
                users['register'][user] = message['From']
                content = 'Registeration successful.'
                with open("/etc/postfix/virtual", "a") as postfixRegister:
                    print(f"{user}@example.com {user}", file=postfixRegister)
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

    key_end = message['To'].find('@')
    if key_end == -1:
        return START
    user = message['To'][: key_end]
    for k in lists[user].keys():
        if email2id(message['From'], users) in lists[user][k]:
            if k == "BLACKLIST":
                print("DISCARDED")
                return START
            message['subject'] = f"[{k}] " + message['subject']

    print(type(message.body()))
    decoding = message.body().encode().decode('utf-8')
    print(message.body(), decoding)
    # label = classifier(message)
    # if label == 0:
    # message['subject'] = "[SPAM] " + message['subject']
    response = MailResponse(
        Body=message.body(),
        To=users['register'][user],
        From=message['From'],
        Subject=message['subject'],
        Html=f'<html><meta charset="UTF-8">你好</html>'
    )
    print(response.base.content_encoding['Content-Type'])
    response.base.content_encoding['Content-Type'] = (
        'html', {"charset": "utf-8"})
    print(response.base.content_encoding['Content-Type'])
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
