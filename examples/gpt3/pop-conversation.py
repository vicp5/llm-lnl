#!/usr/bin/env python
import re
import sys


def pop_conversation(file_name, separator, middle=False):
    """
    Removes a section from a file based on a separator.
    By default it removes the second section
    (first section after initial prompt).

    :param file_name: The name of the file to remove the section from.
    :param separator: The separator between sections.
    :param middle:    Flag to indicate if it should remove middle section.
    """
    with open(file_name, 'r') as f:
        file_contents = f.read()

    # Split the file contents into sections.
    re_separator = re.compile(separator)
    sections = re.split(re_separator, file_contents)

    if middle:
        # Remove the middle section.
        sections.pop(len(sections)//2)
    else:
        # Remove second section (first exchange).
        sections.pop(1)

    # Join the sections back together.
    new_file_contents = separator.join(sections)

    # Write the new file contents to a new file.
    with open(file_name, 'w') as f:
        f.write(new_file_contents)


if __name__ == '__main__':
    middle = False
    if len(sys.argv) < 2:
        raise Exception('missing arguments')
    elif len(sys.argv) == 3:
        if sys.argv == 'middle':
            middle = True

    pop_conversation(sys.argv[1], sys.argv[2], middle)
