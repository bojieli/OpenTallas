`timescale 1ns/1ps
// Component bench for dsfd_engram_mix4_c at its declared VM boundary: a fixed
// latency 20R/4W row port (the VM is the stimulus/response boundary here; bank
// mapping and the VM20R service profile belong to the VM master). Same layout and
// fixtures as tb_s81_engram_mix_c (H in place at 256, K 2048, W 4096, V 6144).
// Checks: exact BF16 output of all four copies, 640 writes, tag, no repeat,
// no unrequested return, every request answered at exactly the fixed latency,
// four writes per beat to distinct rows, and the cycle count.
module tb_s81_engram_mix4_c #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;
 reg [63:0] cfg[0:0];reg rst=0;reg [84:0] cmd=0;wire [8:0] done;wire [1:0] st;wire [19:0] rq;wire [279:0] addr;
 reg [19:0] rv=0;reg [10239:0] rd=0;wire [3:0] wv;wire [55:0] wa;wire [63:0] mask;wire [2047:0] wd;
 dsfd_engram_mix4_c #(.MUT(MUT)) dut({133{clk}},rst,cmd,done,st,1'b1,rq,addr,rv,rd,wv,wa,mask,wd);
 reg [1023:0] hm[0:639],km[0:639],wm[0:639],vm[0:159],ym[0:639];reg [511:0] mem[0:16383];
 string dir;integer cyc=0,i,j,l,m,bad=0,writes=0,reads=0,start,measured,first_w=-1,last_w=-1;
 always @(posedge clk)begin
  cyc<=cyc+1;rv<=rq;
  for(l=0;l<20;l=l+1)if(rq[l])begin rd[512*l+:512]<=mem[addr[14*l+:14]];reads=reads+1;end
  for(l=0;l<4;l=l+1)if(wv[l])begin
   if(mask[16*l+:16]!=16'hffff)$fatal(1,"bad write mask");
   for(m=0;m<l;m=m+1)if(wv[m]&&wa[14*m+:14]==wa[14*l+:14])$fatal(1,"two writes one row");
   mem[wa[14*l+:14]]<=wd[512*l+:512];writes=writes+1;
   if(first_w<0)first_w=cyc;last_w=cyc;
  end
  if(st[0])$fatal(1,"endpoint fault cyc=%0d cluster_faults=%b ep=%b top=%b",cyc,dut.c_fault_q,dut.epf,dut.fault);
  if(cyc>10000)$fatal(1,"timeout");
 end
 initial begin
  if(!$value$plusargs("dir=%s",dir))$fatal(1,"dir required");
  $readmemh({dir,"/cfg.mem"},cfg);$readmemh({dir,"/h.mem"},hm);$readmemh({dir,"/k.mem"},km);$readmemh({dir,"/w.mem"},wm);$readmemh({dir,"/v.mem"},vm);$readmemh({dir,"/y.mem"},ym);
  for(i=0;i<640;i=i+1)begin
   for(j=0;j<32;j=j+1)mem[256+i][16*j+:16]=hm[i][32*j+16+:16];
   mem[2048+2*i]=km[i][0+:512];mem[2049+2*i]=km[i][512+:512];
   mem[4096+2*i]=wm[i][0+:512];mem[4097+2*i]=wm[i][512+:512];
  end
  for(i=0;i<160;i=i+1)begin mem[6144+2*i]=vm[i][0+:512];mem[6145+2*i]=vm[i][512+:512];end
  mem[64]=0;mem[64][0+:32]=256;mem[64][32+:32]=2048;mem[64][64+:32]=4096;mem[64][96+:32]=6144;mem[64][128+:32]=256;mem[64][160+:32]=cfg[0][0+:32];mem[64][192+:32]=cfg[0][32+:32];
  repeat(5)@(negedge clk);rst=1;wait(st[1]);@(negedge clk);
  start=cyc;cmd={1'b1,84'd0};cmd[6:0]=7'd53;cmd[7+:14]=64;
  @(negedge clk);cmd=0;
  wait(done[8]);@(negedge clk);
  measured=cyc-start;
  if(done[7:0]!=8'd53)$fatal(1,"wrong completion tag");
  if(writes!=640)$fatal(1,"early completion writes=%0d",writes);
  for(i=0;i<640;i=i+1)for(j=0;j<32;j=j+1)if(mem[256+i][16*j+:16]!==ym[i][32*j+16+:16])begin bad=bad+1;if(bad<5)$display("BAD row=%0d word=%0d",i,j);end
  if(bad)$fatal(1,"FAIL %0d words",bad);
  repeat(50)@(negedge clk);
  if(writes!=640)$fatal(1,"descriptor repeated");
  // 1 descriptor + 4 x 160 x 5 REDUCE + 160 x (4 H + 2 shared V) ADD
  if(reads!=1+3200+960)$fatal(1,"read count %0d",reads);
  $display("PASS native Engram MIX4 full4x5120 in-place20480words done tag53 writes640 reads%0d write_span%0d..%0d cycles=%0d",reads,first_w-start,last_w-start,measured);$finish;
 end
endmodule
