# Existing-index read-only query executed against immutable G8 root on gold2.
# Result is g8_actual_hierarchy.json. This does not compile or change sources.
from pathlib import Path
import hashlib, json, sys
r=Path('/srv/opentallas-scratch/claude/codex-s81-g8-resume-1021/die72-g8iq')
sys.path.insert(0,str(r/'src/tools'))
import die_port_bind as B
p=json.loads((r/'bind/bind/port_bind.json').read_text())
defs={}
for d in p['defines']:
 k,_,v=d.partition('=');defs[k]=v
variants={}
idx,amb=B.rtl_index(p['rtl_roots'],p['rtl_files'],defs,p['rtl_files'],variants)
for m in ['ot_s81sl_slice_c1x_k8_cap5r_lp','ot_s81sl_xgt_xo','ot_s81sl_rstopt_xo','ot_s81sl_xs4','ot_s81sl_slice','ot_s81sl_xg','ot_s81sl_xs']:
 x=idx.get(m)
 print(m,x.path if x else None,hashlib.sha256(Path(x.path).read_bytes()).hexdigest() if x else None,amb.get(m) if isinstance(amb,dict) else m in amb,variants.get(m))
