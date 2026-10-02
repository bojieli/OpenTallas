#!/usr/bin/env python3
"""Construct selected32SM gateway PG/clock cuts and join real group spans.

Exact archived coordinates, track lattices, PDN recipe and macro clock pins.
No installed CTS/placed cone prerequisite; no timing or whole-program admission.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT/'results/uarch/h4_hbm_gateway_constructive_20261002'
PIN = 'b27f430c7cd68e4dafc45dae4dadab6c795f7130678462b48bf996d5b5b72d75'
REQUEST = dict(owner=128, lease=64, provider_reference=32, canonical_row=18,
               bank=3, slice=2, epoch=16, producer_class=2, word=2, length=8,
               write=1, receipt_mask=4, tag=16, column=4, entry=4, byte_offset=18)
REVERSE = dict(owner=128, lease=64, provider_reference=32, epoch=16,
               entry=4, column=4, receipt_mask=4, ACK=2)

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def sources():
    raw = (HOME/'manifest.json').read_bytes()
    if sha(raw) != PIN: raise ValueError('manifest pin')
    out = {}
    for r in json.loads(raw)['inputs']:
        path = (HOME/r['archive']).resolve()
        if not path.is_relative_to(HOME.resolve()): raise ValueError('archive origin')
        b = path.read_bytes()
        if sha(b) != r['sha256'] or len(b) != r['bytes']: raise ValueError('source pin')
        out[r['path']] = b
    return out

def merged(intervals):
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1]+1: out[-1][1] = max(out[-1][1], hi)
        else: out.append([lo, hi])
    return out

def even_count(lo, hi):
    return max(0, hi//2 - (lo-1)//2)

def stripe_intervals(low, high, anchor, pitch, offset, width, spacing):
    # Both source VDD/VSS stripes of a pair, not a single invented strap.
    result = []
    for k in range(math.floor((low-anchor-offset)/pitch)-1,
                   math.ceil((high-anchor-offset)/pitch)+2):
        for centre in (anchor+offset+k*pitch, anchor+offset+k*pitch+width+spacing):
            result.append([centre-width/2-spacing, centre+width/2+spacing])
    return result

def constructive_cut(old, *, anchor, clock_x, width=None):
    low, high = old['span_um']
    if width is not None: high = low+width
    layers = {}
    for layer, lattice in old['layers'].items():
        origin, pitch = lattice['origin_DBU'], lattice['pitch_DBU']
        lo = max(0, math.ceil((low*1000-origin)/pitch))
        hi = math.floor((high*1000-origin)/pitch)
        # Keep the old50% reserve. Explicit PG/via/clock masks can only reduce
        # signal capacity; replacing the percentage never creates extra tracks.
        # M9 gets the conservative M7/M8 contact projection as well.
        if layer=='M6':
            intervals = stripe_intervals(low, high, anchor, 10.8, 2., .288, .096)
        else:
            intervals = stripe_intervals(low, high, anchor, 21.6, 3., .544, .096)
        if layer=='M9':
            intervals += stripe_intervals(low, high, anchor, 10.8, 2., .288, .096)
        clock_half_width = 4*pitch/1000 + .096
        intervals += [[x-clock_half_width, x+clock_half_width] for x in clock_x]
        blocked = []
        for a, b in intervals:
            a = max(lo, math.ceil((a*1000-origin)/pitch))
            b = min(hi, math.floor((b*1000-origin)/pitch))
            if a <= b: blocked.append([a, b])
        blocked = merged(blocked)
        base = even_count(lo, hi)
        extra = sum(even_count(a,b) for a,b in blocked)
        layers[layer] = dict(origin_DBU=origin, pitch_DBU=pitch,
                             track_index_extent=[lo,hi], old50pct_signal_tracks=base,
                             explicit_excluded_index_intervals=blocked,
                             PG_via_clock_extra_excluded_signal_tracks=extra,
                             signal_tracks=base-extra)
    cap = sum(r['signal_tracks'] for r in layers.values())
    return dict(owner=old.get('owner', 'gateway'), axis=old['axis'],
                coordinate_um=old['coordinate_um'], span_um=[low,high], layers=layers,
                demand_tracks=old['demand_tracks'], signal_capacity_tracks=cap,
                margin_tracks=cap-old['demand_tracks'], screen_pass=cap>=old['demand_tracks'],
                installed_PDN=False, source_recipe_constructed=True,
                via_envelope_um=[.544,.544], via_spacing_envelope_um=.096,
                via_array_must_fit_declared_envelope_before_PR=True)

def group_span_join(overlay, selected):
    required = {(c['PC'],c['rank']): c for c in selected['calls'] if c['corrected_eight_group']}
    covered = set(); rows = []
    for parent in overlay:
        tiles = parent['tiles']; inputs = []; outputs = []
        if len(tiles) != 64: raise ValueError('64 actual tiles per call')
        for ordinal,t in enumerate(tiles):
            if t['parent_template'] != parent['parent_template'] or t['source_PC'] != parent['PC']:
                raise ValueError('source parent identity')
            unsigned = {k:v for k,v in t.items() if k != 'C0_tile_template_id'}
            if sha(canonical(unsigned)) != t['C0_tile_template_id']: raise ValueError('source tile hash')
            if (t['tile_ordinal'],t['group'],t['first']) != (ordinal,ordinal//8,(ordinal%8)*128):
                raise ValueError('source group/word order')
            if t['SM'] != (t['group']*1024+t['first'])//256%32: raise ValueError('source SM partition')
            if t['native_sha256'] != selected['source_native_sha256'] or t['dispatch_sha256'] != selected['source_dispatch_sha256']:
                raise ValueError('current source pin')
            if t['destination_version'] != parent['source_writes'][0]['version']:
                raise ValueError('source destination version')
            if len(t['source_spans']) != 8: raise ValueError('eight source contributors')
            for j,s in enumerate(t['source_spans']):
                if s['source_version'] != parent['source_reads'][0]['version']:
                    raise ValueError('source input version')
                if (s['contributor'],s['source_rank'],s['bytes'],s['words'],s['shared64_beats']) != (j,8*t['group']+j,512,128,8):
                    raise ValueError('source contributor/port span')
                if s['LOAD_flat_word_first'] != (j*8+t['group'])*1024+t['first']:
                    raise ValueError('source LOAD flatten')
                inputs.append((s['LOAD_flat_word_first'],s['LOAD_flat_word_first']+128))
            if t['output_bytes'] != 512 or t['output_words'] != 128 or t['output_flat_word_first'] != t['group']*1024+t['first']:
                raise ValueError('source output span')
            outputs.append((t['output_flat_word_first'],t['output_flat_word_first']+128))
        for spans,total in [(inputs,65536),(outputs,8192)]:
            cursor=0
            for a,b in sorted(spans):
                if a!=cursor: raise ValueError('source operand overlap or gap')
                cursor=b
            if cursor!=total: raise ValueError('source operand incomplete')
        for rank in range(96):
            call = required.get((parent['PC'],rank))
            if call is None or call['template'] != parent['parent_template']: raise ValueError('actual selected call membership')
            covered.add((parent['PC'],rank))
        rows.append(dict(PC=parent['PC'],template=parent['parent_template'],
                         actual_destination_ranks=96,tiles_per_call=64,
                         LOAD_span_bytes_per_call=262144,output_span_bytes_per_call=32768,
                         shared_read64_per_call=4608,shared_write64_per_call=4608,
                         source_input_and_output_coverage=True,production_journal_coverage=False))
    if covered != set(required): raise ValueError('complete corrected call join')
    return dict(source_span_bound_calls=len(covered), remaining_calls_without_this_span_plan=len(selected['calls'])-len(covered),
                records=rows, planned_shared64_transactions=9216*len(covered),
                production_calls_with_actual_interval_upper_bounds=0,
                actual_backend_consumer_reverse_upper_bounds=None,
                arithmetic_intermediate_operand_coverage=False,
                whole_operator_interval_composition_verified=False, cost_recharged=False)

def build():
    b=sources(); load=lambda p:json.loads(b[p])
    atom=load('results/uarch/h4_hbm_atomic_source_g0_20261002/final_epoch/model.json')
    exp=load('results/uarch/h4_v1_expanded_service_20261002/private_routes_r4/model.json')
    ctx=load('results/uarch/h4_hbm_service_context_g0_20261002/final/model.json')
    pdn=b['tools/chip_assembly/tcl/pdn_sm.tcl'].decode()
    for token in ('-width {0.544} -spacing {0.096} -pitch {21.6} -offset {3.0}',
                  '-width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}', '-layers {M7 M8}', '-layers {M4 M5}'):
        if token not in pdn: raise ValueError('source PDN recipe')
    buf=next(v.decode() for k,v in b.items() if 'INVBUF_RVT_TT' in k)
    buffer_area=float(re.search(r'area\s*:\s*([.0-9]+)',buf)[1])
    header_req=sum(REQUEST.values());header_rev=sum(REVERSE.values())
    demand=2368+8*(header_req+256+header_rev+256)
    models={}
    for name,key in [('Qwen','qwen'),('DeepSeek','deepseek')]:
        old=atom['models'][name];base=exp['models'][name];service=base['service']
        fp=load('results/uarch/qwen_hbm_interface_geometry_20261002/'+key+'_floorplan_r11.json')
        controllers=[]
        for slot in old['L2_controller_slots']:
            box=list(slot['bbox_um']);box[2]=box[0]+1024
            original=dict(slot['cut'],demand_tracks=demand)
            cut=constructive_cut(original,anchor=box[0],clock_x=[box[0]+512],width=1024)
            region=next(r for r in fp['regions'] if r['name']=='l2_'+['s0','s1','n0','n1'][slot['stack']])
            conflicts=[]
            for m in fp['macro_placements']:
                if not m['name'].startswith(region['name']+'_m'): continue
                halo=[m['x']-4,m['y']-4,m['x']+174.744+4,m['y']+70.47+4]
                if max(halo[0],box[0])<min(halo[2],box[2]) and max(halo[1],box[1])<min(halo[3],box[3]): conflicts.append(m['name'])
            contained=region['x']<=box[0] and box[2]<=region['x']+region['w'] and region['y']<=box[1] and box[3]<=region['y']+region['h']
            incremental_bits=8*(header_req+header_rev+1024-256-64)
            required=slot['required_footprint_um2']+2*(incremental_bits*.2916+8*(64+32)*4*.3)
            controllers.append(dict(stack=slot['stack'],bbox_um=box,footprint_um2=required,
                                    capacity_um2=1024*64,macro_halo_conflicts=conflicts,
                                    contained=contained,cut=cut,fit=contained and not conflicts and required<=1024*64 and cut['screen_pass']))
        clocks=[];cuts=[]
        leaves=service['extra_register_bits_proposed']+old['source_body_pipeline']['registered_bits']+128+80+130
        if name=='DeepSeek': leaves+=5320+8
        # Fanout8 is a selected analytical topology, never an SS slew proof.
        buffers=math.ceil((leaves-1)/7);footprint=2*buffers*buffer_area
        bank_footprint=.30*footprint/16;central=.70*footprint
        free_bank=min(s['capacity_footprint_um2']-s['required_footprint_um2'] for s in service['logic_slots'])
        used=old['SM_additional_local_GU_mux_footprint_um2']+old['source_body_pipeline']['footprint_um2_per_SM']+old['DS_frame_controller_footprint_um2_per_SM']
        free_central=old['SM_remaining_strip_capacity_um2']-used
        for sm in base['SM_placements']:
            ox,oy=sm['service_origin_um'];root=[ox+1100,oy+2100]
            macro_endpoints=[]
            source_macros=[(macro,ox,oy) for macro in service['macro_placements']]
            if name=='DeepSeek':
                source_macros += [(macro,0,0) for macro in old['DS_result_macros'] if macro['SM']==sm['SM']]
            for macro,mx,my in source_macros:
                master=macro['master'];lef=next(v.decode() for k,v in b.items() if k.endswith('/'+master+'.lef'))
                match=re.search(r'PIN clk\s.*?LAYER (M\d+) ;\s+RECT ([.0-9]+) ([.0-9]+) ([.0-9]+) ([.0-9]+)',lef,re.S)
                if not match: raise ValueError('actual clock pin geometry')
                x,y,x2,y2=map(float,match.groups()[1:]);body=macro['body_bbox_um']
                macro_endpoints.append(dict(macro=macro['name'],master=master,clock_pin_layer=match[1],
                                            clock_pin_bbox_um=[mx+body[0]+x,my+body[1]+y,mx+body[0]+x2,my+body[1]+y2]))
            clocks.append(dict(SM=sm['SM'],stream_source_port='clk',GHz=1.2,root_um=root,
                               bank_roots_um=[[ox+450*(bank%4)+224,oy+508*(bank//4)+312] for bank in range(16)],
                               macro_clock_endpoints=macro_endpoints,planned_clock_sink_upper=leaves,
                               max_fanout=8,selected_buffer='BUFx24_ASAP7_75t_R',buffer_count=buffers,
                               buffer_area_corner_scope='TT library geometric area only; no timing credit',
                               incremental_buffer_footprint_um2=footprint,bank_footprint_um2_each=bank_footprint,
                               central_footprint_um2=central,area_fit=bank_footprint<=free_bank and central<=free_central,
                               SS_slew_and_clock_pin_cap_bound=None,installed_CTS=False))
            local=old['SM_gateway_endpoint_cuts'][sm['SM']]
            clock_taps=[e['clock_pin_bbox_um'][0] for e in macro_endpoints]
            cuts.append(constructive_cut(local,anchor=ox,clock_x=[root[0]]+clock_taps))
            for c in service['bank_cuts']:
                shift=ox if c['axis']=='X' else oy;other=oy if c['axis']=='X' else ox
                d=dict(c,span_um=[x+shift for x in c['span_um']],coordinate_um=c['coordinate_um']+other,
                       owner='SM'+str(sm['SM'])+'/'+c['owner'])
                bank=int(re.match(r'bank(\d+)/',c['owner'])[1])
                if name=='DeepSeek' and bank<8:
                    d['demand_tracks']+=640
                tap_axis=0 if c['axis']=='X' else 1
                taps=[e['clock_pin_bbox_um'][tap_axis] for e in macro_endpoints]
                bank_roots=[shift+450*j+224 for j in range(4)] if tap_axis==0 else [shift+508*j+312 for j in range(4)]
                cuts.append(constructive_cut(d,anchor=shift,clock_x=bank_roots+taps))
        models[name]=dict(SMs=32,full_reserved_die_mm2=old['full_reserved_die_mm2'],
                          L2_controller_slots=controllers,distributed_gateway_and_bank_cuts=cuts,
                          clock_source_allocations=clocks,additional_clock_buffer_footprint_mm2_die=32*footprint/1e6,
                          source_geometry_fit=all(x['fit'] for x in controllers) and all(c['screen_pass'] for c in cuts) and all(c['area_fit'] for c in clocks),
                          old_controller_width_um=512,selected_controller_width_um=1024,
                          expansion_inside_existing_L2_region=True,clock_or_ns_delta=None)
    overlay=json.loads(gzip.decompress(b['results/uarch/h4_c0_group_operand_tiles_20261002/r2/operand_span_overlay.json.gz']))
    selected=json.loads(gzip.decompress(b['results/uarch/h4_hbm_selected_intervals_20261002/DS_selected_r1/selected_calls.json.gz']))
    spans=group_span_join(overlay,selected)
    return dict(schema='opentallas.HBM.gateway-constructive-cuts.v1',models=models,source_group_span_join=spans,
                selected_request_metadata_bits=header_req,selected_reverse_metadata_bits=header_rev,
                request_fields=REQUEST,reverse_fields=REVERSE,L2_endpoint_composed_tracks=demand,
                actual_constructed_clock_PG_via_reservation=True,old50pct_track_reserve_retained=True,
                current_installed_endpoint_not_a_G0_prerequisite=True,installed_CTS_not_a_G0_prerequisite=True,
                engine_build_allowed=False,whole_operator_interval_composition=None,
                SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
                automatic_latency_delta=False,hardware_admitted=False,
                blockers=['actual full operator intervals and external upper bounds',
                          'macro clock pin capacitance and SS clock slew bounds; TT area is not timing',
                          'verify via arrays fit constructor envelope before PR'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    result=build()
    artifacts={'model.json.gz':gzip.compress((json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)}
    artifacts['manifest.json']=(json.dumps(dict(input_pin=PIN,tool_sha256=sha(Path(__file__).read_bytes()),output_sha256={k:sha(v) for k,v in artifacts.items()}),sort_keys=True,indent=2)+'\n').encode()
    if not args.verify: args.out.mkdir(parents=True,exist_ok=False)
    for name,raw in artifacts.items():
        if args.verify:
            if (args.out/name).read_bytes()!=raw: raise ValueError('replay '+name)
        else: (args.out/name).write_bytes(raw)
    print(json.dumps({n:dict(fit=m['source_geometry_fit'],cuts=len(m['distributed_gateway_and_bank_cuts'])) for n,m in result['models'].items()},sort_keys=True))

if __name__=='__main__': main()
