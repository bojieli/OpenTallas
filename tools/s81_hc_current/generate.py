#!/usr/bin/env python3
"""Emit additive source-current HC compositions; preserve pinned arithmetic bytes."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'rtl/dsrom_sys/s81_suhc/hier'
O=ROOT/'rtl/dsrom_sys/s81_suhc/static'
O.mkdir(exist_ok=True)
inputs={}
def read(name):
 p=H/name; s=p.read_text();inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return s
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
pads=read('ot_s81_hc_pad_split.sv')
pad=pads[:pads.index('\nmodule ot_s81_hc_pad_f8')]
align=pads[pads.index('module ot_s81_hc_ccr_align'):pads.index('\nmodule ot_s81_hc_pad_meta2')]
pad=once(pad,'module ot_s81_hc_cpad_split','module ot_s81_hc_cpad_roots20')
pad=once(pad,'sk, srs,','sk, srs,\n    input wire [3:0] sk_pad,')
for i in range(4):pad=pad.replace('.sk(sk)',f'.sk(sk_pad[{i}])',1)
align=once(align,'module ot_s81_hc_ccr_align','module ot_s81_hc_ccr_roots20')
align=once(align,'sk, srs,','sk, srs,\n    input wire [1:0] sk_return,')
for i in range(2):align=align.replace('.sk(sk)',f'.sk(sk_return[{i}])',1)
(O/'ot_s81_hc_pad_roots20.sv').write_text('// Candidate only: existing delay/core arithmetic, independent real child roots.\n'+pad+'\n'+align)
source=read('ot_s81_hc_comb.sv')
# Use measured current split production shape; preserve arithmetic parameterization.
s=once(source,'module ot_s81_hc_comb','module dsfd_sp_hc_comb_roots20')
s=once(s,'RF = 1, RT = 1, RW = 2','RF = 5, RT = 1, RW = 2')
s=once(s,'HALF = 0, RLY = 1','HALF = 1, RLY = 2')
s=once(s,'DW = 3 + RW, RET_EXTRA = 0','DW = 6, RET_EXTRA = 1')
s=once(s,'parameter integer CCF_BP = 0','parameter integer CCF_BP = 3')
s=once(s,'cck, crs, sk, srs,','cck, crs, sk, srs,\n    input wire [19:0] sk_leaf,')
s=once(s,'.cck(cck), .crs(crs), .sk(sk)', '.cck(cck), .crs(crs), .sk(sk_leaf[0])')
# Remaining child connections follow source instance order; wrapper roots are explicit.
s=once(s,'ot_s81_hc_ccr_align `OT_HCC_R u_cr','ot_s81_hc_ccr_roots20 `OT_HCC_R u_cr')
s=s.replace('ot_s81_hc_cpad_split','ot_s81_hc_cpad_roots20')
s=once(s,'ot_s81_hc_crx `OT_HCC_P u_rx (\n        .sk(sk)', 'ot_s81_hc_crx `OT_HCC_P u_rx (\n        .sk(sk_leaf[1])')
s=once(s,'ot_s81_hc_caq u_caq (.sk(sk)', 'ot_s81_hc_caq u_caq (.sk(sk_leaf[3+u])')
s=once(s,'ot_s81_hc_cntree `OT_HCC_P u_nt (\n        .sk(sk)', 'ot_s81_hc_cntree `OT_HCC_P u_nt (\n        .sk(sk_leaf[2])')
s=once(s,'ot_s81_hc_ccr_roots20 `OT_HCC_R u_cr (\n        .sk(sk)', 'ot_s81_hc_ccr_roots20 `OT_HCC_R u_cr (\n        .sk_return(sk_leaf[8:7]), .sk(sk)')
# Retain old branch as explicit rejected selector (no legacy CCF physical root mapping).
s=s.replace('.sk(sk), .srs(srs), .crd_i(r_crd)', '.sk_pad(sk_leaf[12:9]), .sk(sk), .srs(srs), .crd_i(r_crd)')
s=once(s,'.sk_n(sk), .sk_s(sk), .bank_ck({5{sk}})', '.sk_n(sk_leaf[13]), .sk_s(sk_leaf[14]), .bank_ck(sk_leaf[19:15])')
# Unsupported shapes must fail closed rather than accidentally pick historical leaves.
s=once(s,'    // ---------------------------------------------------------------- seam nets', '''    initial if(CCF_BP != 3 || NG != 256 || D != 5120 || NCOL != 3 || S_RT != 4 || S_RD != 2 ||
               RF != 5 || RT != 1 || RW != 2 || HALF != 1 || RLY != 2 || DW != 6 || RET_EXTRA != 1)
        $fatal(1,"roots20 candidate requires exact current split shape / CCF_BP3");
    // ---------------------------------------------------------------- seam nets''')
header='// SOURCE-CURRENT CANDIDATE ONLY. No imported parent physical closure/native claim.\n'
(O/'dsfd_sp_hc_comb_roots20.sv').write_text(header+s)
# Reuse actual existing compiler-calendar controller, with its explicit limitations.
ref='20d2499482ce04930ad8bee9bb269ac52fafe5b9'
path='rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cseq_static.sv'
seq=subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=ROOT,text=True)
(O/'ot_s81_hc_cseq_static.sv').write_text(seq)
inputs[f'{ref}:{path}']=hashlib.sha256(seq.encode()).hexdigest()
t=once(s,'module dsfd_sp_hc_comb_roots20','module dsfd_sp_hc_comb_calendar20')
t=t.replace('ot_s81_hc_cseq #','ot_s81_hc_cseq_static #')
t=once(t,'parameter integer CCF_BP = 3','parameter integer POST_FIRST=16, POST_STRIDE=1, CMD_LAT=2, VM_LAT=12, POST_EXPLICIT=0,\n    parameter [639:0] POST_AGES=0,\n    parameter integer CCF_BP = 3')
t=once(t,'input wire [19:0] sk_leaf,','input wire [19:0] sk_leaf,\n    input wire [31:0] n_y_tag,command_y_tag,command_done_age,command_ss_age,command_scalar_age,\n    input wire [4:0] n_y_row,')
t=t.replace('.PIPE(PIPE), .PD(PIPE_PD)) u_seq', '.PIPE(PIPE), .PD(PIPE_PD), .POST_FIRST(POST_FIRST), .POST_STRIDE(POST_STRIDE),\n        .CMD_LAT(CMD_LAT),.VM_LAT(VM_LAT),.POST_EXPLICIT(POST_EXPLICIT),.POST_AGES(POST_AGES)) u_seq')
t=once(t,'.cck(cck), .crs(crs), .sk(sk_leaf[0])','.n_y_tag(n_y_tag),.n_y_row(n_y_row),.command_y_tag(command_y_tag),\n        .command_done_age(command_done_age),.command_ss_age(command_ss_age),.command_scalar_age(command_scalar_age),\n        .cck(sk_leaf[0]), .crs(crs), .sk(sk_leaf[0])')
t=once(t,'e_r = u_seq.e_r','e_r = 1\'b1')
(O/'dsfd_sp_hc_comb_calendar20.sv').write_text(header+'// External command/tag/calendar inputs MUST already be in the sequencer serial clock domain.\n'+t)
# Current static pin transport: explicit serial-domain input, no credit gating.
cp=read('ot_s81_hc_cpin.sv')
cp=cp[cp.index('module ot_s81_hc_cpin'):]
cp=once(cp,'module ot_s81_hc_cpin','module ot_s81_hc_cpin_calendar')
cp=once(cp,'cck, crs, sk, srs,','cck, crs, sk, srs,\n    input wire [31:0] y_tag,command_y_tag,command_done_age,command_ss_age,command_scalar_age,\n    input wire [4:0] y_row,\n    output reg [31:0] n_y_tag,n_command_y_tag,n_command_done_age,n_command_ss_age,n_command_scalar_age,\n    output reg [4:0] n_y_row,')
cp=cp.replace('posedge cck or negedge crs','posedge sk or negedge srs').replace('if (!crs)','if (!srs)').replace('posedge cck','posedge sk')
cp=cp.replace('    reg       pop;\n    reg [7:0] cnt;\n','')
cp=once(cp,'wire      acc = y_v && y_rdy;','wire      acc = y_v; // compiler-reserved event, never gated by occupancy/pop')
cp=once(cp,"y_rdy <= 1'b0; cnt <= 0; pop <= 1'b0;", "y_rdy <= 1'b0;")
cp=once(cp,'            pop <= n_ypop;\n            cnt <= cnt + acc - pop;\n            y_rdy <= (cnt + acc - pop) < TH;',"            y_rdy <= 1'b1; // compatibility/status only; not an execution enable")
cp=once(cp,'endmodule',"    always @(posedge sk) begin\n        n_y_tag <= y_tag; n_y_row <= y_row;\n        n_command_y_tag <= command_y_tag; n_command_done_age <= command_done_age;\n        n_command_ss_age <= command_ss_age; n_command_scalar_age <= command_scalar_age;\n    end\nendmodule")
(O/'ot_s81_hc_cpin_calendar.sv').write_text('// Candidate only: all command/Y/calendar inputs already in this serial clock domain.\n// No inherited physical view or fixed phase bridge; output y_rdy is compatibility status only.\n'+cp)
receipt={'generator_inputs':inputs,'static_controller_origin':ref,'status':'source candidate; static allkind profile/full composition/physical qualification OPEN','clock_map':[{'index':i,'path':path} for i,path in enumerate(['u_seq','u_rx','u_nt',*[f'g_aq[{i}].u_caq' for i in range(4)],'u_cr.u_core','u_cr.g_meta.u_m','g_cf_bp.u_pd.u_f8','g_cf_bp.u_pd.u_f5r1','g_cf_bp.u_pd.u_r6','g_cf_bp.u_pd.u_r5','g_cf_bp.u_cf.u_n','g_cf_bp.u_cf.u_s',*[f'g_cf_bp.u_cf.g_bank[{i}].u_b' for i in range(5)]])], 'generated_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'ot_s81_hc_pad_roots20.sv',O/'dsfd_sp_hc_comb_roots20.sv',O/'dsfd_sp_hc_comb_calendar20.sv',O/'ot_s81_hc_cseq_static.sv',O/'ot_s81_hc_cpin_calendar.sv']}}
(ROOT/'results/arch/s81_hc_current_1016/source_join.json').write_text(json.dumps(receipt,indent=2)+'\n')
