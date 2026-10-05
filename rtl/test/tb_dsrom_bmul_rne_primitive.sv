`timescale 1ns/1ps
// Deterministic primitive fixture. Delays provide settling only; no frequency/physical credit.
module dsrom_bmul_rne_primitive_test #(parameter integer MUTANT=0);
    `include "dsrom_bmul_rne_primitive_inputs.svh"
    `include "dsrom_bmul_rne_primitive_expected.svh"
    reg clk=0,rst_n=1,v=0;
    reg [31:0] a=0,b=0;
    wire [31:0] old_y,off_y,ref_y,cand_y;
    wire old_f,off_f,ref_f,cand_f;
    ref_ot_v41_bmul2 old_dut (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(old_y),.fault(old_f));
    ref_ot_v41_bmul2_rne_prepare off_dut (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(off_y),.fault(off_f));
    ref_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) ref_dut (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(ref_y),.fault(ref_f));
    cand_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) cand_dut (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(cand_y),.fault(cand_f));
    wire [31:0] my [0:8];wire [8:0] mf;
    assign my[0]=ref_y;assign mf[0]=ref_f;
    mut_truncation_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m1 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[1]),.fault(mf[1]));
    mut_tie_away_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m2 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[2]),.fault(mf[2]));
    mut_shift_offbyone_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m3 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[3]),.fault(mf[3]));
    mut_negative_zero_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m4 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[4]),.fault(mf[4]));
    mut_old_range_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m5 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[5]),.fault(mf[5]));
    mut_underflow_fault_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m6 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[6]),.fault(mf[6]));
    mut_zero_nonfinite_bypass_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m7 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[7]),.fault(mf[7]));
    mut_refusal_no_fault_ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1)) m8 (.clk(clk),.rst_n(rst_n),.v(v),.a(a),.b(b),.y(my[8]),.fault(mf[8]));
    reg esign=0;reg signed [10:0] ebe=0;reg [23:0] esig=24'h800000;
    wire [31:0] ery,ecy;wire [31:0] emy [0:8];
    assign emy[0]=ery;
    ref_ot_v41_bmul_subnormal_rne_prepare er (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(ery));
    cand_ot_v41_bmul_subnormal_rne_prepare ec (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(ecy));
    mut_truncation_ot_v41_bmul_subnormal_rne_prepare e1 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[1]));
    mut_tie_away_ot_v41_bmul_subnormal_rne_prepare e2 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[2]));
    mut_shift_offbyone_ot_v41_bmul_subnormal_rne_prepare e3 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[3]));
    mut_negative_zero_ot_v41_bmul_subnormal_rne_prepare e4 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[4]));
    mut_old_range_ot_v41_bmul_subnormal_rne_prepare e5 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[5]));
    mut_underflow_fault_ot_v41_bmul_subnormal_rne_prepare e6 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[6]));
    mut_zero_nonfinite_bypass_ot_v41_bmul_subnormal_rne_prepare e7 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[7]));
    mut_refusal_no_fault_ot_v41_bmul_subnormal_rne_prepare e8 (.sign_i(esign),.biased_i(ebe),.sig_i(esig),.y(emy[8]));
    integer mode=MUTANT;integer arg_seen;
    integer tag [0:4];integer send_id=-1,i,k,checks=0,encoder_checks=0,negative_witnesses=0;
    reg mutant_seen=0;
    reg [31:0] inp;reg [35:0] einp;reg [32:0] expectation;reg [31:0] eexpect;
    task tick;
        for(k=4;k>0;k=k-1)tag[k]=tag[k-1];
        tag[0]=v?send_id:-1;
        #4;clk=1;#1;
        if(tag[4]>=0)begin
            expectation=product_expected(tag[4]);
            if({old_f,old_y} !== {off_f,off_y}) $fatal(1,"DIFF default-off preservation vector=%0d",tag[4]);
            if({ref_f,ref_y} !== expectation || {cand_f,cand_y} !== expectation)
                $fatal(1,"DIFF corrected primitive vector=%0d expected=%h ref=%h/%b cand=%h/%b",tag[4],expectation,ref_y,ref_f,cand_y,cand_f);
            checks=checks+2;
            if(tag[4]==0 || tag[4]==1)begin
                if(old_y!==32'd0 || old_f!==1'b1 || ref_f!==1'b0) $fatal(1,"negative baseline witness missing");
                negative_witnesses=negative_witnesses+1;
            end
            if(mode!=0 && {mf[mode],my[mode]} !== expectation && !mutant_seen)begin
                $display("DIFF primitive mutant=%0d product_vector=%0d expected=%h actual=%h/%b",mode,tag[4],expectation,my[mode],mf[mode]);mutant_seen=1;
            end
        end else if(old_f || off_f || ref_f || cand_f) $fatal(1,"invalid output fault");
        #4;clk=0;#1;
    endtask
    task reset_now;
        v=0;send_id=-1;rst_n=1;#1;rst_n=0;#1;
        for(k=0;k<5;k=k+1)tag[k]=-1;
        if(old_f || off_f || ref_f || cand_f || old_y || off_y || ref_y || cand_y) $fatal(1,"asyncreset output");
        rst_n=1;#1;
    endtask
    initial begin
        arg_seen=$value$plusargs("MUTANT=%d",mode);
        if(mode<0 || mode>8)$fatal(1,"invalid mutant mode");
        reset_now();
        // Cancel four in-flight valid operands; no post-reset ghost/fault allowed.
        for(i=0;i<4;i=i+1)begin v=1;send_id=-1;a=32'h00800000;b=32'h33800000;#4;clk=1;#1;#4;clk=0;#1;end
        reset_now();for(i=0;i<6;i=i+1)tick();
        for(i=0;i<PRODUCT_COUNT;i=i+1)begin
            inp=product_input(i);a={inp[31:16],16'd0};b={inp[15:0],16'd0};send_id=i;v=1;tick();
            if(i%7==0)begin v=0;send_id=-1;tick();end
        end
        v=0;send_id=-1;for(i=0;i<6;i=i+1)tick();
        for(i=0;i<ENCODER_COUNT;i=i+1)begin
            einp=encoder_input(i);esign=einp[35];ebe=einp[34:24];esig=einp[23:0];#1;
            eexpect=encoder_expected(i);
            if(ery!==eexpect || ecy!==eexpect)$fatal(1,"DIFF corrected encoder vector=%0d expected=%h ref=%h cand=%h",i,eexpect,ery,ecy);
            encoder_checks=encoder_checks+2;
            if(mode!=0 && emy[mode]!==eexpect && !mutant_seen)begin
                $display("DIFF primitive mutant=%0d encoder_vector=%0d expected=%h actual=%h",mode,i,eexpect,emy[mode]);mutant_seen=1;
            end
        end
        if(checks!=2*PRODUCT_COUNT || encoder_checks!=2*ENCODER_COUNT || negative_witnesses!=2)$fatal(1,"exact fixture coverage");
        if(mode!=0 && !mutant_seen)$fatal(1,"mutant missing explicit DIFF");
        $display("PASS primitive RNE mode=%0d product_assertions=%0d encoder_assertions=%0d baseline_witnesses=%0d",mode,checks,encoder_checks,negative_witnesses);
        $finish;
    end
endmodule
module tb_bmul_rne_primitive;dsrom_bmul_rne_primitive_test t();endmodule
module tb_bmul_rne_truncation;dsrom_bmul_rne_primitive_test #(.MUTANT(1)) t();endmodule
module tb_bmul_rne_tie_away;dsrom_bmul_rne_primitive_test #(.MUTANT(2)) t();endmodule
module tb_bmul_rne_shift_offbyone;dsrom_bmul_rne_primitive_test #(.MUTANT(3)) t();endmodule
module tb_bmul_rne_negative_zero;dsrom_bmul_rne_primitive_test #(.MUTANT(4)) t();endmodule
module tb_bmul_rne_old_range;dsrom_bmul_rne_primitive_test #(.MUTANT(5)) t();endmodule
module tb_bmul_rne_underflow_fault;dsrom_bmul_rne_primitive_test #(.MUTANT(6)) t();endmodule
module tb_bmul_rne_zero_nonfinite_bypass;dsrom_bmul_rne_primitive_test #(.MUTANT(7)) t();endmodule
module tb_bmul_rne_refusal_no_fault;dsrom_bmul_rne_primitive_test #(.MUTANT(8)) t();endmodule
