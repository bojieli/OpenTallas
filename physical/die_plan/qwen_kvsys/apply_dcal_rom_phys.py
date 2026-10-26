#!/usr/bin/env python3
"""Idempotent D-ROM-3b physical contents delta on authoritative SYS_C3 interfaces.

Adds one generated profile ROM, its actual LEFclock sink, and a4.32um clock
keepout. No partition pins, outline, clock root, reset/START or schedule changes.
"""
from pathlib import Path
import argparse,copy,json,re
ROOT=Path(__file__).resolve().parents[3]
TYPE='kv3_sys_c'
INST='u_bound.u_dcal.u_profile'
NAME='ot_rom_64x32_m2'
ORIGIN=[302.4,250.56]
HALO=4.32
VIEWS=f'physical/asap7_memory_macros_v2/{NAME}'


def lef_geometry(root=ROOT):
    text=(root/VIEWS/f'{NAME}.lef').read_text()
    size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
    block=re.search(r'^  PIN clk\s*$.*?^  END clk\s*$',text,re.S|re.M).group()
    rect=list(map(float,re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',block).groups()))
    return list(map(float,size.groups())),[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]


def apply(plan,root=ROOT):
    t=plan['partition_types'][TYPE];size,pin=lef_geometry(root)
    content={'inst':INST,'module':NAME,'status':'new','origin_um':ORIGIN,'outline_um':size,
      'orient':'R0','lef':VIEWS+f'/{NAME}.lef','lib':VIEWS+f'/{NAME}_tt.lib','obs_max':'M4',
      'note':'D-ROM-3b generated contents macro; noECC. Profile via map changes content only. Candidate placement; actual b19 scalar/cache logic cluster must stay nearby before route.'}
    entries=t.setdefault('contents',[])
    entries[:]=[c for c in entries if c.get('inst')!=INST]+[content]
    box=[round(ORIGIN[0]-HALO,6),round(ORIGIN[1]-HALO,6),round(ORIGIN[0]+size[0]+HALO,6),round(ORIGIN[1]+size[1]+HALO,6)]
    sink=[round(ORIGIN[0]+pin[0],6),round(ORIGIN[1]+pin[1],6),1]
    ck=t.setdefault('clock',{})
    if box not in ck.setdefault('keepouts_um',[]):ck['keepouts_um'].append(box)
    if sink not in ck.setdefault('sink_sites_um',[]):ck['sink_sites_um'].append(sink)
    return {'schema':'opentallas.kv-dcal-rom-physical-delta.v1','source_plan_commit':'7e20e440116e',
      'type':TYPE,'macro':NAME,'instance':INST,'origin_um':ORIGIN,'outline_um':size,
      'lef_clock_pin_local_um':pin,'clock_sink_um':sink,'clock_keepout_um':box,'halo_um':HALO,
      'new_boot_cycles':0,'new_production_cycles':0,'external_interfaces_changed':False,
      'content_fields':content,'tt_lib':content['lib'],'ff_lib':VIEWS+f'/{NAME}_ff.lib',
      'inherited_missing_M6_PHY_views':'fixed by exact physical-only package02e6431e5c;no behavioral model',
      'review_verdict':'PASS-COND placement-only;parent visually reviewed all3images;no fullroute or SIGNED authorization',
      'review_record':'results/geom_review/codex_kv_dcal_phys_1025/review.json',
      'route_conditions':['Actual b19 placed scalar/cache/START consumers stay local: target within200um, hard reach405um','Inspect new32-bit fanout and pin density on actual placed cells','Check CORE-PG continuity and macro PG connectivity','Review post-placement clock/tap image before full route']}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path)
    ap.add_argument('--manifest',type=Path);a=ap.parse_args();raw=json.loads(a.plan.read_text())
    before=copy.deepcopy(raw);delta=apply(raw);once=copy.deepcopy(raw);apply(raw)
    if raw!=once:raise RuntimeError('physical delta is not idempotent')
    a.plan.write_text(json.dumps(raw,indent=1)+'\n')
    if a.manifest:a.manifest.write_text(json.dumps(delta,indent=2,sort_keys=True)+'\n')
    print(json.dumps(delta,indent=2))
