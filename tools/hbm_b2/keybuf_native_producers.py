#!/usr/bin/env python3
import json, argparse
from pathlib import Path
from b2_top import Die,parse_expr,slice_segs
a=argparse.ArgumentParser(description='Trace native keybuf producer bits through as-built transport')
a.add_argument('--native-top',type=Path,required=True);a.add_argument('--asbuilt',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
a=a.parse_args()
cfg=json.loads(a.asbuilt.read_text())
d=Die(a.native_top,cfg['transport'])
out={}
for q in ['SW','SE','NW','NE']:
 name='hb_idx__s_'+q;obj=d.insts[name];ex=parse_expr(obj['conns']['key_lines'],d.widths)
 slots=[]
 for p in range(4):
  bits=d.resolve(slice_segs(ex,p*1099,(p+1)*1099-1))
  slots.append(dict(pc=p,source_bits=bits))
 out[q]=dict(half=obj['conns']['half'],first_ord=obj['conns']['first_ord'],key_lines=slots,
             beat_v=d.resolve(parse_expr(obj['conns']['beat_v'],d.widths)),beat_index=d.resolve(parse_expr(obj['conns']['beat_index'],d.widths)))
a.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({q:{'half':x['half'],'first_ord':x['first_ord'],'source_nets':sorted({a[0][1] for p in x['key_lines'] for a in p['source_bits']})} for q,x in out.items()},indent=2))
