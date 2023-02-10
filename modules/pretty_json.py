#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

from collections.abc import Mapping, Sequence, Set


def isunwrappable(value):
    if isinstance(value, str):
        return False

    return isinstance(value, (Mapping, Sequence, Set))


def pretty_lines(data, sort_keys=False, sort_sets=False, indent=0):
    if isunwrappable(data):
        if isinstance(data, Mapping):
            items = data.items()

            if sort_keys:
                items = sorted(items)

            for key, value in items:
                if isunwrappable(value):
                    yield indent, f"{key}:"
                    yield from pretty_lines(
                        value, sort_keys, sort_sets, indent + 1
                    )
                else:
                    yield indent, f"{key}: {value}"
        elif isinstance(data, Sequence):
            for value in data:
                if isunwrappable(value):
                    yield from pretty_lines(
                        value, sort_keys, sort_sets, indent + 1
                    )
                else:
                    yield indent, f"{value}"
        elif isinstance(data, Set):
            values = list(data)

            if sort_sets:
                values.sort()

            yield from pretty_lines(values, sort_keys, sort_sets, indent)
        else:
            raise TypeError
    else:
        yield indent, f"{data}"


def pretty_dumps(data, sort_keys=False, sort_sets=False, indent=4):
    if isinstance(indent, int):
        indent = ' ' * indent

    return '\n'.join(
        f"{indent * level}{string}"
        for level, string in pretty_lines(data, sort_keys, sort_sets)
    )
