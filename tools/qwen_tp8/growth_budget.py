#!/usr/bin/env python3
"""Source-bound merged-die area/corridor and root bandwidth analysis; no fit qualification."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
from window_audit import union_area

def category(m):
    if m.startswith(('qfd_rly','qkd_rly','qfd_rst_rep')):return 'relay_reset'
    if m=='qfd_tile_nk':return 'ROM_tile_frames'
    if m.startswith('qfd_cst'):return 'ROM_stations'
    if m.startswith('qkd_') or m=='ot_hbm3e_phy':return 'KV_and_HBM_frames'
    if m.startswith(('qfd_io','ot_qfd_serdes')):return 'IO_frames'
    return 'other_ROM_and_shared_system_frames'

def measure(path,w,h):
    raw=path.read_bytes();x=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw);rows=collections.defaultdict(lambda:dict(count=0,area_mm2=0));non=[];mst=collections.Counter()
    for i in x['insts']:
        c=category(i['m']);rows[c]['count']+=1;rows[c]['area_mm2']+=i['w']*i['h']/1e6;mst[i['m']]+=i['w']*i['h']/1e6
        if c!='relay_reset':non.append((i['x'],i['y'],i['x']+i['w'],i['y']+i['h']))
    area=w*h/1e6;union=union_area(non,(0,0,w,h))/1e6
    tile=next(i for i in x['insts'] if i['m']=='qfd_tile_nk')
    return dict(source=str(path),sha256=hashlib.sha256(raw).hexdigest(),width_um=w,height_um=h,die_mm2=area,reticle_axes_fit=w<=33000 and h<=26000,reticle_area_fit=area<=858,tile_frame_um=[tile['w'],tile['h']],category_frame_sums=dict(rows),nonrelay_frame_sum_mm2=sum(i['area_mm2'] for c,i in rows.items() if c!='relay_reset'),nonrelay_frame_union_mm2=union,geometric_outside_nonrelay_frames_mm2=area-union,nonrelay_frame_union_fraction=union/area,by_master_frame_sum_mm2=dict(mst))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--g5',type=Path,required=True);ap.add_argument('--g8',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    g5=measure(a.g5,32988.384,26017.2);g8=measure(a.g8,31785.696,25891.92)
    density=.5/.048+.75/.064+.75/.080
    growth=dict(tile_large_frame_delta_mm2=g5['category_frame_sums']['ROM_tile_frames']['area_mm2']-g8['category_frame_sums']['ROM_tile_frames']['area_mm2'],SU_lane_only_extra_mm2=3.48-777.576*2058.456/1e6,slab_children_extra_mm2=48*.300259-6*777.576*1840.296/1e6,band_candidate_delta_mm2=3*(820.8*1015.2-777.576*1131.816)/1e6)
    growth['sum_delta_mm2']=sum(growth.values())
    growth['unchanged_outside_frame_die_mm2']=g8['die_mm2']+growth['sum_delta_mm2']
    growth['reclaim_required_for_858_mm2']=growth['unchanged_outside_frame_die_mm2']-858
    growth['updated_nonrelay_frame_sum_mm2']=g8['nonrelay_frame_sum_mm2']+growth['sum_delta_mm2']
    growth['note']='Area accounting scenario, NOT constructive placement. SU omits vreduce and all slots omit new adapters/channels; band candidate not qualified; use large tile model frame, not claim that child lower bound mandates it.'
    corridors=dict(g8_pitch_um=394.848,g8_tile_frame_um=311.016,station_width_um=52.68,g8_pitch_minus_tile_and_station_um=394.848-311.016-52.68,g5_pitch_um=419.904,g5_tile_frame_um=362.856,g5_pitch_minus_tile_and_station_um=419.904-362.856-52.68,candidate_tile_width_um=399.6,candidate_at_g5_pitch_residual_um=419.904-399.6-52.68,minimum_pitch_for_candidate_at_4p344_residual_um=456.624,minimum_pitch_for_candidate_plus_20um_open_channel_um=399.6+52.68+20,note='Residual is geometric sum, not certified channel; any intentional pin-aligned abutment must be stated separately.')
    bandwidth={str(bits):dict(bits_per_edge=bits,min_open_channel_um_at_060=bits/(density*.6),min_M8_only_um_at_060=bits/(.75/.080*.6)) for bits in (128,256,675,4096,8192)}
    out=dict(schema='opentallas.qwen-tp8.growth-budget.v1',qualified=False,baseline_SPEC=dict(width_mm=31.17,height_mm=25.78,reported_die_mm2=803.7,modeled_slot_mm2=481.3,modeled_slot_fraction=481.3/803.7,note='Historical generated frame budget with311um tile and116.7mm2 modeledKV; never placed stdcell utilization.'),g5=g5,g8=g8,g9=dict(state='generation/live; real-bound die route and final geometry not verified'),g5_minus_g8=dict(die_mm2=g5['die_mm2']-g8['die_mm2'],tile_frame_mm2=g5['category_frame_sums']['ROM_tile_frames']['area_mm2']-g8['category_frame_sums']['ROM_tile_frames']['area_mm2'],other_nonrelay_frame_mm2=g5['nonrelay_frame_sum_mm2']-g8['nonrelay_frame_sum_mm2']-(g5['category_frame_sums']['ROM_tile_frames']['area_mm2']-g8['category_frame_sums']['ROM_tile_frames']['area_mm2'])),closed_child_lower_bounds=dict(tile_children_um2=334169,tile_ctl_assumption_um2=66000,tile_768_mm2=(334169+66000)*768/1e6,SU64_lane_only_mm2=3.48,SU_vreduce_mm2=None,slab_48_groups_children_mm2=48*.300259,slab_six_slot_mm2=6*1.431,band_compact_candidate_um=[820.8,1015.2],note='Child-area lower bounds omit channels,clock/reset,pin adapters and packing loss; control66k is current stream estimate; compact band candidate unqualified.'),growth_accounting_scenario=growth,corridor_geometry=corridors,root_bandwidth=dict(quad_root_count=32,source_bits_per_edge=4096,half_endpoint_count=64,branch_bits_per_edge=8192,column_stream_candidate_bits=675,tile_count=768,GT=3072,column_count=48,row_count=16,density_usable_tracks_per_um=density,capacity_models=bandwidth,note='Open-channel M4/M6/M8 horizontal or M5/M7/M9 vertical tracks with PDN derates; numbers are aggregate cuts only if all branches cross same cut. Branch duplication/fanout must be spatially distributed; traffic/cycle is not wire demand until topology maps it.'),historical_split=dict(ROM_dies=8,KV_dies=8,HBM_stacks=32,package_description='2 ROM +2KV dies +8stacks (historical)',crossing_cycles_per_layer_historical=455,extra_cycles_36_layers_historical=16380,native_qualification=False),unknowns=['g9 final geometry and real-view die GRT/STA','all grown slot geometries and20um channels','native indexed-cache full-layer cycles versus immutable price','split D2D packetization/credit/mutants/serializer throughput','package shoreline/bump map/thermal/yield and cost','crossing cycles under current production TP8 issue stream','minimum separate KV/system bounding shape from real required slots'])
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:out[k] for k in ('g5_minus_g8','root_bandwidth')},indent=1))
if __name__=='__main__':main()
