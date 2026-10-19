#!/usr/bin/env python3
"""Extract source-pinned native functional models; retain exact UDP FF tables."""
import re,sys
from pathlib import Path
from generate import cells
root=Path(sys.argv[1]);out=Path(sys.argv[2]);used=set()
for f in sys.argv[3:]: used.update(c['master'] for c in cells(Path(f).read_text()))
pieces=[]
for f in sorted(root.glob('*RVT*')):
 if 'SEQ' in f.name:continue
 for m in re.finditer(r'\bmodule\s+(\w+)\b.*?endmodule',f.read_text(),re.S):
  if m[1] in used:
   pieces.append(re.sub(r'\bspecify\b.*?\bendspecify\b','',m[0],flags=re.S));used.remove(m[1])
seq=(root/'asap7sc7p5t_SEQ_RVT_TT_220101.v').read_text()
seq=re.sub(r'\bspecify\b.*?\bendspecify\b','',seq,flags=re.S)
seq=re.sub(r'\s*wire delayed_[^;]*;','',seq).replace('delayed_','')
# Delayed wires are timing-check aliases of the input pins. No timing backannotation
# is part of this functional proof; the UDP polarity/clear/preset truth tables stay exact.
pieces.append(seq)
used.difference_update(['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','ot_sram_1r1w_64x512_m1_r2c2'])
assert not used,used
out.write_text('\n'.join(pieces))
