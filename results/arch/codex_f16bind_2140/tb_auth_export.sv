`timescale 1ns/1ps
// Full actual hierarchy; force only existing receipt producer Q for a boundary
// capture proof. This does not install a programme or qualify its sinks.
module tb_auth_export;
reg ck=0; always #5 ck=~ck;
reg rst_n=0; wire [82:0] auth;
reg beg=0, ready=0, cap=0;
reg [63:0] digest=0; reg [15:0] epoch=0;
qfd_sys_face_lctx3_wrapped_f16 #(.MU(1),.MU_HEAD(1),.ROPE(1),.L_CONTEXTS(1)) dut(.ck(ck),.rst_n(rst_n),.f16_auth(auth));
initial begin
 force dut.u_ot_pr_core.begin_v=beg;
 force dut.u_ot_pr_core.rp_program_ready=ready;
 force dut.u_ot_pr_core.rp_auth_v=~ready;
 force dut.u_ot_pr_core.rp_cap=cap;
 force dut.u_ot_pr_core.rp_program_digest=digest;
 force dut.u_ot_pr_core.rp_program_epoch=epoch;
 repeat(5) @(negedge ck);
 if(auth!==0) $fatal(1,"AUTH_RESET");
 rst_n=1; repeat(6) @(negedge ck);
 for(integer i=0;i<128;i=i+1) begin
 beg=(i%7)==0; ready=(i%3)!=0; cap=(i%2)==0;
 digest=64'h1234567800000000+i; epoch=16'h4000+i;
 #1;
 if(auth==={beg,ready,cap,digest,epoch}) $fatal(1,"AUTH_COMB_LEAK");
 @(posedge ck); #1;
 if(auth!=={beg,ready,cap,digest,epoch}) $fatal(1,"AUTH_CAPTURE edge=%0d got=%h",i,auth);
 @(negedge ck);
 end
 rst_n=0; repeat(5) @(negedge ck);
 if(auth!==0) $fatal(1,"AUTH_REASSERT");
 $display("PASS F16_AUTH_EXPORT actual_full_hierarchy edges=128 reset_reassert; producer Q forced, no programme claim");
 $finish;
end
endmodule
