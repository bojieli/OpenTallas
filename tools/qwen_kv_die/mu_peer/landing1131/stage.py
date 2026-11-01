#!/usr/bin/env python3
"""Stage the smallest full four-user/eight-rank native protocol coupon."""
import argparse
from pathlib import Path
import shutil
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('out', type=Path)
a = p.parse_args()
here = Path(__file__).resolve().parent
root = here.parents[3]
a.out.mkdir(parents=True, exist_ok=True)
for src, name in [(here.parent / 'landing_profile.py', 'landing_profile.py'),
                  (root / 'rtl/qwen_sys/mu_qwen_20261018/ot_qwen_tp8_token_cohort_mu.sv', 'native.sv'),
                  (here / 'tb.sv', 'tb.sv'), (here / 'run.sh', 'run.sh')]:
    shutil.copyfile(src, a.out / name)
