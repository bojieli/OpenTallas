"""One selected additive b3 k16 physical-feasibility source, F1/F2 plus VCH260.

Explicit source projection, not numerical RTL/SSFF/IR adoption. Preserves b2.
Splits the two independent south stack links at opposite hub faces and at both
edges of the widened vertical channel without narrowing either link payload.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import qwen_rom_fulldie as F
import qwen_rom_fulldie_pg_r3 as PG
from uarch_model_qwen_instruction_transport_r1 import price as instruction_price

ROOT=Path(__file__).resolve().parents[1]

def selected(enabled=False):
    if not enabled:raise ValueError('b3 F1/F2 source selection is default off')
    spec=importlib.util.spec_from_file_location('qfd_b3_private',F.__file__)
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    old_vch=v.VCH
    v.VCH=v.up(260,v.GX);v.SPINE_W_R2+=v.VCH-old_vch
    v.LST_V=(v.VCH,v.LST_V[1])
    v.CORRIDOR_BITS=388;v.TAP_BITS=325
    # Same proposed PG grid as the source-prepared r3; charge rounded coverage.
    v.REGION_PG={r:(.48/PG.bump_pitch(c,90) if c else 0.) for r,c in F.REGION_PG.items()}
    m=v.build(tree_mode='banded');half=v.VCH/2
    oldleg,oldcorner=m['legs'][0]
    removed={i.name for i in oldleg}|{oldcorner.name}
    m['insts']=[i for i in m['insts'] if i.name not in removed]
    splits={}
    for side,dx in [('W',0),('E',half)]:
        leg=[]
        for i in oldleg:
            q=v.Inst(i.name+'_'+side,'qfd_lst_v_split',i.x+dx,i.y,half-v.SHAVE,i.h,
              kind='link_station',region='hub');leg.append(q);m['insts'].append(q)
        corner=v.Inst('lc_S'+side,'qfd_lst_c_split',oldcorner.x+dx,oldcorner.y,
          half-v.SHAVE,oldcorner.h,oldcorner.orient,kind='link_station',region='hub')
        m['insts'].append(corner);splits[side]=(leg,corner)
    # Lower links remain independent 1056-bit payload/control channels.
    buses=[]
    for bid,cl,bits,eps in m['buses']:
        if bid.startswith('lnkv_0_'):continue
        if bid.startswith('lnkh_0W_'):eps=[(splits['W'][1].name,p) if i==oldcorner.name else (i,p) for i,p in eps]
        if bid.startswith('lnkh_0E_'):eps=[(splits['E'][1].name,p) if i==oldcorner.name else (i,p) for i,p in eps]
        buses.append((bid,cl,bits,eps))
    maps=[]
    for side in ['W','E']:
        leg,corner=splits[side];prev=('hub_el','lsw' if side=='W' else 'lse')
        for k,i in enumerate(leg):
            buses.append((f'lnkv_0_{side}_{k}','link_spine',v.LINK_TRACKS,[prev,(i.name,'b')]))
            prev=(i.name,'a')
        buses.append((f'lnkv_0_{side}_c','link_spine',v.LINK_TRACKS,[prev,(corner.name,'v')]))
        maps.append(dict(side=side,old_bus_bits=[0,1055] if side=='W' else [1056,2111],
          independent_payload_width=1056,hub_port='lsw' if side=='W' else 'lse',
          hub_face='W' if side=='W' else 'E',channel_edge_um=m['geo']['x_vch']+(0 if side=='W' else v.VCH),
          stations=[i.name for i in leg],corner=corner.name))
    m['buses']=buses;m['south_split']=splits
    m['die']['budget_mm2']=858;m['die']['margin_mm2']=858-m['die']['mm2']
    base_masters=v.masters
    def masters(model,k=1,port_bits=None):
        out=base_masters(model,k,port_bits)
        hub=out['qfd_hub'];hub.face('lsw',v.LINK_TRACKS,'W','M4',hub.h/8,1)
        hub.face('lse',v.LINK_TRACKS,'E','M4',hub.h/2,1)
        sv=v.Master('qfd_lst_v_split',half-v.SHAVE,v.LST_V[1]-v.SHAVE,3,'b3 one existing lower stack link, half-channel frame')
        sv.face('a',v.LINK_TRACKS,'S','M5',sv.w/2,1);sv.face('b',v.LINK_TRACKS,'N','M5',sv.w/2,1)
        sc=v.Master('qfd_lst_c_split',half-v.SHAVE,v.HCH-v.SHAVE,3,'b3 lower corner, one existing stack link')
        sc.face('v',v.LINK_TRACKS,'S','M5',sc.w/2,1)
        sc.face('w',v.LINK_TRACKS,'W','M4',sc.h/2,1);sc.face('e',v.LINK_TRACKS,'E','M4',sc.h/2,1)
        out[sv.name]=sv;out[sc.name]=sc;return out
    v.masters=masters
    return v,m,maps

def price():
    v,m,maps=selected(True);old=F.build(tree_mode='banded');p=instruction_price()
    old_stages=F.link_stages(old);new_stages=v.link_stages(m)
    extra_stages=max(x['stages_430'] for x in new_stages['paths'])-max(x['stages_430'] for x in old_stages['paths'])
    def wire(model):
        by={i.name:i for i in model['insts']}
        # Rectilinear centre MST upper star estimate, not a routed length.
        return {cl:sum(bits*sum(abs(by[i].cx-by[eps[0][0]].cx)+abs(by[i].cy-by[eps[0][0]].cy) for i,_ in eps[1:])
          for _,c,bits,eps in model['buses'] if c==cl) for cl in {b[1] for b in model['buses']}}
    return dict(schema='QWEN_FULLDIE_B3_SELECTED_PRICE_R1',selected=True,architecture_changed=False,
      original_generator_sha256=hashlib.sha256(Path(F.__file__).read_bytes()).hexdigest(),
      before_die=old['die'],after_die=m['die'],area_delta_mm2=m['die']['mm2']-old['die']['mm2'],
      channel=dict(before_um=F.VCH,requested_um=260,after_aligned_um=v.VCH,
        track_capacity_ratio=v.VCH/F.VCH,old_peak_M9_DC=1.293103448275862,
        unchanged_demand_ideal_peak_DC=1.293103448275862*F.VCH/v.VCH,
        ideal_ratio_is_not_measured=True),
      F1=dict(reset_wires_before=64,after=1,removed_bits_per_corridor_edge=63,
        reset_release_prospective_max_hops=32+12,warm_reset_requires_accepted_debt_drain=True,
        actual_system_reset_installed=False,reset_control_scope='physical source projection, not a destructive warm-reset shortcut'),
      F2=dict(instruction_bits=379,beat_bits=190,beat_controls=3,beat_count=2,column_fifo_entries=2,
        corridor_bits_before=637,after=388,tap_bits_after=325,
        extra_instruction_edges_per_hop=1,critical_hops_upper=44,
        token_delta_cycles='sum exact source critical issue path hops; no <=0.14% claim without program/calendar',
        instruction_component_price=p),
      lower_split=maps,lower_link_widths_unchanged=True,
      link_stages_before=old_stages,link_stages_after=new_stages,
      additional_link_pipeline_cycles=extra_stages*2*36,
      additional_link_pipeline_us=extra_stages*2*36/1200,
      link_registered_reach_limit_um=430.56,existing_corridor_token_delta_cycles=432,
      modeled_wire_bit_um_before=wire(old),modeled_wire_bit_um_after=wire(m),
      PG=dict(rounded_per_net_coverage=v.REGION_PG,full_die_IR_required=True,
        core_fixture_not_die_PASS=True,actual_IR_pass=False),
      qualification=dict(global_route=False,detail_route=False,SSFF=False,numerical_system=False),
      source_scope='full-size hierarchical physical feasibility with retained hardened-element reservations, not installed engine RTL proof')

def prepare(work,enabled=False):
    v,m,maps=selected(enabled);work=Path(work)
    if work.exists() and any(work.iterdir()):raise ValueError('refuse existing b3 output')
    work.mkdir(parents=True,exist_ok=True)
    result=v.case_grt(m,work,16,'b3_k16_banded_i5',5)
    # Guard real master geometry separately from the coarse k16 capacity alias.
    # Actual full-size alignment census runs first; k16 is only a track-capacity
    # pathfinding projection, never a substitute for real pin/DRC qualification.
    real=work/'real_alignment';v.case_real(m,real)
    realtcl=(real/'run.tcl').read_text().split('mem assert\n')[0]
    realtcl+='mem assert\nif {$ov || $out} { error {B3 real geometry overlap/outside} }\n'
    realtcl+='ot_mts::assert_on_track -label b3-full-real\nwrite_db /work/floorplan.odb\n'
    (real/'run.tcl').write_text(realtcl)
    views=work/'guard_views';views.mkdir()
    masters=v.masters(m,1);widths=v.port_widths(m,1)
    for name,master in masters.items():
        directory=views/name;directory.mkdir()
        text,_=v.lef_text(master,1,{p:widths.get((name,p),0) for p in master.order})
        (directory/(name+'.lef')).write_text(text)
    (work/'macro_gate_args.json').write_text(json.dumps([a for name in masters for a in ['--macro-view',f'{name}={views/name}']],indent=2)+'\n')
    result.update(selected_price=price(),south_split=maps,
      producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      defaults_unchanged=True,scope='CHANGED_SOURCE_FULLDIE_K16_GRT_PATHFINDING_ONLY',
      raw_PG_IR_prerequisite='No die IR PASS. PG capacity includes prepared rounded pitches. Actual macro PDN/IR gate separate and mandatory before adoption.')
    (work/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--price',action='store_true');a.add_argument('--work',type=Path);a.add_argument('--enable-b3',action='store_true')
    args=a.parse_args()
    if args.price:print(json.dumps(price(),indent=2))
    else:
        if not args.work:a.error('--work required')
        r=prepare(args.work,args.enable_b3);print(json.dumps({k:r[k] for k in ['tag','instances','bundle_pins','bundle_nets','wires']}))
