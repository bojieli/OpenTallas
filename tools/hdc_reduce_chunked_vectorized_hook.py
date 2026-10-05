#!/usr/bin/env python3
"""Explicit default-off hook for a FUTURE producer, never a live hotpatch.

Call only after the existing producer sets its numerical environment and
imports its golden. This changes process-local dispatch, not source files;
Dewey owns actual qualification consumption and serial producer adoption.
"""


def install(golden, *, enabled=False):
    if not enabled:
        return False
    from hdc_reduce_chunked_vectorized import G, reduce_chunked_vectorized
    if golden is not G:
        raise ValueError('requires the existing initialized hdc_golden module')
    golden.reduce_chunked = reduce_chunked_vectorized
    return True
