#!/usr/bin/env python3
"""Read-only constructive Engram coverage/state intake; no owner generator run.

Uses committed JSON/source blobs, independently derives every coordinate and
state count. It supplies no compiler, physical cost, clock/power or fit credit.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

PIN='9fbe2693ab92ad534075a18830b2e57f68e26fb0'
CLOCK_PIN='c62c7e80c75eff1d377cbf46e76c453cf79753f4'
BASE='results/quality/w16_engram_rom_constructive_home_20261001'
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def require(x,msg):
    if not x:raise ValueError(msg)
def close(a,b,msg):require(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-7),msg)

def inputs():
    hashes={};versions={}
    for version in ['', '/v2','/v3','/v4','/final']:
        name=BASE+version+'/candidate.json';raw=blob(PIN,name);listed=blob(PIN,BASE+version+'/SHA256SUMS').decode().split()
        require(listed==[sha(raw),'candidate.json'],'version manifest '+version);hashes[name]=sha(raw);versions[version]=json.loads(raw)
        require(not versions[version]['composed_admission'],'historical candidate admission')
    d=versions['/final'];invraw=blob(PIN,BASE+'/clock_hold_inventory.json');i=json.loads(invraw);hashes[BASE+'/clock_hold_inventory.json']=sha(invraw)
    require(i['candidate_path']==BASE+'/final/candidate.json' and i['candidate_sha256']==hashes[BASE+'/final/candidate.json'],'clock inventory final binding')
    require(sha(blob(PIN,'tools/engram_rom_constructive_home.py'))==d['generator_sha256'],'candidate generator pin')
    require(sha(blob(CLOCK_PIN,'tools/engram_rom_clock_inventory.py'))==i['generator_sha256'],'clock generator pin')
    data={}
    for name,p in d['source_pins'].items():
        raw=blob(p['commit'],p['path']);require(sha(raw)==p['sha256'],'source pin '+name);data[name]=raw.decode() if name=='model' else json.loads(raw)
    require(d['supersedes_preliminary']['sha256']==hashes[BASE+'/candidate.json'],'preserved preliminary hash')
    return d,i,data,hashes

def xy(local):
    # Independent deinterleave of the seven x/y bit pairs, MSB to LSB.
    x=y=0
    for bit in range(6,-1,-1):x=(x<<1)|((local>>(2*bit+1))&1);y=(y<<1)|((local>>(2*bit))&1)
    return x,y

def coverage(d,demand):
    homes=d['homes'];cols=demand['ROM_candidate']['columns'];require(len(homes)==96 and len(cols)==48,'96home/48column count')
    require([h['home_id'] for h in homes]==list(range(96)),'home identity order')
    coordinates=[xy(m) for m in range(16384)]
    require(set(coordinates)=={(x,y) for x in range(128) for y in range(128)},'leaf coordinate bijection')
    for m,(x,y) in enumerate(coordinates):
        inverse=sum(((x>>(6-b))&1)<<(13-2*b) | ((y>>(6-b))&1)<<(12-2*b) for b in range(7))
        require(inverse==m,'coordinate inverse')
    digest=hashlib.sha256();count=0;rows=0
    for ordinal,c in enumerate(cols):
        n=(c['rows']*8+4095)//4096;require(n==c['macros'] and 16384<n<=32768,'actual macro partition')
        for half in [0,1]:
            h=homes[2*ordinal+half];start=half*16384;end=min(start+16384,n)
            require(h['layer']==c['layer'] and h['column']==c['column'] and h['column_macro_start']==start and h['column_macro_end_exclusive']==end,'column range identity')
            require(h['actual_macros']==end-start and h['padded_slots']==16384 and h['unused_slots']==16384-(end-start),'no missing/duplicate/tail macros')
            require(h['candidate_exclusive_die_id']==h['home_id'] and h['physical_assignment'] is None,'proposal not physical assignment')
            for m in range(start,end):
                local=m-start;x,y=coordinates[local]
                require(2*ordinal+(m>>14)==h['home_id'] and (m&16383)==local,'every macro inverse coverage')
                digest.update(f'{h["home_id"]},{m},{local},{x},{y}\n'.encode());count+=1
            reps=d['coordinate_inventory']['representatives'][h['home_id']]
            require(reps['home_id']==h['home_id'] and reps['first_local_xy']==list(coordinates[0]) and reps['last_local_xy']==list(coordinates[end-start-1]),'coordinate representatives')
        rows+=c['rows']
    require(count==1500067==d['actual_macro_count'] and rows==768022850,'whole exact coverage')
    require(digest.hexdigest()==d['coordinate_inventory']['all1500067_home_macro_local_x_y_tuple_SHA256'],'all-coordinate digest')
    return dict(actual_macros=count,proposed_homes=96,prime_columns=48,leaf_slots_per_home=16384,padded_slots_total=96*16384,unpopulated_slots_total=96*16384-count,coordinate_SHA256=digest.hexdigest(),all_leaf_inverse_mappings=True)

def tree_counts(d,data):
    macro=next(r for r in data['depth']['rows'] if r['macro']=='ot_rom_4096x274_m8')
    planning_width=macro['width_um'];planning_height=(4096*274/75e6)*1e6/planning_width
    require(d['coordinate_inventory']['planning_reservation_macro_width_um']==planning_width,'planning width source')
    close(d['coordinate_inventory']['planning_reservation_macro_height_um'],planning_height,'planning height source')
    totals={}
    for name,v in d['variants'].items():
        px=planning_width+16;py=(planning_height if name=='planning_75Mbit' else macro['height_um'])+16
        require(len(v['geometry']['levels'])==14,'tree levels')
        stage_sum=edges_total=path_cycles=0;link_length=0
        for depth,row in enumerate(v['geometry']['levels']):
            edge_count=2**(depth+1);span=128//(2**(depth//2));length=span*(px if depth%2==0 else py)/4;stages=max(1,math.ceil(length/504))
            require(row['level']==depth and row['edges']==edge_count and row['wire_stages']==edge_count*stages and row['max_path_wire_stages']==stages,'tree edge/stage count')
            close(row['length_um'],edge_count*length,'tree length');close(row['max_edge_um'],length,'tree max length')
            stage_sum+=edge_count*stages;edges_total+=edge_count;path_cycles+=stages;link_length+=edge_count*length
        require(edges_total==32766==v['geometry']['total_edges'] and stage_sum==v['geometry']['edge_wire_stage_sum'],'tree aggregate')
        require(path_cycles==v['geometry']['path_wire_cycles']==v['geometry']['max_path_wire_cycles'],'tree path stage count')
        close(v['geometry']['dedicated_link_length_um'],link_length,'aggregate link length')
        close(v['geometry']['grid_area_mm2'],128*px*128*py/1e6,'grid area reservation')
        base=3*16383*(51+288)+2*16383;extra=(stage_sum-32766)*(51+288)
        mux=16383*288;demux=2*16383*51
        require(base==v['base_tree_FF_bits_per_home'] and extra==v['extra_wire_FF_bits_per_home'],'tree FF count')
        require(mux==v['response_mux2_bit_equivalents_per_home'] and demux==v['request_demux_gate_bit_equivalents_per_home'],'selectedmux/demux count')
        require(v['local_first_beat_cycles_proposed']==2*path_cycles+28+1 and v['local_complete_row_cycles_proposed']==2*path_cycles+28+1+7,'conditional local cycles')
        totals[name]=dict(tree_FF_per_home=base+extra,response_MUX2_per_home=mux,request_AND2_per_home=demux,wire_path_cycles=path_cycles,grid_area_mm2=v['geometry']['grid_area_mm2'])
    return totals

def state(d,i,trees):
    rows=i['homes'];require(len(rows)==96,'full state home count');ff=mux=response=demux=0;captures=0
    tree=trees['planning_75Mbit']
    for h,r in zip(d['homes'],rows):
        capture=h['actual_macros']*(274+24);storage=tree['tree_FF_per_home']+capture+2*304*8+64
        require(r['home_id']==h['home_id'] and r['actual_macros']==h['actual_macros'],'inventory home binding')
        require(r['tree_wire_and_node_control_FF_bits']==tree['tree_FF_per_home'] and r['macro_and_tag_capture_FF_bits']==capture,'tree/capture state')
        require(r['double_packet_FIFO_FF_bits']==4864 and r['root_control_FF_bits']==64 and r['total_storage_FF_bits']==storage,'all FIFO/control state')
        require(r['held_state_feedback_MUX2_bits']==storage and r['selected_response_MUX2_bits']==tree['response_MUX2_per_home'] and r['request_demux_AND2_bits']==tree['request_AND2_per_home'],'one held feedback MUX per FF')
        require(r['feedback_and_select_NAND2_if_four_per_MUX2']==4*(storage+tree['response_MUX2_per_home']) and r['request_demux_NAND2_if_two_per_AND2']==2*tree['request_AND2_per_home'],'NAND equivalents')
        require(r['all_storage_clock_Hz']==1200000000 and r['all_macro_clock_Hz_without_qualified_stop']==1200000000 and not r['physical_clock_enable'] and not r['idle_clock_credit'],'no idle clock credit')
        require(r['exact_clock_buffer_topology'] is None and r['clock_route_length_um'] is None and r['root_to_PHY_additional_stage_state'] is None and r['CRC_framing_arbitration_state'] is None,'unqualified clock/endpoint costs')
        ff+=storage;mux+=storage;captures+=capture;response+=tree['response_MUX2_per_home'];demux+=tree['request_AND2_per_home']
    require(ff==2073575326==i['aggregate_FF_bits'] and mux==ff==i['aggregate_feedback_MUX2_bits'] and response==i['aggregate_response_MUX2_bits'],'aggregate state totals')
    require(d['full_cost']['planning_75Mbit']['all_capture_FF_bits']==captures and d['full_cost']['planning_75Mbit']['all_tree_and_wire_FF_bits']==96*tree['tree_FF_per_home'],'candidate state crosscheck')
    return dict(tree_wire_and_node_control_FF=96*tree['tree_FF_per_home'],macro_tag_capture_FF=captures,double_packet_FIFO_FF=96*4864,root_control_FF=96*64,total_FF=ff,feedback_MUX2=mux,response_MUX2=response,request_AND2=demux,feedback_plus_response_NAND2_equivalents=4*(mux+response),request_NAND2_equivalents=2*demux,clock_Hz=1200000000,clock_or_idle_stop_credit=False)

def admission(d,i,data):
    rejected=d['rejected_48_home_alternative'];limit=float(data['geometry_envelope']['supplied_geometry_envelope']['area_limit_mm2']);raw=max(c['macros'] for c in data['demand']['ROM_candidate']['columns'])*(4096*274/75e6)
    close(rejected['raw_macro_planning_area_mm2'],raw,'48home raw area');require(rejected['owner_field_bound_mm2']==limit and raw>limit and rejected['status'].startswith('FAIL_'),'48home failure preserved')
    require(d['verdict']=='CAPACITY_AND_GRAPH_CONSTRUCTED_NOT_ADMITTED' and not d['composed_admission'] and not d['physical_fit_proven'] and d['physical_home_assignments'] is None and d['headline_rate'] is None,'96home NOT accepted')
    require(d['L1_generated_source'] is None and i['L1_generated_source'] is None,'L1 NULL')
    require(not i['composed_admission'] and i['power_W'] is None and not i['RTL_or_PnR_runs'],'inventory NOT accepted')
    return dict(home48_status=rejected['status'],home48_raw_macro_mm2=raw,owner_field_bound_mm2=limit,home96_preliminary_max_area_mm2=d['full_cost']['planning_75Mbit']['max_allocated_home_area_mm2'],home96_area_accepted=False,L1=None,physical_assignment=None,power_W=None)

def review():
    d,i,data,hashes=inputs();mapping=coverage(d,data['demand']);trees=tree_counts(d,data);inventory=state(d,i,trees);gate=admission(d,i,data)
    pins={}
    for p in ['tools/qc_engram_constructive_intake.py','tests/test_qc_engram_constructive_intake.py']:
        raw=blob('HEAD',p);require((ROOT/p).read_bytes()==raw,'review executed source pin');pins[p]=sha(raw)
    return dict(schema='opentallas.qc.engram-constructive-independent-review.v1',verdict='PASS_BOUNDED_DECLARED_MAPPING_AND_STATE_NOT_ADMISSION',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),owner_candidate_commit=PIN,clock_generator_commit=CLOCK_PIN,review_source_pins=pins,artifact_hashes=hashes,historical_source_pins=d['source_pins'],mapping=mapping,tree_counts=trees,state_inventory=inventory,admission=gate,limits=['All tuples are constructive logical/reservation coordinates, not legal floorplans/pin escape.','2073575326FF is the declared full tree/capture/packetFIFO/rootcontrol inventory with1feedbackMUX each; endpointPHY/CRC/arbitration state and segmented ready-credit lowering still need typed cost provider.','329mm2 preliminary screen excludes held feedbackMUX/CTS/reset and PHY; generic data track arithmetic is not routed availability.','Confucius owns typedFF/MUX/reset/power/clock provider; Avic and Turing own existing costreview; Ram owns whole area/ports/routes/calendar join.'],coordination='Read-only intake only; no owner generator/code rewrite, cost campaign, checkpoint read, image/compiler/RTL/PnR job.',physical_owner=None,jobs=[],checkpoint_reads=0,new_images=0,adoption=False,QC_NAM='original FAIL unchanged')

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--out',type=Path);cli.add_argument('--archive',type=Path);a=cli.parse_args();require(not(a.out and a.archive),'one mode');r=review()
    if a.archive:
        old=json.loads(a.archive.read_text());require({k:v for k,v in r.items() if k!='source_commit'}=={k:v for k,v in old.items() if k!='source_commit'},'archive replay')
    if a.out:
        require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'clean source');require(not a.out.exists(),'immutable output');a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(verdict=r['verdict'],macros=r['mapping']['actual_macros'],homes=96,FF=r['state_inventory']['total_FF'],feedback_MUX2=r['state_inventory']['feedback_MUX2'],L1=None,admitted=False)))
if __name__=='__main__':main()
