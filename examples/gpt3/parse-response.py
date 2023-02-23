#!/usr/bin/env python
import re
import sys


def parse_response(bot_name, response):
    """
    Removes input prompt from OpenAI response

    :param response: Raw response from the completion output
    """
    r = re.compile(f"{bot_name}:")
    sections = re.split(r, response)
    return sections[-1].lstrip()


if __name__ == '__main__':
    response = parse_response(sys.argv[1], sys.argv[2])
    print(response)
