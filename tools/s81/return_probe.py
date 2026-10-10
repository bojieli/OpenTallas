import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as F
args=F.die_options(argparse.ArgumentParser()).parse_args(Path(sys.argv[1]).read_text().split())
F.apply_options(args)
# Inspect existing frame/column mechanism before the whole-die hop pass.
F.HOP_PLAN={}
F._hop_fix=lambda m,p:None
m=F.build();F.finalize_r8(m)
by={it.name:it for it in m['insts']}
names=['y_rt_0_8b_0','y_rt_0_8b_1','y_rt_0_8b_2']
print(json.dumps({'frame':m['frames'][0],'points':{n:{k:getattr(by[n],k) for k in by[n].__slots__} for n in names if n in by},'edges':[b for b in m['buses'] if b[0].startswith('rt_0_8b') or any(e[0] in names for e in b[3])]},default=str),flush=True)
