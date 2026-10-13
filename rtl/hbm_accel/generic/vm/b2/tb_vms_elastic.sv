`timescale 1ns/1ps
module tb_vms_elastic;
 parameter integer S=59,D=8,N=2048;
 integer stall=0,mode=2,mut=0;
 initial begin void'($value$plusargs("STALL=%d",stall));void'($value$plusargs("MODE=%d",mode));void'($value$plusargs("MUT=%d",mut));end
 reg clk=0,rst_n=0;always #1 clk=~clk;
 wire [2223:0] f[0:S];wire [1:0] cr[0:S];
 reg [2223:0] drive=0;reg [1:0] sinkcr=0;
 assign f[0]=drive;assign cr[S]=sinkcr;
 for(genvar i=0;i<S;i=i+1) begin:g
  wire [1:0] localcr;
  integer pulses=0;
  always @(posedge clk) if(rst_n && localcr[0]) pulses<=pulses+1;
  assign cr[i]=(i==S/2 && mut==2)?{localcr[0],localcr[1]}:((i==S/2 && mut==1 && pulses%8==7)?{localcr[1],1'b0}:localcr);
`ifdef RING_REGIONAL_PHY
  initial if(D!=8) $fatal(1,"Regional physical candidate is fixed D8");
  ot_vms_elastic_regional u(.clk(clk),.data_clk({9{clk}}),.rst_n(rst_n),.f_in(f[i]),.f_out(f[i+1]),.cr_in(cr[i+1]),.cr_out(localcr));
  always @(negedge clk) if(rst_n) for(integer v=0;v<2;v=v+1)
   if(u.u.count[v]>D || u.u.credit[v]>D) $fatal(1,"LOCAL_CREDIT stage=%0d vc=%0d",i,v);
`else
  ot_vms_elastic #(.D(D)) u(.clk({10{clk}}),.rst_n(rst_n),.f_in(f[i]),.f_out(f[i+1]),.cr_in(cr[i+1]),.cr_out(localcr));
  always @(negedge clk) if(rst_n) for(integer v=0;v<2;v=v+1)
   if(u.count[v]>D || u.credit[v]>D) $fatal(1,"LOCAL_CREDIT stage=%0d vc=%0d",i,v);
`endif
 end
 integer cyc=0,iss[0:1],rec[0:1],returned[0:1],credits[0:1],pend[0:1],first=-1,last=-1;
 function automatic [2223:0] packet(input integer seq,input integer vc);
  reg [2223:0] p;
  begin
   for(integer w=0;w<69;w=w+1) p[w*32+:32]=32'(seq*71+w*13+vc*65537);
   p[2223:2208]={1'b1,1'(vc),1'b0,4'b0010,2'd0,4'd0,2'(seq),1'b0};packet=p;
  end
 endfunction
 initial begin
  for(integer v=0;v<2;v=v+1) begin iss[v]=0;rec[v]=0;returned[v]=0;credits[v]=D;pend[v]=0;end
  repeat(4) @(negedge clk);rst_n=1;
 end
 always @(posedge clk) if(rst_n) begin
  if(f[S][2223]) begin
   integer v;v=int'(f[S][2222]);
   if(f[S]!==packet(rec[v],v)) $fatal(1,"ORDER vc=%0d seq=%0d",v,rec[v]);
   rec[v]=rec[v]+1;pend[v]=pend[v]+1;
   if(pend[v]>D) $fatal(1,"SINK_OVERRUN");
   if(first<0)first=cyc;last=cyc;
  end
  sinkcr<=0;
  if(!stall || (cyc%101>=31)) begin
   if(pend[1]!=0) begin sinkcr<=2'b10;pend[1]=pend[1]-1;end
   else if(pend[0]!=0) begin sinkcr<=2'b01;pend[0]=pend[0]-1;end
  end
 end
 always @(negedge clk) if(rst_n) begin
  cyc=cyc+1;
  for(integer v=0;v<2;v=v+1) begin
   if(cr[0][v])begin credits[v]=credits[v]+1;returned[v]=returned[v]+1;end
   if(credits[v]<0 || credits[v]>D || returned[v]>iss[v] || credits[v]+iss[v]-returned[v]!=D) $fatal(1,"SOURCE_CREDIT vc=%0d",v);
  end
  drive=0;
  begin
   integer v;v=(mode==2)?cyc%2:mode;
   if(mode==2 && (iss[v]>=N || credits[v]==0))v=1-v;
   if(iss[v]<N && credits[v]>0)begin drive=packet(iss[v],v);iss[v]=iss[v]+1;credits[v]=credits[v]-1;end
  end
  if(rec[0]==((mode==1)?0:N) && rec[1]==((mode==0)?0:N) && returned[0]==rec[0] && returned[1]==rec[1] && pend[0]==0 && pend[1]==0)begin
   if(!stall && last-first+1>1.10*(rec[0]+rec[1])) $fatal(1,"THROUGHPUT");
   $display("PASS elastic S=%0d D=%0d STALL=%0d MODE=%0d count=%0d steady_cycles=%0d rate=%f total=%0d",S,D,stall,mode,rec[0]+rec[1],last-first+1,real'(rec[0]+rec[1])/(last-first+1),cyc);$finish;
  end
  if(cyc>50000)$fatal(1,"TIMEOUT rec=%0d,%0d",rec[0],rec[1]);
 end
endmodule
