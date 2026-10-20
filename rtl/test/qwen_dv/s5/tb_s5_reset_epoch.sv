`timescale 1ns/1ps
// Minimal real generated reset-run mechanism; checks the compiler's release epoch, not numerical payloads.
module tb_s5_reset_epoch;
parameter integer MUT=0;
reg ck=0;always #0.5 ck=~ck;
reg rst_n=0;
    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck), .d(rst_n), .q(lpr_root));
    wire lpr_r_ctl;  ot_pl_pad #(.W(1), .N(9)) u_lpr_r_ctl (.ck(ck), .d(lpr_root), .q(lpr_r_ctl));   // 4 hop(s) from r_fw
    wire lpr_c_u_ctl;  ot_pl_pad #(.W(1), .N((MUT == 4) ? 1 : 0)) u_lprc_u_ctl (.ck(ck), .d(lpr_r_ctl), .q(lpr_c_u_ctl));   // t(u_ctl) = 0
reg [9:0] expected=0;
always @(posedge ck) expected <= {expected[8:0],rst_n};
integer c,checks=0;
initial begin
for(c=0;c<220;c=c+1)begin
 @(negedge ck);rst_n=((c>=20&&c<75)||(c>=110&&c<165)||(c>=190));
 @(posedge ck);#0.1;
 if(c>16)begin
  checks=checks+1;
  if(lpr_c_u_ctl!==expected[9])$fatal(1,"RESET_EPOCH_FAIL cycle=%0d expected=%0d child_reset=%0d compiler_depth=10",c,expected[9],lpr_c_u_ctl);
 end
end
$display("RESET_EPOCH_PASS checks=%0d epochs=3 depth=10",checks);$finish;
end
endmodule
