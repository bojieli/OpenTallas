"""Expand the source-pinned native59 service channel; GEN remains authority."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

NORTH = ('native59','sys_face','d2d_rom','ucie_kv','ckb_rom','rs_bump','bump_fwd_epoch','bump_fwd_lrst')
EAST = ('embed_prov','sys_face')
SEEDS = {'native59':(216,22193.624),'embed_prov':(1101.6,21869.624),'sys_face':(1101.6,22496.024)}

def expand(plan):
    out=copy.deepcopy(plan);by={i['n']:i for i in out['insts']}
    for name,xy in SEEDS.items():
        if name not in by or any(abs(by[name][k]-v)>.0011 for k,v in zip(('x','y'),xy)):
            raise ValueError('native59 service channel seed geometry differs: '+name)
    moved=[]
    for n in dict.fromkeys(NORTH+EAST):
        i=by[n];before=[i['x'],i['y']]
        if n in NORTH:i['y']=round(i['y']+108,3)
        if n in EAST:i['x']=round(i['x']+108,3)
        moved.append(dict(instance=n,before_xy=before,after_xy=[i['x'],i['y']]))
    slot=out['slice_slot_plan'];limits=slot['reticle_um'];outline=slot['die_um']
    bounds=[max(i['x']+i['w']for i in out['insts']),max(i['y']+i['h']for i in out['insts'])]
    if any(b>o+.0011 or o>lim+.0011 for b,o,lim in zip(bounds,outline,limits)):
        raise ValueError('service channel exceeds existing outline or reticle')
    out['native59_service_channel']=dict(schema='opentallas.qwen.native59_service_channel.v1',
        east_gap_um=[108,216],south_gap_um=[108,216],moved=moved,
        planned_die_um=outline,reticle_um=limits,source_instance_bounds_um=bounds,
        runtime_placements={'mu_ctxrx':dict(before_xy=[1555.2,22809.6],after_xy=[1555.2,22852.8],wh=[43.2,97.2],knob='CTXRX_XY / OT_SPLIT_DV_CTXRX_XY')},
        scope='source geometry only; preserve reservations and clock endpoints; actual GEN decides all placement and transport')
    return out

def overlap(a,b):
    return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6

def captured_model(plan,receipt):
    """Keep every captured reservation fixed; test shifted old terminal seats.

    The receipt covers only the old terminal neighborhood. Free seats here are
    candidates, never proof about reservations outside that neighborhood.
    """
    after=expand(plan);reserved={tuple(x['rect'])for s in receipt['terminal_sites']for x in s['occupied_by']}
    # Match current DI source transformations before testing the moved macros.
    macro=[]
    for i in after['insts']:
        x,y,w,h=[i[k]for k in ('x','y','w','h')]
        if i['n'] in ('d2d_rom','ucie_kv','ckb_rom','rs_bump','bump_fwd_epoch','bump_fwd_lrst'):y+=259.2
        if i['n']=='sys_face':x+=129.6
        macro.append((i['n'],(x,y,x+w,y+h)))
    macro.append(('mu_ctxrx',(1555.2,22852.8,1598.4,22950.0)))
    rows=[]
    for s in receipt['terminal_sites']:
        a=s['site'];a=[a[0],a[1]+108,a[2],a[3]+108]
        rows.append(dict(site=a,prior_corridor_allowed=s['corridor_allowed'],
            captured_reservation_collisions=sum(overlap(a,b)for b in reserved),
            macro_collisions=[n for n,b in macro if overlap(a,b)]))
    return dict(scope='captured reservation model only; outside reservations and final corridor/clock/reach require actual GEN',
        captured_reservations_preserved=len(reserved),candidate_count=len(rows),
        locally_unoccupied_candidates=sum(s['prior_corridor_allowed']and not s['captured_reservation_collisions']and not s['macro_collisions']for s in rows),candidates=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('--out',required=True);p.add_argument('--occupancy');p.add_argument('--model-out');a=p.parse_args()
    source=Path(a.plan);d=json.loads(source.read_text());out=expand(d)
    out['native59_service_channel']['source_plan_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
    if a.occupancy:
        if not a.model_out:p.error('--occupancy requires --model-out')
        r=Path(a.occupancy);model=captured_model(d,json.loads(r.read_text()));model['occupancy_sha256']=hashlib.sha256(r.read_bytes()).hexdigest()
        Path(a.model_out).write_text(json.dumps(model,indent=2)+'\n')
        print('captured model candidates',model['locally_unoccupied_candidates'],'of',model['candidate_count'])
    print('source geometry',out['native59_service_channel'])
if __name__=='__main__':main()
