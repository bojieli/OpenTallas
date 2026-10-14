#!/usr/bin/env python3
"""Run actual NG256 hierarchy arithmetic with every-edge HC head pin checks."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import hc_gate
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--mutate-head',action='store_true')
a=p.parse_args()
if a.mutate_head:
    # The submitted remote source is an isolated copy; preserve the exact edit
    # in its current-source record, not an unobserved checker-only mutant.
    src=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv'
    raw=src.read_text();old='n_head_d <= head_d;'
    if raw.count(old)!=1:raise SystemExit('head mutant anchor changed')
    src.write_text(raw.replace(old,"n_head_d <= head_d ^ 84'd1;"))
hc_gate.RTL.append('rtl/dsrom_sys/s81_ctrl/test/ot_s81_hc_head_checker.sv')
sys.argv=['hc_gate.py','run','--out',a.out,'--ng','256','--fp','dpi','--hier','3',
          '--cnl-pin','1','--chain-step','6','--lane-specialize','1','--tmax','50000']
raise SystemExit(hc_gate.main())
