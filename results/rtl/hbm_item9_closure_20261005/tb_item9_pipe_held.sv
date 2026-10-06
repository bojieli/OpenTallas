`timescale 1ns/1ps
module tb_item9_pipe_held;
 localparam N=32,W=64;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0;reg[N-1:0]s_req_v=0,s_mode=0,s_rsp_rdy=0;
 reg[N*8-1:0]s_count=0;reg[N*W-1:0]s_data;
 wire[N-1:0]s_req_rdy,s_rsp_v;wire[W-1:0]s_rsp_data,m_data;
 wire m_req_v,m_mode,m_rsp_rdy;wire[7:0]m_count;
 reg m_req_rdy=0,m_rsp_v=0;reg[W-1:0]m_rsp_data=0;
 ot_gpu_coll_mux_item9_pipe #(.ENABLE(1),.NSM(N),.NL(2),.ODUP(1),.PIPE(1)) dut(.*);
 task tick;begin @(posedge clk);#0.01;end endtask
 task drive;begin @(negedge clk);end endtask
 reg[W-1:0]expected;integer grants=0,completions=0;
 initial begin
  s_data='x;tick();drive();rst_n=1;
  // Withdrawal before source credit is legal; a stray response owns no credit.
  s_req_v[7]=1;tick();drive();s_req_v=0;m_rsp_v=1;s_rsp_rdy='1;
  tick();if(m_req_v||m_rsp_rdy||s_rsp_v)$fatal(1,"withdrawal/stray response accepted");
  drive();m_rsp_v=0;s_rsp_rdy=0;
  for(integer s=0;s<N;s=s+1)begin
   expected=64'h12340000abcdef00+s;
   drive();s_data='x;s_data[s*W+:W]=expected;s_req_v=32'b1<<s;
   s_mode[s]=s%2;s_count[s*8+:8]=s+1;
   tick();if(s_req_rdy!==(32'b1<<s))$fatal(1,"missing source credit");
   tick();grants=grants+1;
   // Producer is free to overwrite immediately after the genuine credit edge.
   drive();s_data='x;s_req_v=0;
   tick();if(!m_req_v||m_data!==expected||m_count!==8'(s+1)||m_mode!==1'(s%2))$fatal(1,"stored descriptor/payload mismatch");
   // Occupied credit must prevent accepting another caller while blocked.
   drive();s_req_v=32'b1<<((s+1)%N);
   repeat(4)begin
    tick();if(!m_req_v||m_data!==expected||s_req_rdy!==0)$fatal(1,"held transaction changed or duplicate credit");
   end
   drive();s_req_v=0;m_req_rdy=1;tick();drive();m_req_rdy=0;
   m_rsp_v=1;m_rsp_data=expected^64'hff;s_rsp_rdy=0;
   repeat(3)begin tick();if(s_rsp_v!==(32'b1<<s)||m_rsp_rdy||s_rsp_data!==(expected^64'hff))$fatal(1,"response owner/hold mismatch");end
   drive();s_rsp_rdy=32'b1<<s;
   #0.01;if(!m_rsp_rdy)$fatal(1,"response credit missing");
   tick();completions=completions+1;drive();m_rsp_v=0;s_rsp_rdy=0;
  end
  // Reset with accepted source payload and blocked downstream aborts validity.
  drive();s_req_v=1;s_data='0;tick();tick();drive();s_req_v=0;tick();
  if(!m_req_v)$fatal(1,"reset test did not reach held state");
  drive();rst_n=0;#0.01;
  if(m_req_v||m_rsp_rdy||s_rsp_v||s_req_rdy)$fatal(1,"reset retained stale credit");
  tick();drive();rst_n=1;m_rsp_v=1;s_rsp_rdy='1;tick();
  if(m_rsp_rdy||s_rsp_v)$fatal(1,"stale response after reset");
  $display("PASS PIPE held32 grants=%0d completions=%0d maskedX/withdraw/stray/blocked/reset",grants,completions);$finish;
 end
 initial begin repeat(2048)tick();$fatal(1,"finite mechanism deadlock");end
endmodule
