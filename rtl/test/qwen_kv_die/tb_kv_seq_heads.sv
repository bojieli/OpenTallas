`timescale 1ns/1ps
// Transport/control exactness, not a substitute for actual attention arithmetic.
module tb_kv_seq_heads;
 parameter integer HEADS=1,Q_FP32=1,MUT=0,CLUSTER=0;
 localparam integer NQ=16*HEADS*(Q_FP32?2:1),NR=32*HEADS,NK=4*HEADS,ROWS=2*HEADS;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,xv=0;reg [10:0] xt=0;reg [511:0] xd=0;
 reg [43:0] kvd=0;reg [3:0] cr=0;reg ov=0,og=0;reg[5:0] ob=0;reg[511:0] od=0;
 wire xc,av,hs,fault;wire[518:0] ad;wire[186:0] ds;wire[8:0] cause;
 wire[2159:0] aq;wire[4*1047-1:0] kvn;
 generate if(CLUSTER==0)begin:g_flat
 ot_qkvd_kv_seq_merged #(.HEADS(HEADS),.Q_FP32(Q_FP32),.KDESC(0),.MUT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.x3_v(xv),.x3_tag(xt),.x3_d(xd),.x3_cr(xc),.sd(56'd0),.kvd(kvd),
 .ar_v(av),.ar_d(ad),.ar_cr(ov),.ds(ds),.pw(),.aq(aq),.kvn(kvn),.kvn_cr(cr),.kc(),.af(4'd0),.mf(4'd0),
 .hs(hs),.a_out_valid(ov),.a_out_g(og),.a_out_beat(ob),.a_out_data(od),.a_hub_fault(1'b0),.hc(182'd0),.tk(),.fault(fault),.fault_cause(cause));
 end else begin:g_cluster
 wire[519:0] ret;wire[9:0] kst;
 `ifdef NATIVE_MASTER
 qkd_seq_tp8 dut(
 .clk_core(clk),.clk_xs0(clk),.clk_xs1(clk),.clk_xs2(clk),.clk_xs3(clk),.clk_fan0(clk),.clk_fan1(clk),.clk_fan2(clk),.clk_fan3(clk),
`else
 qkd_seq #(.HEADS(HEADS),.Q_FP32(Q_FP32)) dut(
 .ck(clk),
`endif
 .rst_n(rst_n),.r_x3_d({xv,xt,xd}),.r_x3_cr(xc),.r_sd(56'd0),.r_kvd(kvd),
 .t_ar_d(ret),.t_ar_cr(ov),.t_ds(ds),.t_pw(),
 .aq_WS(aq[0+:540]),.aq_WN(aq[540+:540]),.aq_ES(aq[1080+:540]),.aq_EN(aq[1620+:540]),
 .kvn_WS_d(kvn[0+:1047]),.kvn_WN_d(kvn[1047+:1047]),.kvn_ES_d(kvn[2094+:1047]),.kvn_EN_d(kvn[3141+:1047]),
 .kvn_WS_cr(cr[0]),.kvn_WN_cr(cr[1]),.kvn_ES_cr(cr[2]),.kvn_EN_cr(cr[3]),
 .kc_WS(),.kc_WN(),.kc_ES(),.kc_EN(),.af_WS(1'b0),.af_WN(1'b0),.af_ES(1'b0),.af_EN(1'b0),
 .mf_WS(1'b0),.mf_WN(1'b0),.mf_ES(1'b0),.mf_EN(1'b0),
 .ar({ov,og,ob,od}),.hf(1'b0),.hs(hs),.hc(182'd0),.tk(),.kst(kst));
 assign {av,ad}=ret;assign {fault,cause}=kst;
 end endgenerate
 function automatic [511:0] word(input integer kind,input integer tag);
  integer j;begin for(j=0;j<64;j=j+1)word[8*j+:8]=8'(kind*71+tag*19+j);end
 endfunction
 integer nq=0,nrow=0,nres=0,ncredit=0,errors=0,cycles=0,fan,g,vg,b;
 reg launched=0,release_last=0;
 always @(negedge clk)if(rst_n)begin
  cycles=cycles+1;
  if(xc)ncredit=ncredit+1;
  if(aq[518])begin
   b=aq[512+:6];
   if(b!=nq||aq[511:0]!==word(1,nq))begin errors=errors+1;$display("Q mismatch expected %0d actual %0d",nq,b);end
   for(fan=1;fan<4;fan=fan+1)if(aq[540*fan+:540]!==aq[0+:540])errors=errors+1;
   nq=nq+1;
  end
  if(kvn[1046])begin
   vg=kvn[1044+:2];g=(HEADS==1)?2*nrow:nrow;
   if(vg!=g||kvn[1023:0]!=={word(0,2*g+1),word(0,2*g)}||kvn[1030+:14]!=6||kvn[1024+:6]!=3)begin
    errors=errors+1;$display("KV row mismatch expected vg=%0d got=%0d",g,vg);
   end
   for(fan=1;fan<4;fan=fan+1)if(kvn[1047*fan+:1047]!==kvn[0+:1047])errors=errors+1;
   nrow=nrow+1;
  end
  if(av)begin
   if(ad[511:0]!==word(2,nres)||ad[512+:6]!=nres%32||ad[518]!=(nres/32))errors=errors+1;
   nres=nres+1;
  end
  if(launched&&!release_last&&nres==NR&&ds[43])begin errors=errors+1;$display("EARLY REMOTE COMMIT FENCE");end
 end
 task step;begin @(posedge clk);#1;end endtask
 task send(input integer kind,input integer tag);begin
  @(negedge clk);#1;xv=1;xt={3'(kind==0?2:1),5'd0,3'(tag)};
  if(kind==1)xt={3'b001,2'd0,6'(tag)};
  xd=word(kind,tag);step();@(negedge clk);#1;xv=0;
 end endtask
 integer i,v,h,jg;
 initial begin
  repeat(4)step();rst_n=1;repeat(4)step();
  // Full native counts and sparse one-head tag space, without any dummy g1.
  for(v=0;v<2;v=v+1)for(jg=0;jg<HEADS;jg=jg+1)for(h=0;h<2;h=h+1)send(0,4*v+2*jg+h);
  for(i=0;i<NQ;i=i+1)send(1,i);
  @(negedge clk);#1;kvd={1'b1,1'b1,18'd6,24'd192};launched=1;step();@(negedge clk);#1;kvd=0;
  wait(nq==NQ&&nrow==ROWS);repeat(8)step();
  // Three quadrants acknowledge every real posted row; fourth quadrant withholds.
  for(i=0;i<ROWS;i=i+1)begin @(negedge clk);#1;cr=4'b0111;step();@(negedge clk);#1;cr=0;repeat(2)step();end
  for(i=0;i<NR;i=i+1)begin @(negedge clk);#1;ov=1;og=(HEADS==1)?0:(i/32);ob=i%32;od=word(2,i);step();end
  @(negedge clk);#1;ov=0;repeat(24)step();
  if(ds[43])begin errors=errors+1;$display("FENCE did not wait for remote fourth quadrant");end
  release_last=1;
  for(i=0;i<ROWS;i=i+1)begin @(negedge clk);#1;cr=4'b1000;step();@(negedge clk);#1;cr=0;repeat(2)step();end
  repeat(24)step();
  if(!ds[43]||nq!=NQ||nrow!=ROWS||nres!=NR||ncredit!=NQ+NK||fault)begin
   errors=errors+1;$display("COUNTS q=%0d rows=%0d res=%0d credits=%0d drained=%b fault=%b cause=%h",nq,nrow,nres,ncredit,ds[43],fault,cause);
  end
  if(errors==0)$display("EXACT_PASS HEADS=%0d Q_FP32=%0d CLUSTER=%0d cycles=%0d q=%0d rows=%0d res=%0d credits=%0d",HEADS,Q_FP32,CLUSTER,cycles,nq,nrow,nres,ncredit);
  else $display("EXACT_FAIL errors=%0d",errors);
  $finish;
 end
 initial begin #100000;$display("EXACT_TIMEOUT");$finish;end
endmodule
