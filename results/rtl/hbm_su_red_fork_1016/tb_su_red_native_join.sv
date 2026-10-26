`timescale 1ns/1ps
module tb_su_red_native_join;
 reg qs=1, ss=1, rst=0;
 always #2 qs=~qs;
 always #1.5 ss=~ss;
 integer n=-1,p=-1,seen=0,errors=0;
 reg [73:0] cmdmem[0:399]; reg [73:0] cmd=0;
 reg [127:0] sx=0;
 wire redv,rfv; wire[31:0] redt,redx; wire qfault,cxfault;
 wire rrv; wire[4:0] rrwa; wire[255:0] rrwd;
 reg rr_v=0; reg[255:0] rr_d=0;
 wire rc_v; wire[2:0] rc_tag; wire[255:0] rc_d;
 reg[64:0] delay_line[0:35];
 wire[64:0] redin=$test$plusargs("MUT_EQUAL_DEPTH")?delay_line[35]:{redv,redt,redx};
 always @(posedge qs)begin
  if(!rst)begin for(integer i=0;i<36;i=i+1)delay_line[i]<=0;end
  else begin delay_line[0]<={redv,redt,redx};for(integer i=1;i<36;i=i+1)delay_line[i]<=delay_line[i-1];end
 end
 ot_hbm_su_static_qcore #(.COLLPORT(1)) core(
 .clk_rf({64{qs}}),.clk_ctl(qs),.clk_red(qs),.rst_n(rst),.rf_rd_cmd(54'd0),.red_cmd(cmd),.rf_drain_cmd(2'd0),
 .slice_x(sx),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),.red_sv(redv),.red_tag(redt),.red_x(redx),.red_rf_v(rfv),
 .rr_wv(rrv),.rr_wa(rrwa),.rr_wd(rrwd),.sfu_x(32'd0),.fault(qfault));
 ot_hbm_su_static_cxport #(.QID(0),.B39_NOOP(1),.INJ_RET(9)) cx(
 .clk_s(ss),.clk_q(qs),.rst_n(rst),.inj_rd(2'd0),.inj_addr(160'd0),.del_valid(4'd0),.del_flit(2180'd0),.del_obase(160'd0),
 .rc_v(rc_v),.rc_tag(rc_tag),.rc_d(rc_d),.rr_v(rr_v),.rr_tag(3'd3),.rr_d(rr_d),.inj_q(4096'd0),
 .red_sv(redin[64]),.red_tag(redin[63:32]),.red_x(redin[31:0]),.rr_wv(rrv),.rr_wa(rrwa),.rr_wd(rrwd),
 .ro_v(16'd0),.ro_x(512'd0),.red_sel(12'd0),.fault(cxfault));
 initial begin
  for(integer i=0;i<400;i=i+1)cmdmem[i]=0;
  for(integer w=0;w<8;w=w+1)cmdmem[10+w]=(74'd1<<73)|(74'(80+w)<<40);
  cmdmem[100] = 74'h3050000000000020000;
  cmdmem[101] = 74'h3051000000000060000;
  cmdmem[102] = 74'h30520000000000a0000;
  cmdmem[103] = 74'h30530000000000e0000;
  cmdmem[104] = 74'h3054000000000120000;
  cmdmem[105] = 74'h3055000000000160000;
  cmdmem[106] = 74'h30560000000001a0000;
  cmdmem[107] = 74'h3057000000080ff0000;
  if($test$plusargs("LATE"))cmdmem[107]=cmdmem[107]|(74'd1<<25);
  #23.9;rst=1;
 end
 always @(posedge qs)if(rst)n=n+1;
 always @(negedge qs)if(rst)begin
  cmd=cmdmem[n+1];
  if(n+1>=11&&n+1<19)sx={4{32'h3f800000+32'(n+1-11)}};
 end
 always @(posedge ss)if(rst)begin
  p=p+1;
  #0.2;
  if(rc_v)begin
   seen=seen+1;
   if(p!=($test$plusargs("LATE")?162:161)||rc_tag!=3)begin $display("BAD_RC_EDGE p=%0d tag=%0d",p,rc_tag);errors=errors+1;end
   for(integer w=0;w<8;w=w+1)if(rc_d[32*w+:32]!==32'h3f800000+32'(w))begin
    $display("BAD_NATIVE_WORD w=%0d got=%h",w,rc_d[32*w+:32]);errors=errors+1;
   end
  end
  if(p==350)begin
   if(seen!=1||errors||qfault||cxfault)$fatal(1,"SU_RED_NATIVE_JOIN FAIL seen=%0d errors=%0d faults=%b%b",seen,errors,qfault,cxfault);
   $display("SU_RED_NATIVE_JOIN PASS actual_qcore_two_mapped_SRAM cxport rc_edge%0d words8",$test$plusargs("LATE")?162:161);$finish;
  end
 end
 always @(negedge ss)if(rst)begin
  rr_v=(p+1==220);
  for(integer w=0;w<8;w=w+1)rr_d[32*w+:32]=32'h40000000+w;
 end
 for(genvar w=0;w<8;w=w+1)begin:g_check_return
  always @(posedge qs)if(rst&&n==170)begin
   #0.2;if(core.u_rf.g_bank[w].u_bank.g_replica[0].v0!==(32'h40000000+w))$fatal(1,"native returned RF bank mismatch %0d",w);
  end
 end
endmodule
