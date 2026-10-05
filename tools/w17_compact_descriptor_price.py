#!/usr/bin/env python3
"""Price explicit compact descriptor proposal, preserving full product blockers."""
import argparse,gzip,hashlib,json,subprocess
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'candidate':('0fb58ac09c4415b4f143c97fed1fbfa4a5486aa9','results/quality/w16_w17_integer_residency_20261001/candidate.json.gz'),
 'parent_width_review':('5916e0b107a252fb48ab557d12731c432be43578','results/quality/parent_rom_descriptor_width_review_20261001/review.json'),
 'scalar_replay':('a2f76583279a984a1ce99d29fe1cbea537c5fbb9','results/rtl/w17_connected_token_preparation_20261001/integer_candidate_scalar_replay.json'),
 'pair':('76ffc2aa0df086016c57edc2abb128a29a05099c','rtl/v41die/ot_v41_pair_w17w10.sv'),
 'spine':('76ffc2aa0df086016c57edc2abb128a29a05099c','rtl/v41die/ot_v41_spine_w17w10.sv'),
 'images':('1c4c5aefdfbbdd41dee75772761a95a3446104cc','tools/v41_die_images_w17w10.py'),
 'clock':('850d9c79bc3767b4ad4ca5d5106b9c97aecf08cc','results/quality/w10_clock_source_contract_r1/contract.json'),
 'rootstop':('4ad1baf66d6411bf01ebd14ad97b4abecbd9ecf9','results/rtl/w17_connected_token_preparation_20261001/rootstop_provider_requirements.json'),
 'sizing_coefficients':('6e1158394262bc47773993e04efce0672ac4552e','tools/common_hbm_backend_provider_contract.py')}
