`timescale 1ns/1ps
module tb_su_sequential_collective_join;
 reg qs=1,ss=1,rst=0;always #2 qs=~qs;always #1.5 ss=~ss;
 integer n=-1,p=-1,checks=0; reg[295:0]redmem[0:399];reg[231:0]ringmem[0:399];
 reg[295:0]cmd=0;reg[231:0]ringcmd=0;wire[6143:0]uop;
 wire[3:0]rv,rfv,rrwv,qfault,crv;wire[127:0]rt,rx;wire[19:0]rrwa;wire[1023:0]rrwd,crd;
 wire[11:0]crt,jfault;
 reg[259:0]del[0:35];
 wire[259:0]nativein=$test$plusargs("MUT_EQUAL_DEPTH")?del[35]:{rv,rt,rx};
 always @(posedge qs)if(!rst)begin for(integer i=0;i<36;i=i+1)del[i]<=0;end else begin
  del[0]<={rv,rt,rx};for(integer i=1;i<36;i=i+1)del[i]<=del[i-1];end
 function automatic[31:0]partial(input integer q);
  case(q)0:partial=32'h60ad78ec;1:partial=32'h3f400000;2:partial=32'he0ad78ec;default:partial=32'hbf200000;endcase
 endfunction
 if(1)begin:g_q0
  assign uop[0*1536+:1536]={848'd0,ringcmd[0*58+:58],630'd0};
  ot_hbm_su_static_qcore #(.COLLPORT(1)) core(
   .clk_rf({64{qs}}),.clk_ctl(qs),.clk_red(qs),.rst_n(rst),.rf_rd_cmd(54'd0),.red_cmd(cmd[0*74+:74]),.rf_drain_cmd(2'd0),
   .slice_x({4{partial(0)}}),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.red_sv(rv[0]),.red_tag(rt[0*32+:32]),.red_x(rx[0*32+:32]),.red_rf_v(rfv[0]),
   .rr_wv(rrwv[0]),.rr_wa(rrwa[0*5+:5]),.rr_wd(rrwd[0*256+:256]),.sfu_x(32'd0),.fault(qfault[0]));
  for(genvar w=0;w<8;w=w+1)begin:g_rfcheck
   always @(posedge qs)if(rst&&n==175)begin
    #0.2;if(core.u_rf.g_bank[56+w].u_bank.g_replica[0].v3!==32'hbf200000)
     $fatal(1,"native returned sequential RF mismatch 0%0d bank%0d",0,56+w);
   end
  end
 end
 if(1)begin:g_q1
  assign uop[1*1536+:1536]={848'd0,ringcmd[1*58+:58],630'd0};
  ot_hbm_su_static_qcore #(.COLLPORT(1)) core(
   .clk_rf({64{qs}}),.clk_ctl(qs),.clk_red(qs),.rst_n(rst),.rf_rd_cmd(54'd0),.red_cmd(cmd[1*74+:74]),.rf_drain_cmd(2'd0),
   .slice_x({4{partial(1)}}),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.red_sv(rv[1]),.red_tag(rt[1*32+:32]),.red_x(rx[1*32+:32]),.red_rf_v(rfv[1]),
   .rr_wv(rrwv[1]),.rr_wa(rrwa[1*5+:5]),.rr_wd(rrwd[1*256+:256]),.sfu_x(32'd0),.fault(qfault[1]));
  for(genvar w=0;w<8;w=w+1)begin:g_rfcheck
   always @(posedge qs)if(rst&&n==175)begin
    #0.2;if(core.u_rf.g_bank[56+w].u_bank.g_replica[0].v3!==32'hbf200000)
     $fatal(1,"native returned sequential RF mismatch 1%0d bank%0d",1,56+w);
   end
  end
 end
 if(1)begin:g_q2
  assign uop[2*1536+:1536]={848'd0,ringcmd[2*58+:58],630'd0};
  ot_hbm_su_static_qcore #(.COLLPORT(1)) core(
   .clk_rf({64{qs}}),.clk_ctl(qs),.clk_red(qs),.rst_n(rst),.rf_rd_cmd(54'd0),.red_cmd(cmd[2*74+:74]),.rf_drain_cmd(2'd0),
   .slice_x({4{partial(2)}}),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.red_sv(rv[2]),.red_tag(rt[2*32+:32]),.red_x(rx[2*32+:32]),.red_rf_v(rfv[2]),
   .rr_wv(rrwv[2]),.rr_wa(rrwa[2*5+:5]),.rr_wd(rrwd[2*256+:256]),.sfu_x(32'd0),.fault(qfault[2]));
  for(genvar w=0;w<8;w=w+1)begin:g_rfcheck
   always @(posedge qs)if(rst&&n==175)begin
    #0.2;if(core.u_rf.g_bank[56+w].u_bank.g_replica[0].v3!==32'hbf200000)
     $fatal(1,"native returned sequential RF mismatch 2%0d bank%0d",2,56+w);
   end
  end
 end
 if(1)begin:g_q3
  assign uop[3*1536+:1536]={848'd0,ringcmd[3*58+:58],630'd0};
  ot_hbm_su_static_qcore #(.COLLPORT(1)) core(
   .clk_rf({64{qs}}),.clk_ctl(qs),.clk_red(qs),.rst_n(rst),.rf_rd_cmd(54'd0),.red_cmd(cmd[3*74+:74]),.rf_drain_cmd(2'd0),
   .slice_x({4{partial(3)}}),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.red_sv(rv[3]),.red_tag(rt[3*32+:32]),.red_x(rx[3*32+:32]),.red_rf_v(rfv[3]),
   .rr_wv(rrwv[3]),.rr_wa(rrwa[3*5+:5]),.rr_wd(rrwd[3*256+:256]),.sfu_x(32'd0),.fault(qfault[3]));
  for(genvar w=0;w<8;w=w+1)begin:g_rfcheck
   always @(posedge qs)if(rst&&n==175)begin
    #0.2;if(core.u_rf.g_bank[56+w].u_bank.g_replica[0].v3!==32'hbf200000)
     $fatal(1,"native returned sequential RF mismatch 3%0d bank%0d",3,56+w);
   end
  end
 end
 ot_hbm_su_collective_red_join joiner(.clk_s(ss),.clk_q(qs),.rst_n(rst),
  .red_sv(nativein[259:256]),.red_tag(nativein[255:128]),.red_x(nativein[127:0]),.collective_uop(uop),
  .rr_wv(rrwv),.rr_wa(rrwa),.rr_wd(rrwd),.collective_rr_v(crv),.collective_rr_tag(crt),.collective_rr_data(crd),.fault(jfault));
 initial begin
  for(integer i=0;i<400;i=i+1)begin redmem[i]=0;ringmem[i]=0;end
  for(integer q=0;q<4;q=q+1)redmem[10][q*74+:74]=(74'd1<<73)|(74'd80<<40);
  redmem[100][0+:74]=74'h3050000000000020000;
  redmem[100][74+:74]=74'h3050000000000020000;
  redmem[100][148+:74]=74'h3050000000000020000;
  redmem[100][222+:74]=74'h3050000000000020000;
  redmem[101][0+:74]=74'h3050000000000060000;
  redmem[101][74+:74]=74'h3050000000000060000;
  redmem[101][148+:74]=74'h3050000000000060000;
  redmem[101][222+:74]=74'h3050000000000060000;
  redmem[102][0+:74]=74'h30500000000000a0000;
  redmem[102][74+:74]=74'h30500000000000a0000;
  redmem[102][148+:74]=74'h30500000000000a0000;
  redmem[102][222+:74]=74'h30500000000000a0000;
  redmem[103][0+:74]=74'h30500000000000e0000;
  redmem[103][74+:74]=74'h30500000000000e0000;
  redmem[103][148+:74]=74'h30500000000000e0000;
  redmem[103][222+:74]=74'h30500000000000e0000;
  redmem[104][0+:74]=74'h3050000000000120000;
  redmem[104][74+:74]=74'h3050000000000120000;
  redmem[104][148+:74]=74'h3050000000000120000;
  redmem[104][222+:74]=74'h3050000000000120000;
  redmem[105][0+:74]=74'h3050000000000160000;
  redmem[105][74+:74]=74'h3050000000000160000;
  redmem[105][148+:74]=74'h3050000000000160000;
  redmem[105][222+:74]=74'h3050000000000160000;
  redmem[106][0+:74]=74'h30500000000001a0000;
  redmem[106][74+:74]=74'h30500000000001a0000;
  redmem[106][148+:74]=74'h30500000000001a0000;
  redmem[106][222+:74]=74'h30500000000001a0000;
  redmem[107][0+:74]=74'h30500000000fefe0000;
  redmem[107][74+:74]=74'h30500000000fefe0000;
  redmem[107][148+:74]=74'h30500000000fefe0000;
  redmem[107][222+:74]=74'h30500000000fefe0000;
  ringmem[163][0+:58]=58'h000000000000007;
  ringmem[164][0+:58]=58'h000000000003800;
  ringmem[166][0+:58]=58'h000000588000000;
  ringmem[220][0+:58]=58'h003324020000000;
  ringmem[163][58+:58]=58'h000000000000007;
  ringmem[168][58+:58]=58'h003014000000000;
  ringmem[169][58+:58]=58'h000000000000070;
  ringmem[171][58+:58]=58'h000000000700000;
  ringmem[180][58+:58]=58'h00000000000b800;
  ringmem[182][58+:58]=58'h000002988000000;
  ringmem[222][58+:58]=58'h003324000000000;
  ringmem[163][116+:58]=58'h000000000000007;
  ringmem[186][116+:58]=58'h003114000000000;
  ringmem[187][116+:58]=58'h000000000000170;
  ringmem[189][116+:58]=58'h000000001700000;
  ringmem[198][116+:58]=58'h00000000000b800;
  ringmem[200][116+:58]=58'h000002d90000000;
  ringmem[218][116+:58]=58'h003324020000000;
  ringmem[163][174+:58]=58'h000000000000007;
  ringmem[184][174+:58]=58'h003114020000000;
  ringmem[202][174+:58]=58'h018848000000000;
  ringmem[203][174+:58]=58'h000000000000270;
  ringmem[205][174+:58]=58'h000000002700000;
  ringmem[214][174+:58]=58'h00000000007b800;
  ringmem[216][174+:58]=58'h1c0003d88000000;
  if($test$plusargs("MUT_READ_LEAD"))ringmem[169][58+:58]=0;
  if($test$plusargs("MUT_LP"))begin ringmem[164]=ringmem[163];ringmem[163]=0;end
  if($test$plusargs("MUT_REASSOC"))begin
   for(integer i=0;i<400;i=i+1)ringmem[i]=0;
   ringmem[163][0+:58]=58'h000000000000007;
   ringmem[164][0+:58]=58'h000000000003800;
   ringmem[166][0+:58]=58'h000000588000000;
   ringmem[220][0+:58]=58'h003324020000000;
   ringmem[163][58+:58]=58'h000000000000007;
   ringmem[168][58+:58]=58'h003014000000000;
   ringmem[169][58+:58]=58'h000000000000070;
   ringmem[171][58+:58]=58'h000000000700000;
   ringmem[198][58+:58]=58'h00000000000b800;
   ringmem[200][58+:58]=58'h000002d88000000;
   ringmem[222][58+:58]=58'h003324000000000;
   ringmem[163][116+:58]=58'h000000000000007;
   ringmem[164][116+:58]=58'h000000000003800;
   ringmem[166][116+:58]=58'h000000d90000000;
   ringmem[218][116+:58]=58'h003324020000000;
   ringmem[163][174+:58]=58'h000000000000007;
   ringmem[168][174+:58]=58'h018848000000000;
   ringmem[169][174+:58]=58'h000000000000270;
   ringmem[171][174+:58]=58'h000000002700000;
   ringmem[202][174+:58]=58'h003114000000000;
   ringmem[203][174+:58]=58'h000000000000570;
   ringmem[205][174+:58]=58'h000000005700000;
   ringmem[214][174+:58]=58'h00000000007b800;
   ringmem[216][174+:58]=58'h1c0003d88000000;
  end
  #23.9;rst=1;
 end
 always @(posedge qs)if(rst)n=n+1;
 always @(negedge qs)if(rst)cmd=redmem[n+1];
 always @(negedge ss)if(rst)ringcmd=ringmem[p+1];
 always @(posedge ss)if(rst)begin
  p=p+1;#0.2;
  if(|jfault||(|qfault))$fatal(1,"SU_SEQUENTIAL_COLLECTIVE FAIL fault stream%0d join%h q%h",p,jfault,qfault);
  for(integer q=0;q<4;q=q+1)begin
   // Independent expected timeline: root3=216, CW q2=218,q0=220,q1=222.
   if(crv[q]!==((q==3&&p==216)||(q==2&&p==218)||(q==0&&p==220)||(q==1&&p==222)))
    $fatal(1,"SU_SEQUENTIAL_COLLECTIVE FAIL return edge stream%0d q%0d",p,q);
   if(crv[q])begin
    if(crt[q*3+:3]!=3||crd[q*256+:256]!=={8{32'hbf200000}})
     $fatal(1,"SU_SEQUENTIAL_COLLECTIVE FAIL FP32 order stream%0d q%0d got%h",p,q,crd[q*256+:256]);
    checks=checks+8;
   end
  end
  if(p==300)begin
   if(checks!=32)$fatal(1,"SU_SEQUENTIAL_COLLECTIVE FAIL coverage");
   $display("SU_SEQUENTIAL_COLLECTIVE PASS actual_qcores4 mapped_SRAM8 cxports4 captured_rings4 checks32 sequential0123 lp163 rr216_218_220_222 RF_all_quarters");$finish;
  end
 end
endmodule
