`timescale 1ns/1ps
// Mechanism only: one actual folded SM head -> actual macro P buffer ->
// actual H8 P source. Operand rows are unit stimuli, not a global programme.
module tb_svc_feedback;
 integer early=0,nv=2,ready_rows=1;
 reg ck=0; always #0.4165 ck=~ck;
 reg rst=0,jst=0,rv=0,rp=0; reg[2:0]rj=0;reg[511:0]rd=0;
 wire wv,fu,fo,alive,den;wire[13:0]wa;wire[15:0]wm;wire[511:0]wd;wire[7:0]jid;
 ot_s81_su_sms_fold2 u_sm(.clk(ck),.rst_in(rst),.cfg_g(4'd0),.j_st(jst),.j_kind(4'd4),.j_jid(8'd1),.r_v(rv),.r_p(rp),.r_j(rj),.r_d(rd),.w_v(wv),.w_a(wa),.w_m(wm),.w_d(wd),.o_fu(fu),.o_fo(fo),.o_alive(alive),.o_den(den),.o_rjid(jid));
 // Bench glue retains the production rs_c BF16/P-buffer sampling equations.
 // This is a local readiness mechanism, not global PIO calibration.
 function automatic[15:0]bf16(input[31:0]x);reg[31:0]y;begin y=x+32'h7fff+32'(x[16]);bf16=y[31:16];end endfunction
 reg sek=0;reg[5:0]pb_n=0;reg[7:0]pk=0;reg pon=0;reg[15:0]jcs=0,pio=0;reg[9:0]tjob=32;
 wire pb_w=wv&&sek&&pb_n!=6'd40;wire[255:0]prw,pb_wd;wire fire,missing;wire[1075:0]beat;
 for(genvar i=0;i<16;i++)assign pb_wd[16*i+:16]=bf16(wd[32*i+:32]);
 wire[7:0]pk_n=fire?pk+1'b1:pk;
 dsdv_svc_mem_ar #(.W(256),.DEPTH(40),.AW(6),.MACRO(1)) u_pb(.clk(ck),.ra_n(pk_n[7:2]),.we(pb_w),.wa(pb_n),.wd(pb_wd),.rd(prw));
 dsdv_svc_p_source #(.H(8))u_p(.pon(pon),.hsel(1'b1),.pk(pk),.tile(4'd0),.tjob(tjob),.jcs(jcs),.pio(pio),.prw(prw),.rows_ready(pb_n),.fire(fire),.missing(missing),.beat(beat));
 integer cyc=0,errors=0,writes=0,fires=0,misses=0,nonzero_rows=0,last_row=0,first_write=0,last_write=0,first_fire=0;reg[255:0]expected[0:39];
 always@(posedge ck)begin
  cyc<=cyc+1;
  if(!rst)begin sek<=0;pb_n<=0;pk<=0;jcs<=0;end
  else begin
   jcs<=jcs+1;
   if(jst)begin sek<=1;pb_n<=0;end else if(pb_w)pb_n<=pb_n+1;
   if(fire)pk<=pk+1;
   if(pb_w)begin expected[writes]=pb_wd;if(|pb_wd)nonzero_rows=nonzero_rows+1;writes=writes+1;if(!first_write)first_write=cyc;last_write=cyc;end
   if(fire)begin
    if(!first_fire)first_fire=cyc;
    fires=fires+1;
    if(missing)misses=misses+1;
    else for(integer i=0;i<4;i++)if(4*pk+i<tjob && beat[32+32*(8*i)+:32]!=={expected[pk/4][16*(4*(pk%4)+i)+:16],16'h0000})errors=errors+1;
   end
  end
 end
 task tick;begin @(negedge ck);end endtask
 initial begin
  if($value$plusargs("early=%d",early));
  if($value$plusargs("nv=%d",nv));
  if($value$plusargs("ready_rows=%d",ready_rows));
  if(nv<1||nv>40)$fatal(1,"invalid nv");
  tjob=16*nv;
  repeat(64)tick;rst=1;repeat(16)tick;jst=1;tick;jst=0;
  rv=1;rp=1;rj=0;rd=0;rd[64+:7]=nv;rd[96+:32]=32'h3e800000;rd[128+:3]=$clog2(nv);tick;
  rj=1;rd={16{32'h3f000000}};tick;rv=0;rp=0;repeat(4)tick;
  for(integer k=0;k<nv;k++)begin rv=1;for(integer i=0;i<16;i++)rd[32*i+:32]=32'h3e800000+(k*16+i)*32'h10000;last_row=cyc;tick;rv=0;repeat(7)tick;end
  // Arm only from measured local readiness, not a presumed global GO offset.
  // The negative control intentionally reads before any e row exists.
  if(!early)wait(pb_n>=ready_rows);
  tick;pio=jcs;pon=1;repeat(600)tick;pon=0;
  if(writes!=nv||fires!=4*nv||nonzero_rows!=nv||fu||fo)errors=errors+1;
  $display("FEEDBACK_DATA nonzero_rows=%0d expected_rows=%0d",nonzero_rows,nv);
  $display("FEEDBACK_TIMES last_row=%0d first_write=%0d last_write=%0d first_fire=%0d write_delta=%0d fire_delta=%0d",last_row,first_write,last_write,first_fire,first_write-last_row,first_fire-last_row);
  if(early)begin if(misses==0)$fatal(1,"FEEDBACK EARLY control missed");$display("FEEDBACK NEGATIVE_CAUGHT misses=%0d writes=%0d fires=%0d",misses,writes,fires);end
  else begin if(errors||misses)$fatal(1,"FEEDBACK FAIL errors=%0d misses=%0d writes=%0d fires=%0d",errors,misses,writes,fires);$display("FEEDBACK PASS writes=%0d fires=%0d errors=0",writes,fires);end
  $finish;
 end
endmodule