def blob(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def owner_index(layer,expert):
    if type(layer) is not int or type(expert) is not int or not 0<=layer<40 or not 0<=expert<384:raise ValueError('invalid resident owner key')
    return layer*384+expert

def build():
    data={k:blob(v) for k,v in PINS.items()};c=json.loads(gzip.decompress(data['candidate']))
    if sha(data['candidate'])!='eff58ce55fb268530aea3fdc981ef53e8009248baee276fc42af5ac335141c98':raise ValueError('candidate identity')
    # Require exact existing loader/storage protocol tokens, no timing promotion.
    for token in (b'CW + 2 cycles',b'reg [47:0] cm [0:DEPTH-1]',b'cfg_d(c_d)'):
        if token not in data['pair']:raise ValueError('pair loader contract changed')
    if b'ph["sbase"] < (1 << 16)' not in data['images']:raise ValueError('stream base width changed')
    q=c['geometry']['q_pairs'];stages=c['expert_only_stage_count'];ranks=4;replicas=q*stages*ranks
    streams={f:c['templates'][f]['stream_issue_cycles'] for f in ('w1','w3','w2')}
    first_overflow=None;base=0
    for slot in range(c['experts_per_stage_capacity']):
        for f in ('w1','w3','w2'):
            if base>=65536 and first_overflow is None:first_overflow=dict(slot=slot,family=f,stream_base=base,phase_index=slot*3+('w1','w3','w2').index(f))
            base+=streams[f]
    if first_overflow is None:raise ValueError('expected source sbase failure absent')
    tables=[]
    for layer in range(40):
        rows=[]
        for expert in range(384):
            o=c['owners'][owner_index(layer,expert)]
            if (o['layer'],o['expert'])!=(layer,expert):raise ValueError('owner table order')
            rows.append((1<<15)|(o['stage']<<9)|o['slot'])
        tables.append(dict(layer=layer,entries=rows,padding_entries=128,padding_value=0))
    cfg_bits_per_pair=4*25*48 # three templates rounded four, output48bit local1R
    affine_regs_per_pair=9+14+14+3+2 # slot, product, base, iteration, family
    # Candidate14bit ripple add plus13bit base rewrite, mux bit equivalents:
    adder_gates_per_pair=(14+13)*5
    muxbits_per_pair=(4*25-1)*48+48 # family template mux and patched output
    pair_area=(D(cfg_bits_per_pair+affine_regs_per_pair)*D('.2916')+D(adder_gates_per_pair+muxbits_per_pair)*D('.2'))/D('.5')/D('1000000')
    owner_bits=512*16;owner_muxbits=511*16
    owner_area=(D(owner_bits)*D('.2916')+D(owner_muxbits)*D('.2'))/D('.5')/D('1000000')
    spine_bits=4*128+256*48
    spine_area=D(spine_bits)*D('.2916')/D('.5')/D('1000000')
    cfg_service=6+27 # five shiftadd iterations +family prefix; existingCW+2
    return dict(schema='opentallas.w17.compact-descriptor-price.v1',status='PRICED_METADATA_CANDIDATE_PHYSICAL_AND_TOKEN_BLOCKED',
        source_pins={k:dict(commit=p[0],path=p[1],sha256=sha(data[k])) for k,p in PINS.items()},
        dense_existing_failures=dict(PHW6_entries=64,required_entries=1023,full_stage_appended_stream_words=base,
            stream_base_field_bits=16,first_stream_base_overflow=first_overflow,whole_stage_not_encodable_by_current_generator=True,rejected_stream_bases=145,parent_no_assert_truncation_changes_adjacent_nrows=True),
        owner_lookup=dict(policy='Explicit512x16 readonly table at each of40 logical layer-hubs/rank, 384valid entries; no combinational div/mod341 lookup credit',tables=tables,
            bits_per_entry=16,fields={'valid':1,'stage':6,'slot':9},logical_hubs=40,TP4_replicas=160,read_ports_per_replica=1,
            allocated_bits_fleet=owner_bits*160,analytic_register_mux_screen_mm2_per_replica=str(owner_area),analytic_screen_mm2_fleet=str(owner_area*160),
            proposed_registered_lookup_cycles=2,actual_SS_FF_or_macro_latency_qualified=False,hub_physical_assignment_pending=True),
        affine_address_generation=dict(formula='base=slot*pair_stride+family_prefix; logical=base+template_offset; parity=logical%2;physicalrow=logical//2',
            slot_bits=9,stride_bits=5,logical_address_bits=13,product_and_base_bits=14,
            policy='Per-pair fixed-stride five-step shift/add, one prefix-add step; registered13bit template-base rewrite on48bit config stream',
            shiftadd_iterations=5,prefix_add_cycles=1,register_bits_per_pair=affine_regs_per_pair,
            adder_gate_equivalents_per_pair=adder_gates_per_pair,template_mux_bit_equivalents_per_pair=muxbits_per_pair,
            replayed_stride_max=max(c['pair_stride'].values()),actual_adder_SS_FF_qualified=False),
        template_storage=dict(cfg_template_entries_allocated=4,cfg_words_per_template=25,cfg_bits_per_word=48,
            cfg_bits_per_pair=cfg_bits_per_pair,expert_q_pair_replicas=replicas,config_bits_fleet=cfg_bits_per_pair*replicas,
            spine_phase_template_bits_per_stage_rank=512,spine_stream_template_words=224,stream_bits_per_word=48,
            spine_stream_words_allocated=256,spine_bits_per_stage_rank=spine_bits,
            cfg_affine_register_mux_screen_mm2_per_pair=str(pair_area),cfg_affine_screen_mm2_per_stage_rank=str(pair_area*q),
            spine_register_storage_screen_mm2_per_stage_rank=str(spine_area),
            area_scope='Analytical register/mux/add gate candidate screen at50% density (not strict minimum), not ROMcompiler/measuredarea; excludes ownerdecode/clock/wake/broadcast/control/routes/CDC and does not add again existing cfg registers',
            mask_ROM_area_or_abstract=None,full_slot_fit=None),
        service_candidate=dict(owner_lookup_cycles=2,perpair_parallel_affine_precompute_cycles=6,
            cfg_read_bits_per_pair_cycle=48,cfg_read_ports_per_pair=1,per_stage_aggregate_local_cfg_bits_per_cycle=q*48,fullstage_cfg_bits_per_cycle_including_reserved_BF_clear=(q+1024)*48,reserved_BF_phase_clear_required=True,reserved_BF_clear_enable_control_area=None,
            cfg_load_cycles=27,affine_plus_cfg_cycles=cfg_service,
            per_family_cfg_plus_stream_issue_cycles={f:cfg_service+v for f,v in streams.items()},
            one_expert_three_family_cfg_plus_stream_cycles=3*cfg_service+sum(streams.values()),
            scope='Proposed parallel localcfg ports; current27cycle loader protocol plus6candidate arithmetic steps. Excludes lookup forselecteddispatch, broadcasts/CDC, GO/inputquantizer startup, actualwaits/reduction/drain/write/credit/wake. No throughput/clock proof.',
            actual_complete_stage_cycles=None,root_stop_cycles=None),
        interface_change=dict(new_slot_bits=9,new_family_bits=2,old_cfg_ph_bits=6,
            global_key_bits=17,local_identity_bits_required=10,
            existing_PHW6_compatible=False,new_template_rom_loader_and_spine_contract_required=True,
            old_dense_outputs_not_relabelled=True),
        clock_obligations='Union actualwake/drain/depth/acceptedoutput/credits;107root separate from3766gated. No fixed+127 or rootstop credit; standalonePGnot instantiated.',
        remaining=['Ownerkey validation/decode and bounded selectedexpert dispatch/return queues','Actual cfg/stream template word replay and bitexact dynamicbase patch','14bit arithmetic pipeline +template/localport area/SSFF +broadcast/CDC/rootfanout','DenseHCconstantoccupancy/qPPstrip area/hops/KV/publication','Complete actual stageevent providers and fulltoken calendar'],
        exact_gate_passed=False,physical_admission=False,engine_RTL_build_ready=False,adopt=False,full_token_cycles=None,full_token_rate=None,jobs_launched=0)
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2)+'\n')
