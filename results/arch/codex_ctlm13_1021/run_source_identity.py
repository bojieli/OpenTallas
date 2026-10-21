#!/usr/bin/env python3
"""Executable source-identity chain; unchanged sequential boundaries, clocks and output wiring."""
from pathlib import Path
import argparse
import hashlib
import re
import subprocess
import sys
import tarfile
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--mutant', action='store_true')
a = p.parse_args()
here = Path(__file__).resolve().parent
root = here.parents[2]
new = root / 'rtl/qwen_dv/lp9f_rrloc/qfd_tt_ctlm_dv_np_lp.sv'
helpers = root / 'rtl/qwen_dv/lp9f_rrloc/qfd_tt_ctlm_dv_np_helpers.sv'
with tempfile.TemporaryDirectory(prefix='ctlm13_identity_') as work:
    work = Path(work)
    with tarfile.open(here / 'baselines.tgz') as t:
        t.extractall(work, filter='data')
    assert hashlib.sha256(helpers.read_bytes()).digest() == hashlib.sha256((work/'helpers.sv').read_bytes()).digest()
    if a.mutant:
        text = new.read_text()
        pattern = r'(qfd_bmath_\w+ #\(\.ID\(0\)\) u_qkorr_13_\d+\([^\n]*?\.A\()(n_\d+)(\))'
        text, count = re.subn(pattern, r"\g<1>1'b1\g<3>", text, count=1)
        assert count == 1
        new = work / 'mutant.sv'
        new.write_text(text)
    for left, right in [(work/'npl.sv', work/'rr2.sv'), (work/'rr2.sv', new)]:
        result = subprocess.run([sys.executable, str(here/'check_equivalent.py'), str(left), str(right)], capture_output=True, text=True)
        print(result.stdout, end='')
        if result.returncode:
            print(result.stderr, end='')
            print('CTLM13_SOURCE_IDENTITY FAIL')
            sys.exit(1)
print('CTLM13_SOURCE_IDENTITY PASS FF_delta=0 clock_delta=0 data_edge_delta=0')
