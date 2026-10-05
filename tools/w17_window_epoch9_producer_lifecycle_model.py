#!/usr/bin/env python3
"""Static producer/descriptor integration specification; no payload, RTL or builds."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
CORE='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv'
DIE='rtl/chip/ckvsel/ot_chip_v41x_die.sv'
PROGRAM='results/rtl/hdc_v41x_fullshape_1m_s20260930_program_bind_rope_hbm.json'
PATHS=[CORE,DIE,PROGRAM,'rtl/hdc/v41/ot_hdc_v41_qe.sv','rtl/chip/ot_chip_v41x_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv','rtl/chip/ot_chip_v41x_window_block_guard.sv','rtl/chip/ot_chip_v41x_window_kv_prefetch.sv','rtl/chip/ot_chip_v41x_window_attn_source.sv','rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv','rtl/chip/ot_chip_v41x_window_retention.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/test/v41_runtime/ot_v41_rt_die.sv','rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp']

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);args=ap.parse_args()
    raws={p:subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT) for p in PATHS}
    assert all((ROOT/p).read_bytes()==b for p,b in raws.items())
    program=json.loads(raws[PROGRAM]);pos=program['position'];rows=min(pos+1,128)
    assert rows==128 and pos==1048575
    desc=[]
    for x in program['instruction_trace']:
        f=x.get('fields',{})
        if f.get('me_mmode')!=1:continue
        resolved=dict(f)
        if f.get('me_d_nout')=='T0':resolved['me_nout']=rows
        if f.get('me_d_tiles')==['ceil','T0',32]:resolved['me_tiles']=(rows+31)//32
        if f.get('me_d_k')=='T0':resolved['me_k']=rows
        desc.append(dict(pc=x['pc'],tag=x['tag'],fields=resolved))
    assert [d['pc'] for d in desc]==[24,32]
    producer_instructions=[x for x in program['instruction_trace'] if x['pc'] in (20,21,22)]
    assert producer_instructions[0]['fields']['qe_nb']==16 and producer_instructions[0]['fields']['qe_obase']==55232
    assert producer_instructions[1]['fields']['a_base']==55232 and producer_instructions[1]['fields']['dst']==3
    q,p=[d['fields'] for d in desc]
    assert (q['me_ts'],q['me_ks'],q['me_k'],q['me_nout'],q['me_tiles'])==(512,1,512,128,4)
    assert (p['me_ts'],p['me_ks'],p['me_k'],p['me_nout'],p['me_tiles'])==(1,32,128,512,16)
    idx=raws['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'].decode()
    timing={n:int(re.search(r'parameter integer\s+'+n+r'\s*=\s*(\d+)',idx)[1]) for n in ('CLK_PS','CWL_PS','BURST_PS','WTRS_PS','WTRL_PS','CL_PS')}
    visibility=timing['CWL_PS']+timing['BURST_PS'];tail=(visibility+timing['CLK_PS']-1)//timing['CLK_PS']-1
    assert visibility==7274 and tail==7
    producer_bits=16*256+16*8+2+5+4+2*30+2*21+1
    life_bits=3+2*16+10+4*21+4*30+2+1+2*11+1+1+4
    assert 'refill_epoch <= refill_epoch + 1\'b1;' in raws['rtl/chip/ot_chip_v41x_window_kv_prefetch.sv'].decode()
    r=dict(schema='opentallas.window_epoch9.producer_lifecycle_model.v1',source_commit=PIN,
        source_sha256={p:sha(b) for p,b in raws.items()},generator_sha256=sha(Path(__file__).read_bytes()),
        verdict='STATIC_HEALTHY_INTEGRATION_SPEC_READY_WRITE_VISIBILITY_AND_SYSTEM_RECOVERY_UNQUALIFIED',
        actual_descriptors=desc,producer_instructions=producer_instructions,
        producer=dict(path='QE QDQ8 kvb capture -> window_kv_blocks -> tile win_blk_user -> die block guard -> source WC/WS',
            capture_instruction_PC=20,capture_base=55232,capture_address='QE obase+(block_index<<5); verified kvb_src_addr source',drain_instruction_PC=21,scalar_alias_instruction_PC=22,capture_blocks=16,codes_per_block=32,block_payload_bits=264,one_row_payload_bits=4224,
            producer_state_bits=producer_bits,source_user_bits=10,source_row_bits=21,block_idx_bits=4,
            capture_contract='16 contiguous32-element-aligned captures; FULL admits matching SU WINM1 drain; DRAIN holds block until accepted. Core suppresses scalar KVT writes for this exact capture provenance.',
            row_identity=dict(absolute_row=pos,local_KVT_row=127,HBM_slot=pos%128,
                first_element='kvt_base+((local_row>>4)<<13)+(block_idx<<9)+(local_row&15)'),
            writes_per_new_row=32,code_full_sector_writes=16,scale_masked_sector_writes=16,
            payload_bytes=528,request_data_boundary_bytes=32*32,
            write_control='WC grant -> WC_DONE ack -> WS grant(single-byte strobe at block_idx) -> WS_DONE ack. One global write at a time; tags remain sector0..15/code,16/scale, independent of refill credits/epoch.',
            logical_row_publish='block_valid bits ordered0..15; row_valid set only after block15 WS_DONE. Stage invalidated by accepted block/prime. Producer becomes EMPTY at final block acceptance, before source finishes its writes: producer idle alone is not row/write drain.'),
        step_user_reset=dict(host='t_start captures10-bit host_user and step_pos. Host start must occur only when previous core/service/lifecycle/producer operation is drained; wrapper has no general start_ready guard.',
            controller='core_user registered with core_start; die captures one edge later, producer follows many cycles later. Verify this path separately before multiuser claims.',
            reset='Two-flop die reset synchronizer rn is driven by external rst_n. t_start resets neither lifecycle last_gen nor source refill_epoch. No per-token reset assumption; runtime driver boots once and starts one L0 step.',
            isolation='User/absolute row participate in row+stage provenance and lifecycle descriptor stability. User not carried in backend tag; single active source and empty-row transport enforce ownership. Configuration/user changes only at drained operation boundaries.'),
        operation_lifecycle=dict(state_storage_bits=life_bits,GENW=16,GEN0='forbidden; generation wraps65535->1 with wrap_drained',
            transitions='IDLE accepts descriptor -> STAGE actual source stage -> READY issue_ok -> ARM engine starts -> STREAM32masked beats with matching generation -> DRAIN engine idle -> done.',
            stage_and_beat_gen='Die latches win_service_gen from att_packed_desc_gen at actual window_source_start; source does not create descriptor generation. Both stage and beat labels use that latched16bit generation.',
            operation_binding='QK PC24 rows derive nout because ks1; PV PC32 rows derive k because ks32; both128 rows. Source start_first=pos-127 and count128. No simulator force/epoch seeding permitted in future producer integration.',
            nonretain_readiness='desc_accept is lifecycle-IDLE based; source start_ready not explicitly in nonretained desc gate. Future test must prove lifecycle idle implies source ready and producer writes drained, or separately model an admission guard.',
            lifecycle_wrap_check='Existing wrap_drained checks !service_busy && window_prime_ready && !win_blk_v, not physical write visibility. Peirce owns stronger recovery/quiescence composition.'),
        epoch_lifetime=dict(width=9,initial=0,advance='Only accepted cold row prefetch in REFILL_CREDITS>1. Writes/prime/t_start/newuser/descriptor completion do not reset or advance it.',
            L0_per_step_cold_max=256,L0_retained_pair_max=128,
            unbounded_repeated_steps='Persistent modulo512 across operations and token starts. Two nonretained128+128 L0 pairs reach epoch0; next job reuses1 only after healthy row transport drain. There is no finite whole-session lifetime bound without operation count.',
            descriptor_gen_independent='16bit generation changes once per accepted operation; not concatenated with row epoch or backend tags. Gen wrap and epoch wrap are distinct contracts.',
            healthy_invariant='Before each advance: all previously admitted WINDOW request/reply state retired exactly once, no replay/hidden queues; reused epoch cannot certify absence of a ghost. Fault path delegated to Peirce.'),
        retention=dict(default=0,qualification='Only exact L0 QK->PV signatures resolved above, same normalized key; new nonzero descriptor generation different from QK.',
            key_bits=320,content_epoch_bits=32,retention_additional_control_bits=824,
            invalidation='t_start, accepted block/prime, region/config change, explicit invalidate, faults; generation_wrap forces miss. Stage can be reused only for one PV after QK lifecycle done AND engine idle AND source storage drained.',
            content_epoch='Increments on mutation cycles; independent of9bit row epoch. No across-token cache. Intervening prime/write/user/config/step disallows hit.',
            hit_cost='No row epochs/refill requests; refill counter0, but registered decision/dispatch, lifecycle and replay edges remain. Do not subtract an independently cold20,601 prediction from a later PV calendar.'),
        write_visibility=dict(timing_parameters_ps=timing,WR_model='idx_hbm commits masked mem[addr %MEM_WORDS] and sets wr_done at WRcolumn issue edge I; source sees registered ack at I+1.',
            physical_data_visibility_lag_ps=visibility,physical_visibility_deadline='tcol+CWL_PS+BURST_PS; source-observed wr_done alone is not physical write completion or all-owner quiescence.',
            final_row_visibility_guard=dict(conditional_wait_after_last_ack_cycles=tail,clock_ps=1000,
                proof='All32 writes globally serialized. Each WRtcol is no later than its issue edgeI; latest observedackA=I+1. AtA+7, (I+8)*1000 >= tcol+7274. Earlier acknowledged writes complete by same deadline. Valid only for pinned registered next-edge ack and stated timings.',
                minimal_future_control_bits=4,control='3bit countdown7..0 plus final-ack-seen1; keep final WS_DONE until countdown finishes, gate row_valid/producer ready/prefetch, reuse held row/user, no new payload or FSM state.',
                added_critical_cycles_upper_bound_per_new_row=7,
                alternative='Use actual physical write-visible completion/watermark, not wr_done; width/ports/latency require owning PHY interface model before RTL.'),
            read_turnaround='Pinned RDcolumn after latestWR is constrained by CWL+BURST+WTR(S/L): >=11649/13524ps, exceeding write-visible7274ps by4375/6250ps. This protects same-PC modeled read scheduling, but does not upgrade ack or row_valid into a universal physical publication/reset proof.',
            qualification='WR semantic gap preserved, not an observed numerical failure. No producer-write simulation launched. The guard is a model/spec only, not implemented or adopted.'),
        address_contract=dict(AW=30,MEM_WORDS=264320,original_MOD='Every modeled access indexes addr %MEM_WORDS; that operation cannot prove fullAW capacity or unconditional alias safety.',
            no_alias_condition='For every admitted address including burst beats: 0<=address<MEM_WORDS; additionally regions/users disjoint and no width overflow.',
            window_address='base+user*2176+(absolute_row&127)*17+sector',
            bounded_user0='base262144, user0 spans262144..264319 so MEM_WORDS264320 injective; user1 is outside this fixture and forbidden without increased allocation/new finite model.',
            writer_restricted='Currentrow slot127 code16fullwrites+scale16maskedwrites must match same generation/provenance; historical127rows may use legitimate primeAPI, currentrow must come from actual capture/blk port, not prime.'),
        future_parameter_plumbing=dict(status='SPEC_ONLY_NO_RTL_OR_WRAPPER_EDITS',
            existing_die='WINDOW_REFILL_CREDITS default1; opt-in8, WINDOW_RETAIN_L0 default0, WINDOW_STREAM_II1 unchanged0.',
            missing_runtime='ot_v41_rt_die lacks exposed credit/retention pass-through and currently instantiates unchanged source. Future isolated new simulation wrapper/copies must pass defaults1/0 with explicit candidate8/retain opt-ins and select exactly qualified9bit prefetch/source copies in source manifest.',
            production_guard='Do not compile original11bit prefetch with credit8 as a safeepoch adoption. Existing credit1 remains sector-only. No global overlay/source replacement.',
            external_interfaces='No new tag/user widths or payload/ports for healthy9bit encoding; writer-visible completion is a separate model interface; fault-drain interface owned by Peirce.'),
        full_token_composition=dict(status='UNPRICED_NO_TOTAL_RATE_TRANSFER',
            causal_cost='sum each actual descriptor-dependent cold refill event calendar + producer capture/writes/visibility tail + generation/stage/engine/stream barriers + all other scheduled core/ROM/collective/serial work. Starts and bank/refresh state come from preceding operations, not reset again.',
            L0_count='Pinned program has2WINDOW mmode operations QK/PV; retention may eliminate PV fetch only when exact qualified hit. Later layers/CKV descriptor shapes are not transferred from this L0 result.',
            measured_conditional_cold_refill=20601,total_layer_or_token_cycles=None,
            write_guard_additional_cycles_upper_bound_one_current_row=7,
            excluded='No40*L0, no warmtoken or whole-token headline; 1percent adoption criterion cannot be evaluated until composed actual program critical path is priced.'),
        minimal_next_gate=['Review this finite producer/write-visibility model and Peirce interface boundary before any producer bench.','Isolated producer+lifecycle fixture driven by actual QE capture interface,16orderedblocks, step user/pos, actual QK/PV descriptors and engine-idle/issue/beat controls; no simulator epoch force, no full engine build.','Check actual row publication before QK, fresh descriptor generations through QK/PV, retained miss/hit/mutation rules, data addresses injective and no producer/source idle gap misuse.','Healthy no-force wrap can use repeated legitimate QK/PV operations; write visibility controls compared to delayed-commit model, no reset-per-token. Fault/recovery joins only after Peirce contract; no duplicate recovery bench.'],
        parent_evidence=dict(candidate_intake='3f63970f3',independent_connected='7a355939e',metadata_failure='4bfc480f9',metadata_fix='81de41b21'),
        no_payload_reads=True,no_build=True,no_live_or_main_edit=True)
    out=(ROOT/args.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'verdict':r['verdict'],'descriptors':[d['pc'] for d in desc],'producer_bits':producer_bits,'lifecycle_bits':life_bits,'write_visibility_ps':visibility,'tail_cycles':tail},indent=2))
if __name__=='__main__':main()
