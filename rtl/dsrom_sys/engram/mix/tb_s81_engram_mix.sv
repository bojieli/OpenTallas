`timescale 1ns/1ps
module tb_s81_engram_mix #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;
 reg [63:0] cfg[0:0];reg rst_n=0,go=0,phase=0,in_v=0;reg [1:0] copy=0;
 reg [1023:0] h,key,weight,value;
 wire gate_v,out_v,fault;wire [1:0] gc,oc;wire [31:0] gate,hh,kk,dd;wire [1023:0] y;
 ot_s81_engram_mix #(.MUT(MUT)) dut(clk,rst_n,go,phase,in_v,copy,h,key,weight,value,cfg[0][0+:32],cfg[0][32+:32],gate_v,gc,gate,hh,kk,dd,out_v,oc,y,fault,{31{clk}});
 reg [1023:0] hm[0:639],km[0:639],wm[0:639],vm[0:159],ym[0:639];reg [127:0] gm[0:3];
 string dir;integer c,i,j,got=0,bad=0,cyc=0,start;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(out_v)begin
   if(oc!==copy)$fatal(1,"copy tag");
   for(j=0;j<32;j=j+1)if(y[32*j+:32]!==ym[160*copy+got][32*j+:32])begin bad=bad+1;if(bad<5)$display("BAD row=%0d word=%0d got=%h exp=%h",160*copy+got,j,y[32*j+:32],ym[160*copy+got][32*j+:32]);end
   got<=got+1;
  end
  if(cyc>10000)$fatal(1,"timeout");
 end
 initial begin
  if(!$value$plusargs("dir=%s",dir))$fatal(1,"dir required");
  $readmemh({dir,"/cfg.mem"},cfg);$readmemh({dir,"/h.mem"},hm);$readmemh({dir,"/k.mem"},km);$readmemh({dir,"/w.mem"},wm);$readmemh({dir,"/v.mem"},vm);$readmemh({dir,"/y.mem"},ym);$readmemh({dir,"/g.mem"},gm);
  repeat(5)@(negedge clk);rst_n=1;
  for(c=0;c<4;c=c+1)begin
   @(negedge clk);copy=c;go=1;phase=0;start=cyc;got=0;
   @(negedge clk);go=0;
   for(i=0;i<160;i=i+1)begin in_v=1;h=hm[160*c+i];key=km[160*c+i];weight=wm[160*c+i];@(negedge clk);end
   in_v=0;wait(gate_v);@(negedge clk);
   $display("GATE copy=%0d cyc=%0d gate=%h hh=%h kk=%h dd=%h",c,cyc-start,gate,hh,kk,dd);
   if({gate,dd,kk,hh}!==gm[c])begin bad=bad+1;$display("BAD scalars exp=%h",gm[c]);end
   phase=1;
   for(i=0;i<160;i=i+1)begin in_v=1;h=hm[160*c+i];value=vm[i];@(negedge clk);end
   in_v=0;wait(got==160);@(negedge clk);
   $display("COPY %0d cycles=%0d",c,cyc-start);
  end
  if(bad||fault)$fatal(1,"FAIL bad=%0d fault=%0d",bad,fault);
  $display("PASS Engram 20480 BF16 words and 16 scalars exact cycles=%0d",cyc);$finish;
 end
endmodule
