#!/usr/bin/env python3
"""Source-bound, model-only site budget. Never emits a placement or launches P&R."""
import argparse
import hashlib
import json
import math
import re
from decimal import Decimal as D
from pathlib import Path
import uarch_model as U
ROOT = Path(__file__).resolve().parents[1]

def budget(extra_std_um2=0):
    # Integer placement grid: 54nm site, 270nm row. Round halo OUTWARD.
    width_sites = 18492
    macro_sites = 4 * 2320 * 233
    escape_sites = 8 * 256 * 233
    halo_sites = 4 * (2320 + 2*38) * 2*8
    std = D('62705.9') + D(str(extra_std_um2))
    demand = math.ceil(std / D('0.01458'))
    rows = math.ceil((2*demand + macro_sites + escape_sites + halo_sites)/width_sites)
    free = width_sites*rows-macro_sites-escape_sites-halo_sites
    return dict(width_sites=width_sites, rows=rows, macro_sites=macro_sites,
                exclusive_escape_sites=escape_sites, exclusive_top_bottom_halo_sites=halo_sites,
                standard_cell_demand_sites=demand, free_sites=free,
                density=0.5, stdcell_capacity_um2=float(D(free)*D('0.01458')/2),
                core_um=[998.568, rows*.270], outline_um=[1002.89,rows*.270+4.32],
                additional_stdcell_reserve_um2=extra_std_um2)

def price(outline):
    key = 'w10_fullmap_site_budget_diagnostic'
    assert key not in U.CONS_PITCH
    U.CONS_PITCH[key] = dict(U.CONS_PITCH[U.PRODUCT_PITCH],bf16_outline_um=tuple(outline))
    try:
        args = ('analytical',U.CONS['overhead'],'ring',U.PRODUCT_GEOM,key,'columns','4096m8')
        stages=U.cons_min_stages(*args)
        usable=U.cons_field_usable_mm2(U.CONS['overhead'],'ring',U.PRODUCT_GEOM)
        need=lambda s: U.cons_field_need_mm2(s,'analytical',key,'columns','4096m8')
        assert need(stages)<=usable and need(stages-1)>usable
        head=U.cons_head_dies('analytical',U.CONS['overhead'],'ring',U.PRODUCT_GEOM,U.PRODUCT_PITCH,'8192m8')
        r=U.cons_v41_rom(stages,head,U.cons_table_dies('analytical')['dies'],bf16='columns',
            clock_hz=U.PRODUCT_CLOCK_HZ,field_concurrency=U.FIELD_CONCURRENCY,
            added_latency=dict(U.SOFTPLUS_FIX,**U.W11_STREAM_SS,**U.PLUS_LAT),dyn_scale=U.PRODUCT_DYN_SCALE,
            slow_domain=(.9e9,'w18'),elem_stages=8,ss_wire=True,serial=U.PRODUCT_SERIAL,
            die=U.DIE_SHRUNK_INTERIM,vmh=U.VMC_FUSED,hub_block=U.PRODUCT_HUB)
        return dict(stages=stages, dies=r['dies'], usable_field_mm2=usable,
                    required_field_mm2=need(stages), preceding_stage_field_mm2=need(stages-1),
                    conditional_ar_tokens_s=r['ar_tokens_s_b1'],conditional_token_us=1e6/r['ar_tokens_s_b1'],
                    scope='Unchanged LAT8; conditional no additional interface cycles. Redistribution, routes and exactness unqualified.')
    finally:
        del U.CONS_PITCH[key]

def build(endpoint_path):
    paths=['physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef',
           'results/uarch/w10_baseline_wake/fullmap_r2/1_synth.json',
           'results/uarch/w10_baseline_wake/fullmap_r2/strict_structure.json',
           'results/uarch/w10_wake_pinaccess_contract_review/inputs.json','tools/uarch_model.py']
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    assert pins[paths[0]]=='99d748ee4cd4eada18c2931f9b472e369759a7fa1fbd865f08b62f559f7cf1bf'
    synth=json.loads((ROOT/paths[1]).read_text())
    assert synth['synth__design__instance__area__stdcell']==62705.9
    lef=(ROOT/paths[0]).read_text()
    ports=[]
    for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',lef,re.S):
        if 'USE POWER' in body or 'USE GROUND' in body: continue
        rect=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body)
        if rect:
            x0,y0,x1,y1=[int(D(v)*1000) for v in rect.groups()]
            ports.append(dict(name=name,edge='west' if x0==0 else 'east',center_y_nm=(y0+y1)//2))
    assert len(ports)==288
    assert all(p['center_y_nm']%48==12 for p in ports)
    assert sum(p['edge']=='west' for p in ports)==144
    endpoints=json.loads(endpoint_path.read_text())
    sets=[set(v['endpoints']) for v in endpoints.values()]
    assert len(sets)==4 and all(len(s)==272 for s in sets) and len(set.union(*sets))==1088
    minimum=budget()
    stress=budget(4665.4) # Failed c8 GRT minus synth; sensitivity, not qualified new-context growth.
    for b in (minimum,stress): b['composed_model']=price(b['outline_um'])
    return dict(schema='opentallas.w10.fullmap.slotfit.v1',verdict='MODEL_ONLY_PHYSICAL_HOLD',adopt=False,
        physical_admission=False,source_sha256=pins,endpoint_trace_sha256=hashlib.sha256(endpoint_path.read_bytes()).hexdigest(),
        fullmap_netlist_sha256='d6b8f7848db0fdfb1f1142deaa298154c4a6366447ee5d1906df8055ed4ba2ea',
        ports=dict(west=144,east=144,capture_flops=1088,per_macro_capture_flops=272,logic_hops_to_capture=2),
        necessary_coordinate_bounds_nm=dict(escape_only_left_x=15984,escape_only_right_x=861624,
            capture_corridor_left_x=22464,capture_corridor_right_x=855144,bottom_y=6480,mirrored_top_y=74250,
            capture_corridor_width=6480,capture_corridor_note='Conditional local reservation within already-counted stdcell area; capture muxes and clocks not yet allocated.'),
        minimum_site_budget=minimum,historical_growth_sensitivity=stress,
        historical_growth_scope='4665.4um2 is failed c8 GRT65051.7 minus synth60386.3; not a bound on wake CTS/hold/routing growth.',
        unresolved=['Root-owner all-port VIA/EOL/PG escape and obstruction legality',
            'Actual capture mux/FF/clock buffer local assignment and track demand',
            'PDN/tap/endcap blockages and final standard-cell growth',
            'Eight physical ICG clock load/placement/CTS and exact clock/reset gates',
            'Owner redistribution exactness, actual abstracts, SS/FF contextual timing and IR'],
        constraints=dict(density=.5,streaming_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--endpoints',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(build(a.endpoints),indent=2)+'\n')
