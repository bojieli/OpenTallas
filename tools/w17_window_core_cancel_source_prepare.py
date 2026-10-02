#!/usr/bin/env python3
"""Actual core source-copy preparation; no build, source selection or provider."""
from pathlib import Path
import re,json,hashlib,subprocess,difflib
ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRODUCER_PIN='3625a502b889d3a69aada6796cd9ceb8eefb6810'
PRODUCER='rtl/test/w17_window_actual_producer_cancel_declaration_repaired/ot_hdc_v41x_window_kv_blocks_cancel.sv'
NAME='ot_hdc_core_v41x'
ORIGINS={'base':'rtl/hdc/v41x/ot_hdc_core_v41x.sv','fastpp':'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv'}
OUT=ROOT/'rtl/test/w17_window_core_cancel_prepared_r7'
RECORD=ROOT/'results/uarch/w17_window_core_cancel_source_preparation_r7_20261002'

def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT).decode()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def edit(s,a,b):
 if s.count(a)!=1:raise ValueError('source hook not unique: '+a)
 return s.replace(a,b)

def extract(s):
 starts=list(re.finditer(r'^module '+NAME+r' #\(',s,re.M));ends=list(re.finditer(r'^endmodule\s*$',s,re.M))
 if len(starts)!=1 or len(ends)!=1:raise ValueError('anchored core boundaries')
 return s[starts[0].start():ends[0].end()]

CONTROL='''
    input wire rec_request,
    input wire rec_token,
    input wire rec_rearm_request,
    input wire rec_provider_ready,
    input wire rec_delivery_certified,
    input wire rec_visibility_certified,
    input wire rec_provenance_valid,
    input wire rec_fault_inject,
    output wire rec_frozen_out,
    output wire rec_local_ack,
    output wire rec_local_token_ack,
    output wire rec_commit_qualified,
    output wire rec_provenance_fault
'''

LOGIC='''
    // One selected QDQ8 operation; no new identity/provider on output wires.
    reg [4:0] rec_suffix;
    reg rec_active, rec_frozen, rec_violation;
    wire rec_terminal = win_capture_v || win_capture_fault;
    wire rec_qe_idle_raw = RAW_QE_IDLE;
    wire rec_raw_qe_accept = qe_go && qe_ready && qe_mode == 2'd1;
    wire rec_bad_terminal = (win_capture_v && win_capture_fault) ||
        (rec_terminal && (!rec_active || rec_suffix >= 16)) ||
        ((rec_active || rec_terminal) && (rec_terminal != ww_q_we[0]));
    wire rec_bad_qe_go = qe_go && (!qe_ready ||
        (qe_mode == 2'd1 && (!win_idle || rec_active)));
    // Scope is the pinned PC20 QDQ8 / PC21 packed writer; PC22 scalar alias excluded.
    // Registered decode operands become current AFTER the S_DEC NBA edge.
    wire [AW:0] rec_issue_last = {1'b0,o_base} +
        ((((AW+1)'(o_row[NW-1:0]) >> 4) << 13)) +
        ((AW+1)'(511) << 4) + (AW+1)'(o_row[3:0]);
    // PC21's current IR is already valid in S_DEC; prior registered QE operands are not.
    wire [AW-1:0] rec_current_base = ir[O_A_BASE +: W_A_BASE] +
        dyn[c_dslot * NDYN + ir[O_A_D +: W_A_D]];
    wire [AW-1:0] rec_current_row = dyn[c_dslot * NDYN + ir[O_O_D +: W_O_D]];
    wire [AW:0] rec_current_last = {1'b0,ir[O_O_BASE +: W_O_BASE]} +
        ((((AW+1)'(rec_current_row) >> 4) << 13)) +
        ((AW+1)'(511) << 4) + (AW+1)'(rec_current_row[3:0]);
    wire rec_bad_current_descriptor = st == S_DEC && pc == PAW'(21) &&
        (c_unit != 2 || ir[O_DST +: W_DST] != 3 || ir[O_A_SRC +: W_A_SRC] != 0 ||
         c_su_nout != 1 || c_su_nin != 512 || rec_current_row >= AW'(128) ||
         rec_current_last[AW] || (rec_suffix == 16 && rec_current_base != win_cap_src_base));
    wire rec_bad_selected_descriptor = st == S_ISSUE &&
        pc == PAW'(21) && (d_unit != 2 || dst != 3 || a_src != 0 ||
            su_nout != 1 || su_nin != 512 ||
            (rec_suffix == 16 && a_base != win_cap_src_base) ||
            win_abs_row >= NW'(1048576) ||
            o_row >= AW'(128) || rec_issue_last[AW]);
    wire rec_bad_su_terminal = su_go && win_su_match && rec_terminal;
    // Ready includes the cancellation gate: never feed it back into rec_stop.
    wire rec_bad_su_ready = su_go && (!su_ready ||
        (win_su_match && !win_issue_ready));
    wire rec_stop = rec_frozen || rec_violation || rec_request ||
        rec_fault_inject || fault || me_fault || su_fault || qe_fault || xu_fault || he_fault ||
        (FULL_SHAPE && (coll_fault || rope_pf_fault)) || ROM_FAULT
        win_fault || win_capture_fault ||
        rec_bad_terminal || rec_bad_qe_go || rec_bad_su_terminal ||
        rec_bad_selected_descriptor || rec_bad_current_descriptor;
    wire rec_suffix_closed = rec_qe_idle_raw && !rec_terminal && !ww_q_we[0] &&
        (!rec_active || rec_suffix == 16);
    wire rec_cancel_local = rec_stop && rec_suffix_closed;
    wire rec_rearm = rec_rearm_request && rec_frozen && !rec_violation &&
        rec_local_ack && rec_local_token_ack == rec_token && rec_suffix_closed && su_idle &&
        win_idle && rec_provider_ready && rec_delivery_certified &&
        rec_visibility_certified && rec_provenance_valid;
    wire rec_qe_go = qe_go && !rec_stop && !rec_rearm;
    wire rec_su_go = su_go && !rec_stop && !rec_rearm && !rec_bad_su_ready;
    wire rec_cap_v = win_capture_v && !rec_stop && !rec_rearm;
    assign rec_frozen_out = rec_stop;
    assign rec_provenance_fault = rec_violation;
    assign rec_commit_qualified = rec_rearm;
    // Existing producer ACK/token registers provide the local receipt.
    // rec_token must be held by caller from request through shared rearm.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rec_suffix <= 0; rec_active <= 0; rec_frozen <= 0; rec_violation <= 0;
        end else begin
            if (rec_terminal && rec_active && rec_suffix < 16)
                rec_suffix <= rec_suffix + 1'b1;
            if (rec_raw_qe_accept && !rec_stop && !rec_rearm) begin
                rec_active <= 1; rec_suffix <= 0;
            end else if (rec_active && rec_suffix_closed) rec_active <= 0;
            if (rec_bad_terminal || rec_bad_qe_go || rec_bad_su_terminal ||
                rec_bad_selected_descriptor || rec_bad_current_descriptor ||
                (!rec_stop && rec_bad_su_ready) ||
                (rec_cap_v && !win_cap_ready)) rec_violation <= 1;
            if (rec_stop || rec_bad_su_ready || (rec_cap_v && !win_cap_ready)) rec_frozen <= 1;
            if (rec_rearm) begin rec_frozen <= 0; rec_suffix <= 0; end
        end
    end
    initial if (!FULL_SHAPE || !KV_HBM || MP != 1 || AW != 30 || NW != 21)
        $fatal(1,"prepared selected QDQ8 cancel core shape");
'''

