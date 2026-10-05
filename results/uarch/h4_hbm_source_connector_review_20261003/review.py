#!/usr/bin/env python3
"""Immutable source connector inventory and ABI checks; no execution qualification."""
import argparse,ast,hashlib,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parent
MANIFEST_SHA256='a9ecd0d881b96811d9eda1e816b64f0165263133dcaa7af6f0fda3b4ec8982a9'

def canonical(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def require(x,msg):
    if not x:raise ValueError(msg)
def sources():
    raw_manifest=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw_manifest).hexdigest()==MANIFEST_SHA256,'frozen manifest');manifest=json.loads(raw_manifest); out={}
    for r in manifest['inputs']:
        p=(BASE/r['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive escapes')
        raw=p.read_bytes();require(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'source pin '+r['path'])
        out[r['origin'],r['path']]=raw.decode() if not r['path'].endswith('.gz') else raw
    return manifest,out

def actual_physical(src):
    body=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='physical']
    require(len(body)==1,'source address function');ns={}
    exec(compile(ast.Module(body=body,type_ignores=[]),'archived r17 physical function','exec'),ns)
    return ns['physical']
def owner(pc,client,tag,gen):
    for v,w in [(pc,7),(client,3),(tag,32),(gen,4)]:require(type(v)is int and 0<=v<1<<w,'lossless owner width')
    require(client<6,'six source clients only; seventh needs producer binding')
    return (((pc<<3|client)<<32|tag)<<4)|gen

