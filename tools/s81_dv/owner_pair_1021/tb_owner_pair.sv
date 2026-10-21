`timescale 1ns/1ps
// Synthetic rank-partial boundary inputs only; all copies and FP32 sums use RTL.
module tb_owner_pair;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0; integer cycle=0,bad=0,mut=0,count=0,index=0,read_cycle=0,read_seen=0;
 reg [1103:0] stimulus[0:63]; reg [31:0] dates[0:63]; reg [255:0] expected[0:0];
 reg [1103:0] line=0; reg read_v=0; reg [9:0] read_a=916;
 wire de,dw,dv; wire [1103:0] e,w,ci; wire [275:0] vb;
 wire [2:0] dir; wire [4:0] cv,swv,lov; wire [159:0] cd;
 wire [49:0] swa; wire [39:0] swm; wire [1279:0] swd,lod;
 wire rf,xf,pf,sf,pcv,pswv,lv,qv,sv,xrv,xwv;
 wire [159:0] pcd,sd; wire [9:0] pswa,xra,xwa;
 wire [7:0] pswm,xwm; wire [255:0] pswd,ld,qd,xwd;
 wire [157:0] unused_dn; wire [409:0] unused_up;
 ot_s81sl_rstopt r(.clk(clk),.rst_n(rst_n),.sid(4'd4),.ri_w(line),.ri_e(1104'd0),
  .vi(276'd0),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_eo(173'd0),.nx_wo(173'd0),
  .dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(vb),.ci_dir(dir),.ci_b(ci),.fault(rf));
 ot_s81sl_xrt x(.clk(clk),.rst_n(rst_n),.sid(4'd4),.dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(vb),
  .ci_dir(dir),.ci_b(ci),.bi(1104'd0),.c_v(cv),.c_d(cd),.sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),
  .lo_v(lov),.lo_d(lod),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
  .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf));
 ot_s81sl_rly #(.W(594),.D(4)) dn(.clk(clk),.d({cv[0],cd,swv[0],swa[9:0],swm[7:0],swd[255:0],158'd0}),
  .q({pcv,pcd,pswv,pswa,pswm,pswd,unused_dn}));
 ot_s81sl_rly #(.W(667),.D(4)) up(.clk(clk),.d({lv,ld,410'd0}),.q({lov[0],lod[255:0],unused_up}));
 assign lov[4:1]=0; assign lod[1279:256]=0;
 ot_s81sl_vp p(.clk(clk),.rst_n(rst_n),.c_v(pcv),.c_d(pcd),.sw_v(pswv),.sw_a(pswa),.sw_m(pswm),.sw_d(pswd),
  .cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),.lo_v(lv),.lo_d(ld),.s_v(sv),.s_d(sd),
  .x_rv(xrv|read_v),.x_ra(read_v?read_a:xra),.x_qv(qv),.x_qd(qd),
  .x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd),.hq_v(1'b0),.hq_d(256'd0),.fault(pf));
 // The final inspection request belongs to the bench reader, not the VS
 // operand channel. Deliver every VS-requested response unchanged.
 ot_s81sl_vs s(.clk(clk),.rst_n(rst_n),.s_v(sv),.s_d(sd),.x_rv(xrv),.x_ra(xra),.x_qv(qv && read_cycle==0),.x_qd(qd),
  .x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd),.sw_vi(1'b0),.sw_ri(64'd0),.sw_fi(1'b0),
  .ra_vi(1'b0),.ra_ri(32'd0),.ra_fi(1'b0),.ve_pv(1'b0),.ve_pc(2'd0),.ve_phh(32'd0),.ve_pkk(32'd0),
  .ve_pdd(32'd0),.ve_ov(1'b0),.ve_oc(2'd0),.ve_oy(256'd0),.ve_fi(1'b0),.g_v(1'b0),.g_c(2'd0),.g_d(32'd0),.fault(sf));
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(rst_n && (rf|xf|pf|sf)) bad=bad+1;
  if(pswv) $display("PAIR_WRITE %0d row=%0d mask=%h",cycle,pswa,pswm);
  if(xwv) $display("RB_WRITE %0d row=%0d mask=%h",cycle,xwa,xwm);
  if(read_cycle && qv) begin
   read_seen=read_seen+1;
   if(qd!==expected[0]) begin bad=bad+1; $display("BAD got=%h expected=%h",qd,expected[0]); end
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut)); void'($value$plusargs("COUNT=%d",count));
  $readmemh("stim.mem",stimulus); $readmemh("dates.mem",dates); $readmemh("expected.mem",expected);
  repeat(32) @(negedge clk); rst_n=1;
  // All commands use fixed dates; neither issue nor completion waits on RTL.
  repeat(2100) begin
   @(negedge clk); line=0; read_v=0;
   if(index<count && cycle==dates[index]) begin
    line=stimulus[index];
    if(mut && line[37+:5]==4 && line[78+:10]==905) line[78]=0;
    index=index+1;
   end
   if(cycle==2000) begin read_v=1; read_cycle=cycle; end
  end
  if(index!=count || read_seen!=1) bad=bad+1;
  $display("OWNER_PAIR mut=%0d bad=%0d commands=%0d rf=%h xf=%h pf=%h sf=%h",mut,bad,index,rf,xf,pf,sf);
  if(bad) $fatal(1,"OWNER_PAIR FAIL"); $display("OWNER_PAIR PASS"); $finish;
 end
endmodule
