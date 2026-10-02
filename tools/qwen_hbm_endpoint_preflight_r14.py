#!/usr/bin/env python3
"""Emit source-only endpoint inventory/admission failures. No compiler or simulator."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from run_hbm_finite_stage_r14 import ROOT, TOOLROOT, manifest, compile_argv, IMAGE
from qwen_hbm_r14_metadata import emit

def sha(raw): return hashlib.sha256(raw).hexdigest()

def record():
    original='8e0f4d1eaad24ea79b9569089fc732df2635fdf6'
    paths=manifest();original_pins={}
    for path in paths:
        if path.startswith(('rtl/abi3/','physical/')):
            raw=subprocess.check_output(['git','show',f'{original}:{path}'],cwd=ROOT)
            assert raw==(ROOT/path).read_bytes(), path
            original_pins[path]={'commit':original,'SHA256':sha(raw),'byte_identical':True}
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/'rom.svh';metadata=emit(rom)
        assert rom.read_bytes()==(ROOT/'rtl/test/model_ready_hbm_r14/qwen_stage_metadata_r14.svh').read_bytes()
    version=subprocess.check_output([str(TOOLROOT/'bin/verilator'),'--version'],text=True).strip()
    # Wrapper help is supported. Direct verilator_bin --help is not; no fallback build.
    help_result=subprocess.run([str(TOOLROOT/'bin/verilator'),'--help'],capture_output=True,text=True)
    assert '--binary' in help_result.stdout and '--timing' in help_result.stdout
    tool={name:sha((TOOLROOT/'bin'/name).read_bytes()) for name in ['verilator','verilator_bin']}
    owner=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv').read_text()
    assert 'if(remaining_PC[tag_saved]==1)' in owner and 'live[tag_saved]<=0' in owner
    return {
      'status':'BLOCKED_SOURCE_REVIEW_NO_RTL_EXECUTION_ADMISSION',
      'base_commit':original,'source_manifest':paths,
      'source_manifest_SHA256':sha(json.dumps(paths,sort_keys=True,separators=(',',':')).encode()),
      'original_pins':original_pins,'metadata':metadata,
      'tool':{'path':str(TOOLROOT/'bin/verilator'),'version':version,'SHA256':tool,
              'binary_option_documented':True,'direct_binary_help':'Unsupported, invalid option; wrapper help verified'},
      'implemented_candidate_paths':['Causal per-PC ACT/PRE/column/refresh handshakes',
        'Whole472bit queue reorder carries full producer64/transport32 epochs',
        'Four pending WR slots reserved before headpop; delayed backing guard>=8COREedges',
        'Exact local bounds before AW31 physical narrowing; LEN6/BEAT5 native ports',
        'Real SRAM context lookup restores immutable identity',
        'Actual sector store, registered sector retire, reverse credit and held grant',
        'Distinct actual generic IRS and reader ledger/lease interfaces',
        'Finite RF RMW27SER pipeline and cancellation drain'],
      'geometry_inheritance':{'source_r11':'ba5ca57274dba17a5ae1751e8d6632f532017e27',
        'Qwen_slot_mm2_per_stack':16.6015872,'Qwen_r11_modeled_need_mm2_per_stack':16.582108825564255,
        'map_budget_mm2_per_stack':0.69093226712,'Qwen_residents_per_die':676,'DS_residents_per_die':292,
        'DS_service_fit':'OPEN_SEPARATE_INVENTORY_NO_QWEN_TRANSFER',
        'r14_actual_source_fit':False,'PHY_replacement_credit_mm2':0},
      'named_exact_inventory_subset':{
        'per_stack_queue_macros':{'64x512_1R1W_request':32,'64x512_1R1W_return':32},
        'per_stack_context_macros':{'128x256_1R1W':32},
        'tag_root_live_bits':4096,'tag_root_remaining_PC_bits':4096*6,
        'CAM_bits':32*128*13,'seen_beat_bits':32*128*32,
        'tag_owner_named_state_subtotal_bits':4096+4096*6+32*128*(13+32),
        'per_PC_bank_and_calendar_bits':32*(19+64*3)+32+(4+4+4+4+2)*64,
        'per_PC_scan_address_write_arrival_bits':16*(34+1+64),
        'per_PC_held_best_bits':2*472,'per_PC_return_staging_bits':3*471,
        'per_PC_journal_register_bits':8+472,
        'per_die_four_stack_three_bridge_bits':4*(5*(455+467+404)+3*(2*26+7)),
        'sector_store_named_state_bits':4*192+16+272+9+1+2+2+465+1,
        'reader_lease_named_state_bits':4+96+24+6*5+6*32+12+4*192+288+10,
        'not_a_complete_FF_or_cell_area_count':True,
        'replacement_credit':0,'timer_width_reduction':False,'macro_refund':0},
      'latency_contract':{'CORE_ps':1000,'FAST_ps':'2500/3','SER_ps':'10000/9',
        'scans':'Serialized first16 with source18..35edge freeze and headprefetch; CORE edges, not FAST',
        'bridge_no_stall_contribution':'42FAST +3destination_edges; actual stalls additional',
        'WR_backing_minimum_source_ps':7274,'WR_guard_CORE_edges':8,
        'RMW_SER_edges':27,'owner_lookup_CORE_edges':12,'return_arbitration_CORE_edges':6,
        'critical_path':'max(request/queue_ready, refresh/bank/timing, WRreservation/RAWdependency), then actual column->CWL/burst->backing ACK->owner lookup->CDC/route->store->registered retire->reverse CDC->held grant->forward CDC->consumer release',
        'additional_grant_roundtrip':'Must be added to inherited r13 latency; not free and not yet replayed',
        'effective_bandwidth_or_per_user_rate_credit':0,'SS_FF_qualification':False},
      'blockers':[
        {'id':'R14_TAG_LIFETIME_FAIL','path':'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
         'witness':'held&&ore -> remaining_PC==1 -> live[tag_saved]<=0 before actual reverse credit',
         'effect':'Physical tag lifetime ends at return delivery rather than downstream ownership retirement.',
         'required_change':'Retain quarantine until validated addressed per-beat reverse credits finish; price state and duplicate/epoch validation. Root count proof alone insufficient.'},
        {'id':'R14_READER_CREDIT_VALIDATION_OPEN','path':'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
         'witness':'if(!credit_we) credit_match=1',
         'effect':'CORE grants reader reverse packet without validating against retained physical owner context.',
         'required_change':'Use retained immutable context and per-beat retired credit state; reject stale/duplicate/mismatched full identity.'},
        {'id':'R14_RMW_AND_BURST_REVERSE_ENDPOINT_MISSING',
         'paths':['rtl/model_ready_hbm_r14/ot_hbm_r14_finite_client.sv','rtl/test/model_ready_hbm_r14/ot_hbm_r14_burst_client.sv'],
         'witness':'RMW MERGED pulses RMW_retire then proceeds directly to WRREQ; diagnostic burst marks seen/done without reverse endpoint.',
         'effect':'Retaining tag quarantine would reveal undrained RMW and diagnostic-reader physical owners.',
         'required_change':'Wire separate RMW-read and burst-read reverse retirement acknowledgements before tag reuse; retain real272 opcode/sector distinction and reader288 lease distinction.'},
        {'id':'R14_MAP_AND_COMPOSED_SLOT_ACCOUNTING_OPEN',
         'effect':'Named state subset is available; mux/decode/clock and required quarantine additions are not fully reconciled against0.690932/16.6015872 budgets.',
         'required_change':'Complete source-level cell inventory and revised causal schedule including grant roundtrip before execution GO.'},
        {'id':'R14_INDEPENDENT_JOURNAL_AUDIT_PARTIAL',
         'effect':'Partial auditor covers exact address bankmap and7274ps backing floor only; no comprehensive providerPASS.',
         'required_change':'Full currentrefresh/ACT/turnaround/allocation-generation/retirement/IRS/lease checks and intended mutant reason validation.'}],
      'finite_gate':{'source_only':True,'compiled':False,'simulated':False,'full_engine_joined':False,
        'case0':'Actual one-channel gateway and32beat diagnostic traffic; not opcode17 execution',
        'case1':'Two272writer phases,256RMW each,288reader ownership; integer test SCORES/EXP/PV commit producers, not golden arithmetic',
        'case2':'Canceled writer delayed backing and actual retirement drain',
        'case3':'Canceled reader actual return/reverse drain; no unissued opcode discard callbacks',
        'case4':'Held invalidAW2^32 negative case',
        'mutants':['earlyWRbacking','fullAWalias','BEAT4wrap','producerEpochcorruption'],
        'caps':{'CPU_count':1,'memory_GiB':4,'swap':0,'compile_seconds':120,'all_sims_seconds':30,'whole_cgroup_seconds':150,'cycles_per_case':500000},
        'compile_argv':compile_argv(Path('/EXTERNAL_REVIEWED_OUTPUT')),'image':IMAGE,
        'execution_GO':'NONE; reviewed source manifest plus inventory_and_tag_quarantine_admitted required'},
      'fleet':{'our_existing_pve2_jobs':[],'our_existing_pve3_jobs':[],'our_queued_launches':[],
               'new_pve2_or_pve3_admissions':False,'new_jobs_launched':0},
      'arithmetic_admission':'Parentb33395215 commonBF16mul underflow failure retained; no differential qualification transfer',
      'failure_preservation':'4933ebbf and original r5 retrospectiveACT/earlyWR/AWalias evidence retained unchanged'}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(record(),indent=2,sort_keys=True)+'\n')
