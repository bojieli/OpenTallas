#!/usr/bin/env python3
"""Export the actual mapped S81 capture object and typed parent boundary loads."""
import argparse
from collections import Counter
from decimal import Decimal
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/physical/dsrom_s81_capture_native_map_20261004/r2_PASS'
TYPES={'DFFASRHQNx1_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','NAND2x1_ASAP7_75t_R'}
def require(v,msg):
    if not v:raise ValueError(msg)
def digest(data):return hashlib.sha256(data).hexdigest()
def summarize(module,terminal,areas):
    cells=module['cells'];counts=Counter(c['type'] for c in cells.values())
    require(set(counts)==TYPES,'unknown native cell')
    require(dict(counts)==terminal['actual_cell_census'],'terminal native census mismatch')
    clock=module['ports']['clk']['bits'];reset=module['ports']['rst_n']['bits']
    clocks=resets=sets=0
    reset_pins=Counter();constant_pins=Counter()
    for c in cells.values():
        if c['type'].startswith('DFF'):
            require(c['connections']['CLK']==clock,'non-source clock on mapped FF');clocks+=1
            if c['type'].startswith('DFFASR'):
                rp,sp=c['connections']['RESETN'],c['connections']['SETN']
                require((rp==reset and sp==['1']) or (sp==reset and rp==['1']),'non-source cold-reset pair on mapped FF')
                reset_pins['RESETN' if rp==reset else 'SETN']+=1
                constant_pins['SETN' if rp==reset else 'RESETN']+=1
                resets+=1;sets+=1
    require(clocks==16271 and resets==7567,'clock/reset source census')
    require(module['ports']['r_valid']['bits'].__len__()==128 and len(module['ports']['vm_accept']['bits'])==128,'root/grant width')
    area=sum(Decimal(v)*Decimal(str(areas[k]['liberty_area_raw'])) for k,v in counts.items())
    return {'cell_counts':dict(sorted(counts.items())),'cells':sum(counts.values()),'FF_cells':clocks,
        'actual_cell_area_um2':float(area),'cell_only_50pct_reservation_mm2':float(area*2/Decimal(1000000)),
        'source_clock':{'port':'clk','net_bits':clock,'native_CLK_sinks':clocks,'physical_buffers_or_CTS_included':False},
        'source_cold_reset':{'port':'rst_n','net_bits':reset,'native_async_sinks':resets,'native_sink_pin_counts':dict(sorted(reset_pins.items())),'release_or_distribution_closed':False},
        'required_constant_supply':{'native_constant_one_sinks':sets,'native_constant_pin_counts':dict(sorted(constant_pins.items())),'physical_TIEHI_cells_present':0,'positive_tie_and_route_cost_pending':True}}

