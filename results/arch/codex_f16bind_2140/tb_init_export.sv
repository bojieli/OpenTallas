`timescale 1ns/1ps
module tb_init_export;
reg ck=0; always #5 ck=~ck;
reg rst_n=0, tv=0; reg [2:0] tp=0; reg[8:0] ta=0; reg[3:0] tk=0;reg[4:0] tb=0;
wire init_u0; wire[186:0] dh;
qfd_sys_face_lctx3_wrapped_f16 #(.MU(1),.MU_HEAD(1),.ROPE(1),.L_CONTEXTS(1)) dut(.ck(ck),.rst_n(rst_n),.init_u0(init_u0),.seq_dh(dh));
task event_check(input bit valid,input[2:0]port,input[8:0]arg,input bit expect_init);
begin
 @(negedge ck);tv=valid;tp=port;ta=arg;tk=arg[8:5];tb=arg[4:0];
 @(posedge ck);#1;
 @(negedge ck);tv=0;
 @(posedge ck);#1;
 if(init_u0!==expect_init) $fatal(1,"INIT_SELECTOR port=%0d arg=%h got=%b",port,arg,init_u0);
 if(dh[42]!==(valid&&port==0)) $fatal(1,"INIT_DH_AGE");
 if(valid&&port==0&&dh[41:36]!==arg[5:0]) $fatal(1,"INIT_STAGE");
 if(valid&&port==0&&dh[35:0]!=={18'd777,18'd0}) $fatal(1,"INIT_CONTEXT");
 @(negedge ck);@(posedge ck);#1;
 if(init_u0!==0||dh[42]!==0) $fatal(1,"INIT_DUPLICATE");
end endtask
initial begin
 force dut.u_ot_pr_core.t_ev=tv;
 force dut.u_ot_pr_core.t_p=tp;
 force dut.u_ot_pr_core.t_k=tk;
 force dut.u_ot_pr_core.t_b=tb;
 force dut.u_ot_pr_core.tok=18'd777;
 force dut.u_ot_pr_core.pos=18'd0;
 repeat(6)@(negedge ck);
 if(init_u0!==0) $fatal(1,"INIT_RESET");
 rst_n=1;repeat(8)@(negedge ck);
 event_check(1,5,9'd128,0); // actual cold MARK argument, no DH start
 event_check(1,0,9'd0,1); // actual cold prefix INIT row47
 event_check(1,0,9'd65,0); // original first L0 stage1+L flag
 event_check(1,0,9'd256,0); // recurring ordinary RESULT stage0
 event_check(1,0,9'd256,0); // later ordinary stage0 must remain ordinary
 event_check(0,0,9'd0,0); // idle argument0 never requests INIT
 $display("PASS F16_INIT_EXPORT cold_MARK INIT first_L0 two_later_RESULT idle exact_DH_context_age");
 $finish;
end
endmodule
