`timescale 1ns/1ps
// KV-PLAN-FIN 2026-10-17: lockstep bench qkd_pv_fin_s (512-b beat stream) vs the reference final join
// ot_qwen_tp8_pv256_finalize_static_cal, whose 32 blocks are identical ot_qwen_tp8_pv_join16_static_cal slices sharing cal /
// start / epoch (block b: partials [512 b +: 512], reciprocal head b / 8; out_valid = block 0's).  Two actual reference
// slices run every command on blocks KA = c mod 32 and KB = (7 c + 13) mod 32 (iverilog elaborates the 1,024-unit top in
// hours; the slices are the top's only arithmetic), so 32+ commands compare every block and every head.  Per command: random P0 / P1 (|P0 - P1| <= SKEW), R <= max(P0, P1), random FP32 partials (normal range,
// mixed signs, cancellations, zeros) and 4 head reciprocals.  The reference takes each word whole at its slot; the DUT takes
// beat b at slot + b.  Checks: DUT beat b == reference out_data[512 b +: 512] bit for bit, beat b leaves exactly
// (reference out edge + 1 + b) (pin stage), beat index / epoch, no fault on either.  +MUT runs expect a mismatch.
// Negative controls (+NEG=1 beat index off, +NEG=2 epoch off, +NEG=3 a missing beat) expect the DUT fault.
// QXF-FACE 10-18 (TOKEN-XDIE-QWEN F3): +STRETCH=1 cycles the reciprocal age through three regimes per command (c mod 3):
// R <= max(P0, P1), max < R <= max + 8, and the die's STRETCH=1 calendar regime R = max + 9 .. max + 1108 (the KV die's
// R - max(P0, P1) is 832 at T = 256, 106 at T = 8192); the reference joins at max(P0, P1, R), so must the DUT
// (MUT 3 = R left out of the join age must FAIL).
module tb_qkd_pv_fin_s;
 parameter integer MUT=0;
 parameter integer SKEW=2;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg start=0;reg [15:0] epoch=0;reg [47:0] cal=0;
 reg rv=0;reg [127:0] rz=0;reg [15:0] rep=0;
 reg p0v=0,p1v=0;reg [16383:0] P0D=0,P1D=0;reg [15:0] e0=0,e1=0;
 integer KA=0,KB=0;
 wire [1:0] ova,rfa;wire [511:0] oda,odb;
 ot_qwen_tp8_pv_join16_static_cal u_refa(.cal(cal),.clk(ck),.rst_n(rst_n),.start(start),.epoch(epoch),
  .p0_valid(p0v),.p1_valid(p1v),.p0_ready(),.p1_ready(),.p0_epoch(e0),.p1_epoch(e1),.p0_data(P0D[512*KA+:512]),
  .p1_data(P1D[512*KA+:512]),.reciprocal(rz[32*(KA/8)+:32]),.reciprocal_valid(rv),.reciprocal_ready(),.reciprocal_epoch(rep),
  .out_valid(ova[0]),.out_ready(1'b1),.out_epoch(),.out_data(oda),.fault(rfa[0]));
 ot_qwen_tp8_pv_join16_static_cal u_refb(.cal(cal),.clk(ck),.rst_n(rst_n),.start(start),.epoch(epoch),
  .p0_valid(p0v),.p1_valid(p1v),.p0_ready(),.p1_ready(),.p0_epoch(e0),.p1_epoch(e1),.p0_data(P0D[512*KB+:512]),
  .p1_data(P1D[512*KB+:512]),.reciprocal(rz[32*(KB/8)+:32]),.reciprocal_valid(rv),.reciprocal_ready(),.reciprocal_epoch(rep),
  .out_valid(ova[1]),.out_ready(1'b1),.out_epoch(),.out_data(odb),.fault(rfa[1]));
 wire ov=ova[0],rf=|rfa;
 reg s0v=0,s1v=0;reg [4:0] s0b=0,s1b=0;reg [15:0] s0e=0,s1e=0;reg [511:0] s0d=0,s1d=0;
 reg drv=0;reg [127:0] drz=0;reg [15:0] dre=0;
 wire dv,df;wire [4:0] db;wire [15:0] de;wire [511:0] dd;
 qkd_pv_fin_s #(.SKEW(SKEW),.MUT(MUT)) u_dut(.ck(ck),.rst_n(rst_n),.start(start),.epoch(epoch),.cal(cal),
  .p0_valid(s0v),.p0_beat(s0b),.p0_epoch(s0e),.p0_data(s0d),.p1_valid(s1v),.p1_beat(s1b),.p1_epoch(s1e),.p1_data(s1d),
  .rz_valid(drv),.rz_epoch(dre),.rz(drz),.out_valid(dv),.out_beat(db),.out_epoch(de),.out_data(dd),.fault(df));
 integer cyc=0;always @(posedge ck)cyc<=cyc+1;
 integer NEG=0,NCMD=24,seed=1,errs=0,beats=0,cmd,i,a0,a1,ar,last,t,ref_out,nb,STRETCH=0,kend;
 reg [511:0] OA,OB;integer cmpd=0;
 function [31:0] rnd_fp(input integer kind);
  reg [31:0] r;
  begin
   r=$random(seed);
   case(kind%8)
    0:rnd_fp=32'd0;
    1:rnd_fp={r[31],8'd127+{4'd0,r[3:0]}-8'd8,r[22:0]};
    default:rnd_fp={r[31],8'd100+{2'd0,r[29:24]},r[22:0]};
   endcase
  end
 endfunction
 task one(input integer c);
  integer b,l,k,e;
  begin
   a0=1+($random(seed)&31);a1=a0+(($random(seed)&7)%(2*SKEW+1))-SKEW;if(a1<1)a1=1;
   last=(a0>a1)?a0:a1;ar=1+(($random(seed)&255)%last);
   if(STRETCH!=0&&c%3==1)ar=last+1+(($random(seed)&255)%8);
   if(STRETCH!=0&&c%3==2)ar=last+9+(($random(seed)&16'hffff)%1100);
   kend=((ar>last)?ar:last)+80;
   e=$random(seed)&16'hffff;
   for(b=0;b<512;b=b+1)begin
    P0D[32*b+:32]=rnd_fp($random(seed)&255);
    P1D[32*b+:32]=(($random(seed)&7)==0)?{~P0D[32*b+31],P0D[32*b+:31]}:rnd_fp($random(seed)&255);   // exact cancellations
   end
   for(k=0;k<4;k=k+1)rz[32*k+:32]={1'b0,8'd120+{5'd0,k[2:0]},23'($random(seed))};   // finite, normal
   KA=c%32;KB=(7*c+13)%32;
   // start on one edge for both; slot X = sampled at the X-th edge after the start edge
   @(negedge ck);start=1;epoch=e;cal={16'(ar),16'(a1),16'(a0)};
   t=cyc;
   @(negedge ck);start=0;
   ref_out=-1;nb=0;
   for(k=1;k<=kend;k=k+1)begin
    // inputs for edge k (the k-th edge after the start edge)
    p0v=(k==a0);p1v=(k==a1);rv=(k==ar);e0=e;e1=e;rep=e;
    s0v=(k>=a0&&k<a0+32);s0b=5'(k-a0);s0e=e;s0d=P0D[512*((k-a0)&31)+:512];
    s1v=(k>=a1&&k<a1+32);s1b=5'(k-a1);s1e=e;s1d=P1D[512*((k-a1)&31)+:512];
    drv=(k==ar);dre=e;drz=rz;
    if(NEG==1&&c==3&&k==a0+5)s0b=5'd9;
    if(NEG==2&&c==3&&k==a1+7)s1e=e^16'h1;
    if(NEG==3&&c==3&&k==a0+20)s0v=0;
    @(negedge ck);
    if(ov&&ref_out<0)begin ref_out=k;OA=oda;OB=odb;end
    if(dv)begin
     if(ref_out<0||k!=ref_out+1+nb||db!=5'(nb)||de!=e||(nb==KA&&dd!==OA)||(nb==KB&&dd!==OB))begin
      errs=errs+1;if(errs<6)$display("MISMATCH cmd %0d beat %0d at k %0d (ref out %0d) db %0d",c,nb,k,ref_out,db);
     end
     cmpd=cmpd+(nb==KA)+(nb==KB);nb=nb+1;beats=beats+1;
    end
   end
   p0v=0;p1v=0;rv=0;s0v=0;s1v=0;drv=0;
   if(nb!=32&&NEG==0)begin errs=errs+1;if(errs<6)$display("cmd %0d: %0d beats",c,nb);end
   if((rf||df)&&NEG==0)begin errs=errs+1;$display("cmd %0d fault ref %0d dut %0d",c,rf,df);end
  end
 endtask
 initial begin
  if($value$plusargs("SEED=%d",seed));if($value$plusargs("N=%d",NCMD));if($value$plusargs("NEG=%d",NEG));
  if($value$plusargs("STRETCH=%d",STRETCH));
  repeat(3)@(negedge ck);rst_n=1;repeat(2)@(negedge ck);
  for(cmd=0;cmd<NCMD;cmd=cmd+1)begin
   one(cmd);
   if(NEG!=0&&cmd==3)begin
    if(df&&!rf)begin $display("NEG %0d: DUT fault raised (expected) -- PASS",NEG);$finish;end
    $display("NEG %0d: no DUT fault -- FAIL",NEG);$finish;
   end
  end
  if(errs==0&&cmpd==2*NCMD)$display("PASS STRETCH=%0d %0d commands, %0d beats timed, %0d blocks bit-exact vs the reference slices, beat b = ref + 1 + b",STRETCH,NCMD,beats,cmpd);
  else $display("FAIL %0d mismatches (%0d beats, %0d compared)",errs,beats,cmpd);
  $finish;
 end
endmodule
