`timescale 1ns/1ps
// Actual source wrapper capture/reset contract only. No programme is installed.
// Core output wires are driven solely to test the existing output capture edge.
module tb_lctx3_wrapper_capture;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,oq=0;reg[4:0]ob=0;integer i,n=0;
reg[0:0] d2d_epoch_abort=0;
reg[0:0] prog_auth_slot=0;
reg[0:0] prog_context_slot=0;
reg[0:0] prog_head_context_slot=0;
reg[0:0] prog_witness_slot=0;
reg[68:0] seq_descriptor_obs=0;
reg[75:0] seq_program_obs=0;
reg[75:0] tt_program_obs=0;
qfd_sys_face_lctx3_wrapped #(.MU(1),.MU_HEAD(1),.ROPE(1),.L_CONTEXTS(1)) d(.ck(ck),.rst_n(rst_n), .d2d_epoch_abort(d2d_epoch_abort), .prog_auth_slot(prog_auth_slot), .prog_context_slot(prog_context_slot), .prog_head_context_slot(prog_head_context_slot), .prog_witness_slot(prog_witness_slot), .seq_descriptor_obs(seq_descriptor_obs), .seq_program_obs(seq_program_obs), .tt_program_obs(tt_program_obs));
initial begin force d.q_slot__ot_pr=oq;force d.q_slot_beat__ot_pr=ob;
repeat(7)@(negedge ck);rst_n=1;
for(i=0;i<120;i=i+1)begin
d2d_epoch_abort=(i*32'h9e3779b9) ^ 1;
prog_auth_slot=(i*32'h9e3779b9) ^ 2;
prog_context_slot=(i*32'h9e3779b9) ^ 3;
prog_head_context_slot=(i*32'h9e3779b9) ^ 4;
prog_witness_slot=(i*32'h9e3779b9) ^ 5;
seq_descriptor_obs=(i*32'h9e3779b9) ^ 6;
seq_program_obs=(i*32'h9e3779b9) ^ 7;
tt_program_obs=(i*32'h9e3779b9) ^ 8;
oq=i%2;ob=i%32;@(negedge ck);end
$display("PASS WRAPPER_CAPTURE edges=%0d all45same-D inputcopies, Qoutputcapture and reset2+3; no programme claim",n);$finish;end
always @(posedge ck)begin #1;n=n+1;
if(d.copy_0!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 0 edge%0d",n);
if(d.copy_1!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 1 edge%0d",n);
if(d.copy_2!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 2 edge%0d",n);
if(d.copy_3!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 3 edge%0d",n);
if(d.copy_4!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 4 edge%0d",n);
if(d.copy_5!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 5 edge%0d",n);
if(d.copy_6!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 6 edge%0d",n);
if(d.copy_7!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 7 edge%0d",n);
if(d.copy_8!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 8 edge%0d",n);
if(d.copy_9!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 9 edge%0d",n);
if(d.copy_10!==prog_witness_slot)$fatal(1,"WRAPPER_COPY_DIFF 10 edge%0d",n);
if(d.copy_11!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 11 edge%0d",n);
if(d.copy_12!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 12 edge%0d",n);
if(d.copy_13!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 13 edge%0d",n);
if(d.copy_14!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 14 edge%0d",n);
if(d.copy_15!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 15 edge%0d",n);
if(d.copy_16!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 16 edge%0d",n);
if(d.copy_17!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 17 edge%0d",n);
if(d.copy_18!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 18 edge%0d",n);
if(d.copy_19!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 19 edge%0d",n);
if(d.copy_20!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 20 edge%0d",n);
if(d.copy_21!==prog_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 21 edge%0d",n);
if(d.copy_22!==prog_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 22 edge%0d",n);
if(d.copy_23!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 23 edge%0d",n);
if(d.copy_24!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 24 edge%0d",n);
if(d.copy_25!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 25 edge%0d",n);
if(d.copy_26!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 26 edge%0d",n);
if(d.copy_27!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 27 edge%0d",n);
if(d.copy_28!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 28 edge%0d",n);
if(d.copy_29!==tt_program_obs[75])$fatal(1,"WRAPPER_COPY_DIFF 29 edge%0d",n);
if(d.copy_30!==seq_program_obs[75])$fatal(1,"WRAPPER_COPY_DIFF 30 edge%0d",n);
if(d.copy_31!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 31 edge%0d",n);
if(d.copy_32!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 32 edge%0d",n);
if(d.copy_33!==prog_auth_slot)$fatal(1,"WRAPPER_COPY_DIFF 33 edge%0d",n);
if(d.copy_34!==seq_descriptor_obs[68])$fatal(1,"WRAPPER_COPY_DIFF 34 edge%0d",n);
if(d.copy_35!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 35 edge%0d",n);
if(d.copy_36!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 36 edge%0d",n);
if(d.copy_37!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 37 edge%0d",n);
if(d.copy_38!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 38 edge%0d",n);
if(d.copy_39!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 39 edge%0d",n);
if(d.copy_40!==prog_head_context_slot)$fatal(1,"WRAPPER_COPY_DIFF 40 edge%0d",n);
if(d.copy_41!==d2d_epoch_abort)$fatal(1,"WRAPPER_COPY_DIFF 41 edge%0d",n);
if(d.copy_42!==d2d_epoch_abort)$fatal(1,"WRAPPER_COPY_DIFF 42 edge%0d",n);
if(d.copy_43!==d2d_epoch_abort)$fatal(1,"WRAPPER_COPY_DIFF 43 edge%0d",n);
if(d.copy_44!==d2d_epoch_abort)$fatal(1,"WRAPPER_COPY_DIFF 44 edge%0d",n);
if(d.q_slot!==oq || d.q_slot_beat!==ob)$fatal(1,"WRAPPER_OUTPUT_CAPTURE_DIFF");
if(n>=12 && d.u_ot_pr_core.rst_forest[0]!==1)$fatal(1,"RESET_2_PLUS_3_DIFF");
end
endmodule
