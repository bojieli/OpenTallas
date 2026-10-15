#!/usr/bin/env python3
"""Source-pinned feasibility census; never qualifies or launches a physical job."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/hbm_hc_static_1015/sys1_physical_census'
def blob(commit,path):
    b=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
    return {'commit':commit,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
def main():
    sources=[blob('d30ae4714','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv'),
      blob('d30ae4714','rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_projection_static.sv'),
      blob('faa293303','rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_engine_mtp_static.sv'),
      blob('b3b45c34d','results/rtl/ref_tile/hc_tile_xl/c5_redesign_spec.md'),
      blob('15c472f82','rtl/dsrom_sys/s81_hcx/ot_s81_hcx_hcp_partition.sv')]
    base='physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/'
    for f in ['ot_hdc_v41x_hcp_lanes.lef','child_lint.json','insertion.json','abstract.json']:
        sources.append(blob('4bb5ee22d',base+f))
    lane=json.loads((OUT/'lane_routed_ioref.json').read_text());tile=json.loads((OUT/'tile_routed_ioref.json').read_text())
    W,LM,LA,ML,SOR,DRLY=32,8,7,3,1,2
    syslat=2*DRLY+1+7*(LA+1+SOR)+3+2+(ML-2)+LM+LA+SOR
    descriptor=2+(W.bit_length())+2*16
    r={'scope':'HBM PMAX8 SYS1 source/master census and proposed binding only; no prototype is admitted because the physical contracts do not yet compose',
      'source_pins':sources,'parameters':{'W':W,'stages':8,'LG':8,'PMAX':8,'K':20480,'LM':LM,'LA':LA,'TML':ML,'SOR':SOR,'DRLY':DRLY},
      'proposed_actual_binding':{'controller':'ot_hdc_v41x_hcp SYS=1 STATIC_CALENDAR=1; compiler launch/raw-read slots',
        'bank_stage':'ot_hdc_v41x_hcp_stage W32 ML3 LM8 LA7 SOR1 LG8, eight real stages in term0..7 order',
        'lane_master':'32 parameterless ot_hdc_v41x_hcp_lanes (four per bank), existing hardened defaults unchanged',
        'weight_storage':'existing static aperture banks, split physically into eight local bank stores; no historical credit-driven weight windows',
        'residual_storage':'existing actual16x1024x256 SRAMs, two per bank, BF16 data; local registered read capture',
        'memory_shell':'new physical local read/write/address shell required; existing ot_hgi_hc_tile cannot be reused as static SRAM shell because its HBM window path contains ready/FIFO state',
        'tail':'controller tree/tail/rsqrt raw storage needs its own bounded roots/slot, not covered by MAC master'},
      'analytical_model':{'logical_lanes':8*W,'MACs_per_issue_edge':8*W,'rows':24,'positions':8,
        'weight_bytes_per_read_edge':8*W*4,'residual_bytes_per_read_edge':8*W*2,
        'weight_SRAMs_128x256':64,'weight_capacity_bytes':64*128*256//8,
        'residual_SRAMs_1024x256':16,'residual_capacity_bytes':16*1024*256//8,
        'bank_weight_read_bits':W*32,'bank_residual_read_bits':W*16,
        'crossbank_sum_bits':W*32,'crossbank_descriptor_bits':descriptor,'crossbank_fault_bits':1,
        'crossbank_sum_plus_descriptor_fault_bits':W*32+descriptor+1,
        'descriptor_hop_edges':LA+1+SOR,'legacy_SYS_LAT_formula_edges':syslat,
        'legacy_SYS_leaf_capture_edges':syslat+1,'flat_SYS0_leaf_capture_edges':31+2,
        'nominal_delta_leaf_edges':syslat+1-(31+2),
        'caveat':'90-edge SYS_LAT is the existing legacy timing formula, not verified static prototype latency. Added pin/register/relay/clock phases can increase it. Do not reuse SYS0 raw-read calendar or performance receipt.'},
      'measured_existing_lane_master':{'outline_um':[138.24,138.24],'flops':11251,
        'TT_setup_ps':lane['setup_tt']['worst_slack_ps'],'FF_hold_ps':lane['hold_ff']['worst_slack_ps'],
        'qualified_scope':'historical accepted MAC leaf; current export/physical binding must be checked before reuse; standalone leaf closure does not close bank/tile'},
      'failed_existing_native_tile':{'job':'hc_tile_xl-c4-550082537-hs','TT_setup_ps':tile['setup_tt']['worst_slack_ps'],
        'FF_hold_ps':tile['hold_ff']['worst_slack_ps'],'DRC':11,'c5_status':'source-pinned redesign specification only, no implemented/qualified replacement',
        'causes':['250..480um wire plus5..14logic levels in one hop','window/memory capture cross-root skew','legacy weight-window runtime ready path forbidden in static successor']},
      'clock_root_contract_gaps':['Existing32MACleaves each11251FF fit count; new eight SRAMbank/shell roots and controller/tree/tail roots have no measured census or CTS.',
        'SYS1 bank stages expose a common clk only; independent hardened-child clock delivery/phi-R and mixed-phase exactness not implemented in this proposal.',
        'S81 first42/later46-root partition uses resident ROM and a different bank/rotator tree, not an interchangeable HBM SYS1 master.',
        'No assigned bank/shell/controller outlines, physical pin faces,500um hop/reach proof, crossbank cut capacity or fixed compiler calendar exists.'],
      'required_next_steps':['Obtain H-DIE slot/pin/clock contract for eight local bank clusters plus controller/tree/tail; preserve accepted MAC views.',
        'Model proposed SRAM bank shell and controller roots, exact crossbank pin faces and paths before writing the native composition.',
        'Then build opt-in SYS1/static controller+realbankstage composition using real SRAM stores; prove minimum component at PMAX8 and K20480 against independent golden plus actual source mutant.',
        'Only after assigned slot/model and source-bound gate, route new shells/parents and validate SS/FF/DRC/CTS/phi-R.'],
      'prototype_implemented':False,'route_submitted':False,'physical_qualified':False,'full_native_qualified':False,
      'evidence_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.name!='census.json'}}
    assert syslat==90 and descriptor==40
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'census.json').write_text(json.dumps(r,indent=2)+'\n')
    print('HC SYS1 census:32 actual MAC leaves;90-edge legacy latency;80 operand SRAMs; physical contracts missing; no prototype/route')
if __name__=='__main__':main()
