#!/usr/bin/env python3
"""Export complete endpoint identities and exact generated local pin rectangles.

This preserves missing pins and centroid-only PHY placeholders explicitly.
It is an input for system floorplanning, not a physical qualification receipt.
"""
import argparse
import hashlib
import json
import os
import re
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
        pins[name] = dict(w=master.w, h=master.h, generated_obstruction_top=master.obs_top,
            pins=[dict(name=n, layer=L, rect=list(r))
                  for n, L, r in v.pin_rects(master, 1,
                      {q: widths.get((name, q), 0) for q in master.order})])
    from qwen_split.gfp_homes import source_fingerprint
    return dict(source_model_sha256=model.get('gfp_source_fingerprint') or source_fingerprint(model), schema='opentallas.qwen.system-geometry.v1',
        scope='complete generated graph and local physical pin rectangles; no routed qualification',
        die=model['die'],
        insts=[dict(n=i.name, m=i.master, x=i.x, y=i.y, w=i.w, h=i.h, o=i.orient)
               for i in model['insts']],
        buses=[dict(b=b, c=c, n=n, e=[list(e) for e in es])
               for b,c,n,es in model['buses']],
        native_control_contract=model.get('native_control_contract'),
        masters=pins, port_join=model.get('port_join', {}),
        port_split=model.get('port_split', {}),
        relay_equal_groups=model.get('relay_equal_groups', {}),
        centroid_only_pins=[dict(instance=i, port=p, xy=list(xy))
                            for (i,p),xy in (getattr(v,'PIN_POS_EXTRA',None) or {}).items()],
        routing_capacity_model=dict(
            scope='Generated die GRT planning contract; actual bound-view OBS, PG shapes, via spacing and detailed route remain authoritative',
            source='tools/qwen_rom_fulldie.py write_grt_tcl / write_pdn_tcl',
            disabled_grt_layers=['M2','M3','M4','M5'],
            directional_layers=dict(horizontal=['M6','M8'],vertical=['M7','M9']),
            track_geometry_um=dict(v.TRK), via_obs_fraction=v.VIA_OBS,
            pg_coverage_per_net_by_kind=dict(v.REGION_PG),
            regional_layer_adjustment={k:v.VIA_OBS+2*cov for k,cov in v.REGION_PG.items()},
            pg_stripe_width_um=.48, pg_layers=['M8','M9'], regions=model.get('regions', [])),
        constraints=dict(per_hop_um=500, cut_max=.60,
            actual_registered_pin_reach_required=True,
            all_clocks_require_measured_insertion_and_compensated_phase=True,
            relay_skip=os.environ.get('OT_RELAY_SKIP')=='1',
            legacy_io_graph_is_not_native_static_binding=True))


def audit(result):
    from qwen_split.placement_repack import validate
    by={i['n']:i for i in result['insts']}
    widths={}
    for name,master in result['masters'].items():
        for pin in master['pins']:
            key=(name,re.sub(r'\[\d+\]$','',pin['name']))
            widths[key]=widths.get(key,0)+1
    mismatch=[]
    for bus in result['buses']:
        if bus['c'] in ('clock_trunk','reset'):continue
        for inst,port in bus['e']:
            have=widths.get((by[inst]['m'],port),0)
            if have!=bus['n']:
                mismatch.append(dict(bus=bus['b'],instance=inst,port=port,required=bus['n'],actual=have))
    return dict(scope='Generated physical-plan consistency only; does not prove actual whole-die RTL binding or native qualification',
                geometry_errors=validate(result['insts'],result['die']),
                nonclock_reset_endpoint_bit_mismatches=mismatch)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('output',type=Path);a=ap.parse_args()
    import die_top_lint as D
    D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
    v,m=D.load_qwen()[:2]
    result=export(v,m)
    result['generated_plan_audit']=audit(result)
    result['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() if (ROOT/'.git').exists() else (ROOT/'SOURCE_COMMIT').read_text().strip()
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'tools/qwen_split').glob('*.py'))}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(a.output),instances=len(result['insts']),buses=len(result['buses']),masters=len(result['masters']))))

if __name__=='__main__':main()
