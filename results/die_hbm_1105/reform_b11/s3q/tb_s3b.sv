`timescale 1ns/1ps
`default_nettype none
// HBM-REFORM-B11 s3_q S2B form lock-step: old ot_hidx_s3_q (git, B7 tie form) vs new (S2B), same pins.
//   ret and qfault cycle exact; selected_v_o / selected_line_o of the new form one edge later (calendar +1).
//   Legal schedules only (the compiler's rules = the hazard terms): passes of op1, op2 ingest lines (ids rising with time),
//   op6 / op4 scans of the ingested range in address order, op7 flush, op3 / op5 histogram ops; op6 -> op2 / op7 spacing
//   >= GAP; op1 may follow op6 / op7 at any distance (no hazard term), so the realigned op1 clears are exercised.
//   Both qfault must stay 0 (the schedule is legal); MUT0 PASS, DMUT 1/6..13 FAIL.
module tb #(parameter integer DMUT=0)();
 reg clk=0,rst_n=0; always #1 clk=~clk;
 reg [13:0] cw=0,ties=0; reg [15:0] thr=0; reg [591:0] in_line=0;
 wire [24:0] ra,rb; wire fa,fb,va,vb; wire [591:0] la,lb;
 old_hidx_s3_q ua(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),.ret(ra),.qfault_o(fa),.selected_v_o(va),.selected_line_o(la));
 ot_hidx_s3_q #(.DMUT(DMUT)) ub(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),.ret(rb),.qfault_o(fb),.selected_v_o(vb),.selected_line_o(lb));
 integer last6=-1000,last7=-1000,last24=-1000;
 integer qfa=0,qfb=0;
 integer cyc=0,err=0,sel=0,tiehi=0,sat=0,ehit=0,qf=0,npass=0,nop6=0,nop1near=0,packs=0; reg [15:0] keys[0:3];
 reg pva; reg [591:0] pla;
 function automatic [15:0] orderkey(input [15:0] x); orderkey=x[15]?~x:(x^16'h8000); endfunction
 always @(negedge clk) if(rst_n && cyc>40) begin
  if(ra!==rb || (`QCMP && fa!==fb) || {pva,pla}!=={vb,lb}) begin err=err+1;
   if(err<6) $display("DIFF cyc %0d ret %h %h f %b %b v(old-1) %b new %b line %0d", cyc,ra,rb,fa,fb,pva,vb,pla!==lb); end
  if(ua.hz!=0||ub.hz!=0||ua.idbad!=0||ub.idbad!=0) if(qf<3) $display("HZ cyc %0d old hz %b id %h new hz %b id %h cw %0d d6 %0d d7 %0d d24 %0d", cyc,ua.hz,ua.idbad,ub.hz,ub.idbad,cw[3:0],cyc-last6,cyc-last7,cyc-last24);
  if(fa||fb) qf=qf+1;
  if(fa) qfa=qfa+1;
  if(fb) qfb=qfb+1;
  if(va) sel=sel+1;
  if(ub.gtie[0].tavail>=32 && ub.s2bv_t[0]) tiehi=tiehi+1;
  if(ub.s2bv_t[0] && ub.gtie[0].ecnt!=0 && ub.gtie[0].ecnt>ub.gtie[0].tavail) sat=sat+1;
  if(ub.s2bv_t[0] && ub.gtie[0].ecnt!=0) ehit=ehit+1;
  if(ub.wreq) packs=packs+1;
 end
 always @(negedge clk) begin pva<=va; pla<=la; end
 // per-cycle data: ids rise with time (source-id order), keys from 4 values so ties and gt both occur
 integer idc=1;
 always @(negedge clk) begin
  idc=idc+1;
  thr=orderkey(keys[$urandom%4]);
  if($urandom%4==0) case($urandom%4) 0: ties=$urandom&14'h3f; 1: ties=$urandom; 2: ties=33+$urandom%12; default: ties=$urandom%18; endcase
  for(int l=0;l<16;l++) begin in_line[l*37+:37]=37'({$urandom,$urandom}); in_line[l*37+1+:16]=keys[$urandom%4];
   in_line[l*37]=($urandom%8!=0); in_line[l*37+17+:20]=20'(idc*16+l); end
 end
 // compiler rule under test: op2 / op7 no earlier than GAP edges after the last op6 (hz[0] / hz[1] window)
 task automatic op(input [3:0] o,input [7:0] a);
  //   op1 no earlier than G1 after op6 (last_id is S1 domain);
  //   op2 also no earlier than GAP after an op7 (its flush write); op3 no earlier than 8 after op2 / op4 (histogram adds)
  while(((o==2||o==7)&&cyc-last6<`GAP)||(o==2&&cyc-last7<`GAP)||(o==3&&cyc-last24<8)||(o==1&&(cyc-last6<`G1||cyc-last7<`G1))) begin cw[3:0]=0; cw[13:6]=$urandom; @(negedge clk); cyc=cyc+1; end
  cw[3:0]=o; cw[5:4]=$urandom%3; cw[13:6]=a; if(o==6) last6=cyc; if(o==7) last7=cyc; if(o==2||o==4) last24=cyc;
  @(negedge clk); cyc=cyc+1; endtask
 task automatic idle(input integer n); repeat(n) op(0,$urandom); endtask
 int base,n,g,pk,npk=0,ib=64,in_=1; bit ing,pscan;
 initial begin
  for(int i=0;i<4;i++) keys[i]=$urandom;
  repeat(12) @(negedge clk); rst_n=1; idle(30);
  while(cyc<`CYC) begin
   npass=npass+1;
   // ingest at >= 64 (pack writes land at 0..wp-1, wp <= 20); a pass without ingest rescans the last ingested range
   ing=($urandom%4!=0)||npass<3; pscan=0;
   // pack rescan: the next pass scans the packed lines 0..wp-1 of the previous pass (makes the pack data observable)
   if(!ing && $urandom%2==0) begin idle(16); pk=ua.wp; if(pk>0) begin pscan=1; n=pk; base=0; npk=npk+1; end end
   if(!ing && !pscan) begin base=ib; n=in_; end
   op(1,0);                                    // pass start: clears tie budget / fill / selected / wp / last_id
   if(ing) begin n=1+$urandom%20; base=64+$urandom%(192-n); idle($urandom%3); for(int i=0;i<n;i++) op(2,8'(base+i)); idle($urandom%4); ib=base; in_=n; end
   if($urandom%5==0) begin                     // histogram pass: op3 clear, op4 scans, op5 reads
    op(3,0); idle($urandom%3); for(int i=0;i<n;i++) begin op(4,8'(base+i)); if($urandom%3==0) idle(1); end
    idle(`GAP); for(int i=0;i<4;i++) op(5,$urandom);
   end else begin
    for(int i=0;i<n;i++) begin op(6,8'(base+i)); nop6=nop6+1; if($urandom%4==0) idle($urandom%3); end
    g=$urandom%3;
    if(g==0) begin idle($urandom%4); op(7,0); idle($urandom%12); end   // flush, then the next op1 at any distance
    else if(g==1) begin idle($urandom%12); nop1near=nop1near+1; end         // op1 right behind the scan (no hazard term)
    else begin idle($urandom%4); end
   end
  end
  idle(40);
  $display("S3Q packscans %0d",npk);
  $display("S3Q cyc %0d err %0d selected %0d passes %0d op6 %0d op1near %0d packs %0d tavail_hi %0d ecnt_nz %0d saturate %0d qfault_cycles %0d",
   cyc,err,sel,npass,nop6,nop1near,packs,tiehi,ehit,sat,qf);
  $display("QFAULT old %0d new %0d",qfa,qfb);
  if(err!=0) $fatal(1,"FAIL");
  if(`QCMP && qf!=0) $fatal(1,"FAIL qfault: schedule not legal");
  $display("PASS"); $finish;
 end
endmodule
`default_nettype wire
