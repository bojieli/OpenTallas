`timescale 1ns/1ps
module tb;
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0, larm_v=0; reg[3:0] larm_g=0; reg[13:0] larm_base=0;
 reg[3:0] i_v=0; reg[1023:0] i_d01=0,i_d23=0;
 wire[3:0] a_v,b_v; wire[55:0] a_row,b_row; wire[1023:0] a_d01,a_d23,b_d01,b_d23;
 wire[2:0] a_fault,b_fault;
 dsfd_vm_static_landing #(.PINREG(1)) ref_dut(.ck(ck),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
 .i_v(i_v),.i_d01(i_d01),.i_d23(i_d23),.o_v(a_v),.o_row(a_row),.o_d01(a_d01),.o_d23(a_d23),.fault(a_fault));
 dsfd_vm_static_landing_joined dut(.ck({5{ck}}),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
 .i_v(i_v),.i_d01(i_d01),.i_d23(i_d23),.o_v(b_v),.o_row(b_row),.o_d01(b_d01),.o_d23(b_d23),.fault(b_fault));
 reg [2:0] prev_fault0,prev_fault1;
 always @(posedge ck) begin prev_fault0<=a_fault; prev_fault1<=prev_fault0; end
 integer c,j,l,bad=0, checked=0; integer seed=81; reg[31:0] rng=32'h12345678;
 task step;
 begin
 @(posedge ck); #1;
 if(c>6) begin
 if(a_v!==b_v || prev_fault1!==b_fault || a_d01!==b_d01 || a_d23!==b_d23) bad=bad+1;
 for(l=0;l<4;l=l+1) if(a_v[l] && a_row[14*l+:14]!==b_row[14*l+:14]) bad=bad+1;
 checked=checked+1;
 end
 @(negedge ck);
 end endtask
 initial begin
 // Full payload shape, simultaneous four-lane traffic, arm-adjacent arrivals, rollover, invalid groups and reset.
 for(c=0;c<1400;c=c+1) begin
 rng = (rng<<1) ^ (rng[31]?32'h04c11db7:0);
 rst_n = c>=8 && !(c>=700 && c<706);
 i_v = rng[3:0]; larm_v=0;
 if(c%73==12) begin larm_v=1; larm_g=0; larm_base=(c%146==12)?14'd16380:14'd90; end
 if(c%73==13) begin larm_v=1; larm_g=5; larm_base=14'd16382; end
 if(c%73==14) begin larm_v=1; larm_g=6; larm_base=14'd50; end
 if(c%73==40) begin larm_v=1; larm_g=3; end
 for(j=0;j<32;j=j+1) begin i_d01[32*j+:32]=rng^(c*32+j); i_d23[32*j+:32]=~rng^(c*32+j); end
 step;
 end
 if(bad==0) begin $display("LANDING_JOINED PASS checked=%0d age=2 lanes=4 diagnostic_age_added=2 startup=lane_plus_2",checked); $finish; end
 else begin $display("LANDING_JOINED FAIL bad=%0d checked=%0d",bad,checked); $fatal(1); end
 end
endmodule
