"""Compose a910 mapped q growth with complete BF/selector and I66 evidence."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import dsrom_PAR2_complete_selector_wire_join as J
import dsrom_noECC_complete_parent_map as P

BASE=P.ROOT/'results/uarch/dsrom_I66_terminal_destination_review_20261002'


def build():
    m=J.build();old,fields,macros,cfg,bands,services=P.build()
    terminal=json.loads((BASE/'mapped_element_a910.json').read_text())
    q=terminal['elements']['q'];bf=terminal['elements']['bfcolumn']
    if terminal['candidate']!=m['candidate'] or bf['area']['extra_reservation_over_already_priced_frame_um2']!=0:
        raise ValueError('one candidate and unchanged BF frame')
    halo=4320;x=y=halo;rowh=0;new=[];offset={}
    for f in fields:
        outline=(q if f['source_class']=='q_pair' else bf)['area']['proposed_outline_DBU']
        w,h=outline[2:]
        if x+w+halo>33000000:x=halo;y+=rowh+2*halo;rowh=0
        box=[x,y,x+w,y+h]
        offset[f['local_pair']]=(x-f['bbox_DBU'][0],y-f['bbox_DBU'][1])
        new.append(dict(f,bbox_DBU=box,mapped_frame_source='a91078135'))
        x+=w+2*halo;rowh=max(rowh,h)
    end=max(f['bbox_DBU'][3] for f in new);dy=end-m['field']['field_end_DBU']
    relocated=[]
    for macro in macros:
        dx,dy_m=offset[macro['local_pair']]
        relocated.append(dict(macro,bbox_DBU=[v+(dx if k%2==0 else dy_m) for k,v in enumerate(macro['bbox_DBU'])]))
    cfg=[dict(b,bbox_DBU=P.shifted(b['bbox_DBU'],dy)) for b in cfg]
    bands=[dict(b,bbox_DBU=P.shifted(b['bbox_DBU'],dy)) for b in bands]
    s=m['selector']['single_full_slot_bbox_DBU'];sy=math.ceil((s[1]+dy)/2160)*2160
    s=[s[0],sy,s[2],sy+s[3]-s[1]]
    preserved=new+cfg+bands+[b for b in services if b['name']!='X_SEL_TOPK_STORE']
    if any(P.overlap(s,b['bbox_DBU']) for b in preserved) or s[3]>26000000 or end>26000000:
        raise ValueError('fullslot overlaps reserved capacity or exceeds reticle')
    rows={}
    for f in new:rows.setdefault(f['bbox_DBU'][1],[]).append(f)
    for rs in rows.values():
        if any(P.overlap(a['bbox_DBU'],b['bbox_DBU']) for a,b in zip(rs,rs[1:])):
            raise ValueError('field collision')
    ys=sorted(rows)
    if any(max(f['bbox_DBU'][3] for f in rows[a])>b for a,b in zip(ys,ys[1:])):
        raise ValueError('field row collision')
    qgrowth=1686*q['area']['extra_reservation_over_already_priced_frame_um2']/1e6
    extra_void=max(0,33*dy/1e6-qgrowth)
    m['area']['mapped_q_growth_charged_once_mm2']=qgrowth
    m['area']['extra_row_envelope_noncontainment_mm2']=extra_void
    m['area']['combined_noncontainment_policy_screen_mm2']+=qgrowth+extra_void
    m['area']['remaining_before_unpriced_interfaces_mm2']=858-m['area']['combined_noncontainment_policy_screen_mm2']
    m['field'].update(field_end_DBU=end,mapped_q_outline_um=[510.84,151.20],
                      BF_outline_um=[1002.89,157.68],current_cfg_band_additional_y_shift_DBU=dy)
    m['selector']['single_full_slot_bbox_DBU']=s
    m['mapped_clock_G0']=dict(q=q['WAKE'],BF=bf['WAKE'],
        q_SS_FF_closed=q['SSFF_setup_hold_closed'],BF_SS_FF_closed=bf['SSFF_setup_hold_closed'],
        clock_buffer_prices_already_inside_new_q_and_existing_BF_core=True,
        routed_CTS_hold_PG_corridor_cost_not_free=True,
        additional_context_area_unknown=True)
    m['actual_I66_review']=json.loads((BASE/'review-r1.json').read_text())
    m['source_mapped']=dict(commit='a91078135',path='results/uarch/dsrom_noECC_complete_element_mapping_20261002/terminal_pair/model.json',
                          sha256=hashlib.sha256((BASE/'mapped_element_a910.json').read_bytes()).hexdigest())
    m['new_q_growth_latency']=dict(added_RTL_cycles=0,source_arithmetic_unchanged=True,
        physical_route_clock_pipeline_delta=None,no_zero_wire_cost_claim=True,
        full_MTP_iteration_delta=None,diecount_change_selected=False)
    m['schema']='opentallas.dsrom.PAR2.mapped-q-complete-budget.v1'
    m['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    m['geometry_G0']['mapped_q_BF_WAKE_G0_PASS']=False
    return m,new,relocated,cfg,bands


if __name__=='__main__':
    import gzip
    p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    if a.out_dir.exists():raise ValueError('immutable record')
    m,field,macros,cfg,bands=build();a.out_dir.mkdir()
    (a.out_dir/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    for name,data in [('field',field),('macros',macros),('cfg',cfg),('bands',bands)]:
        (a.out_dir/(name+'.json.gz')).write_bytes(gzip.compress((json.dumps(data,sort_keys=True)+'\n').encode(),mtime=0))
