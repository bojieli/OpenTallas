#!/usr/bin/env python3
"""Source-pinned candidate placement for the new private HC row slot."""
import argparse,hashlib,json
from pathlib import Path
import hbm_accel_die_fp as H
import hbm_die_clock_inputs as C

def serial(v):
    if isinstance(v,dict):return {str(k):serial(q) for k,q in v.items()}
    if isinstance(v,(list,tuple)):return [serial(q) for q in v]
    return v

def export(out, variant):
    if variant not in ('R25I','R25IC2','R25M'):raise ValueError(variant)
    m=H.build(getattr(H,variant),network_probe=True)
    if not m.get('external_clock_inputs'):C.apply(m)
    x=H.up(m['geo']['cx']-700,H.GX);y=H.up(m['geo']['hub_y'][0]+43.2,H.GY)
    box=[x,y,x+1400,y+1400]
    hits=[i.name for i in m['insts'] if min(box[2],i.x+i.w)>max(box[0],i.x) and min(box[3],i.y+i.h)>max(box[1],i.y)]
    if hits:raise ValueError(('new HC slot overlaps actual instances',box,hits))
    slot=H.Inst('hb_hc_row','hfd_hc_row',x,y,1400,1400,kind='spine',region='hub',domain='serial_0p9')
    m['insts'].append(slot);m['hub']['hc_row']=slot
    for bid,cls,bits,eps in m['buses']:
        if bid=='clk_serial':eps.append(('hb_hc_row','clk'))
        if bid=='por_serial':eps.append(('hb_hc_row','por_serial'))
    peers={k:dict(box_um=[i.x,i.y,i.x+i.w,i.y+i.h],center_distance_um=abs(i.x+i.w/2-x-700)+abs(i.y+i.h/2-y-700)) for k,i in m['hub'].items() if k in ('loader','coll','su_full','su_red','hc_row')}
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    rec=dict(scope='CURRENT_DIE_CANDIDATE_PLACEMENT_NOT_FUNCTIONAL_INTEGRATION',variant=variant,variant_dict=m['variant'],geo=m['geo'],new_slot=dict(name=slot.name,master=slot.master,box_um=box,area_um2=1960000,macro_count=64,production_clock_hz=900000000),overlaps=hits,peers=peers,clock_contract=m['external_clock_inputs'],producer=dict(port='x_valid/x_ready,x_lease16,x_beat11,x_data256',beats=1280,live_bytes=40960,body_snapshots_per_die=20,body_bytes=819200,binding='direct SU-tail BF16 publisher and finite CDC collar pending'),remaining=['actual SU BF16 publication and admission binding','HBM service registered clock crossing and transaction binding','row-result collective/mixing consumer and finite credits','actual endpoint pin placements and SS/FF I/O budgets','clock source jitter/phase receiver costs and local reset release'],source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(H.__file__),Path(C.__file__))})
    (root/'context.json').write_text(json.dumps(serial(rec),indent=2)+'\n');C.write_sdc(m,root/'clock_inputs.sdc')
    print(json.dumps(dict(variant=variant,slot=box,overlaps=hits)))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--variant',default='R25I');v=a.parse_args();export(v.out,v.variant)
