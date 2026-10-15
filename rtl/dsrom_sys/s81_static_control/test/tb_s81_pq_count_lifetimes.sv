`timescale 1ns/1ps
module tb_s81_pq_count_lifetimes;
 reg ck=0,rst_n=0;always #5 ck=~ck;
 reg[3:0]live_source=0;reg root=0;reg[1:0]tag=0;
 wire[3:0]live[0:12];wire[15:0]ga[0:11];wire[11:0]q2f;
 assign live[12]=live_source;
 genvar k;
 generate for(k=0;k<12;k=k+1)begin:g_leaf
  if(k%3==1)ot_s81_pq_rwbc2 u_leaf(.clk(ck),.rst_n(rst_n),.r_v({2{root}}),.r_tag({2{tag}}),.r_e(2'd0),.g_flt(1'b0),.live(live[k+1]),.q2f(q2f[k]),.ga(ga[k]),.live_o(live[k]));
  else ot_s81_pq_rwbc15 u_leaf(.clk(ck),.rst_n(rst_n),.r_v({15{root}}),.r_tag({15{tag}}),.r_e(15'd0),.g_flt(1'b0),.live(live[k+1]),.q2f(q2f[k]),.ga(ga[k]),.live_o(live[k]));
 end endgenerate
 integer mode=0,tick=0,i,live_tick=-1,root_tick=-1,ga_first=-1,fault_first=-1,counts=0;reg saw_fault=0;
 integer expected;
 initial begin
  if($value$plusargs("mode=%d",mode))begin end
  repeat(4)@(negedge ck);rst_n=1;repeat(12)@(negedge ck);
  // Source live mask is a declared boundary event. Whole native production
  // still requires the static controller to emit this exact source calendar.
  live_source=1;live_tick=tick;
  repeat(mode==1?0:12)@(negedge ck);
  root=1;root_tick=tick;@(negedge ck);root=0;
  // Clear while the old root is still inside the leaf checks (negative).
  if(mode==2)live_source=0;
  repeat(10)@(negedge ck);live_source=0;
  repeat(14)@(negedge ck);
  if(mode==0&&saw_fault)$fatal(1,"valid fixed live calendar faulted");
  if(mode!=0&&!saw_fault)$fatal(1,"invalid live fill/drain escaped mode%0d",mode);
  if(counts!=128)$fatal(1,"actual count loss %0d expected128",counts);
  $display("PASS actual12leaf live profile mode%0d fill12 root_to_ga%0d root_to_q2f%0d counts%0d",mode,ga_first-root_tick,fault_first<0?-1:fault_first-root_tick,counts);$finish;
 end
 always @(posedge ck)begin tick=tick+1;#1;
  if(rst_n&&live_source!=0&&live_tick>=0&&tick-live_tick<=12)begin
   for(i=0;i<12;i=i+1)begin
    expected=(tick-live_tick>=12-i)?1:0;
    if(live[i]!==expected[3:0])$fatal(1,"live relay edge changed leaf%0d rel%0d got%h expected%0d",i,tick-live_tick,live[i],expected);
   end
  end
  if(|q2f)begin saw_fault=1;if(fault_first<0)fault_first=tick;end
  for(i=0;i<12;i=i+1)if(ga[i]!=0)begin
   if(ga_first<0)ga_first=tick;
   if(ga[i]!=(i%3==1?2:15))$fatal(1,"count leaf%0d data%h",i,ga[i]);counts=counts+(i%3==1?2:15);
  end
 end
 initial begin #2000;$fatal(1,"timeout");end
endmodule
