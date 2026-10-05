"""Read-only measured k16 hotspots and default-off prospective transport pricing."""
import argparse
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_fulldie as F

def windows(model):
    out={r['name']:r['rect'] for r in model['regions'] if r['name'] in ['spine','spine_vchan']}
    for inst in model['insts']:
        if inst.name in ['hub_el','sp_tree_top']:
            out[inst.name]=[inst.x,inst.y,inst.x+inst.w,inst.y+inst.h]
    return out

def hotspot_usage(path, regions, dbu_per_um):
    if dbu_per_um!=1000:
        raise ValueError('frozen bundled tech uses 1000 DBU/um')
    op=gzip.open if str(path).endswith('.gz') else open
    result={n:{layer:dict(capacity=0.,demand=0.,windows=0,over_capacity_windows=0,positive_demand_zero_capacity_windows=0,peak_fraction=None) for layer in ['M8','M9']} for n in regions}
    with op(path,'rt') as f:
        gx=f.readline().strip();gy=f.readline().strip()
        if not gx.startswith('GRIDX ') or not gy.startswith('GRIDY '):raise ValueError('grid headers missing')
        x=[int(v)/dbu_per_um for v in gx.split()[1].split(',')];y=[int(v)/dbu_per_um for v in gy.split()[1].split(',')]
        if any(len(a)<2 or any(b<=c for c,b in zip(a,a[1:])) for a in [x,y]):
            raise ValueError('invalid grid coordinates')
        seen=set()
        for line in f:
            v=line.split()
            if not v or v[0]!='L' or v[1] not in ['M8','M9']:continue
            layer,j=v[1],int(v[2]);key=(layer,j)
            if j%4 or not 0<=j<len(y) or key in seen:raise ValueError('invalid/duplicate grid row')
            seen.add(key)
            if len(v[3:])!=math.ceil(len(x)/4):raise ValueError('truncated grid row')
            endj=min(j+4,len(y)-1);cy=(y[j]+y[endj])/2
            matching=[(n,r) for n,r in regions.items() if r[1]<=cy<r[3]]
            for col,cell in enumerate(v[3:]):
                i=4*col;cx=(x[i]+x[min(i+4,len(x)-1)])/2
                cap,use=map(float,cell.split('/'))
                if not math.isfinite(cap+use) or min(cap,use)<0:raise ValueError('invalid grid inventory')
                for name,r in matching:
                    if not r[0]<=cx<r[2]:continue
                    d=result[name][layer];d['capacity']+=cap;d['demand']+=use;d['windows']+=1
                    d['over_capacity_windows']+=use>cap
                    d['positive_demand_zero_capacity_windows']+=bool(use>0 and cap==0)
                    if cap>0 and (d['peak_fraction'] is None or use/cap>d['peak_fraction']):
                        d['peak_fraction']=use/cap
                        d['peak_window_rect_um']=[x[i],y[j],x[min(i+4,len(x)-1)],y[endj]]
        for layer in ['M8','M9']:
            if len([k for k in seen if k[0]==layer])!=math.ceil(len(y)/4):raise ValueError('missing layer coverage')
    for d in result.values():
        for e in d.values():e['demand_capacity_fraction']=e['demand']/e['capacity'] if e['capacity'] else None
    return result


def overflow_sources(path, regions, model):
    classes={'n_'+n:cl for n,cl,_,_ in model['buses']}
    out={n:dict(vertical_edges=0,capacity=0,usage=0,source_mentions_by_class={}) for n in regions}
    for block in Path(path).read_text().split('violation type: ')[1:]:
        if not block.startswith('Vertical'):continue
        b=re.search(r'bbox = \(\s*([\d.]+),\s*([\d.]+)\) - \(\s*([\d.]+),\s*([\d.]+)\)',block)
        c=re.search(r'capacity:(\d+) usage:(\d+)',block)
        if not b or not c:raise ValueError('unparsed congestion edge')
        x0,y0,x1,y1=map(float,b.groups());cx,cy=(x0+x1)/2,(y0+y1)/2
        nets=re.findall(r'net:(\S+)',block.split('comment:')[0])
        for name,r in regions.items():
            if not (r[0]<=cx<r[2] and r[1]<=cy<r[3]):continue
            d=out[name];d['vertical_edges']+=1;d['capacity']+=int(c[1]);d['usage']+=int(c[2])
            for net in nets:
                cl=classes.get(net.split('[')[0],'UNKNOWN');h=d['source_mentions_by_class'];h[cl]=h.get(cl,0)+1
    return out

