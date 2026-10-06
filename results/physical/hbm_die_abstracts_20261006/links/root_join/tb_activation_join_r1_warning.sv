`timescale 1ns/1ps
module tb_activation_join;
 reg clk_stream=0;always #5 clk_stream=~clk_stream;
 reg por_stream_n=0,warm_req=0,wr_v=0,wr_bank=0,wr_ACK_ready=0,rd_v=0,rd_bank=0;
 reg [6:0] wr_addr=7'd9,rd_addr=7'd9;
 reg [2062:0] wr_data=0;reg [191:0] wr_owner=192'h800112233445566778899aabbccddeeff0123456789abcdef,rd_owner;
 wire wr_ready,wr_ACK_v,rd_ready;wire [191:0] wr_ACK_owner;
 wire [3:0] fclk_o,out_v;reg [3:0] out_r=0,ACK_v=0;reg [767:0] ACK_owner=0;
 wire [8251:0] out_data;wire [767:0] out_owner;
 wire native_release,activation_drained,warm_drained,paused,fault;
 ot_hbm_activation_station_join #(.ENABLE(1),.F_SW(1),.F_SE(1),.F_NW(1),.F_NE(1)) dut(.*);
 integer accepted[0:3];integer releases=0;reg monitor=0;
 always @(posedge clk_stream)if(monitor)begin
  for(integer q=0;q<4;q=q+1)if(out_v[q]&&out_r[q])begin
   if(out_data[q*2063+:2063]!==wr_data||out_owner[q*192+:192]!==wr_owner)$fatal(1,"quarter payload/owner mismatch");
   accepted[q]=accepted[q]+1;
  end
  if(native_release)releases=releases+1;
 end
 task tick;begin @(posedge clk_stream);#1;end endtask
 task edge_low;begin @(negedge clk_stream);end endtask
 task wait_publish;
  integer steps;
  begin steps=0;while(out_v!=15&&!fault&&steps<16)begin tick();steps=steps+1;end
   if(fault||out_v!=15)$fatal(1,"accepted root publication did not reach real children during warm");
  end
 endtask
 reg [31:0] rng=32'h1062026;
 initial begin
  for(integer q=0;q<4;q=q+1)accepted[q]=0;
  for(integer b=0;b<2063;b=b+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);wr_data[b]=rng[0];end
  rd_owner=wr_owner;
  repeat(3)tick();edge_low();por_stream_n=1;repeat(2)tick();monitor=1;
  edge_low();wr_v=1;#1;if(!wr_ready)$fatal(1,"initial write admission");tick();edge_low();wr_v=0;warm_req=1;
  repeat(6)tick();
  if(!wr_ACK_v||wr_ACK_owner!==wr_owner||warm_drained||activation_drained||wr_ready||rd_ready)$fatal(1,"warm erased pending verified-write receipt");
  repeat(4)tick();if(!wr_ACK_v)$fatal(1,"verified-write ACK not held while warm");
  edge_low();wr_ACK_ready=1;tick();edge_low();wr_ACK_ready=0;tick();
  if(!warm_drained||fault)$fatal(1,"write receipt did not drain honestly");
  edge_low();warm_req=0;rd_v=1;#1;if(!rd_ready)$fatal(1,"read admission");tick();edge_low();rd_v=0;warm_req=1;
  wait_publish();
  repeat(4)tick();if(warm_drained||native_release||activation_drained)$fatal(1,"publication masqueraded as terminal");
  // Each quarter accepts once, but root must await every actual child ACK.
  for(integer q=0;q<4;q=q+1)begin
   edge_low();out_r=1<<q;tick();edge_low();out_r=0;tick();
  end
  repeat(3)tick();if(warm_drained||native_release||releases)$fatal(1,"capture acceptance fabricated rootACK");
  // Repair an actual owned child seat while its reverse ACK arrives. This is
  // new root/child composition evidence, not a standalone leaf PASS replay.
  edge_low();dut.quarter[0].u_station.held.inputs[0].u_cut.u_state.code[32]=dut.quarter[0].u_station.held.inputs[0].u_cut.u_state.code[32]^72'b100;
  for(integer q=0;q<4;q=q+1)begin
   edge_low();ACK_v=1<<q;ACK_owner[q*192+:192]=wr_owner;
   tick();edge_low();ACK_v=0;tick();
   if(q<3&&(warm_drained||native_release))$fatal(1,"root released with unmatched child debt");
  end
  repeat(8)tick();
  for(integer q=0;q<4;q=q+1)if(accepted[q]!=1)$fatal(1,"quarter duplicate/loss");
  if(releases!=1||!warm_drained||!activation_drained||fault)$fatal(1,"matching full192 child receipts failed whole activation drain");
  $display("PASS joined actual22macro VMroot+4sharedstation NO1 fixture seed1062026: exact2063/full192, warm admitted work drains, receipt retained through real child CE, one root retirement");
  // Reuse the written SRAM row; new join transaction, then corrupt the actual
  // child reverse owner. Parent must quarantine debt without warm success.
  edge_low();warm_req=0;rd_v=1;tick();edge_low();rd_v=0;warm_req=1;wait_publish();
  edge_low();out_r=1;tick();edge_low();out_r=0;ACK_v=1;ACK_owner[191:0]=wr_owner^192'b1;
  #1;if(!fault||warm_drained||native_release||wr_ready||rd_ready)$fatal(1,"wrong child owner authorized parent terminal/admission");
  tick();edge_low();ACK_v=0;repeat(3)tick();
  if(!fault||activation_drained||warm_drained||releases!=1)$fatal(1,"warm erased child/root debt after wrong owner");
  $display("PASS negative wrong child192owner blocks parent retirement/new admission/warm drain; retained root+child debt");
  $finish;
 end
endmodule
