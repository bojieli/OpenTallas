"""Correct measured S81 soft-partition censuses without reformatting geometry."""
import argparse
import copy
import json
import re
from pathlib import Path

COUNTS = {1:1904350, 3:1940880, 4:1931578, 5:1891769}

def apply(plan):
    for t,n in COUNTS.items():
        plan['partition_types'][f'ot_s81sl_kv_leaf__t{t}']['cells'] = n
    return plan

def rewrite(text):
    original = json.loads(text)
    expected = apply(copy.deepcopy(original))
    for t,n in COUNTS.items():
        name = f'ot_s81sl_kv_leaf__t{t}'
        pattern = r'(^  "' + re.escape(name) + r'": \{\n)'
        # The frozen source has no explicit measured census. Add it beside the
        # type key instead of rewriting millions of compact coordinate rows.
        if 'cells' in original['partition_types'][name]:
            pattern = r'(^  "' + re.escape(name) + r'": \{\n   "cells": )([0-9]+)'
            replacement = lambda m: m[1] + str(n)
        else:
            replacement = lambda m: m[1] + f'   "cells": {n},\n'
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
        if count != 1:
            raise ValueError(f'{name}: exactly one top-level cells field required')
    assert json.loads(text) == expected, 'unexpected plan edit'
    return text

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('plan')
    p.add_argument('output')
    a = p.parse_args()
    Path(a.output).write_text(rewrite(Path(a.plan).read_text()))