def header_end(module):
 closes=list(re.finditer(r'^\);[ \t]*$',module,re.M))
 if len(closes)!=1:raise ValueError('actual anchored port closing line')
 return closes[0].start()+2

def generate(kind):
 raw=blob(PIN,ORIGINS[kind]);module=extract(raw);header=module[:header_end(module)]
 params=re.findall(r'parameter\s+integer\s+(\w+)\s*=',header)
 ports=re.findall(r'^\s*(?:input|output)\s+(?:wire|reg)\s+(?:\[[^\]]+\]\s+)?(\w+)',header,re.M)
 if len(ports)<200 or len(params)<45:raise ValueError('incomplete actual header')
 if len(set(params))!=len(params) or len(set(ports))!=len(ports):raise ValueError('header identity collision')
 base=NAME+'_cancel_'+kind;legacy=module.replace(NAME,base+'_legacy',1);enabled=module.replace(NAME,base+'_enabled',1)
 enabled=enabled[:header_end(enabled)-2] + ',\n'+CONTROL+enabled[header_end(enabled)-2:]
 logic=LOGIC.replace('RAW_QE_IDLE','qe_idle_e' if kind=='fastpp' else 'qe_idle').replace('ROM_FAULT', 'rom_fault_w ||' if kind=='fastpp' else '')
 enabled=edit(enabled,'    // The captured QDQ8 VM row is the provenance',logic+'\n    // The captured QDQ8 VM row is the provenance')
 # Stop at BOTH registered-go consumer edge and source sequencer edge.
 enabled=edit(enabled,'            if (FULL_SHAPE && (coll_fault || rope_pf_fault)) st <= S_COLL_HALT;',
 '''            if (rec_rearm) st <= S_IDLE;
            else if (rec_stop || rec_bad_su_ready) st <= S_COLL_HALT; // PC held; accepted engines keep draining
            else if (FULL_SHAPE && (coll_fault || rope_pf_fault)) st <= S_COLL_HALT;''')
 if kind=='fastpp':enabled=edit(enabled,'wire qe_go_e = qe_go && !qe_rom;','wire qe_go_e = rec_qe_go && !qe_rom;');enabled=edit(enabled,'wire rom_q_go = qe_go && qe_rom;','wire rom_q_go = rec_qe_go && qe_rom;')
 else:enabled=edit(enabled,'.go(qe_go), .ready(qe_ready)', '.go(rec_qe_go), .ready(qe_ready)')
 # Other SU variants retain geometry and accepted pipeline suffix; only go changes.
 enabled=enabled.replace('.go(su_go)', '.go(rec_su_go)').replace('.go(su_go &&', '.go(rec_su_go &&')
 enabled=edit(enabled,'wire win_issue = su_go && win_su_match && win_issue_ready;', 'wire win_issue = rec_su_go && win_su_match && win_issue_ready;')
 enabled=edit(enabled,'else if (su_idle && !su_go) win_scalar_suppress <= 1\'b0;', 'else if (su_idle && !rec_su_go) win_scalar_suppress <= 1\'b0;')
 enabled=edit(enabled,'else if (start && st == S_IDLE) fault <= 1\'b0;', 'else if (rec_rearm) fault <= 1\'b0;\n        else if (start && st == S_IDLE && !rec_stop) fault <= 1\'b0;')
 enabled=edit(enabled,'ot_hdc_v41x_window_kv_blocks #(.AW(AW)', 'ot_hdc_v41x_window_kv_blocks_cancel #(.OPT_CANCEL(1), .AW(AW)')
 enabled=edit(enabled,'.rst_n(rst_n), .cap_v(win_capture_v)', '.rst_n(rst_n), .cap_v(rec_cap_v)')
 enabled=edit(enabled,'.blk_scale(win_blk_scale), .fault(win_fault));', '''.blk_scale(win_blk_scale), .fault(win_fault),
            .rec_freeze(rec_stop), .rec_cancel(rec_cancel_local && !rec_rearm),
            .rec_token(rec_token), .rec_suffix_closed(rec_suffix_closed),
            .rec_qe_idle(rec_qe_idle_raw), .rec_rearm(rec_rearm),
            .rec_retired_certified(rec_rearm), .rec_cancel_ack(rec_local_ack),
            .rec_cancel_token_ack(rec_local_token_ack));''')
 # Raw QE VM port and every arithmetic/helper connection remains unchanged.
 wrapper=header.replace(NAME,base,1).replace('output reg','output wire')
 wrapper=edit(wrapper,'    parameter integer FULL_SHAPE = 0,','    parameter integer OPT_CORE_PRODUCER_CANCEL = 0,\n    parameter integer FULL_SHAPE = 0,')
 wrapper=wrapper[:header_end(wrapper)-2]+',\n'+CONTROL+wrapper[header_end(wrapper)-2:]
 forwarding=', '.join('.'+x+'('+x+')' for x in params);connect=',\n'.join('    .'+x+'('+x+')' for x in ports)
 controls=re.findall(r'^\s*(?:input|output) wire (\w+)',CONTROL,re.M)
 wrapper+='\ngenerate if (!OPT_CORE_PRODUCER_CANCEL) begin : g_default\n'+base+'_legacy #('+forwarding+') u_impl (\n'+connect+');\n'
 for x in controls:
  if x.startswith('rec_') and ('output wire '+x) in CONTROL:wrapper+='assign '+x+'=0;\n'
 wrapper+='end else begin : g_cancel\n'+base+'_enabled #('+forwarding+') u_impl (\n'+connect+',\n'+',\n'.join('    .'+x+'('+x+')' for x in controls)+');\nend endgenerate\nendmodule\n'
 text=raw.splitlines()[0]+'\n'+wrapper+'\n'+legacy+'\n\n'+enabled+'\n'
 assert legacy.replace(base+'_legacy',NAME,1)==module
 return {'origin_path':ORIGINS[kind],'origin_sha256':sha(raw),'candidate_sha256':sha(text),'default_inverse':True,'parameters_forwarded':len(params),'ports_forwarded':len(ports),'extra_core_register_bits':8,'module':base},text,module,enabled

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=False);RECORD.mkdir(parents=True,exist_ok=False)
 records={}
 for kind in ORIGINS:
  r,text,old,enabled=generate(kind);records[kind]=r
  (OUT/(kind+'_core_cancel.sv')).write_text(text)
  (OUT/(kind+'_enabled.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),enabled.replace(r['module']+'_enabled',NAME,1).splitlines(True),fromfile=ORIGINS[kind],tofile='prepared_enabled_'+kind)))
 (RECORD/'sources.json').write_text(json.dumps({'status':'UNCOMPILED_SOURCE_REVIEW_REQUIRED_NOT_COMPLETE_COMPOSED_GATE','source_commit':PIN,'repaired_producer_pin':PRODUCER_PIN,'repaired_producer_path':PRODUCER,'repaired_producer_sha256':sha(blob(PRODUCER_PIN,PRODUCER)),'copies':records,'generator_sha256':sha(Path(__file__).read_text()),'accounting':{'provider':259,'core':8,'producer_ACK':2,'concrete':269,'envelope':278},'raw_VM_write_ports_unchanged':True,'healthy_stages_intended':0,'remaining_before_runtime':['Nash committed edge/descriptor model and source diff review','PC20/PC21 descriptor-class binding only; other packed program locations unqualified','Actual core+QE+producer+guard+WINDOW bench/event calendar and mutants','Resource/output model and fresh GO; no compile now'],'physical_causal_provider':False,'fulltoken':False},indent=2)+'\n')
