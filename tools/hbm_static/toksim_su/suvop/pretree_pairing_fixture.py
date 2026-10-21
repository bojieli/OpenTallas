#!/usr/bin/env python3
"""Sensitive production-shape square reduction for the real join-pairing mutant."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import prod_compile as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    a = ap.parse_args()
    seed = np.zeros((512, 512), dtype=C.F)
    # First quarter's first 128-word block: four 16-word join leaves.
    seed[0, [0, 16, 32, 48]] = [4096, 1, 2, 3]
    opts = SimpleNamespace(out=str(a.out), rec='ds_q_norm_ss', rr=12, wr=10,
                           fill_slack=1, drain_slack=2, side_ii=0, rfd_slack=1,
                           pretree=True, qpr=1, seed_override=seed)
    C.compile_rec(opts)
    p = a.out / 'programme.json'
    m = json.loads(p.read_text())
    assert m['reduction']['finals']['0'] == '4b800006', m['reduction']
    m['fixture'] = dict(shape='production ds_q_norm_ss N1280 rows1',
                        input_join_leaves=[4096, 1, 2, 3],
                        canonical_squared_result='4b800006',
                        wrong_join_squared_result='4b800007',
                        reason='canonical (2^24+1)+(4+9) rounds to2^24+12; wrong (2^24+4)+(1+9) gives2^24+14')
    p.write_text(json.dumps(m, indent=2) + '\n')
    print(json.dumps(m['fixture']))


if __name__ == '__main__':
    main()
