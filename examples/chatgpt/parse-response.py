#!/usr/bin/env python
import re
import sys


def parse_response(bot_name, response):
    """
    Removes input prompt from completion response

    :param bot_name: The name of the bot in current conversation
    :param response: Raw response from the completion output
    """
    r = re.compile(f"{bot_name}:")
    sections = re.split(r, response)
    return sections[-1].lstrip()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise Exception('missing arguments')

    response = parse_response(sys.argv[1], sys.argv[2])
    print(response)
