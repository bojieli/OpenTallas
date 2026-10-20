`timescale 1ns/1ps
module tb;
parameter integer RR=18,WR=15;
reg refclk=0;always #5 refclk=~refclk;reg por_n=0;wire clk,stream,rs,rq,br,brfault;
hfd_ckgen cg(.refclk(refclk),.por_n(por_n),.pll_stream(stream),.pll_serial(clk),.por_serial(rq),.por_stream(rs));
ot_hbm_su_bridge_release_s rel(.clk_serial(clk),.rst_n(rq),.prog_busy(busy),.bridge_rst_n(br),.fault(brfault));

// Functional PLL causality and precise simulator phase receipts.
integer stream_edges=0, serial_edges=0;
time previous_stream=0, previous_serial=0;
always @(posedge stream) begin
 stream_edges++;
 if(stream_edges==1 && $realtime!=0.417)$fatal(1,"CLOCK_PHASE stream first=%0t",$realtime);
 if(stream_edges>1 && ($rtoi($realtime*1000.0+0.5)-previous_stream)!=834)$fatal(1,"CLOCK_PHASE stream period");
 previous_stream=$rtoi($realtime*1000.0+0.5);
end
always @(posedge clk) begin
 serial_edges++;
 if(serial_edges==1 && $realtime!=0.556)$fatal(1,"CLOCK_PHASE serial first=%0t",$realtime);
 if(serial_edges>1 && ($rtoi($realtime*1000.0+0.5)-previous_serial)!=1112)$fatal(1,"CLOCK_PHASE serial period");
 previous_serial=$rtoi($realtime*1000.0+0.5);
end
initial begin
 #200;
 if(stream_edges<2 || serial_edges<2 || !cg.locked || !rs || !rq)
  $fatal(1,"CLOCK_CAUSAL_GUARD stream=%0d serial=%0d locked=%b rs=%b rq=%b",stream_edges,serial_edges,cg.locked,rs,rq);
 $display("CLOCK_CAUSAL_PASS stream_half_ps=417 serial_half_ps=556 lock=%b release=%b%b",cg.locked,rs,rq);
end
initial begin repeat(4400)@(posedge stream);$fatal(1,"FIXED_EVENT_HORIZON incomplete after4400 stream edges");end

integer reqmut=0;integer st=-1,qt=-1;always @(posedge stream)if(rs)st=st+1;always @(posedge clk)if(rq)qt=qt+1;
wire[16:0] srq_unused,rrq_unused;wire[256:0] ret;wire bf;assign srq_unused=0;
ot_hbm_su_multirate_bridge bridge(.serial_clk(clk),.stream_clk(stream),.rst_n(br),.serial_rq(srq_unused),.serial_wq(281'b0),.stream_rq(rrq_unused),.stream_rr(257'b0),.stream_done(1'b0),.fault(bf));
always @(posedge stream)begin #0.001;if(rs && rrq_unused[16])$display("TIMING rq stream=%0d ps=%0t sector=%h phase=%d",st,$realtime,rrq_unused[15:0],bridge.phase);end
always @(posedge br)$display("TIMING bridge release ps=%0t st=%0d qt=%0d",$realtime,st,qt);
reg rst_n=0,we=0,start=0;reg[15:0] bank=0;reg[6:0] row=0;reg[255:0] data=0;
wire busy,valid,done,fault;wire[15:0] edge_index;wire[2421:0] command;
reg[279:0] cfg[0:4095];reg[2421:0] exp[0:7110];integer cyc=-1,s=-1,n=0,first=-1;string fn;integer want_startup=9,N=44,W=56;string goldfile;
ot_hbm_su_programme_pslice_c5 dut(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),.start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
always @(posedge clk) if(rst_n) begin
 cyc=cyc+1;
 if(start)s=cyc;
 if(valid)begin
  if(first<0)begin first=cyc;if(cyc-s!=want_startup)$fatal(1,"PRODUCER FAIL startup got=%0d expected=%0d",cyc-s,want_startup);end
  $display("CMD e=%0d serial=%0d stream=%0d delta=%0d ps=%0t",edge_index,qt,st,cyc-s,$time);
  if(edge_index!=n || command!==exp[n] || fault)$fatal(1,"PRODUCER FAIL edge=%0d n=%0d fault=%b",edge_index,n,fault);
  n=n+1;
 end
end

reg cv=0,dv=0,lv=0;reg[7:0] ct=96;reg[11:0] ca=0;reg[255:0] cd=0;reg[12:0] dl=160;
wire acv,adv,alv;wire[7:0] act;wire[11:0] aca,adb;wire[255:0] acd;wire[12:0] adl;wire[15:0] adlp;
ot_hbm_host_cfg_leaf_sw leaf(.clk(stream),.rst_n(rs),.cfg_v(cv),.cfg_target(ct),.cfg_addr(ca),.cfg_data(cd),.desc_v(dv),.desc_base(12'b0),.desc_limit(dl),.desc_loops(16'd1),.launch_v(lv),.a_cfg_v(acv),.a_cfg_target(act),.a_cfg_addr(aca),.a_cfg_data(acd),.a_desc_v(adv),.a_desc_base(adb),.a_desc_limit(adl),.a_desc_loops(adlp),.a_launch_v(alv),.t_ready(14'b0),.t_active(14'b0),.t_fault(23'b0));
wire tf,cf,calv;wire[23:0] lr,lw,rslot,wslot;wire[7:0] rv,wv;wire[31:0] ordinal;
hfd_hgi_vm_calendar_f20 cal(.clk(stream),.clk_cap(stream),.clk_mem(stream),.clk_tgt(stream),.rst_n(rs),.tgt(8'd96),.cfg_v(acv),.cfg_target(act),.cfg_addr(aca),.cfg_data(acd),.desc_v(adv),.desc_base(adb),.desc_limit(adl),.desc_loops(adlp),.launch_v(alv),.tgt_fault(tf),.fault(cf),.calendar_v(calv),.ordinal(ordinal),.lg_local_read(lr),.lg_local_write(lw),.rslot_v(rv),.wslot_v(wv),.rslot(rslot),.wslot(wslot));
reg[255:0] image[0:159];integer mut=0;
initial begin
 $value$plusargs("MUT=%d",mut);$readmemh("calendar.mem",image);wait(rs);repeat(20)@(negedge stream);
 for(integer i=0;i<160;i++)begin cv=1;ca=i;cd=image[i];if(mut==1)cd[162:139]=0;if(mut==2)cd[88:81]=8'h01;@(negedge stream);end
 cv=0;repeat(10)@(negedge stream);dv=1;@(negedge stream);dv=0;
 while(st<(3500+(mut==3?1:0)))@(negedge stream);lv=1;@(negedge stream);lv=0;
end
wire[1:0] pfault; wire sfault,lfault;wire[33:0] lgrq;wire[561:0] wq;wire[513:0] rr;wire[1:0] dn;
ot_hbm_su_static_pgslice_lg #(.QID(0),.G(0),.READ_RETURN(18),.WRITE_RETURN(15),.MLAT(4),.ALAT(3),.LEAF(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1)) slice(
.pg_clk(stream),.clk_lane({256{clk}}),.clk_insert({128{clk}}),.rst_lane_n({32{rq}}),.clk_bcast({4{clk}}),.rst_bcast_n({4{rq}}),.clk_bank({32{clk}}),.clk_bank_macro({192{clk}}),.clk_ctl(clk),.clk_side({6{clk}}),.rst_n(rq),.bridge_rst_n(br),.control(command[2421:680]),.vmr_cmd(command[499:440]),.vmw_cmd(command[205:128]),.rf_bword(128'b0),.rf_bcmd(36'b0),.rf_dsec(256'b0),.red_sel(12'b0),.tree_cmd(12'b0),.inj_rd(2'b0),.inj_addr(160'b0),.dw_v(2'b0),.dw_row(18'b0),.dw_d(1024'b0),.fault(sfault),.lg_fault(lfault),.lg_rq(lgrq),.lg_wq(wq),.lg_rr(rr),.lg_w_done(dn),.lg_read(lr[1:0]),.lg_write(lw[1:0]),.far_rq(34'b0),.far_wq(562'b0));
integer checked=0;integer fills=0;
always @(posedge clk)if(slice.u_slice.fr_v[0] || slice.u_slice.fr_v[1])begin fills=fills+1;$display("FILL qt=%d data=%h",qt,slice.u_slice.fr_dat[0]);end
for(genvar b=0;b<2;b++)begin:B
wire[16:0] nrq;wire[280:0] nwq;wire[256:0] nrr;wire ndn;
// Exact expanded GEN2c+l12 source depths: read4/3 and5/2; write3/4.
source_lane #(17,3,b+1,0) rq_lane(stream,rs,lgrq[17*b+:17],nrq);
source_lane #(281,3,0,0) wq_lane(stream,rs,wq[281*b+:281],nwq);
source_lane #(257,3-b,0,(b==0)) rr_lane(stream,rs,nrr,rr[257*b+:257]);
wire ack_pad;source_lane #(1,3-b,0,(b==0)) done_relays(stream,rs,ndn,ack_pad);hbfd_pad #(.W(1),.N(b+1)) done_lane(.ck(stream),.rs(rs),.i(ack_pad),.o(dn[b]));
reg[280:0] hostw=0; reg[16:0] hostr=0;wire[256:0] hostrr;wire hostdone;
wire[2:0] ws=((st<200)||(st>=3800&&st<3900))?3'd1:wslot[3*b+:3];wire wv0=((st<200)||(st>=3800&&st<3900))?(|hostw):wv[b];
wire[2:0] rsel=((st>=3740&&st<3800)||st>=4140)?3'd1:rslot[3*b+:3];wire rv0=((st>=3740&&st<3800)||st>=4140)?hostr[16]:rv[b];
hfd_vms_bank_native_q0_faces vm(.rq0(nrq),.rr0(nrr),.rq1(hostr),.rr1(hostrr),.rq2(17'b0),.rq3(17'b0),.rq4(17'b0),.wq0(nwq),.wq_done0(ndn),.wq1(hostw),.wq_done1(hostdone),.bid(3'(b)),.sid(2'b0),.clk(stream),.clk_n(stream),.clk_s(stream),.clk_e(stream),.clk_w(stream),.clk_macro0(stream),.clk_macro1(stream),.clk_macro2(stream),.rst_n(rs),.rslot_v(rv0),.rslot(rsel),.wslot_v(wv0),.wslot(ws),.dq(281'b0),.kq(281'b0),.xq(276'b0),.xq2(276'b0),.pq(285'b0));
reg[255:0] expected[0:1];integer seen=0;
initial begin
if(b==0)begin
expected[0]=256'h3ea100003e8f00003e0b00003e1800003e0800003dce00003e2200003e470000;
expected[1]=256'h3df700003e3000003dd700003d9200003ec200003f0f00003e6600003ec00000;
end
if(b==1)begin
expected[0]=256'h3de900003eb800003e7700003dc400003ea800003e0400003e4300003e2d0000;
expected[1]=256'h3d8600003e1c00003e0800003ddb00003e8a00003e8d00003dfb00003e4f0000;
end
wait(rs); while(st<100)@(negedge stream);
if(b==0)hostw={1'b1,16'd264,256'h3ea0e35f3e8f2d283e0b309c3e1874323e087e3c3dcdb42f3e22152f3e471b6a,8'hff};else hostw={1'b1,16'd265,256'h3de8c4703eb80cb23e76cd7e3dc445983ea82b4c3e0454cf3e42ae3e3e2caef6,8'hff};
@(negedge stream);hostw=0;repeat(12)@(negedge stream);
if(b==0)hostw={1'b1,16'd272,256'h3df69e453e3068863dd706293d91d4593ec18c363f0f5f843e659ae23ec05ff4,8'hff};else hostw={1'b1,16'd273,256'h3d85f0423e1c163b3e07d37a3ddb711a3e8a28463e8c8e853dfab5ef3e4f398a,8'hff};
@(negedge stream);hostw=0;repeat(12)@(negedge stream);
while(st<3750)@(negedge stream);hostr={1'b1,16'(280+b)};@(negedge stream);hostr=0;
while(st<3770)@(negedge stream);hostr={1'b1,16'(288+b)};@(negedge stream);hostr=0;
end
always @(posedge stream)if(rs&&hostrr[256])begin
$display("NUM b=%d n=%d got=%h expected=%h",b,seen,hostrr[255:0],expected[seen]);
if(seen>=2 || hostrr[255:0]!==expected[seen])$fatal(1,"ARITHMETIC FAIL b=%d n=%d",b,seen);
seen=seen+1;checked=checked+1;
end
end
initial begin
if(!$value$plusargs("CFG=%s",fn))$fatal;
$value$plusargs("N=%d",N);$value$plusargs("W=%d",W);if(!$value$plusargs("GOLD=%s",goldfile))$fatal;
$readmemh(fn,cfg);$readmemh(goldfile,exp);por_n=0;#100 por_n=1;wait(rq);rst_n=1;repeat(12)@(negedge clk);
for(integer i=0;i<W;i++)begin we=1;bank=cfg[i][279:264];row=cfg[i][262:256];data=cfg[i][255:0];@(negedge clk);end
we=0;while(qt<2665)@(negedge clk);start=1;@(negedge clk);start=0;
while(st<3800)@(negedge stream);
$display("RESULT commands=%d checked=%d fills=%d producer=%b slice=%b tap=%b target=%b cal=%b release=%b",n,checked,fills,fault,sfault,lfault,tf,cf,brfault);
if(n!=N || checked!=4 || fills!=2 || fault||sfault||lfault||tf||cf||brfault)$fatal(1,"ARITHMETIC FAIL final");
$display("NATIVE_RECORD23 PASS original32words sourceGEN2c+l12 diagnostic current53cb arithmetic");$value$plusargs("REQMUT=%d",reqmut);
$display("REQUEST0_ACCEPT stream3800 original32words unchanged");
n=0;first=-1;fills=0;checked=0;
B[0].seen=0;B[1].seen=0;
begin reg[255:0] temp;
 temp=B[0].expected[0];B[0].expected[0]=B[0].expected[1];B[0].expected[1]=temp;
 temp=B[1].expected[0];B[1].expected[0]=B[1].expected[1];B[1].expected[1]=temp;
end
while(st<3805)@(negedge stream);
if(reqmut!=1)B[0].hostw={1'b1,16'd264,256'h3df69e453e3068863dd706293d91d4593ec18c363f0f5f843e659ae23ec05ff4,8'hff};
if(reqmut!=1)B[1].hostw={1'b1,16'd265,256'h3d85f0423e1c163b3e07d37a3ddb711a3e8a28463e8c8e853dfab5ef3e4f398a,8'hff};
while(st<3806)@(negedge stream);B[0].hostw=0;B[1].hostw=0;
while(st<3818)@(negedge stream);
if(reqmut!=1)B[0].hostw={1'b1,16'd272,256'h3ea0e35f3e8f2d283e0b309c3e1874323e087e3c3dcdb42f3e22152f3e471b6a,8'hff};
if(reqmut!=1)B[1].hostw={1'b1,16'd273,256'h3de8c4703eb80cb23e76cd7e3dc445983ea82b4c3e0454cf3e42ae3e3e2caef6,8'hff};
while(st<3819)@(negedge stream);B[0].hostw=0;B[1].hostw=0;
while(st<3850)@(negedge stream);if(reqmut!=2)dv=1;
while(st<3851)@(negedge stream);dv=0;
while(st<3900)@(negedge stream);lv=1;
while(st<3901)@(negedge stream);lv=0;
while(qt<(2965+(reqmut==4)))@(negedge clk);start=1;
while(qt<(2966+(reqmut==4)))@(negedge clk);start=0;
while(st<4150)@(negedge stream);B[0].hostr={1'b1,16'(280+(reqmut==3?8:0))};B[1].hostr={1'b1,16'(281+(reqmut==3?8:0))};
while(st<4151)@(negedge stream);B[0].hostr=0;B[1].hostr=0;
while(st<4170)@(negedge stream);B[0].hostr={1'b1,16'(288-(reqmut==3?8:0))};B[1].hostr={1'b1,16'(289-(reqmut==3?8:0))};
while(st<4171)@(negedge stream);B[0].hostr=0;B[1].hostr=0;
while(st<4200)@(negedge stream);
$display("RESULT second commands=%d checked=%d fills=%d producer=%b slice=%b tap=%b target=%b cal=%b release=%b",n,checked,fills,fault,sfault,lfault,tf,cf,brfault);
if(n!=N || checked!=4 || fills!=2 || fault||sfault||lfault||tf||cf||brfault)$fatal(1,"ARITHMETIC FAIL final second");
$display("SERIAL_REQUESTS2 PASS contexts=1 requests=2 start_offset_serial=300 acceptance_stream=3800,4200");
$finish;
end
endmodule
module tb_lane #(parameter integer W=1, parameter integer D=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
 if(D==0) begin:g_w assign q=d; end
 else begin:g_r
  reg [W-1:0] s [0:D-1];
  initial for(integer i=0;i<D;i=i+1) s[i]=0;
  always @(posedge clk) begin s[0]<=d; for(integer i=1;i<D;i=i+1) s[i]<=s[i-1]; end
  assign q=s[D-1];
 end
endmodule


module source_lane #(parameter W=1, N=3, PAD=0, SN=0)(input clk,rs,input[W-1:0] d,output[W-1:0] q);
wire[W-1:0] dp;
if(PAD>0)hbfd_pad #(.W(W),.N(PAD)) pad(.ck(clk),.rs(rs),.i(d),.o(dp));else assign dp=d;
wire[623:0] v[0:N];assign v[0]={{(624-W){1'b0}},dp};
for(genvar i=0;i<N;i++)begin:G
if(SN&&i==0)hbfd_rly_624_SN r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));
else hbfd_rly_624_EW r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));
end
assign q=v[N][W-1:0];endmodule
