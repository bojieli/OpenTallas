`timescale 1ns/1ps
module tb_vm_root_ck9;
 reg clk=0;always #0.4166665 clk=~clk;
 reg por_n=0,wr_v=0,wr_bank=0,rd_v=0,rd_bank=0,wr_ACK_ready=0;
 reg [6:0] wr_addr=0,rd_addr=0;
 reg [2062:0] wr_data=0;reg [191:0] wr_owner=0,rd_owner=0;
 reg [3:0] tap_ready=0,tap_ACK_v=0;reg [767:0] tap_ACK_owner=0;
 wire wr_ready,rd_ready,wr_ACK_v,drained,fault,native_release;
 wire [191:0] wr_ACK_owner;wire [3:0] tap_v;wire [8251:0] tap_data;wire [767:0] tap_owner;
 integer cycles=0,comparisons=0,write_edges,read_edges,start_edge;
 always @(posedge clk)cycles<=cycles+1;
 wire mem_cmd_v,mem_cmd_we,mem_cmd_bank;wire [6:0] mem_cmd_addr;wire [2815:0] mem_wd;
 reg mem_rd_v=0;reg [2815:0] mem_rd;
 reg [2815:0] rows[0:255];
 reg mutate_verify=0;
 function [71:0] encode64(input [63:0] data);
  begin encode64={^{data[0],data[1],data[2],data[4],data[5],data[7],data[10],data[11],data[12],data[14],data[17],data[18],data[21],data[23],data[24],data[26],data[27],data[29],data[32],data[33],data[36],data[38],data[39],data[41],data[44],data[46],data[47],data[50],data[51],data[53],data[56],data[57],data[58],data[60],data[63]},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}}; end
 endfunction

`ifdef VM_CK_BASELINE
 ot_hfd_vm_root_x #(.ENABLE(1),.SEATP(1),.FREG(1)) dut(.*);
`else
 vm_root_ck9 #(.ENABLE(1),.SEATP(1),.FREG(1)) dut(.*);
`endif
 always @(posedge clk)begin
  mem_rd_v<=mem_cmd_v&&!mem_cmd_we;
  if(mem_cmd_v)begin
   if(mem_cmd_we)rows[{mem_cmd_bank,mem_cmd_addr}]<=mem_wd;
   else mem_rd<=rows[{mem_cmd_bank,mem_cmd_addr}]^(mutate_verify?{2744'd0,encode64(64'd1)}:2816'd0);
  end
 end
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
  $display("EXACT seed=1 fullshape banks=2 depth=128 external_memory_abstract=2816bit rows=0,127 comparisons=%0d write_ACK_edges=%0d read_publication_edges=%0d",comparisons,write_edges,read_edges);
  // Real wrong-owner reverse ACK must hold the source closed.
  step();rd_bank=1;rd_addr=127;rd_owner=own;rd_v=1;tick();step();rd_v=0;
  while(tap_v==0&&!fault)tick();step();tap_ready=1;tick();step();tap_ready=0;
  tap_ACK_owner[0+:192]=own^192'b1;tap_ACK_v=1;tick();step();tap_ACK_v=0;
  if(!fault||native_release||drained)$fatal(1,"wrong-owner ACK did not quarantine");
  $display("NEGATIVE actual reverse ACK wrong-owner quarantined no release");
  // Corrupt two external mutable SRAM response bits; do not mutate a golden/expected value.
  reset();write_row(0,127,own,d);
  step();rows[127][0]=~rows[127][0];
  rows[127][1]=~rows[127][1];
  rd_bank=0;rd_addr=127;rd_owner=own;rd_v=1;tick();step();rd_v=0;
  repeat(12)begin
   tick();if((|tap_v)||native_release)$fatal(1,"external mutable SRAM response UE published before quarantine");
  end
  if(!fault)$fatal(1,"external mutable SRAM response UE not quarantined");
  $display("NEGATIVE external mutable SRAM response double-bit error refuses publication");
  // Correct a single returned data bit, then prove read-owner mismatch cannot transiently publish.
  reset();write_row(0,127,own,d);
  step();rows[127][10]=~rows[127][10];read_row(0,127,own,d);
  reset();write_row(0,127,own,d);
  step();rd_bank=0;rd_addr=127;rd_owner=own^192'b1;rd_v=1;tick();step();rd_v=0;
  repeat(12)begin tick();if((|tap_v)||native_release)$fatal(1,"wrong read owner published before quarantine");end
  if(!fault)$fatal(1,"wrong read owner not quarantined");
  // A valid-code changed write readback must never ACK, even for one edge.
  reset();step();mutate_verify=1;wr_bank=0;wr_addr=127;wr_owner=own;wr_data=d;wr_v=1;tick();step();wr_v=0;
  repeat(12)begin tick();if(wr_ACK_v)$fatal(1,"changed write readback ACKed before quarantine");end
  if(!fault)$fatal(1,"changed write readback not quarantined");
  $display("NEGATIVE valid-code read-owner and write-readback mismatches never transiently publish/ACK");
  $display("VM_ROOT_CK9 COMPONENT PASS (memory physical integration/production price OPEN)");$finish;
 end
 initial begin #1000;$fatal(1,"bench deadlock");end
endmodule