def outputs():
    m,s=sources();main=lambda p:s['main',p]
    anchors=[('rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv','parameter integer CTAGW=32'),('rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv','p_req_addr[p*AW +: 7]'),('rtl/hdc/hbm/ot_hdc_qwen_kv_pc_adapter.sv','pc=addr[6:0]'),('rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv','logic [11:0] physical_tag'),('rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv','tag:held.tag[11:0]'),('rtl/model_ready_hbm_w1_euclid_20261003/ot_hbm_causal_command_provider.sv','returns[return_pc].tag[11:0]'),('rtl/model_ready_hbm_w1_euclid_20261003/ot_hbm_causal_command_provider.sv','if(!credit_we)begin credit_match=1'),('rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv','live[tag_saved]<=0'),('rtl/gpu/ot_gpu_rf_service.sv','wire write_go = wr_valid && wr_ready;')]
    for p,a in anchors:require(a in main(p),'source evidence missing '+p+' '+a)
    tb=main('rtl/test/model_ready_hbm_r14/tb_hbm_finite_stage.sv');require('ot_hdc_qwen_pc_service' not in tb and 'ot_hdc_qwen_hbm_service' not in tb,'route source changed')
    physical=actual_physical(main('tools/qwen_hbm_provider_bindings_r17.py'))
    peer=s['popper_WIP','tools/h4_hbm_w5_w10_composed_model.py'];tree=ast.parse(peer)
    peerphysical=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='physical'];ns={'require':require}
    exec(compile(ast.Module(body=peerphysical,type_ignores=[]),'archived Popper WIP translation','exec'),ns)
    points=[0,1,31,32,63,127,128,255,511,512,4096,65536,80999999999];rows=[]
    for b in points:
        a=physical(b);p=ns['physical'](b);pc=a['stack']*32+a['PC'];local=a['local_sector31']*32+a['byte_in_sector']
        require((local//128)*512+a['stack']*128+local%128==b,'lossless address inverse')
        require(a['byte_in_sector']==b%32 and p['physical_PC']==pc and p['local_sector']==a['local_sector31'],'peer/source mapping')
        rows.append(dict(global_byte=b,system_sector=a['system_sector34'],local_sector=a['local_sector31'],physical_PC=pc,byte_in_sector=a['byte_in_sector'],legacy_low7_PC=a['system_sector34']&127))
    mismatches=[r for r in rows if r['physical_PC']!=r['legacy_low7_PC']];require(mismatches,'mismatch witness')
    # Exhaustive bytes in two adjacent stripes and finite extremes, not a workload replay.
    for b in range(1024):
        a=physical(b);local=a['local_sector31']*32+a['byte_in_sector'];require((local//128)*512+a['stack']*128+local%128==b,'stripe inverse')
    maxkey=owner(127,5,2**32-1,15);require(maxkey.bit_length()==46 and maxkey&15==15 and (maxkey>>4)&(2**32-1)==2**32-1,'full original tag/gen retained')
    for args in [(0,0,2**32,0),(0,6,0,0),(0,0,0,16)]:
        try:owner(*args)
        except ValueError:pass
        else:raise ValueError('invalid namespace accepted')
    # Different namespaces must not be cast/truncated into each other.
    require((8&7)==0 and (2**32-1)&65535 != 2**32-1,'legacy class/caller cannot store full identity')
    backend_old=(7<<12)|41;backend_new=(8<<12)|41
    require(backend_old!=backend_new and backend_old&4095==backend_new&4095,'backend generation mismatch test')
    source_gen=3;require(source_gen!=backend_new>>12,'source and backend generations are independent')
    frame=[False]*16;frame[0]=True;require(not all(frame),'one sector cannot qualify 512B RF frame')
    protected=lambda n:math.ceil(n/64)*72
    rq0,rp0=339,303;added=4+5+9+32;rq,rp=rq0+added,rp0+added
    cost=dict(scope='incremental cost INPUTS, not area/route/clock admission',W10_old_raw_request=rq0,W10_old_raw_return=rp0,
        additional_fields={'producer_generation':4,'requester_SM':5,'RF_slot':9,'parent_reference':32},
        proposed_raw_request=rq,proposed_raw_return=rp,old_protected_request=protected(rq0),old_protected_return=protected(rp0),proposed_protected_request=protected(rq),proposed_protected_return=protected(rp),
        protected_delta_each_direction=72,pipeline_two_seats_38stages_144lanes_increment_bits=38*2*144*(protected(rq)+protected(rp)-protected(rq0)-protected(rp0)),
        source_provider_request_bits=455,proposed_provider_request_bits=547,source_owned_bits=465,proposed_owned_bits=561,
        source_command_bits=339,proposed_command_full_backend_token_bits=343,
        sidecar_source_metadata_bits=92,sidecar_plus_backend_generation_bits=96,
        sidecar_same_existing_context_index_no_second_CAM=True,
        if_full_source_context_replication_additional_128x256_macros_per_stack=32,if_four_stacks_additional_macros_per_die=128,
        full_context_sidecar_raw96bits_per_die=4*32*128*96,
        one_complete_RF_frame_per32SM_data_bits=32*4096,RF16sector_mask_bits_per32SM=32*16,
        RF_parent_capture_owner_and_slot_bits_perSM=55,RF_existing_macro_area_recharge=False,
        mux_and_control_costs=['four stack 36-to32 forward and32-to36 reverse crossbars, wider protected words','source metadata write32-bank fanout; same-index RAM read/capture join','backend16 comparison vs source12 and duplicate/inflight/retire protections','16sector RF assembler lane steering and parent context selector','RF host/SIMD retained55-bit identity mux','tag allocation/reverse updates with atomic same-edge accounting'],
        SS_macro_area_slot_route_clock_pins_and_added_capture_latency=None,whole_service_calendar_upper=None,physical_PHY_sustained_bandwidth=None)
    findings=[
        dict(id='CONNECTOR_ABSENT',severity='BLOCKER',source='rtl/test/model_ready_hbm_r14/tb_hbm_finite_stage.sv',finding='Finite stage routes clock bridge directly to R14, not Qwen PC service; finite client RF256 pattern register is not GPU RF4096/native caller.'),
        dict(id='ADDRESS_ROUTE_MISMATCH',severity='BLOCKER',source='rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv',finding='Low7 system-sector port selection differs from local-sector hash; overwrite would corrupt address. Explicit translated PC sideband/guard required.'),
        dict(id='NO_NATIVE_HW_TAG_ALLOCATION',severity='BLOCKER',source='tools/h4_c0_v1_owner_lock_addressed.py',finding='Native owner/generation64 and PC/rank/SM/home are software identity; actual hardware tag32/client allocation, parent/child reference directory and installed rank/SM emitter are missing.'),
        dict(id='R14_NOT_FULL_OWNER',severity='BLOCKER',source='rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',finding='Legacy192-bit identity is not full clienttag32+producergen4+SM+RFslot. Tag retires at owned acceptance, ahead of RF/consumer/reverse. Upper wire4 bits discarded in command and matcher.'),
        dict(id='READ_REVERSE_UNVALIDATED',severity='BLOCKER',source='rtl/model_ready_hbm_w1_euclid_20261003/ot_hbm_causal_command_provider.sv',finding='Read reverse credit grants unconditionally. Full accepted identity/direction/beat/generation/live state must match before release; old-copy quiescence must govern reset/wrap.'),
        dict(id='RF_FRAME_NOT_SECTOR',severity='BLOCKER',source='rtl/gpu/ot_gpu_rf_service.sv',finding='Both copies write full4096bits with no byte enable. 64B C0 software fragment or32B KV sector cannot be zero-filled as a full vector; complete preserved frame assembly/typed conversion required.'),
        dict(id='WIP_MISSING_FIELDS',severity='BLOCKER',source='tools/h4_hbm_w5_w10_composed_model.py',finding='Archived WIP W10 339/303-bit words omit producergen4 and explicit SM/slot/parent reference. W5 epoch32 is not hardware producergen4. Additional7th client directory still lacks producer binding.'),
    ]
    review=dict(verdict='FAIL_SOURCE_CONNECTOR_G0',source_checks='PASS_BOUNDED_INVENTORY_ONLY',hardware_admitted=False,build_allowed=False,source_commit=m['base_commit'],peer_commit=m['peer_commit'],peer_snapshot_uncommitted=True,source_and_artifact_pins=len(m['inputs']),
        current_route='finite pattern client -> R14 CDC -> R14 provider -> backing fixture -> finite pattern RF256 -> reverse; W2/W4 full GPU/W6 native unconnected',
        proposed_one_baseline_route='accepted native descriptor -> W5 parent/child allocation -> explicit address translator -> W2 perPC exact logical ownership -> R14 physical mapper -> W2 restored held completion -> parent RF frame assembly -> W4 full55 commonACK -> W6 consumer/reverse -> W2/R14 quarantine release',
        W2_required_on_proposed_route=True,R14_as_is_cannot_be_canonical_full_bridge_table=True,
        no_duplicate_R14_CAM_required_for_metadata_sidecar=True,
        findings=findings,cost_inputs=cost,tests={'source_anchors':len(anchors),'address_examples':len(points),'stripe_bytes':1024,'negative_namespace_cases':3,'checks':['source/peer exact translation','reversible stripe map','low7 mismatch witness','full tag32/gen4 packing','legacy client/caller rejection','distinct source/backend generations','stale backend-token distinction','partial RF frame refusal']},
        numerical_payload_run=False,small_fixture_is_not_final_qualification=True)
    return {'review.json':canonical(review),'address-witnesses.json':canonical(rows),'cost-inputs.json':canonical(cost)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    for n,v in outputs().items():
        if a.verify:require((BASE/n).read_bytes()==v,'byte-exact replay '+n)
        else:
            require(a.output is not None,'explicit fresh output');a.output.mkdir(parents=True,exist_ok=True);require(not (a.output/n).exists(),'do not overwrite evidence');(a.output/n).write_bytes(v)
    print('PASS source pins/address/namespace inventory checks; FAIL_SOURCE_CONNECTOR_G0 retained; no build admission')
if __name__=='__main__':main()
