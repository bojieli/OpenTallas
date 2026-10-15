#!/usr/bin/env python3
"""Bounded VM canopy screen, geometry and conditional cut arithmetic only."""
import argparse,hashlib,json,math,re
from pathlib import Path
from window_audit import overlap,union_area
from bind_real import macros

def pg_free_span(lo,hi,pg):
    spans=[]
    for phase in (pg['M9_VSS_phase_um'],pg['M9_VDD_phase_um']):
        for k in range(math.floor((lo-phase)/pg['net_pitch_um'])-1,math.ceil((hi-phase)/pg['net_pitch_um'])+1):
            center=phase+k*pg['net_pitch_um'];half=pg['stripe_width_um']/2
            if center+half>lo and center-half<hi:spans.append((max(lo,center-half),min(hi,center+half)))
    end=lo;blocked=0
    for a,b in sorted(spans):blocked+=max(0,b-max(a,end));end=max(end,b)
    return dict(total_um=hi-lo,blocked_metal_um=blocked,free_metal_um=hi-lo-blocked,note='PG metal-only geometric bound; excludes wire/via clearance and new station PG. Not assigned signal tracks.')

def conflicts(insts,rect,skip=()):
    out=[]
    for i in insts:
        if i['n'] in skip:continue
        ar=overlap((i['x'],i['y'],i['x']+i['w'],i['y']+i['h']),rect)
        if ar:out.append(dict(i,intersection_um2=ar))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--obs',type=Path,required=True);ap.add_argument('--phy-lef',type=Path,required=True);ap.add_argument('--pdn',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    model=json.loads(a.model.read_text());cand=json.loads(a.candidate.read_text());obs=json.loads(a.obs.read_text());pg=cand['actual_PG_screen'];ins=model['insts'];pgfree=1-2*pg['stripe_width_um']/pg['net_pitch_um'];remaining=.75;limit=.6
    # Core M8/M9 stripes use the same exact source phases in the candidate measured phase audit.
    profiles=[]
    for response in (149,154,233):
        common=380;request=109
        source=32*response+common
        local=response+common;vertical=response+request+common
        profiles.append(dict(response_bits=response,request_bits=request,common_bits=common,aggregate_source_bits=source,local_H_bits=local,local_M9_bay_bits=vertical,fork_inside_bay_M9_bits=2*response+request+common,fork_inside_bay_required_width_um=(2*response+request+common)*.080/(pgfree*remaining*limit),neighbor_two_response_H_bits=2*response+common,neighbor_two_response_H_required_height_um=(2*response+common)*.080/(pgfree*remaining*limit),original_strip_required_H_um=source*.080/(pgfree*remaining*limit),local_H_required_height_um=local*.080/(pgfree*remaining*limit),local_M9_required_bay_width_um=vertical*.080/(pgfree*remaining*limit),new_row_H_admissible_bits=pg_free_span(16900,17029.6,pg)['free_metal_um']/.080*remaining*limit,new_row_M9_admissible_bits_min=min(pg_free_span(13284+151.2*c,13284+151.2*(c+1),pg)['free_metal_um']/.080*remaining*limit for c in range(32))))
    clkrect=(14700.,15480.,15112.536,15892.536);ckconf=conflicts(ins,clkrect,('clk_rx',))
    slots=[];unique={}
    for c in range(32):
        rect=(13294.8+151.2*c,16900.,13294.8+151.2*c+129.6,17029.6)
        cf=conflicts(ins,rect,('clk_rx',));unique.update({i['n']:i for i in cf});slots.append(dict(name='canopy_repack_candidate_'+str(c),rect_um=rect,M9_bay_um=[13284+151.2*c,13284+151.2*(c+1)],existing_conflicts=cf))
    phyb=next(iter(macros(a.phy_lef.read_text()).values()))[2];layers=re.findall(r'LAYER (M\d+)\s*;',phyb.split('\n  OBS',1)[-1]);phyinst=[i for i in ins if i['m']=='ot_hbm3e_phy']
    pganchors={};lines=a.pdn.read_text().splitlines()
    target_names={'clk_rx','sp_band_lanes_1','sp_port_tiles_1','sp_port_tiles_1_f1','tt_ctlm','tt_up4_0','pll','seq','embgw','phy_WN','phy_WS','phy_EN','phy_ES'}
    for k,line in enumerate(lines):
        if line.startswith('define_pdn_grid -macro'):
            for name in target_names:
                if '^'+name+'$' in line:
                    pganchors[name]=dict(grid=re.search(r'-name (\S+)',line).group(1),following_commands=lines[k+1:k+4])
    out=dict(schema='opentallas.qwen-tp8.canopy-screen.v1',qualified=False,adopted=False,assigned=False,sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.model,a.candidate,a.obs,a.phy_lef,a.pdn)},elements_LEF_receipt=dict(path=obs['source'],sha256=obs['sha256'],masters=obs['masters']),PHY_OBS_layers=sorted(set(layers)),PHY_instances=phyinst,source_pin_status=cand['pin_screen_status'],rejected_actual_PG_screen=pg,macro_PG_anchors=pganchors,phase_source='Candidate measured qwen_vm/band_plan audit; g8 core PDN add_pdn_stripe M8/M9 width.48 pitch9.091 offset0 startsGROUND',PG_only_free_fraction=pgfree,remaining_cut_derate=remaining,cut_limit=limit,capacity_note='PG metal removal multiplied by remaining.75 derate and.60 limit. Not PG-only capacity, not a threshold change. Source phases geometric, actual signal track phase/pin clearance/CTS/vias must be proven. Existing macro-anchored M8 stripe phases and new station PG overlay are not reduced to core PG alone.',conditional_profiles=profiles,clock_relocation_candidate=dict(old=next(i for i in ins if i['n']=='clk_rx'),new_rect_um=clkrect,hardframe_conflicts=[i for i in ckconf if i['w']*i['h']>40000],relay_reset_conflicts=[i for i in ckconf if i['w']*i['h']<=40000],clock_grant='None: existing clocks/job unchanged; relocation requires new measured insertion/delivery and all affected hop proofs'),station_repack_candidate=dict(rectangles=slots,hardframe_conflicts=[i for i in unique.values() if i['w']*i['h']>40000],relay_reset_conflicts=list(unique.values()),station_height_um=129.6,station_width_um=129.6,VM_face_gap_um=17051.04-17029.6,requires_clock_relocation=True,station_area_mm2=32*129.6*129.6/1e6,required_topology='One source response leaves S through its own151.2um M9bay; defer W/E fork below station row. No neighboring-root H collection. Current W/E candidate ports would need structural replacement and exact native proof; no pins assigned.',note='Partial constructive geometry: all existing conflicting relays/reset must be replanned, never moved in live g9; full native source and registered transport not supplied.'),M5_conditional_extra_layers='Actual g8 surrounding frame OBS stops atM7: no M6/M7 escape counted. Any M5-cap extra capacity requires real replacement LEF and PG receipt.',missing=['Actual VM-owned internal source-to-Sface registered transport; current13 remaining bays do not prove fit','Actual root master RTL/physical size and native full-key/context ABI','Instruction and request sourceplacement: upstream aggregate choke may persist','All W/E forks, returns, clock/reset/select demand and all cut/window map','Signal-track phase, clearance, actual PG-aware pin placement; all old ranges rejected','NewstationPG and overlay with macro-anchored g8 grids','Pin-to-register and <=500um staged reach, phi-R per hardened leaf, threecornerSTA','Native layer throughput and cost qualification'],finite_result='Current84.264strip and original41.04 station do not supply shared aggregate canopy. Local129.6 high row +151.2 vertical bays can pass metal-only per-root conditional233 arithmetic after clock relocation, but this is not full placement/routing feasibility.')
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(profiles=profiles,hard=len(out['station_repack_candidate']['hardframe_conflicts']),relays=len(unique),clock_conflicts=len(ckconf)),indent=1))
if __name__=='__main__':main()
