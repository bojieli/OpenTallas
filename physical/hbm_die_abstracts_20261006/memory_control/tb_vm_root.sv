`timescale 1ns/1ps
module tb_vm_root;
 reg clk=0;always #0.4166665 clk=~clk;
 reg por_n=0,wr_v=0,wr_bank=0,rd_v=0,rd_bank=0,wr_ACK_ready=0;
 reg [6:0] wr_addr=0,rd_addr=0;
 reg [2062:0] wr_data=0;reg [191:0] wr_owner=0,rd_owner=0;
 reg [3:0] tap_ready=0,tap_ACK_v=0;reg [767:0] tap_ACK_owner=0;
 wire wr_ready,rd_ready,wr_ACK_v,drained,fault,native_release;
 wire [191:0] wr_ACK_owner;wire [3:0] tap_v;wire [8251:0] tap_data;wire [767:0] tap_owner;
 integer cycles=0,comparisons=0,write_edges,read_edges,start_edge;
 always @(posedge clk)cycles<=cycles+1;
 ot_hbm_die_vm_multicast_root #(.ENABLE(1)) dut(.*);
 task tick;begin @(posedge clk);#0.001;end endtask
 task step;begin @(negedge clk);end endtask
 task reset;begin step();por_n=0;wr_v=0;rd_v=0;tap_ACK_v=0;tap_ready=0;tick();step();por_n=1;tick();end endtask
 task write_row(input bit b,input [6:0] a,input [191:0] owner,input [2062:0] data);
 begin
  step();wr_bank=b;wr_addr=a;wr_owner=owner;wr_data=data;wr_v=1;
  if(!wr_ready)begin #0.001;if(!wr_ready)$fatal(1,"write not ready");end
  tick();start_edge=cycles;step();wr_v=0;
  while(!wr_ACK_v&&!fault)tick();if(fault)$fatal(1,"write fault");
  write_edges=cycles-start_edge;
  repeat(3)begin tick();if(!wr_ACK_v||wr_ACK_owner!==owner||drained)$fatal(1,"write ACK not held");end
  step();wr_ACK_ready=1;tick();step();wr_ACK_ready=0;
  if(!drained)$fatal(1,"write not drained");
 end endtask
 task read_row(input bit b,input [6:0] a,input [191:0] owner,input [2062:0] data);
 begin
  step();rd_bank=b;rd_addr=a;rd_owner=owner;rd_v=1;#0.001;
  if(!rd_ready)$fatal(1,"read not ready");tick();start_edge=cycles;step();rd_v=0;
  while(tap_v==0&&!fault)tick();if(fault)$fatal(1,"read fault");read_edges=cycles-start_edge;
  repeat(2)begin tick();for(integer t=0;t<4;t=t+1)begin
   if(!tap_v[t]||tap_data[t*2063+:2063]!==data||tap_owner[t*192+:192]!==owner)$fatal(1,"held output mismatch");comparisons=comparisons+1;
  end end
  for(integer t=0;t<4;t=t+1)begin
   step();tap_ready=4'b1<<t;tick();step();tap_ready=0;
   if(tap_v[t])$fatal(1,"duplicate send");
   tick();step();tap_ACK_owner[t*192+:192]=owner;tap_ACK_v=4'b1<<t;tick();step();tap_ACK_v=0;
   if(t<3&&(native_release||drained))$fatal(1,"released before all ACKs");
  end
  if(!native_release)$fatal(1,"missing native release");tick();if(!drained||fault)$fatal(1,"bad final drain");
 end endtask
 initial begin
  reg [2062:0] d;reg [191:0] own;
  reset();
  for(integer b=0;b<2;b=b+1)for(integer edge_row=0;edge_row<2;edge_row=edge_row+1)begin
   for(integer k=0;k<2063;k=k+1)d[k]=((k*13+b*7+edge_row*3)%19)<9;
   own=192'h123456789abcdef0123456789abcdef0 + b*2 + edge_row;
   write_row(1'(b),edge_row?127:0,own,d);read_row(1'(b),edge_row?127:0,own,d);
  end
  $display("EXACT seed=1 fullshape banks=2 depth=128 macros=22 rows=0,127 comparisons=%0d write_ACK_edges=%0d read_publication_edges=%0d",comparisons,write_edges,read_edges);
  // Real wrong-owner reverse ACK must hold the source closed.
  step();rd_bank=1;rd_addr=127;rd_owner=own;rd_v=1;tick();step();rd_v=0;
  while(tap_v==0&&!fault)tick();step();tap_ready=1;tick();step();tap_ready=0;
  tap_ACK_owner[0+:192]=own^192'b1;tap_ACK_v=1;tick();step();tap_ACK_v=0;
  if(!fault||native_release||drained)$fatal(1,"wrong-owner ACK did not quarantine");
  $display("NEGATIVE actual reverse ACK wrong-owner quarantined no release");
  // Corrupt two actual SRAM bits; do not mutate a golden/expected value.
  reset();write_row(0,127,own,d);
  step();dut.on.banks[0].macros[0].u_sram.arr[127][0]=~dut.on.banks[0].macros[0].u_sram.arr[127][0];
  dut.on.banks[0].macros[0].u_sram.arr[127][1]=~dut.on.banks[0].macros[0].u_sram.arr[127][1];
  rd_bank=0;rd_addr=127;rd_owner=own;rd_v=1;tick();step();rd_v=0;
  repeat(6)tick();if(!fault||(|tap_v)||native_release)$fatal(1,"actual SRAM UE published");
  $display("NEGATIVE actual SRAM double-bit error refuses publication");
  $display("PASS VM ROOT COMPONENT (whole VM parent and physical clock OPEN)");$finish;
 end
 initial begin #1000;$fatal(1,"bench deadlock");end
endmodule
