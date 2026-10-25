#!/usr/bin/env python3
"""Full-shape A0 trace miter: ROM stream may have an explicit priced delay; neighbor bus remains cycle exact.
A successful shifted comparison does not establish same-cycle equivalence or authorize G3 adoption.
"""
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trace',type=Path,required=True);ap.add_argument('--shift',type=int,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 rows=[(int(p[0]),*[int(x,16) for x in p[1:]]) for ln in a.trace.read_text().splitlines() if len(p:=ln.split())==5]
 b={c:x for c,x,k,bn,kn in rows};k={c:x for c,bt,x,bn,kn in rows}
 nv=sum(bool(v>>512&1) for v in b.values());kv=sum(bool(v>>512&1) for v in k.values())
 bad=sum(k.get(c+a.shift)!=v for c,v in b.items() if v>>512&1)
 reverse=sum(b.get(c-a.shift)!=v for c,v in k.items() if v>>512&1)
 nodes=sum(bn!=kn for c,bt,kt,bn,kn in rows)
 ok=nv>0 and kv==nv and bad==0 and reverse==0 and nodes==0
 r=dict(verdict='PASS_WITH_LATENCY_CHANGE' if ok and a.shift else 'PASS' if ok else 'FAIL',scope='valid ROM t_out words shifted by explicit latency; neighbor n_y every edge unchanged; no G3 or same-cycle claim',rom_t_out_added_cycles=a.shift,neighbor_n_y_added_cycles=0,rom_words_bound=nv,rom_words_kit=kv,rom_mismatches=bad,reverse_mismatches=reverse,neighbor_mismatches=nodes,neighbor_edges=len(rows))
 a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
