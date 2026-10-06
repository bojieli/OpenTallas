`timescale 1ps/1ps
module tb_dsrom_protected_vm;
 // Common 278ps VCO grid. Functional3:4 edges, NOT a timing/rate qualification.
 reg fast_clk=1,slow_clk=1;always #417 fast_clk=~fast_clk;always #556 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0;
 reg request_v=0;wire request_ready;reg [46:0] request_owner={16'd7,10'd865,21'd31};
 reg [1:0] read_enable=0;reg [29:0] read_addr=0;
 reg [4:0] write_enable=0;reg [74:0] write_addr=0;reg [2559:0] write_data=0;reg [79:0] write_mask=0;
 wire reply_v;wire [46:0] reply_owner;wire [1023:0] read_data;wire [4:0] row_visible;
 wire [74:0] visible_addr;wire [79:0] visible_mask;wire corrected;
 reg consume_v=0;reg [46:0] consume_owner=0;reg allcopies_fenced=0;
 wire port_retired,pending,quarantined,fault,initializing;
 ot_dsrom_protected_vm #(.ENABLE(1)) dut(.*);
 reg [511:0] golden[0:32767];integer mode=0,cycles=0,transactions=0,visible_writes=0,reads=0;
 integer accepted_edge,reply_edge,retire_edge;
 always @(posedge fast_clk)cycles<=cycles+1;
 // No test timeout on a host build. This is a no-backpressure functional
 // progress bound derived from priced65 backendedges and three16edge crossings.
 localparam WAIT_BOUND=2*(2*4+5*11+2)+3*16;
 function automatic [511:0] payload(input integer tag);
  begin for(integer j=0;j<16;j=j+1)payload[j*32+:32]=32'h71358a42^(32'(tag)*32'h79ad)^32'(j);end
 endfunction
 task automatic expect_quarantine;
  begin repeat(5)@(negedge fast_clk);
   if(!pending||!quarantined||!fault||reply_v||row_visible||port_retired)$fatal(1,"negative released owned work MODE%0d",mode);
   $display("PASS PROTECTED_DSVM negative MODE=%0d pending_preserved=1 no_publication=1",mode);$finish;
  end
 endtask
 task automatic start;
  begin
   @(negedge fast_clk);while(!request_ready)@(negedge fast_clk);
   request_v=1;accepted_edge=cycles;
   @(negedge fast_clk);request_v=0;transactions++;
  end
 endtask
 task automatic finish_transaction(input bit expect_ce);
  reg [511:0] expected0,expected1;reg [74:0] clean_wa;reg [79:0] clean_wm;integer waited;
  begin
   expected0=0;expected1=0;if(read_enable[0])expected0=golden[read_addr[14:0]];if(read_enable[1])expected1=golden[read_addr[29:15]];
   clean_wa=0;clean_wm=0;for(integer w=0;w<5;w=w+1)if(write_enable[w])begin clean_wa[w*15+:15]=write_addr[w*15+:15];clean_wm[w*16+:16]=write_mask[w*16+:16];end
   waited=0;
   while(!reply_v&&!fault)begin @(negedge fast_clk);waited++;if(waited>WAIT_BOUND)$fatal(1,"no protected reply within source bound state%0d debt%b",dut.g_live.u_backend.state,pending);end
   if(fault)$fatal(1,"unexpected fault state%0d",dut.g_live.u_backend.state);
   reply_edge=cycles;
   if(!pending||reply_owner!==request_owner||row_visible!==write_enable||visible_addr!==clean_wa||visible_mask!==clean_wm)$fatal(1,"identity/row visibility mismatch");
   if(read_enable[0]&&read_data[511:0]!==expected0)$fatal(1,"readA olddata/golden mismatch");
   if(read_enable[1]&&read_data[1023:512]!==expected1)$fatal(1,"readB olddata/golden mismatch");
   if(expect_ce&&!corrected)$fatal(1,"actual corrected receipt absent");
   if(mode==4)begin consume_owner=request_owner^47'd1;allcopies_fenced=1;consume_v=1;@(negedge fast_clk);consume_v=0;expect_quarantine();end
   for(integer w=0;w<5;w=w+1)if(write_enable[w])begin
    for(integer l=0;l<16;l=l+1)if(write_mask[w*16+l])golden[write_addr[w*15+:15]][l*32+:32]=write_data[w*512+l*32+:32];visible_writes++;
   end
   reads+=integer'(read_enable[0])+integer'(read_enable[1]);
   // Real output is held; row visibility must not imply C8/port retirement.
   repeat(7)begin @(negedge fast_clk);if(!reply_v||!pending||port_retired)$fatal(1,"visible row retired without receipt");end
   consume_owner=request_owner;allcopies_fenced=1;consume_v=1;
   @(negedge fast_clk);consume_v=0;allcopies_fenced=0;
   waited=0;while(!port_retired&&!fault)begin @(negedge fast_clk);waited++;if(waited>WAIT_BOUND)$fatal(1,"matching reverse receipt failed");end
   if(fault||pending)$fatal(1,"matching receipt did not retire");retire_edge=cycles;
   $display("EVENT txn%0d accept_fast%0d reply_fast%0d retired_fast%0d reads%0d writes%0d CE%b",transactions,accepted_edge,reply_edge,retire_edge,read_enable,write_enable,corrected);
  end
 endtask
 initial begin
  void'($value$plusargs("MODE=%d",mode));for(integer i=0;i<32768;i=i+1)golden[i]=0;
  repeat(5)@(negedge fast_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
  wait(!initializing);@(negedge fast_clk);
  if(mode==2)begin
   write_enable=1;write_addr=0;write_data=2560'(payload(1));write_mask=80'hffff;start();
   consume_owner=request_owner;consume_v=1;allcopies_fenced=1;@(negedge fast_clk);consume_v=0;expect_quarantine();
  end
  if(mode==7||mode==8)begin
   write_enable=1;write_addr=0;write_data=2560'(payload(1));write_mask=80'hffff;start();
   if(mode==7)dut.g_live.serial_check=dut.g_live.serial_check^32'd1;
   else dut.g_live.u_request.wp_check=dut.g_live.u_request.wp_check^2'd1;
   expect_quarantine();
  end
  if(mode==5||mode==6)begin
   write_enable=1;write_addr=0;write_data=2560'(payload(1));write_mask=80'hffff;start();
   wait(dut.g_live.u_backend.debt);@(negedge fast_clk);
   if(mode==5)fast_rst_n=0;else slow_rst_n=0;
   repeat(3)@(negedge fast_clk);fast_rst_n=1;slow_rst_n=1;expect_quarantine();
  end
  // Initial real physical write; same source owner reused with captured ordinal.
  write_enable=1;write_addr=0;write_data=2560'(payload(1));write_mask=80'hffff;start();finish_transaction(0);
  @(negedge slow_clk);
  if(mode==1||mode==3)begin
   dut.g_live.u_backend.g_data[0].g_column[0].u_data.arr[0][0]=~dut.g_live.u_backend.g_data[0].g_column[0].u_data.arr[0][0];
   if(mode==3)dut.g_live.u_backend.g_data[0].g_column[0].u_data.arr[0][4]=~dut.g_live.u_backend.g_data[0].g_column[0].u_data.arr[0][4];
  end
  read_enable=1;read_addr=0;write_enable=0;write_mask=0;write_data=0;start();
  if(mode==3)begin wait(fault);expect_quarantine();end
  finish_transaction(mode==1);
  if(mode==1)begin $display("PASS PROTECTED_DSVM actualSRAM CE corrected golden and positive receipt");$finish;end
  // Both reads observe olddata; all five writes to one row use native lastwriter priority and masked lanes.
  read_enable=3;read_addr={15'd0,15'd0};write_enable=31;write_addr=0;
  for(integer w=0;w<5;w=w+1)begin write_data[w*512+:512]=payload(w+11);write_mask[w*16+:16]=16'hffff;end
  write_mask[64+:16]=16'h5555;for(integer l=1;l<16;l=l+2)write_data[4*512+l*32+:32]=32'hx;start();finish_transaction(0);
  read_enable=3;read_addr={15'd0,15'd32767};write_enable=0;write_mask=80'bx;write_addr=75'bx;write_data=2560'bx;start();finish_transaction(0);
  // Actual full-depth last row +check-half/group boundary, not reduced memory.
  read_enable=0;write_enable=1;write_addr=75'(32767);write_data=2560'(payload(33));write_mask=80'hffff;start();finish_transaction(0);
  read_enable=3;read_addr={15'd32767,15'd0};write_enable=0;write_mask=80'bx;write_addr=75'bx;write_data=2560'bx;start();finish_transaction(0);
  if(fault||pending)$fatal(1,"final protection/owner state");
  $display("PASS PROTECTED_DSVM full2MiB 256data+32check 3:4 transactions=%0d reads=%0d visiblewrites=%0d cycles=%0d",transactions,reads,visible_writes,cycles);$finish;
 end
endmodule
