#!/usr/bin/env python3
"""Read-only source-sized W6 contextual timing plan; never invokes synth/P&R.

Liberty table envelopes are analytical, not STA. One unchanged RTL candidate,
32 copies, no sweep. Ampere selected placement/clock/load inventory fills only
measured inputs; frozen RTL, clock and uncertainty remain exact.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/hbm_W6_contextual_plan_20261003/r1'
RTL='rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv'
CODEC='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def groups(t,kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{',t):
        i=m.end();start=i;depth=1;quote=False;escape=False
        while depth and i<len(t):
            c=t[i]
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quote=not quote
            elif not quote:
                if c=='{':depth+=1
                elif c=='}':depth-=1
            i+=1
        require(depth==0,'unbalanced Liberty')
        yield m[1].strip(' "'),t[start:i-1]
def scalar(t,key):
    m=re.search(r'\b'+key+r'\s*:\s*([-+\d.eE]+)',t);require(m is not None,'Liberty scalar '+key)
    return float(m[1])
def cells(t,name,seq=False):
    c=[b for n,b in groups(t,'cell') if n==name];require(len(c)==1,'unique master '+name);c=c[0]
    results=dict(master=name,area_um2=scalar(c,'area'),input_cap_fF={},arcs=[])
    for n,b in groups(c,'pin'):
        if re.search(r'direction\s*:\s*input',b):results['input_cap_fF'][n]=scalar(b,'capacitance')
    for _,arc in groups(c,'timing'):
        typ=re.search(r'timing_type\s*:\s*(\w+)',arc)[1]
        if typ not in ('combinational','rising_edge','setup_rising','hold_rising'):continue
        for kind in ('cell_rise','cell_fall','rise_constraint','fall_constraint'):
            for _,table in groups(arc,kind):
                ii={k:[float(v) for v in re.search(r'index_'+str(k)+r'\s*\("([^"]+)"\)',table)[1].split(',')] for k in (1,2)}
                rows=[[float(v) for v in row.split(',')] for row in re.findall(r'"([^"]+)"',re.search(r'values\s*\((.*?)\)\s*;',table,re.S)[1])]
                require(len(rows)==len(ii[1]) and all(len(r)==len(ii[2]) for r in rows),'table dimensions')
                results['arcs'].append(dict(timing_type=typ,kind=kind,index1=ii[1],index2=ii[2],values=rows))
    return results

def envelope(fact,kind,minimum=False,load=None):
    vals=[]
    for a in fact['arcs']:
        if kind=='delay' and a['kind'].startswith('cell_') or a['timing_type']==kind:
            # Characterized slew<=80ps only; all characterized load columns.
            # This is an envelope, not any claim actual driver load meets it.
            cols=list(range(len(a['index2']))) if load is None else [next((j for j,c in enumerate(a['index2']) if c>=load),-1)]
            require(-1 not in cols,'source load outside characterized table')
            vals += [row[j] for i,row in enumerate(a['values']) if a['index1'][i]<=80 for j in cols]
    require(vals,'missing timing '+kind)
    return min(vals) if minimum else max(vals)

def portbook():
    text=(ROOT/RTL).read_text();body=text[text.index(')(\n')+3:text.index('\n);')]
    # Parse original declarators with carried direction/width; no guessed portbook.
    fields=[];direction=None;width=1
    for token in body.replace('\n',' ').split(','):
        token=token.strip();m=re.match(r'(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)$',token)
        if m:direction=m[1];width=int(m[2])+1 if m[2] else 1;name=m[3]
        else:
            require(re.fullmatch(r'\w+',token) and direction is not None,'port declaration '+token);name=token
        fields.append(dict(name=name,direction=direction,width=width))
    require(len({p['name'] for p in fields})==len(fields),'duplicate port')
    return fields

def depth():
    # Count exact loop-written XOR folds from Hamming positions1..71.
    folds=[sum(bool(p&(1<<k)) for p in range(1,72)) for k in range(7)]
    enc=[n-1 for n in folds]  # excludes parity-position itself, initial0 fold
    return dict(decode_syndrome_left_fold_XOR_counts=folds,
      decode_syndrome_longest_serial_XOR=max(folds),encode_check_left_fold_XOR_counts=enc,
      encode_check_longest_serial_XOR=max(enc),overall_parity_reduction_bits=72,
      ideal_balanced_syndrome_XOR_depth=math.ceil(math.log2(max(folds))),
      ideal_balanced_encode_check_XOR_depth=math.ceil(math.log2(max(enc))),
      reduction_tree_guaranteed_by_source=False,identity_equality_bits=55,
      identity_reduction_binary_tree_depth=math.ceil(math.log2(55)),identity_match_ports=7,
      variable_correction_read_mux_inputs=71,variable_correction_binary_mux_depth=7,
      variable_write_index_decode_bits=7,FSM_phase_branches=10,
      reset_mask_control_bits=71,retained_guard_age_bits=2,
      cone='retained144 -> decode syndrome/range/overall -> variable correction -> identity/phase/reset priority -> encode two chunks -> retained144')

def build():
    facts={};pins={RTL:sha(ROOT/RTL),CODEC:sha(ROOT/CODEC)}
    for p in sorted((BASE/'inputs').iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
    for corner in ('SS','FF'):
        d={}
        for family,suffix in [('SIMPLE','211120.lib.gz'),('SEQ','220123.lib'),('INVBUF','220122.lib.gz')]:
            p=BASE/'inputs'/f'asap7sc7p5t_{family}_RVT_{corner}_nldm_{suffix}'
            t=(gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text())
            require(re.search(r'time_unit\s*:\s*"1ps"',t) and re.search(r'capacitive_load_unit\s*\(1,ff\)',t),'ps/fF Liberty units')
            for alias,name in ({'XOR':'XOR2x1_ASAP7_75t_R','XNOR':'XNOR2x1_ASAP7_75t_R','AND':'AND2x2_ASAP7_75t_R','NAND':'NAND2x1_ASAP7_75t_R'} if family=='SIMPLE' else {'FF':'DFFHQNx1_ASAP7_75t_R'} if family=='SEQ' else {'INV':'INVx1_ASAP7_75t_R'}).items():
                d[alias]=cells(t,name,alias=='FF')
        facts[corner]=d
    dep=depth();ss=facts['SS'];ff=facts['FF']
    full_envelope={n:envelope(v,'delay') for n,v in ss.items()}
    # Seven syndrome/identity loads conservative source fanout; wire remains external.
    xor_load=7*max(ss['XOR']['input_cap_fF'].values())
    bound={n:envelope(v,'delay',load=(max(ss['INV']['input_cap_fF'].values()) if n=='FF' else xor_load)) for n,v in ss.items()}
    setup=envelope(ss['FF'],'setup_rising');hold=envelope(ff['FF'],'hold_rising')
    # One analytical depth screen of the exact unchanged candidate. Source folds
    # and optimistically balanced form are not two alternative implementations.
    common=bound['FF']+bound['INV']+setup+60
    serial=common+(dep['decode_syndrome_longest_serial_XOR']+dep['encode_check_longest_serial_XOR']+7)*bound['XOR']
    balanced=common+(dep['ideal_balanced_syndrome_XOR_depth']+dep['ideal_balanced_encode_check_XOR_depth']+7)*bound['XOR']
    # Extra variable correction, equality, FSM priority, routing/skew IN ADDITION.
    period=1000/1.2
    ports=portbook();pinbits=sum(p['width'] for p in ports if p['name'] not in ('clk','por_n','rst_n'))
    bits_in=sum(p['width'] for p in ports if p['direction']=='input' and p['name'] not in ('clk','por_n','rst_n'))
    early=envelope(ff['FF'],'delay',True)
    base=json.loads((ROOT/'results/uarch/hbm_W6_local_RTL_20261003/model_r1/model_r2_fanout.json').read_text())
    return dict(schema='W6_FULL32_CONTEXTUAL_SINGLE_ROUTE_PLAN_V1',sourcepins=pins,
      plan_tool_sha256=sha(Path(__file__)),source_adapter_sha256=sha(ROOT/'tools/hbm_w6_physical_source_adapter.py'),source_component='e951f5097b852eeb94bf8511d86ecb5344dc9cd9',parameter=dict(ENABLE=1,replicas=32,source_default_ENABLE=0),
      source_depth=dep,Liberty_cell_facts=facts,
      clocks=dict(target_GHz=1.2,period_ps=period,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
          functional_bench_period_ps=10000,functional_bench_proves_target_clock=False,
          boundary_age_is_not_combinational_pipeline=True,CDC_age3_is_not_installed_CDC=True,
          clk_reference='same streaming clock; retained-state timing tested with propagated clock after CTS',
          runtime_reset='synchronous rst_n with synchronized release, immediate output mask; constrain recovery/removal of coldPOR, no blanket false-path for live reset'),
      prospective_timing=dict(SS_source_fanout_cell_envelope_ps=bound,SS_all_table_load_envelope_ps=full_envelope,
          source_XOR_7receiver_load_fF=xor_load,wire_capacitance_in_source_load=False,SS_setup_ps=setup,FF_hold_ps=hold,
          SS_serial_parity_plus_FF_INV_setup_uncertainty_ps=serial,
          SS_ideal_balanced_parity_plus_FF_INV_setup_uncertainty_ps=balanced,
          SS_remaining_ideal_parity_only_ps=period-balanced,
          excluded_but_required_in_actual_STA=['variable read/write correction mux/index decode/range','all7 identity match and fanout','phase decode/priority/heldport/reset enable','wires/coupling/vias','clock skew/CTS','actual source driver/load/slew'],
          interpretation='Primary envelope uses characterized slew<=80ps and next tabulated load ceiling for7 source XORreceiver pin loads, no favorable interpolation. All-table-load envelope separate. Actual wire/loads/mappedfanout still require inventory. Not STA or proof of failure/closure. Serial source fold and best possible balancing expose risk on the one candidate, not a tuning sweep.',
          mapped_source_path_required=True,parity_balance_not_free=True,
          FF_min_characterized_clkQ_ps=early,FF_clkQ_minus_hold_uncertainty_ps=early-hold-25,
          FF_hold_not_proved_by_setup_depth=True,actual_endpoint_min_delay_skew_and_subgrid_load_unknown=True),
      state=dict(raw_per_SM=71,protected_RTL_width_per_SM=144,full32_protected_RTL_bits=4608,
          protected_padding_constant_bits_per_SM=57,
          mapping_may_remove_constant_code_bits=True,mapped_FF_count_not_claimed=0,
          active_owner_phase_fault_origin_ages_and_check_coverage_required=True,
          padded_constant_synthesis_debit_only_after_exact_mapped_inventory=True),
      slot=dict(proxy_logic_um2_per_SM=base['area']['prospective_logic_um2_per_SM'],
          reserved_um2_per_SM=base['area']['reserved_slot_um2_per_SM'],utilization=.5,
          full32_proxy_mm2=base['area']['full32SM_slot_mm2'],
          local_clock_pin_load_fF=144*ss['FF']['input_cap_fF']['CLK'],full32_clock_pin_load_fF=4608*ss['FF']['input_cap_fF']['CLK'],
          CTS_reset_hold_repair_and_pin_escape_area_not_yet_charged=True,
          added_area_fit_requires_mapped_cells_plus_clock_reset_hold_and_neighbor_exclusions=True,
          no_recharge_of_RF_data_W4_or_external8frame128child_directory=True),
      ports=dict(ports=ports,data_and_control_bits_per_SM=pinbits,inputs_per_SM=bits_in,outputs_per_SM=pinbits-bits_in,
          conservative_per_port_bundle_tracks=pinbits,distinct_cut_tracks_must_be_extracted=True,full32_local_signal_endpoints=pinbits*32,
          control_payload_bytes_per_cycle=0,maximum_boundary_bits_per_cycle_per_SM=pinbits,
          perboundary_throughput='one retained owner perSM; perphase heldvalidready. Parallel wires are not concurrent transaction throughput',
          target_clock_fanout=4608,reset_scope='32 replicas only; no free broadcast to source/global directory'),
      selected_route=dict(id='W6_FULL32_DISTRIBUTED_ASAP7_RVT_M2_M5_R1',alternatives=0,
          top='ot_gpu_w6_full32_context',replicas=32,
          placement='one W6 slot adjoining each actual32SM RF/W4 landing; preserve exact Ampere32SM placement and all RF/scratch OBS/halos/PG, no central cluster relocation',
          signal_layers=['M2','M3','M4','M5'],clock_layers=['M4','M5'],
          additional_layers_allowed=False,layer_selection_requires_Ampere_no_conflict=True,
          backend_macro_count_RF=32*4*16*2,
          macro_evidence='RF128x256 mirrored4096instances plus actual context scratch/othermacros from Ampere. Do not synthesize fakeRF or tie bareACK to owner55.',
          floorplan='no fabricated physical origin; bind named32 W6 slots/bboxes and corridor capacities in Ampere actual fullsize inventory',
          no_new_data_or_arithmetic=True,retain_all_replica_port_paths=True,
          synthesis='one source map atSS with exactcells and preserved hierarchy, followed by one place/CTS/global+detail route; FF reanalysis of same exact extracted netlist/geometry',
          rejection='negative SSsetup/FFhold/slot/pin/DRC/PG/corridor rejects exactcandidate; preserve failure. No clock relaxation, automatic tune or alternative sweep',
          success_scope='predictive ASAP7 full32 local component context only, not foundry signoff or full bridge/whole-token'),
      Ampere_inventory_contract=dict(worktree='/tmp/opentallas-hbm-fullsize-inventory-20261003',receipt=None,
          required=['clean source/config/PDK/toolhashes for selectedfullsizecontext','32physicalSM IDs and actualrows/sites/orientations/bboxes','4096RF macro inventory and exactscratch/neighbor/OBS/halo/PG exclusions','32named W6 slots and matching W4/drain/consumer/return endpoint coordinates','source launch driver cells/slew/max/min delays and destination pin loads for every scoped55bit port','selectedlegal M2-M5 actualtracks/corridors/PG/cut capacities and access','sameclock CTS target/source current latency/min/maxskew and reset source/release','SS andFF libs/RC/corneridentity and actualLEF/lib footprint matching'],
          excludes_fullbridge_functional_requirement=True,
          installed_allcopy_producer_not_required_for_local_timing=True,
          source_contract_substitution_claim=False),
      acceptance=['exactsource ENABLE1 and32retainedinstances, no disconnected/tiedidentity ports','SS1.2GHz max paths nonnegative with60ps uncertainty, actual sourcepin delays and propagatedclock','FFmin paths nonnegative with25ps uncertainty, recovery/removal and min/max skew','zero unexplained unconstrained paths; no falsepath throughcodec/matches/reset/feedback','actualmappedstate/protection/defaultoff equivalence and mappedclock/resetload inventory','all32slots includingCTS/holdrepair/PG/via/OBS/halo/escape fit with same allowedlayers','actualmacro placement census joins stricttrackchecker for all instances, not two samplemacros','routeDRC/density/coupling/PG and all actualcuts within capacity','measure each added transport/protection latency and return to unifiedmodel before adoption'],
      resources=dict(allowed_hosts=['local','PVE1','128GiB_VM'],PVE2_PVE3=False,
          build_wall_limit=None,CPU_time_limit=None,FSIZE_limit=None,AS_limit=None,memory_hard_limit=None,swap_hard_limit=None,
          policy='fresh measured host/cgroup/livelease/calendar before exactsource GO; estimate from comparable full32 map/place object and memory inventory, retain increments. No guessed pilot caps.',
          current_host_observation='separate resource_observation.json read-only snapshot; not exclusive launch reservation'),
      launch_ready=False,launch_not_ready_reason='Ampere actual full32 slot/driver/load/clock/layer inventory and selected toolchain/corner hashes pending; local plan is prepared independently of caller/allcopy hardware',
      P_and_R_launched=False,physical_qualified=False,fullbridge_qualified=False)

def validate_inventory(plan,i):
    require(i.get('schema')=='W6_AMPERE_FULL32_CONTEXT_INPUT_V1','Ampere inventory schema')
    require(i.get('source_sha256')=={RTL:sha(ROOT/RTL),CODEC:sha(ROOT/CODEC)},'exact source pins')
    require(len(i.get('SMs',[]))==32 and {s['SM'] for s in i['SMs']}==set(range(32)),'all32 unique physicalSMs')
    require(i.get('signal_layers')==['M2','M3','M4','M5'],'selected layers')
    require(i.get('SS_setup_uncertainty_ps')==60 and i.get('FF_hold_uncertainty_ps')==25,'unchanged uncertainty')
    require(i.get('target_period_ps')==1000/1.2,'unchanged target clock')
    for s in i['SMs']:
        require(s.get('reserved_W6_um2',0)>=plan['slot']['reserved_um2_per_SM'],'perSM slot proxy')
        require(s.get('RF_macro_count')==128,'two physical RF copies fullshape')
        require(s.get('context_macro_and_route_receipt_sha256') and s.get('all_port_minmax_load_driver_receipt_sha256'),'actual physical context/source ports')
    artifacts=i.get('artifacts',{})
    require(len(artifacts)>=4,'complete external source/placement/port/tool manifests')
    for path,digest in artifacts.items():
        require(re.fullmatch(r'[0-9a-f]{64}',digest) and Path(path).is_file() and sha(path)==digest,'external artifact pin '+path)
    require(i.get('tool_corner_LEF_RC_manifest_sha256') and i.get('actual_placement_census_sha256'),'actual tool/corner/placement identity')
    return 'PASS_EXACT_LOCAL_CONTEXT_INPUTS_REQUIRES_PARENT_SOURCE_MODEL_RESOURCE_GO'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--inventory',type=Path);a=ap.parse_args()
    p=build()
    if a.inventory:p['inventory_validation']=validate_inventory(p,json.loads(a.inventory.read_text()))
    with a.out.open('x') as f:json.dump(p,f,indent=2,sort_keys=True);f.write('\n')
