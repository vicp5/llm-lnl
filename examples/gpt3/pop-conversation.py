#!/usr/bin/env python
import re
import sys


def pop_conversation(file_name):
    """
    Removes the middle section from a file based on separator <|im_end|>.

    :param file_name: The name of the file to remove the section from.
    """
    with open(file_name, 'r') as f:
        file_contents = f.read()

    # Split the file contents into sections.
    sections = re.split(r'<\|im_end\|>', file_contents)

    # Remove the middle section.
    sections.pop(len(sections)//2)

    # Join the sections back together.
    new_file_contents = '<|im_end|>'.join(sections)

    # Write the new file contents to a new file.
    with open(file_name, 'w') as f:
        f.write(new_file_contents)


if __name__ == '__main__':
    pop_conversation(sys.argv[1])
