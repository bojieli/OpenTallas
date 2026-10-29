module candidate(input clk, input raw_0, input raw_1, input raw_2, input root_raw,
 input cland_fstart_in_a, input cland_fstart_in_b, input cland_fstart_in_c,
 input [1:0] strap_ca_tsel, input [1:0] strap_ca_pad, input strap_ca_efall,
 input strap_ca_root, output cland_start);
    wire cland_oraw = (strap_ca_tsel == 2'd0) ? raw_0 : (strap_ca_tsel == 2'd1) ? raw_1 : raw_2;
    wire cland_start_child, cland_start_root;
    wire cland_raw_sel = strap_ca_root ? root_raw : cland_oraw;
    ot_dp_landing_root #(.SETTLE(40)) u_cland_root (.clk(clk), .rst_raw_n(root_raw), .start(cland_start_root));
    assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;
    wire cland_start_t0, cland_start_t1, cland_start_t2;
    ot_dp_landing_origin_s #(.PADW(2)) u_cland_origin_t0 (
        .clk(clk), .rst_raw_n(raw_0), .p_start(cland_fstart_in_a), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t0));
    ot_dp_landing_origin_s #(.PADW(2)) u_cland_origin_t1 (
        .clk(clk), .rst_raw_n(raw_1), .p_start(cland_fstart_in_b), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t1));
    ot_dp_landing_origin_s #(.PADW(2)) u_cland_origin_t2 (
        .clk(clk), .rst_raw_n(raw_2), .p_start(cland_fstart_in_c), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t2));
    assign cland_start_child = (strap_ca_tsel == 2'd0) ? cland_start_t0 : (strap_ca_tsel == 2'd1) ? cland_start_t1 : cland_start_t2;
endmodule
module reference(input clk, input raw_0, input raw_1, input raw_2, input root_raw,
 input cland_fstart_in_a, input cland_fstart_in_b, input cland_fstart_in_c,
 input [1:0] strap_ca_tsel, input [1:0] strap_ca_pad, input strap_ca_efall,
 input strap_ca_root, output cland_start);
 wire raw_sel = strap_ca_tsel == 0 ? raw_0 : strap_ca_tsel == 1 ? raw_1 : raw_2;
 wire ps = strap_ca_tsel == 0 ? cland_fstart_in_a : strap_ca_tsel == 1 ? cland_fstart_in_b : cland_fstart_in_c;
 wire cs, rs;
 ot_dp_landing_origin_s #(.PADW(2)) orig (.clk(clk),.rst_raw_n(raw_sel),.p_start(ps),
   .strap_efall(strap_ca_efall),.strap_pad(strap_ca_pad),.start(cs));
 ot_dp_landing_root #(.SETTLE(40)) root (.clk(clk),.rst_raw_n(root_raw),.start(rs));
 assign cland_start = strap_ca_root ? rs : cs;
 endmodule
module tb;
 reg clk=0; always #5 clk=~clk;
 reg raw_0=0,raw_1=0,raw_2=0,root_raw=0;
 reg a=0,b=0,c=0;
 wire [63:0] eq;
 genvar t,p,e,r;
 generate for(t=0;t<4;t=t+1) begin:T
 for(p=0;p<4;p=p+1) begin:P
 for(e=0;e<2;e=e+1) begin:E
 for(r=0;r<2;r=r+1) begin:R
 wire cn,rf;
 candidate dut(clk,raw_0,raw_1,raw_2,root_raw,a,b,c,2'(t),2'(p),1'(e),1'(r),cn);
 reference ref0(clk,raw_0,raw_1,raw_2,root_raw,a,b,c,2'(t),2'(p),1'(e),1'(r),rf);
 assign eq[16*t+4*p+2*e+r] = (cn===rf);
 end end end end endgenerate
 integer i, comparisons=0;
 initial begin
 for(i=0;i<160;i=i+1) begin
 @(negedge clk); #1;
 raw_0=(i>3 && !(i>=72 && i<=75));
 raw_1=(i>7 && !(i>=88 && i<=91));
 raw_2=(i>11 && !(i>=104 && i<=107));
 root_raw=(i>15 && !(i>=120 && i<=123));
 a=(i>=22 && i<60) || i>=80;
 b=(i>=31 && i<65) || i>=98;
 c=(i>=43 && i<70) || i>=115;
 @(posedge clk); #1;
 if(i>1) begin
 if(eq!==64'hffffffffffffffff) $fatal(1,"MISMATCH cycle=%0d eq=%h",i,eq);
 comparisons=comparisons+64;
 end
 end
 $display("PASS ORIGIN_LOCKSTEP comparisons=%0d variants=64 added_cycles=0",comparisons);
 $finish;
 end
 endmodule