def build():
    graph=json.loads((BASE/'inputs/return_connectivity.json').read_text())
    require(graph['pairs']==2417 and graph['RD']==64 and len(graph['nodes'])==5090 and len(graph['roots'])==128 and graph['no_READY'],'selected return source changed')
    require(sum(x['unilateral'] for x in graph['nodes'])==384,'retained unary node omission')
    t=json.loads((BASE/'terminal.json').read_text());p=json.loads((BASE/'preparation.json').read_text());a=json.loads((BASE/'library_cell_areas.json').read_text())
    require(t['exit_code']==0 and t['source_unchanged'] and not t['unmapped_cells'],'mapping not terminal native PASS')
    raw=gzip.decompress((BASE/'mapped.json.gz').read_bytes());require(digest(raw)==t['artifacts_sha256']['mapped.json'],'mapped JSON hash')
    for name in ('mapped.v','mapped.log'):
        require(digest(gzip.decompress((BASE/(name+'.gz')).read_bytes()))==t['artifacts_sha256'][name],name+' hash')
    for name in ('map.ys','process.json','preparation.json'):
        require(digest((BASE/name).read_bytes())==t['artifacts_sha256'][name],name+' hash')
    require(p['parameters']=={'ENABLE':1,'ROOTS':128,'CAPACITY':1,'VM_AW':19,'VM_ALWAYS_ACCEPT':1},'selected parameter mismatch')
    for v in a.values():require(p['source_sha256'][v['library']]==v['library_sha256'],'library identity')
    n=json.loads(raw)['modules']['ot_dsrom_rd64_vm_capture'];actual=summarize(n,t,a)
    ports={k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in n['ports'].items()}
    edges=[]
    for src,dst,bits in [('rv','r_valid',128),('re','r_error',128),('rrow','r_row',2048),('rpos','r_pos',384),('rfp32','r_fp32',4096),('rbf16','r_bf16',2048)]:
        require(ports[dst]=={'direction':'input','bits':bits},'native return/capture ABI')
        edges.append({'from_module':'ot_v41_return_rd64_pruned','from_port':src,'to_module':'ot_dsrom_rd64_vm_capture','to_port':dst,'bits':bits,'READY':False,'root_order':'unchanged0..127'})
    return {'schema':'opentallas.dsrom.S81.actual-native-capture.v1','source_commit':t['source_commit'],
        'selected_parent_commit':p['source_parent_commit'],'selected':{'S':81,'NP':2417,'BF':519,'RD':64,'return_nodes':5090,'unilateral':384,'roots':128},
        'actual_capture':actual,'ports':ports,'root_capture_interface':edges,
        'actual_return_source_classes':{'binary_RD64':len(graph['nodes'])-384,'unilateral_RD64_retained':384,'ROOTD128':128,'no_tree_regeneration':True},
        'native_VM_grant_cone':{'owner':'Nash','included':False,'accept_port':'vm_accept','accept_bits':128,'physical_ports_proven':False,'provider_and_postNBA_visibility_required':True},
        'Clock_C_join':{'stream_MHz':1200,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'max_region_dimension_mm':5.25,
            'native_object_has_one_clock_port':True,'mapped_clock_is_actual_parent_clk':True,'M8_M9_shielded_trunk_local_CTS_filtered_rail_required':True,
            'whole_object_clock_or_reset_route_closed':False,'no_clock_mesh':True,'extra_mapping_latency_cycles':0},
        'area_composition':{'charge_actual_component_once':True,'old_raw_FF_proxy_not_a_logic_fit':True,'no_existing_row_register_credit':True,
            'native_return_binary_object_reuse':'Existing complete RD64 native mapping; source-independent primitive object, no S82 floorplan reuse',
            'unilateral_count_preserved':384,'unilateral_or_root_abstract_timing_qualified':False,
            'selected_capture_physical_home':None,'disjoint_fixed_residual_containment_closed':False,
            'clock_reset_ties_PG_routes_hold_cells_not_in_native_body':True},
        'job':{'terminal':'PASS_EXIT0','unit':'dsrom-s81-capture-native-map-r2.service','host':'5.199.165.104','MainPID':0,'former_yosys_PID':2177765,'elapsed_s':t['elapsed_s'],'estimated_peak_GiB':16,'reserve_GiB':150,'no_runtime_caps':True},
        'phase_latency':'Retains source-model capture/commit and two enclosing idle edges; mapping itself inserts no cycles. Actual executed phase count/runtime supplied by Arch, not all checkpoint declarations.',
        'tool_sha256':digest(Path(__file__).read_bytes()),
        'inputs_sha256':{name:digest((BASE/name).read_bytes()) for name in ('mapped.json.gz','mapped.v.gz','mapped.log.gz','library_cell_areas.json','terminal.json','preparation.json','process.json','map.ys','resources.txt','inputs/return_connectivity.json','inputs/clock_option_C.json')},
        'synthesis_check':'PASS_ZERO_PROBLEMS','native_mapping_PASS':True,'HDL_equivalence_qualified':False,'physical_fit':False,'SSFF_qualified':False,'runtime_or_full_token_qualified':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    result=build();text=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.verify:require((BASE/'native_object.json').read_text()==text,'native object replay differs')
    if args.out:args.out.write_text(text)
    print(json.dumps({'native_mapping_PASS':True,'cells':result['actual_capture']['cells'],'FF':result['actual_capture']['FF_cells'],'body_um2':result['actual_capture']['actual_cell_area_um2'],'physical_fit':False}))
if __name__=='__main__':main()