def prospective(model, facts):
    ff=facts['facts']['DFFASRHQNx1_ASAP7_75t_R']['SS'];n=len([i for i in model['insts'] if i.kind=='station'])
    # Per station: 2x190 FIFO +379 assembly+9 valid/phase/pointer/count bits.
    raw=2*190+379+9
    protected=2*math.ceil(190/64)*72+math.ceil(379/64)*72+72
    bits=protected*n;area=bits*ff['area_um2'];clk=bits*ff['pins']['CLK']['cap_fF']
    in_bits,out_bits=20480,37120
    extra=math.ceil(in_bits/256)-math.ceil(in_bits/512)+math.ceil(out_bits/256)-math.ceil(out_bits/512)
    widths={'corridor_and_head':dict(before=637,after=388),'tile_tap':dict(before=511,after=325),
            'stack_link':dict(before=1056,after=544),'paired_spine_links':dict(before=2112,after=1088)}
    for v in widths.values():
        v.update(before_k16_nets=math.ceil(v['before']/16),after_k16_nets=math.ceil(v['after']/16),wire_cut_fraction=1-v['after']/v['before'])
    return dict(default_off=True,selection_order=['reset+two-beat instruction+256-bit links/GALS','M8 longhaul and PG away from spine with actual IR','spine widening using reticle slack','hub relocation last'],
        ports=widths,instruction=dict(word_bits=379,beat_data_bits=190,beat_control_bits=3,accept_only_two_ordered_beats=True,FIFO_entries=2,assembly_mask_bits=2,extra_issue_edges=1,per_token_extra_edges='N_instructions_on_critical_path (source count/overlap not yet bound)',
          stations=n,raw_bits_per_station=raw,protected_bits_per_station=protected,protected_added_bits=bits,gross_FF_body_um2=area,clock_pin_load_SS_fF=clk,
          logic_reserve_proxy_um2=.5*area,logic_proxy_is_not_measured=True,body_plus_proxy_mm2=1.5*area/1e6,slot_area_at_50pct_mm2=3*area/1e6,
          matched_replaced_state_debit='UNKNOWN: zero credit',added_codec_mux_timing='UNKNOWN'),
        narrow_links=dict(old_data_bits_per_direction=512,new_data_bits_per_direction=256,controls=32,
          old_B_per_cycle_each_direction=64,new_B_per_cycle_each_direction=32,
          old_bits_per_cycle_each_direction=512,new_bits_per_cycle_each_direction=256,
          serialized_extra_edges_per_layer=extra,serialized_extra_edges_per_36layer_token=36*extra,
          serialized_extra_us_at_1p2GHz=36*extra/1200,critical_path_policy='4 stacks parallel: count max stack, not sum; conservative full serialization, overlap uncredited',
          rounding_order_unchanged_required=True,partial_final_payload_and_version_ACK_source='UNKNOWN'),
        reset=dict(wires_before=64,wires_after=1,requires_per_hop_registered_reset=True,
          reset_drain_and_fanout_source='UNKNOWN; no clock wire removal credited'),
        GALS=dict(data_width=256,proposed_depth_per_direction=8,links=4,directions=2,
          raw_buffer_bits=4*2*8*(256+32),protected_buffer_bits=4*2*8*math.ceil((256+32)/64)*72,
          per_cut_forward_latency_prospective_cycles=3,per_cut_reverse_credit_prospective_cycles=3,
          source_matched_cut_count=None,finite_backpressure_and_reset_quiescence_source='UNKNOWN',
          existing_FIFO_replacement_debit='UNKNOWN: zero credit'),
        implementation_admitted=False,reason='Prospective ports/state priced; no exact caller/FIFO/reset/GALS source or loaded new codec/mux SSFF context. Do not generate a fake reduced-demand hardware PASS.')

def build_record(grid, tree, facts_path, tech_path, congestion_report):
    tech=Path(tech_path).read_text()
    if 'DATABASE MICRONS 1000' not in tech or 'k = 16' not in tech:raise ValueError('wrong physical k16 tech')
    model=F.build(tree_mode=tree);reg=windows(model)
    return dict(schema='QWEN_ROM_K16_HOTSPOT_DEMAND_MODEL_V1',tree=tree,bundle_k=16,
      pins={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [grid,facts_path,tech_path,Path(F.__file__),Path(__file__),congestion_report]},
      region_rects_um=reg,measurement_scope='raw OpenDB 4x4-gcell sums; centroid assigns boundary-crossing windows; overlapping region summaries are not additive',
      before_measured=hotspot_usage(grid,reg,1000),overflow_source_mentions=overflow_sources(congestion_report,reg,model),after_measured=None,
      after_status='UNKNOWN: no changed-source contextual route; never uniformly scale measured layer demand by wire cuts',
      prospective=prospective(model,json.loads(Path(facts_path).read_text())),
      reticle=dict(hard_mm2=858,existing_die_mm2=model['die']['mm2'],existing_slack_mm2=858-model['die']['mm2'],
         DSpark_approx_composition_mm2=823,DSpark_source_bound=False,conditional_slack_at_823_mm2=35,
         max_extra_spine_width_um_if_823_actual=35e6/model['die']['h'],widening_not_selected=True),
      clock_policy=dict(stream_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
      corridor=dict(slab_min_um=17.28,centered_pins=True,no_M2_M5_longhaul=True,max_reach_um=430.56,existing_token_link_delta_cycles=432),
      actual_protected_FIFO_codec_or_dispatcher_RTL_written=False,new_physical_launch=False)

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--congestion-report',required=True,type=Path);a.add_argument('--grid',required=True,type=Path);a.add_argument('--tree',required=True,choices=['central','banded'])
    a.add_argument('--facts',required=True,type=Path);a.add_argument('--tech',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    v=a.parse_args()
    if v.out.exists():raise SystemExit('refuse existing evidence output')
    r=build_record(v.grid,v.tree,v.facts,v.tech,v.congestion_report);v.out.parent.mkdir(parents=True,exist_ok=True);v.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'before':r['before_measured'],'after':r['after_status'],'implementation_admitted':False},indent=2))
