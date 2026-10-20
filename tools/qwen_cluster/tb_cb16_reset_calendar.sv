`timescale 1ns/1ps
// Independent reset-calendar check: actual generated fabric reset paths, all sixteen regions.
// Payload is unobserved, so only reset logic remains after Verilator optimization.
module tb_reset_calendar #(parameter integer M=0);
reg ck=0,rst_n=0; always #0.5 ck=~ck;
wire [15:0] rr,rf,rb; integer cyc;
qfd_c_b16_dv_fabric #(.MUT(0)) u_ref (.ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck), .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck), .rst_c0r0(rst_n), .rst_c0r1(rst_n), .rst_c0r2(rst_n), .rst_c0r3(rst_n), .rst_c1r0(rst_n), .rst_c1r1(rst_n), .rst_c1r2(rst_n), .rst_c1r3(rst_n), .rst_c2r0(rst_n), .rst_c2r1(rst_n), .rst_c2r2(rst_n), .rst_c2r3(rst_n), .rst_c3r0(rst_n), .rst_c3r1(rst_n), .rst_c3r2(rst_n), .rst_c3r3(rst_n), .far(1'b0), .trst_0_0(rr[0]), .trst_0_1(rr[1]), .trst_0_2(rr[2]), .trst_0_3(rr[3]), .trst_1_0(rr[4]), .trst_1_1(rr[5]), .trst_1_2(rr[6]), .trst_1_3(rr[7]), .trst_2_0(rr[8]), .trst_2_1(rr[9]), .trst_2_2(rr[10]), .trst_2_3(rr[11]), .trst_3_0(rr[12]), .trst_3_1(rr[13]), .trst_3_2(rr[14]), .trst_3_3(rr[15]));
qfd_c_b16_full_fabric #(.MUT(M)) u_full (.ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck), .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck), .rst_c0r0(rst_n), .rst_c0r1(rst_n), .rst_c0r2(rst_n), .rst_c0r3(rst_n), .rst_c1r0(rst_n), .rst_c1r1(rst_n), .rst_c1r2(rst_n), .rst_c1r3(rst_n), .rst_c2r0(rst_n), .rst_c2r1(rst_n), .rst_c2r2(rst_n), .rst_c2r3(rst_n), .rst_c3r0(rst_n), .rst_c3r1(rst_n), .rst_c3r2(rst_n), .rst_c3r3(rst_n), .far(1'b0), .trst_0_0(rf[0]), .trst_0_1(rf[1]), .trst_0_2(rf[2]), .trst_0_3(rf[3]), .trst_1_0(rf[4]), .trst_1_1(rf[5]), .trst_1_2(rf[6]), .trst_1_3(rf[7]), .trst_2_0(rf[8]), .trst_2_1(rf[9]), .trst_2_2(rf[10]), .trst_2_3(rf[11]), .trst_3_0(rf[12]), .trst_3_1(rf[13]), .trst_3_2(rf[14]), .trst_3_3(rf[15]));
qfd_c_b16_fullb_fabric #(.MUT(0)) u_fullb (.ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck), .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck), .rst_c0r0(rst_n), .rst_c0r1(rst_n), .rst_c0r2(rst_n), .rst_c0r3(rst_n), .rst_c1r0(rst_n), .rst_c1r1(rst_n), .rst_c1r2(rst_n), .rst_c1r3(rst_n), .rst_c2r0(rst_n), .rst_c2r1(rst_n), .rst_c2r2(rst_n), .rst_c2r3(rst_n), .rst_c3r0(rst_n), .rst_c3r1(rst_n), .rst_c3r2(rst_n), .rst_c3r3(rst_n), .far(1'b0), .trst_0_0(rb[0]), .trst_0_1(rb[1]), .trst_0_2(rb[2]), .trst_0_3(rb[3]), .trst_1_0(rb[4]), .trst_1_1(rb[5]), .trst_1_2(rb[6]), .trst_1_3(rb[7]), .trst_2_0(rb[8]), .trst_2_1(rb[9]), .trst_2_2(rb[10]), .trst_2_3(rb[11]), .trst_3_0(rb[12]), .trst_3_1(rb[13]), .trst_3_2(rb[14]), .trst_3_3(rb[15]));
initial begin
for(cyc=0;cyc<500;cyc=cyc+1)begin
 @(negedge ck); rst_n=!(cyc<20 || (cyc>=100 && cyc<400));
 @(posedge ck); #0.1;
 if(cyc>=20)begin
  if(rf!==rr)$fatal(1,"CB16_RESET_CALENDAR_SLIP dut=full cycle=%0d expected=%h actual=%h",cyc,rr,rf);
  if(rb!==rr)$fatal(1,"CB16_RESET_CALENDAR_SLIP dut=fullb cycle=%0d expected=%h actual=%h",cyc,rr,rb);
 end
end
$display("CB16_RESET_CALENDAR_PASS M=%0d leaves=16 cycles=500",M); $finish;
end
endmodule
