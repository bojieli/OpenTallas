#!/usr/bin/env python3
"""Create a shared-epoch bench from two actual independently lowered images."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('images',type=Path);a=p.parse_args()
s=json.loads((a.images/'serial/manifest.json').read_text());t=json.loads((a.images/'stream/manifest.json').read_text())
assert s['line_bits']==9688 and t['line_bits']==64
text=(ROOT/'rtl/hbm_accel/host_static_20261015/su_target/host_su_pair_tb.sv').read_text()
for prefix,m in [('S',s),('T',t)]:
 for k,key in [('EDGES','edges'),('WRITES','config_transactions'),('MACROS','total_macros'),('ENTRIES','dictionary_entries'),('BANKS','dictionary_banks')]:
  v=m[key];v="'{"+','.join(map(str,v))+"}" if isinstance(v,list) else str(v)
  text=text.replace('@'+prefix+k+'@',v)
(a.images/'host_su_pair_tb.sv').write_text(text)
