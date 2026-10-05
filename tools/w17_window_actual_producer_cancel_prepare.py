#!/usr/bin/env python3
"""Prepare actual producer opt-in source copy and source-bound integration plan.

No compiler, simulator, service, live overlay or core source mutation.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRODUCER='rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv'
CORE='rtl/hdc/v41x/ot_hdc_core_v41x.sv'
QE='rtl/hdc/v41/ot_hdc_v41_qe.sv'
NASH='8a156f62548aa927414d1d2e4f1a00baa2898bbf'
OUT=ROOT/'rtl/test/w17_window_actual_producer_cancel_prepared'
RECORD=ROOT/'results/uarch/w17_window_actual_producer_cancel_preparation_20261002'
NAME='ot_hdc_v41x_window_kv_blocks'

def origin(path):return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT).decode()
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def edit(s,old,new):
 if s.count(old)!=1:raise ValueError('expected exactly one source hook: '+old)
 return s.replace(old,new)

def candidate():
 original=origin(PRODUCER);start=original.index('module ');module=original[start:original.index('endmodule',start)+len('endmodule')]
 header=module[:module.index(');')+2];legacy=module.replace(NAME,NAME+'_cancel_legacy',1)
 enabled=module.replace(NAME,NAME+'_cancel_enabled',1)
 extra='''    input wire rec_freeze,
    input wire rec_cancel,
    input wire rec_token,
    input wire rec_suffix_closed,
    input wire rec_qe_idle,
    input wire rec_rearm,
    input wire rec_retired_certified,
    output reg rec_cancel_ack,
    output reg rec_cancel_token_ack
'''
 enabled=edit(enabled,'    output reg               fault\n','    output reg               fault,\n'+extra)
 enabled=edit(enabled,'    reg [1:0] state;','''    // Adapter holds rec_freeze independently of token-start-cleared core fault.
    // rec_cancel covers only local metadata, NEVER WINDOW or provider intent.
    wire rec_stop = rec_freeze || fault;
    reg [1:0] state;''')
 enabled=edit(enabled,"assign cap_ready = (state == EMPTY || state == FILL) && count < 5'd16;","assign cap_ready = !rec_stop && (state == EMPTY || state == FILL) && count < 5'd16;")
 enabled=edit(enabled,'assign issue_ready = state == FULL;','assign issue_ready = !rec_stop && state == FULL;')
 enabled=edit(enabled,'assign blk_v = state == DRAIN;','assign blk_v = !rec_stop && state == DRAIN;')
 enabled=edit(enabled,'            src_base <= 0; kvt_base <= 0; row <= 0; kvt_row <= 0;','''            src_base <= 0; kvt_base <= 0; row <= 0; kvt_row <= 0;
            rec_cancel_ack <= 0; rec_cancel_token_ack <= 0;''')
 enabled=edit(enabled,'        end else begin\n            if (cap_v) begin','''        end else if (rec_cancel) begin
            // No local reset: preserve sticky cause and accepted downstream work.
            if (rec_rearm || !(rec_freeze && rec_suffix_closed && rec_qe_idle)) begin
                fault <= 1'b1;
            end else if (!rec_cancel_ack) begin
                state <= EMPTY; count <= 0; rd_idx <= 0;
                rec_cancel_ack <= 1'b1; rec_cancel_token_ack <= rec_token;
            end else if (rec_cancel_token_ack != rec_token) begin
                fault <= 1'b1; // cannot turn an outstanding receipt into a new one
            end
        end else if (rec_rearm) begin
            // Certified means local+selected-owner retirement AND causal fences.
            // No such physical provider exists in current source; never use timer.
            if (rec_cancel_ack && rec_freeze && rec_suffix_closed && rec_qe_idle &&
                rec_retired_certified && rec_cancel_token_ack == rec_token) begin
                fault <= 1'b0; rec_cancel_ack <= 1'b0;
            end else fault <= 1'b1;
        end else begin
            if (cap_v && !rec_stop) begin''')
 enabled=edit(enabled,'            if (issue) begin','            if (issue && !rec_stop) begin')
 # The producer must inhibit simultaneous valid new work when local validation
 # discovers a fault at the same edge; original code otherwise commits in parallel.
 cap_bad="(cap_v && (!((state == EMPTY || state == FILL) && count < 5'd16) || cap_scale == 8'hff || (state == FILL && (cap_expected[AW] || cap_src_addr != cap_expected[AW-1:0])) || cap_src_addr[4:0] != 5'd0))"
 issue_bad="(issue && (state != FULL || issue_src_base != src_base || issue_abs >= POS_W'(1048576) || (SEPARATE_ROWS && issue_row >= POS_W'(128)) || issue_last_wide[AW]))"
 enabled=edit(enabled,'    assign cap_ready =',f'''    wire rec_local_bad = {cap_bad} || {issue_bad} || (cap_v && issue);
    assign cap_ready =''')
 enabled=edit(enabled,'if (cap_v && !rec_stop) begin','if (cap_v && !rec_stop && !rec_local_bad) begin')
 enabled=edit(enabled,'if (issue && !rec_stop) begin','if (issue && !rec_stop && !rec_local_bad) begin')
 enabled=edit(enabled,'            if (blk_v && blk_ready) begin','''            if (!rec_stop && rec_local_bad) fault <= 1'b1;
            if (blk_v && blk_ready && !rec_local_bad) begin''')
 # External handshake must also see the same local-error admission stop.
 enabled=edit(enabled,'assign blk_v = !rec_stop && state == DRAIN;','assign blk_v = !rec_stop && !rec_local_bad && state == DRAIN;')
 wrapper=header.replace(NAME,NAME+'_cancel',1)
 wrapper=edit(wrapper,'    parameter integer AW = 30,','    parameter integer OPT_CANCEL = 0,\n    parameter integer AW = 30,')
 wrapper=edit(wrapper,'    output reg               fault\n','    output wire              fault,\n'+extra.replace('output reg','output wire'))
 ports=re.findall(r'^\s*(?:input|output)\s+(?:wire|reg)\s+(?:\[[^\]]+\]\s+)?(\w+)',header,re.M)
 params='.AW(AW), .POS_W(POS_W), .KVT_SH(KVT_SH), .SEPARATE_ROWS(SEPARATE_ROWS)'
 connections=',\n'.join('    .'+x+'('+x+')' for x in ports)
 extras=['rec_freeze','rec_cancel','rec_token','rec_suffix_closed','rec_qe_idle','rec_rearm','rec_retired_certified','rec_cancel_ack','rec_cancel_token_ack']
 wrapper+='\ngenerate if (!OPT_CANCEL) begin : g_default\n'+NAME+'_cancel_legacy #('+params+') u_impl (\n'+connections+');\nassign rec_cancel_ack=0; assign rec_cancel_token_ack=0;\nend else begin : g_cancel\n'+NAME+'_cancel_enabled #('+params+') u_impl (\n'+connections+',\n'+',\n'.join('    .'+x+'('+x+')' for x in extras)+');\nend endgenerate\nendmodule\n'
 return original,wrapper+'\n'+legacy+'\n\n'+enabled+'\n',module,legacy,enabled

def plan():
 texts={p:origin(p) for p in (PRODUCER,CORE,QE)}
 core=texts[CORE];qe=texts[QE]
 for hook in ['.go(qe_go)', '.cap_v(win_capture_v)', 'wire win_issue = su_go && win_su_match && win_issue_ready;', 'else if (start && st == S_IDLE) fault <= 1\'b0;', 'w_we(ww_q_we)']:
  assert hook in core,hook
 assert 'kvb_v <= aq_vo && mode == QDQ8' in qe and 'kvb_fault <= aq_vo && mode == QDQ8' in qe
 nash_path='results/uarch/w17_window_qdq8_cancel_contract_20261002/interfaces.json';nash=subprocess.check_output(['git','show',NASH+':'+nash_path],cwd=ROOT)
 return {'status':'MODEL_PLUS_UNCOMPILED_ACTUAL_PRODUCER_COPY_ONLY_NO_CORE_OVERLAY',
  'source_commit':PIN,'source_sha256':{p:sha(s) for p,s in texts.items()},'Nash_contract_commit':NASH,'Nash_interfaces_sha256':hashlib.sha256(nash).hexdigest(),'selectedowner':'WIN_STACK2 / backend TAG100|epoch9|sector5','actual_shape':{'AW':30,'NW':21,'BL':16,'IL':8,'NBMAX':192,'CHUNK8':1,'MP':1,'QE_mode':1,'nb':16,'xbase':54720,'obase':55232},
  'core_hooks':[
   {'location':'S_ISSUE waited/unit_ready predicate + u_qe .go(qe_go)','change':'Gate both sequencer admission and actual QE go with sticky recovery freeze/current known fault. Gating go alone would let sequencer advance without actual acceptance. Gate selected mode1 on producer available and no old suffix; do not reset an active QE.'},
   {'location':'u_qe kvb_v / kvb_fault / ww_q_we / qe_idle','change':'Count each good OR poison terminal; verify exclusive good/poison and QDQ8 VM write correspondence. Continue raw QE reads/arithmetic/VM writes until source idle; never stall suffix on cap_ready or block client ready.'},
   {'location':'u_blocks .cap_v(win_capture_v)','change':'Suppress capture COMMIT after sticky freeze/current fault/poison; still observe and discard every fixed QE terminal independently. Producer cap_ready is capacity diagnostics, NEVER feed ready back into fixed QE output or into a cap_v/ready combinational loop. Poison is a terminal, not a missing block.'},
   {'location':'win_issue + win_scalar_suppress','change':'Gate actual issue and associated SU admission consistently; preserve existing scalar suppression for already accepted selected SU. Producer issue_ready stays independent of issue pulse, avoiding existing win_issue&&issue_ready feedback. Validate descriptor in S_ISSUE before SUgo; illegal descriptor must fault, not indefinite stall. No global SU-reset claim.'},
   {'location':'u_blocks blk_v/blk_ready -> guard -> WINDOW','change':'Stop new atomic block handshakes at fault; previously accepted33byte block remains WINDOW owned for BOTH WC and WS. Keep source fault-drain candidate continuation enabled.'},
   {'location':'core fault clear-on-start','change':'Hold recovery freeze/cause independently until full selected-owner retirement and certified delivery/causalvisibility fence. New start cannot implicitly clear cancellation state.'}],
  'local_cancel_contract':{'request':'held rec_cancel+rec_token after sticky freeze + all16 terminal outputs (or no QE accepted) + actual QE idle','ack':'metadata EMPTY/count0/rd_idx0 and held matching token; no payload zeroing, no source pending or provider credits cleared','producer_fault_rearm':'Explicit rec_rearm requires held matching cancel_ack/token + freeze + suffixclosed + QEidle + rec_retired_certified. The certified input MUST bind localcancel/QEidle/WINDOW ownerzero/muxKARBbackend retire/delivery fence/causalvisibility/provenance. No actual causal PHY provider exists; never assert it from projected deadline, timer, EMPTY or ACK. Token-start does not rearm. Source-copy hook only, not installed/qualified.','adapter_late_identity':'One closed QE operation, no tag added to sideband. Future suffix count5 active1 frozen1 provenance_fault1=8bits; any unexpected/duplicate terminal blocks rearm. Wire-identical ghost cannot be detected; provider provenance required.'},
  'unified_compatible_entry':{'applicable_designs':['v41_rom','v41_hbm'],'element':'actual_QDQ8_window_producer_cancel_adapter','replicas':1,'macs_per_cycle':0,'new_payload_bits':0,'prepared_local_ack_state_bits':2,'future_suffix_and_freeze_state_bits':8,'concrete_subtotal_bits':10,'prior_conservative_local_adapter_envelope_bits':19,'do_not_add_19_and10':True,'DFF_proxy_um2_subtotal':10*0.2916,'conservative_19_DFF_proxy_um2':19*0.2916,'control_ports_producer_added_bits':9,'existing_stream_per_terminal_bits':1+30+256+8+1,'terminal_event_rate_blocks_per_cycle':1,'ports_bytes_per_cycle':{'QE_codes_scale':33,'QE_VM_write':128,'accepted_WINDOW_block_payload':33},'boundary_bits_per_cycle':{'QE_sideband':296,'QE_VM_payload':1024,'producer_recovery_control':9},'control_boundary_track_proxy':9,'route_capacity':'UNBOUND; no physical channel/slot fit assertion','enable_mux_fanout_cost':'QEgo + capturecommit + producerissue + newblk gates; exact cell/SSFF cost unmeasured. No payload mux added.','area_slot_fit':'UNQUALIFIED; DFF-only proxy, needs enable gates plus actual layout slot pricing','healthy_added_stages_intended':0,'healthy_added_guard_cycles':0,'fault_latency':'remaining <=16 QE terminal outputs then actual sourceidle + registered localack; arbitrary stalls in provider drain have no finite bound absent bounded fairness/causal visibility/delivery contract','provider_composition':'259 prepared provider/source bits reused; 19 adapter envelope separate. Optional228read observer not mandatory hardware; actual PHY provider state unknown.'},
  'unchanged_healthy_landmarks':{'producer_EMPTY_cycle':871,'final_WR_ACK_cycle':905,'projected_visible_ps':911274,'projected_deadline_not_causal_completion':True},
  'next_review':{'no_compile_GO':True,'Nash_review_needed':['sameedge known versus delayed fault','goodORpoison + VM terminal conservation and actual sourceidle','S_ISSUE/go consistency and SU scalar suppression','sticky fault explicit rearm requirement before restart'], 'following_real_gate':'Reuse actual QE arithmetic/source and producer integration vectors after composition; do not replace QE with synthetic cap-v fixture. No bench added here.'},
  'qualification':{'local_source_hooks_prepared':True,'actual_core_adapter_installed':False,'causal_PHY_provider':False,'producer_safe':False,'restart_complete':False,'fulltoken':False,'adoption':False}}

def prepare():
 OUT.mkdir(parents=True,exist_ok=False);RECORD.mkdir(parents=True,exist_ok=False)
 original,text,module,legacy,enabled=candidate();assert legacy.replace(NAME+'_cancel_legacy',NAME,1)==module
 (OUT/'ot_hdc_v41x_window_kv_blocks_cancel.sv').write_text(text)
 (OUT/'enabled.diff').write_text(''.join(difflib.unified_diff(module.splitlines(True),enabled.replace(NAME+'_cancel_enabled',NAME,1).splitlines(True),fromfile=PRODUCER,tofile='generated_OPT_CANCEL1_producer')))
 r=plan();r.update(generator_sha256=sha(Path(__file__).read_text()),candidate_sha256=sha(text),default_inverse_byte_identical=True,prepared_declared_added_register_bits=2)
 (RECORD/'model.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');a=ap.parse_args()
 if a.prepare:prepare()
 else:print(json.dumps(plan(),indent=2))
