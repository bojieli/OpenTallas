`timescale 1ns/1ps
module tb_qwen_tile_local_drain;
 reg core_clk=0,rst_n=0,issue_last=0;
 reg [15:0] issue_context=16'h1111;reg [31:0] issue_version=32'h12345678;
 reg [3:0] drain_ack_toggle=0;wire [3:0] drain_toggle;wire [191:0] drain_tuple;wire overflow_fault;
 ot_qwen_tile_local_drain dut(.*);
 task step;begin #2;core_clk=1;#2;core_clk=0;#2;end endtask
 integer i;
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;
  // The marker registered on issueedge0 is first observed by the helper atedge1.
  issue_last=1;step();issue_last=0;
  for(i=2;i<=48;i=i+1)begin step();if(drain_toggle!==0)$fatal(1,"early drain atstep%0d",i);end
  #200;if(drain_toggle!==0)$fatal(1,"base elapsed time counted");
  step();if(drain_toggle!==1||drain_tuple[47:0]!=={issue_context,issue_version})$fatal(1,"no exactstep49 drain");
  repeat(60)step();if(drain_toggle!==1||overflow_fault)$fatal(1,"event not durable");
  drain_ack_toggle=drain_toggle;issue_context=16'h2222;issue_last=1;step();issue_last=0;
  repeat(48)step();if(drain_toggle!==0||drain_tuple[47:32]!==16'h2222)$fatal(1,"slot not reused afterack");
  $display("PASS registered-marker issue+49 coherentsteps; elapsed-basepause ignored; durableidentity+ACKreuse");$finish;
 end
endmodule
