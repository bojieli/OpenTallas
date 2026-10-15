#!/usr/bin/env python3
"""Export complete endpoint identities and exact generated local pin rectangles.

This preserves missing pins and centroid-only PHY placeholders explicitly.
It is an input for system floorplanning, not a physical qualification receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


def export(v, model):
    masters = v.masters(model, 1)
    widths = v.port_widths(model, 1)
    pins = {}
    for name, master in masters.items():
        pins[name] = dict(w=master.w, h=master.h,
            pins=[dict(name=n, layer=L, rect=list(r))
                  for n, L, r in v.pin_rects(master, 1,
                      {q: widths.get((name, q), 0) for q in master.order})])
    return dict(schema='opentallas.qwen.system-geometry.v1',
        scope='complete generated graph and local physical pin rectangles; no routed qualification',
        die=model['die'],
        insts=[dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient)
               for i in model['insts']],
        buses=[dict(b=b, c=c, n=n, e=[list(e) for e in es])
               for b,c,n,es in model['buses']],
        masters=pins, port_join=model.get('port_join', {}),
        port_split=model.get('port_split', {}),
        relay_equal_groups=model.get('relay_equal_groups', {}),
        centroid_only_pins=[dict(instance=i, port=p, xy=list(xy))
                            for (i,p),xy in (getattr(v,'PIN_POS_EXTRA',None) or {}).items()],
        constraints=dict(per_hop_um=500, cut_max=.60,
            actual_registered_pin_reach_required=True,
            all_clocks_require_measured_insertion_and_compensated_phase=True,
            relay_skip=os.environ.get('OT_RELAY_SKIP')=='1',
            legacy_io_graph_is_not_native_static_binding=True))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('output',type=Path);a=ap.parse_args()
    import die_top_lint as D
    D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
    v,m=D.load_qwen()[:2]
    result=export(v,m)
    result['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() if (ROOT/'.git').exists() else (ROOT/'SOURCE_COMMIT').read_text().strip()
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'tools/qwen_split').glob('*.py'))}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(a.output),instances=len(result['insts']),buses=len(result['buses']),masters=len(result['masters']))))

if __name__=='__main__':main()
