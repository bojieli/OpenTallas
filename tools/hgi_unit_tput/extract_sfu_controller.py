#!/usr/bin/env python3
"""Reproduce the distinct opt-in SFU controller from the untouched real c12 source."""
from pathlib import Path
import hashlib,json,re
r=Path(__file__).resolve().parents[2]; src=r/'rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv'; original=src.read_text(); s=original[:original.index('endmodule')+len('endmodule')]
s=s[s.index('module ot_hdc_v41x_vec'):].replace('module ot_hdc_v41x_vec #(','module ot_hgi_sfu_ctl_extract #(\n    parameter integer ENABLE_NATIVE = 0,',1)
params={'N':16,'M':16,'AW':24,'BCAST_STAGES':1,'RET_STAGES':5,'MLAT':6,'ALAT':6,'OPR':1,'DDIV':21,'SIDEX':4,'CAPR':1,'CTL12':2,'GSH':1,'KIMM':1,'DENR':1,'SFUT':0,'DRING':3}
for k,v in params.items():s=re.sub(r'(parameter integer '+k+r'\s*=\s*)\d+',r'\g<1>'+str(v),s,count=1)
# Memory requests belong to the grid, not the extracted controller.
a=s.index('    // ---- per lane: gather-index read');b=s.index('    // ---- per lane: element writes',a);s=s[:a]+s[b:]
s=s.replace('    output wire [7:0]        dbg_sseq\n','    output wire [7:0]        dbg_sseq,\n    output wire [1741:0]     grid_control,\n    input wire [N-1:0] l_fault, l_coll, l_rov, l_vm_we, l_kv_we,\n    input wire [N*32-1:0] l_rox, l_vm_wdata, l_kv_wdata,\n    input wire [N*AW-1:0] l_vm_waddr, l_kv_waddr,\n    output reg admission_fault\n')
s=s.replace('assign ready = (pst == 2\'d0);',"wire instruction_supported = i_red == RED_NONE && i_asrc == 0 && i_bsrc == 0 && i_csrc == 0 && i_dsrc == 0 && (i_dst == DST_NONE || i_dst == 2'd1) &&\n        (i_sfu == SFU_NONE || i_sfu == SFU_EXP || i_sfu == SFU_SIGM || i_sfu == SFU_SILU);\n    assign ready = ENABLE_NATIVE && (pst == 2'd0) && instruction_supported;\n    always @(posedge clk or negedge rst_n)\n        if (!rst_n) admission_fault <= 1'b0;\n        else if (ENABLE_NATIVE && go && !instruction_supported) admission_fault <= 1'b1;")
a=s.index('    wire [N-1:0]    l_fault');b=s.index('    // =========================================================================================\n    // RETURN:',a)
fields=['tr_ld','tr_ldbank','padded_terms','tr_emit','tr_bank','tr_ov','tr_iv','tr_no','tr_ni','tr_ls','tr_lvw','tr_vb','tr_krow','tr_obase','tr_aibase','tr_aind','tr_gsh','tr_cpair','tr_dst','tr_srcs','`CW_ARND(cwx)','`CW_ARELU(cwx)','`CW_AMIN(cwx)','`CW_CCLIP(cwx)','`CW_IMM3(cwx)','`CW_M1(cwp)','`CW_IMM1(cwp)','`CW_M1(cwm)','`CW_M2(cwm)','`CW_QM(cwm)','`CW_IMM1(cwm)','`CW_AD(cwa)','`CW_IMM2(cwa)','`CW_SFU(cwi)','`CW_SFU(cws)','`CW_E1(cws)','`CW_IMM2(cws)','`CW_E2(cwe)','`CW_IMM1(cwe)','`CW_RND(cwo)','`CW_DST(cwo)']
replacement='''    // Lane array is external: sixteen unchanged CLOSED lanes behind four-edge mappers plus CLOSED b_q input stage.
    wire [1199:0] padded_terms;
    for (genvar stream = 0; stream < 5; stream = stream + 1) begin:g_term_pad
        for (genvar bit_j = 0; bit_j < 10; bit_j = bit_j + 1) begin:g_term
            if (bit_j < LN) assign padded_terms[(stream*10+bit_j)*24+:24] = tr_ldc[(stream*LN+bit_j)*AW+:AW];
            else assign padded_terms[(stream*10+bit_j)*24+:24] = 24'd0;
        end
    end
    assign grid_control = {'''+', '.join(fields)+'''};
    // Reductions/side operations are refused at instruction admission; no arithmetic surrogate.
    wire [7:0] red_seq = 8'd0;
    wire red_lastres = 1'b0, red_ev = 1'b0, red_busy = 1'b0, red_f = 1'b0, side_f = 1'b0;
    wire [NR-1:0] l_res_we = '0;
    wire [NR*AW-1:0] l_res_addr = '0;
    wire [NR*32-1:0] l_res_data = '0;

'''
s=s[:a]+replacement+s[b:]
s=s.replace('ot_hdc_delay #(.W(2 * N), .D(RET_STAGES), .RESET(1)) u_rwe','ot_hdc_delay #(.W(2 * N), .D(0), .RESET(1)) u_rwe').replace('ot_hdc_delay #(.W(N * (2 * AW + 64)), .D(RET_STAGES)) u_rwd','ot_hdc_delay #(.W(N * (2 * AW + 64)), .D(0)) u_rwd')
s=s.replace('    // LV is bounded', '''    initial begin
        if (N != 16 || M != 16 || AW != 24 || BCAST_STAGES != 1 || RET_STAGES != 5 ||
            MLAT != 6 || ALAT != 6 || OPR != 1 || DDIV != 21 || CAPR != 1 ||
            GSH != 1 || KIMM != 1 || DENR != 1 || SFUT != 0 || DRING != 3)
            $fatal(1, "SFU controller extraction requires exact CLOSED lane and mapper params");
    end
    // LV is bounded''',1)
out=r/'rtl/hbm_accel/generic/peers/ot_hgi_sfu_ctl_extract.sv';out.write_text('`timescale 1ns/1ps\n// Opt-in actual c12 controller extraction; not a native VM/cache qualification.\n// Original issue/setup/control pipes retained; no original CLOSED source edited.\n'+s+'\n')
(r/'results/arch/hbm_native_1013/sfu_native_quarter/extraction.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'changes':['module rename and exact physical defaults','ENABLE_NATIVE default0 and refuse reduction/side/unsupported destination','external real-lane interface','LN4 to LN10 zero-padding','RET5 metadata but RET0 payload because grid adds5 plus original LEAF1'],'control_fields':fields,'not_qualified':['controller clock synthesis/pins','local8 cache','native VM group','production throughput','arithmetic grid phase oracle']},indent=2)+'\n')
