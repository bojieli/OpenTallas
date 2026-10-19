#!/usr/bin/env python3
"""Run on fleet from immutable lane root AFTER canonical mapped netlist exists."""
from pathlib import Path
import sys
r = Path.cwd()
p = r / 'src/tools/textbook_lint.py'
s = p.read_text().replace('hf[:8]', 'hf[:1000]').replace('bad[:12] + ([f"... {len(bad) - 12} more"] if len(bad) > 12 else [])', 'bad')
net = next((r / 'map/work/orfs/results').glob('asap7/*/base/1_2_yosys.v'))
sys.argv = [str(p),'check','--netlist',str(net),'--top','dsdv_gunit_l5','--set','hf_report=1','hf_max=32','--out',str(r/'map/fanout_complete.json')]
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p.resolve())})
