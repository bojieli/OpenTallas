`timescale 1ns/1ps
`ifndef SU8_MUT
`define SU8_MUT 0
`endif
`ifndef SU8_XI
`define SU8_XI 0
`endif
// QW-SU8 10-20 lockstep bench: shipping SU8 leaf qfd_dv_s5_su8_rst3 (MUT=`SU8_MUT) vs the SUVM7 control projection
// (ref outputs delayed by the priced +2 input alignment / +1 output pin edges, i.e. c_su 2->6).  SU8_XI=1: run with
// --x-initial unique and compare control/valid outputs (gv, lv1, su_nr, su_idle, su_fault, su_prog, su_rows) from the
// first compare cycle, the full 1058-bit vector only from 40 cycles after the first start (datapath payload unreset by design).
module tb_su8; reg ck=0; always #1 ck=~ck; reg rst_n=0; integer cyc,warm=0,ncmp=0,bad=0,first_start=-1,nctl=0;
reg [0:0] start;
reg [0:0] d0_start, d1_start;
always @(posedge ck) begin d0_start<=start;d1_start<=d0_start;end
reg [456:0] si;
reg [456:0] d0_si, d1_si;
always @(posedge ck) begin d0_si<=si;d1_si<=d0_si;end
reg [0:0] l_retire;
reg [0:0] d0_l_retire, d1_l_retire;
always @(posedge ck) begin d0_l_retire<=l_retire;d1_l_retire<=d0_l_retire;end
reg [0:0] l_last;
reg [0:0] d0_l_last, d1_l_last;
always @(posedge ck) begin d0_l_last<=l_last;d1_l_last<=d0_l_last;end
reg [7:0] l_fault;
reg [7:0] d0_l_fault, d1_l_fault;
always @(posedge ck) begin d0_l_fault<=l_fault;d1_l_fault<=d0_l_fault;end
reg [7:0] kv_we;
reg [7:0] d0_kv_we, d1_kv_we;
always @(posedge ck) begin d0_kv_we<=kv_we;d1_kv_we<=d0_kv_we;end
reg [0:0] rd_v;
reg [0:0] d0_rd_v, d1_rd_v;
always @(posedge ck) begin d0_rd_v<=rd_v;d1_rd_v<=d0_rd_v;end
reg [0:0] red_busy;
reg [0:0] d0_red_busy, d1_red_busy;
always @(posedge ck) begin d0_red_busy<=red_busy;d1_red_busy<=d0_red_busy;end
reg [0:0] red_fault;
reg [0:0] d0_red_fault, d1_red_fault;
always @(posedge ck) begin d0_red_fault<=red_fault;d1_red_fault<=d0_red_fault;end
reg [7:0] lvm_we;
reg [7:0] d0_lvm_we, d1_lvm_we;
always @(posedge ck) begin d0_lvm_we<=lvm_we;d1_lvm_we<=d0_lvm_we;end
wire [243:0] ref_gb;
wire [2:0] ref_gv;
wire [7:0] ref_lv1;
wire [767:0] ref_pd1;
wire [0:0] ref_su_nr;
wire [0:0] ref_su_idle;
wire [0:0] ref_su_fault;
wire [15:0] ref_su_prog;
wire [15:0] ref_su_rows;
wire [243:0] good_gb;
wire [2:0] good_gv;
wire [7:0] good_lv1;
wire [767:0] good_pd1;
wire [0:0] good_su_nr;
wire [0:0] good_su_idle;
wire [0:0] good_su_fault;
wire [15:0] good_su_prog;
wire [15:0] good_su_rows;
qfd_dv_su7_control_projection u_ref(.ck(ck),.rst_n(rst_n),.start(start),.si(si),.l_retire(l_retire),.l_last(l_last),.l_fault(l_fault),.kv_we(kv_we),.rd_v(rd_v),.red_busy(red_busy),.red_fault(red_fault),.lvm_we(lvm_we),.gb(ref_gb),.gv(ref_gv),.lv1(ref_lv1),.pd1(ref_pd1),.su_nr(ref_su_nr),.su_idle(ref_su_idle),.su_fault(ref_su_fault),.su_prog(ref_su_prog),.su_rows(ref_su_rows));
qfd_dv_s5_su8_rst3 #(.MUT(`SU8_MUT)) u_good(.ck(ck),.rst_n(rst_n),.start(start),.si(d1_si),.l_retire(d1_l_retire),.l_last(d1_l_last),.l_fault(d1_l_fault),.kv_we(d1_kv_we),.rd_v(d1_rd_v),.red_busy(d1_red_busy),.red_fault(d1_red_fault),.lvm_we(d1_lvm_we),.gb(good_gb),.gv(good_gv),.lv1(good_lv1),.pd1(good_pd1),.su_nr(good_su_nr),.su_idle(good_su_idle),.su_fault(good_su_fault),.su_prog(good_su_prog),.su_rows(good_su_rows));
wire [1057:0] ref_all={ref_gb,ref_gv,ref_lv1,ref_pd1,ref_su_nr,ref_su_idle,ref_su_fault,ref_su_prog,ref_su_rows};
wire [1057:0] good_all={good_gb,good_gv,good_lv1,good_pd1,good_su_nr,good_su_idle,good_su_fault,good_su_prog,good_su_rows};
reg [1057:0] q0,q1,q2,q3; always @(posedge ck)begin q0<=ref_all;q1<=q0;q2<=q1;q3<=q2;end
initial begin
start='0;
si='0;
l_retire='0;
l_last='0;
l_fault='0;
kv_we='0;
rd_v='0;
red_busy='0;
red_fault='0;
lvm_we='0;
for(cyc=0;cyc<12000;cyc=cyc+1)begin
@(negedge ck);
if(cyc==16||cyc==3016||cyc==7016)rst_n=1; if(cyc==3000||cyc==7000)rst_n=0;
if(!rst_n)warm=0;else warm=warm+1;
start=(warm>40 && cyc%47==0); if(start && first_start<0) first_start=cyc;
si={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
l_retire=warm>40 ? $urandom : '0;
l_last=warm>40 ? $urandom : '0;
l_fault=warm>40 ? $urandom : '0;
kv_we=warm>40 ? $urandom : '0;
rd_v=warm>40 ? $urandom : '0;
red_busy=warm>40 ? $urandom : '0;
red_fault=warm>40 ? $urandom : '0;
lvm_we=warm>40 ? $urandom : '0;
si[18:1]=1+(cyc%3);si[36:19]=8*(1+cyc%4);
@(posedge ck);#0.5;
if(warm>55)begin
if(!`SU8_XI || (first_start>=0 && cyc>first_start+40)) begin ncmp=ncmp+1;
if(good_all!==q3)begin bad=bad+1;if(bad<6)$display("SU8_DIFF cyc=%0d diff=%h",cyc,good_all^q3);end end
nctl=nctl+1; if({good_all[813:803],good_all[34:0]}!=={q3[813:803],q3[34:0]})begin bad=bad+1;if(bad<6)$display("SU8_CTL_DIFF cyc=%0d",cyc);end
end end
$display("SU8_STATS mut=%0d xi=%0d n=%0d ctl=%0d bad=%0d",`SU8_MUT,`SU8_XI,ncmp,nctl,bad);
if(ncmp>10000 && bad==0)$display("SU8_EQ PASS");else $display("SU8_EQ FAIL");
$finish;end endmodule
