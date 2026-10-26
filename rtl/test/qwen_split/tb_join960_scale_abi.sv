`timescale 1ns/1ps
// Q-FUNC join960: scale-ROM ABI bench. The six REAL TP8 slab masters (qfd_port_tiles_b + _b_f1, 384 mapped
// ot_rom_4096x266_m8 macros, released masks) are wired exactly as join960 (tc -> pt.tc, pt.tc_e -> f1.tc, f1.am/rq/cw
// -> pt), and every command word c_b is packed with the TT's own c-port expression (qfd_tt_ctlm_static_s:
// {scale_addr[192b+191:192b], scale_gre[8b+7:8b], scale_re, p_f_e2, p_v_e2, t_tv_e, t_sel_e}). Each of the 24 groups gets
// a DISTINCT resident address per cycle (a_g = (i + 997 g) mod WORDS) so any slot/half/band mis-mapping fails.
// Observed: each result group's registered merged scale word (u_results.sq, observation only) at ONE fixed latency
// LAT after the command edge (+LAT=, one value for all words/groups); the expected words are compare-only. MUT=1 swaps groups 0/1 address slots in the pack.
module tb_join960_scale_abi;
parameter integer WORDS=30576, LMAX=16, MUT=0;
integer LAT=8;
reg clk=0,rst_n=0;always #1 clk=~clk;
reg [575:0] scale_addr=0;reg [23:0] scale_gre=0;reg scale_re=0;
wire [112:0] p_f_e2=0;wire p_v_e2=0;wire [12:0] t_tv_e=0,t_sel_e=0;
wire [340:0] c[0:2];
wire [575:0] pack_addr = MUT ? {scale_addr[575:48],scale_addr[23:0],scale_addr[47:24]} : scale_addr;
assign c[0]={pack_addr[191:0],scale_gre[7:0],scale_re,p_f_e2[112:0],p_v_e2,t_tv_e[12:0],t_sel_e[12:0]};
assign c[1]={pack_addr[383:192],scale_gre[15:8],scale_re,p_f_e2[112:0],p_v_e2,t_tv_e[12:0],t_sel_e[12:0]};
assign c[2]={pack_addr[575:384],scale_gre[23:16],scale_re,p_f_e2[112:0],p_v_e2,t_tv_e[12:0],t_sel_e[12:0]};
wire [6143:0] sq;

 wire [340:0] tce0;wire [2047:0] tye0;wire [2212:0] rq0f;wire [51:0] am0f;wire [2049:0] cw0f;
 wire [4095:0] tw0;wire [4424:0] rq0;wire [103:0] tf0;
 qfd_port_tiles_0 u_pt0 (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
   .tc(c[0]),.cf1(cw0f),.ty(4096'd0),.rqe(rq0f),.ame(am0f),.tc_e(tce0),.tye(tye0),.tw(tw0),.rq(rq0),.tf(tf0));
 qfd_port_tiles_0_f1 u_pt0f (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw8(514'd0),.bw9(514'd0),.bw10(514'd0),.bw11(514'd0),.bw12(514'd0),.bw13(514'd0),.bw14(514'd0),.bw15(514'd0),
   .tc(tce0),.ty(tye0),.rq(rq0f),.am(am0f),.cw0(cw0f));
 assign sq[2048*0 +: 1024]=u_pt0.u_results.sq; assign sq[2048*0+1024 +: 1024]=u_pt0f.u_results.sq;
 wire [340:0] tce1;wire [2047:0] tye1;wire [2212:0] rq1f;wire [51:0] am1f;wire [2049:0] cw1f;
 wire [4095:0] tw1;wire [4424:0] rq1;wire [103:0] tf1;
 qfd_port_tiles_1 u_pt1 (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
   .tc(c[1]),.cf1(cw1f),.ty(4096'd0),.rqe(rq1f),.ame(am1f),.tc_e(tce1),.tye(tye1),.tw(tw1),.rq(rq1),.tf(tf1));
 qfd_port_tiles_1_f1 u_pt1f (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw8(514'd0),.bw9(514'd0),.bw10(514'd0),.bw11(514'd0),.bw12(514'd0),.bw13(514'd0),.bw14(514'd0),.bw15(514'd0),
   .tc(tce1),.ty(tye1),.rq(rq1f),.am(am1f),.cw1(cw1f));
 assign sq[2048*1 +: 1024]=u_pt1.u_results.sq; assign sq[2048*1+1024 +: 1024]=u_pt1f.u_results.sq;
 wire [340:0] tce2;wire [2047:0] tye2;wire [2212:0] rq2f;wire [51:0] am2f;wire [2049:0] cw2f;
 wire [4095:0] tw2;wire [4424:0] rq2;wire [103:0] tf2;
 qfd_port_tiles_2 u_pt2 (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
   .tc(c[2]),.cf1(cw2f),.ty(4096'd0),.rqe(rq2f),.ame(am2f),.tc_e(tce2),.tye(tye2),.tw(tw2),.rq(rq2),.tf(tf2));
 qfd_port_tiles_2_f1 u_pt2f (.ck(clk),.ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),.ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),.ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),.ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),.ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),.rst_n(rst_n),.bw8(514'd0),.bw9(514'd0),.bw10(514'd0),.bw11(514'd0),.bw12(514'd0),.bw13(514'd0),.bw14(514'd0),.bw15(514'd0),
   .tc(tce2),.ty(tye2),.rq(rq2f),.am(am2f),.cw2(cw2f));
 assign sq[2048*2 +: 1024]=u_pt2.u_results.sq; assign sq[2048*2+1024 +: 1024]=u_pt2f.u_results.sq;
reg [255:0] expected[0:WORDS-1];reg [8191:0] expected_path;
integer i,g,errors=0,checked=0,cyc=0;
reg [23:0] hist_a[0:LMAX][0:23];reg hist_v[0:LMAX];
always @(posedge clk) begin
 cyc<=cyc+1;
 for(integer k=LMAX;k>0;k=k-1) begin hist_v[k]<=hist_v[k-1]; for(integer q=0;q<24;q=q+1) hist_a[k][q]<=hist_a[k-1][q]; end
 hist_v[0]<=scale_re; for(integer q=0;q<24;q=q+1) hist_a[0][q]<=scale_addr[24*q+:24];
 #0.1;
 if(hist_v[LAT]) begin
  for(g=0;g<24;g=g+1) if(sq[256*g+:256]!==expected[hist_a[LAT][g]]) begin
   errors=errors+1; if(errors<6)$display("MISMATCH group=%0d addr=%0d got=%h exp=%h",g,hist_a[LAT][g],sq[256*g+:256],expected[hist_a[LAT][g]]);
  end
  checked=checked+1;
 end
end
initial begin
 for(integer k=0;k<=LMAX;k=k+1) hist_v[k]=0;
 if($value$plusargs("LAT=%d",LAT)) $display("LAT %0d",LAT);
 if(!$value$plusargs("EXPECTED=%s",expected_path))$fatal(1,"missing declared observer expected words");
 $readmemh(expected_path,expected);
 repeat(6)@(negedge clk); rst_n=1; repeat(6)@(negedge clk);
 for(i=0;i<WORDS;i=i+1) begin
  scale_re=1; scale_gre=24'hffffff;
  for(g=0;g<24;g=g+1) scale_addr[24*g+:24]=24'((i+997*g)%WORDS);
  @(negedge clk);
 end
 scale_re=0; scale_gre=0; repeat(LAT+4)@(negedge clk);
 if(checked!=WORDS) begin errors=errors+1; $display("COUNT checked=%0d expected=%0d",checked,WORDS); end
 if(errors) $display("FAIL join960_scale_abi errors=%0d checked=%0d",errors,checked);
 else $display("PASS join960_scale_abi checked=%0d words x 24 groups (distinct addresses) via TT c-port packing, 6 real slab masters, fixed latency %0d",checked,LAT);
 $finish;
end
endmodule
