`timescale 1ns/1ps
module tb_endpoint;
parameter integer IS=1,OS=1;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,go=0,a_src=0,eq_v=0,ea_cr=0;
wire ea_v;wire[23:0] accepted;wire idle;wire[15:0] progress,rows;
wire[63:0] mask_unused;
reg [2:0] retires=0;
wire retiring=retires[2];
reg [23:0] expected_count=0;
reg [56:0] pipeline[0:8];
reg[56:0] sampled;
integer n,i,real_accepts=0,rejected=0,prefetch_waits=0;
ot_qfd_sp_su64_sfu_bv_acc #(.IS(IS),.OS(OS)) dut(.clk(clk),.rst_n(rst_n),.go(go),.a_src(a_src),
 .i_nout(18'd2),.i_nin(18'd128),.i_sfu(3'd0),.tok(18'd123),.eq_v(eq_v),.ea_cr(ea_cr),.eq_data(512'd0),
 .accepted_ops(accepted),.idle(idle),.progress(progress),.progress_rows(rows),.ea_v(ea_v));
initial begin
 // Full production SW64 endpoint control, actual embedding prefetch and
 // vstream acceptance FSM. Lane arithmetic and retirement datapath isolated;
 // retired events supplied at fixed3-edge latency to exercise real occupancy.
 force dut.u_su.l_retire={63'd0,retiring};
 force dut.u_su.l_last=64'hffffffffffffffff;
 force dut.u_su.vm_we=64'd0;force dut.u_su.kv_we=64'd0;
 force dut.u_su.rd_v=1'b0;force dut.u_su.reducer_busy=1'b0;
 force dut.u_su.l_fault=64'd0;force dut.u_su.f_red=1'b0;
 for(i=0;i<9;i=i+1)pipeline[i]=0;
 repeat(6)@(negedge clk);rst_n=1;
 for(n=0;n<240;n=n+1)begin
  // Back-to-back controller attempts prove rejected go is not acceptance.
  // Embedding n20 requests a full65-word row and can stall behind credits.
  go=(n==2 || n==3 || n==4 || n==10 || n==20 || n==150 || n==170 || n==171);
  a_src=(n==20 || n==150);
  eq_v=ea_v;ea_cr=ea_v;
  @(posedge clk);
  sampled={expected_count,dut.s_idle && !dut.e_pend,dut.s_progress,dut.s_rows};
  for(i=8;i>0;i=i-1)pipeline[i]=pipeline[i-1];pipeline[0]=sampled;
  if(!dut.rs)begin expected_count=0;retires=0;end
  else begin
   if(dut.go_s && dut.s_ready)begin expected_count=expected_count+1;real_accepts=real_accepts+1;end
   if(dut.go_s && !dut.s_ready)rejected=rejected+1;
   if(dut.e_pend && !dut.go_s)prefetch_waits=prefetch_waits+1;
   retires<={retires[1:0],dut.u_su.emit};
  end
  #1;
  if(dut.accepted_count !== expected_count)$fatal(1,"count wrong n=%0d got%0d want%0d",n,dut.accepted_count,expected_count);
  if(OS>0 && {accepted,idle,progress,rows} !== pipeline[OS-1])$fatal(1,"snapshot wrong n=%0d got%h want%h",n,{accepted,idle,progress,rows},pipeline[OS-1]);
  if(OS==0 && accepted !== expected_count)$fatal(1,"zero-stage count wrong");
  @(negedge clk);
 end
 if(real_accepts<4 || rejected<1 || prefetch_waits<20)$fatal(1,"coverage missing accept%0d reject%0d prefetch%0d",real_accepts,rejected,prefetch_waits);
 rst_n=0;#1;
 if(accepted!==24'd0 || dut.accepted_count!==24'd0)$fatal(1,"counter epoch reset failed");
 $display("PASS endpoint SW64 IS%0d OS%0d accept%0d reject%0d prefetchwait%0d",IS,OS,real_accepts,rejected,prefetch_waits);$finish;
end
endmodule
