# uncapped fanout census of the mapped safe3 netlist with the repository textbook lint (hf_max 32, every finding listed)
from pathlib import Path
import sys,re,json
p=Path('src/tools/textbook_lint.py');s=p.read_text().replace('hf[:8]','hf[:1000]').replace('bad[:12] + ([f"... {len(bad) - 12} more"] if len(bad) > 12 else [])','bad')
net=next(Path('map_safe3/work/orfs/results').glob('asap7/*/base/1_2_yosys.v'))
sys.argv=[str(p),'check','--netlist',str(net),'--top','dsfd_coll_lane_w_safe3','--set','hf_report=1','hf_max=32','--out','map_safe3/fanout_complete.json']
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p.resolve())})
