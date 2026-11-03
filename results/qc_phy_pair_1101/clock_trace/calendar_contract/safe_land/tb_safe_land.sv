`timescale 1ns/1fs
module tb_safe_land;
reg core=0;
always begin #0.416 core=~core; #0.417 core=~core; end
reg fdi=0;
always #0.5 fdi=~fdi;
reg rst_n=0,slot=0;
integer selected_edge=100,core_index=-1,core_seen=0,link_seen=0;
integer first_link_ps=-1,reset_cut=0;
wire w_slot,r_slot,wr_v,rd_v,w_version,r_version;
wire [5:0] w_addr,r_addr,wr_slot,rd_slot;
ot_coll_lcal_tx #(.KC(4),.KW(2),.SAFE_RING(1),.LAND_CORE(1)) dut (
 .clk(core),.lck(fdi),.rs_c(rst_n),.rs_l(rst_n),.rs_l2(rst_n),.slot(slot),
 .w_slot(w_slot),.w_addr(w_addr),.w_version(w_version),
 .r_slot(r_slot),.r_addr(r_addr),.r_version(r_version),
 .wr_v(wr_v),.wr_slot(wr_slot),.rd_v(rd_v),.rd_slot(rd_slot));
always @(posedge core) begin
 core_index=core_index+1;
 if(rst_n && w_slot)core_seen=core_seen+1;
 slot<=rst_n && core_index==selected_edge;
end
always @(posedge fdi)begin
 #0.000001;
 if(rst_n && r_slot)begin
  link_seen=link_seen+1;
  if(first_link_ps<0)first_link_ps=$rtoi($realtime*1000+0.5);
 end
end
initial begin
 if(!$value$plusargs("SLOT_EDGE=%d",selected_edge))selected_edge=100;
 reset_cut=$test$plusargs("RESET_CUT");
 #10;rst_n=1;
 if(reset_cut)begin
  // Cancel a word already written into the unreset data slots but not read.
  #74.8;rst_n=0;
  #0.001;if(r_slot||wr_v||rd_v)$fatal(1,"SAFE_ASYNC_RESET_FLUSH");
  #4.999;rst_n=1;
  #110.2;
  if(core_seen!=1 || link_seen!=0)$fatal(1,"SAFE_RESET_GHOST_SLOT core=%0d link=%0d",core_seen,link_seen);
  $display("SAFE_LAND_RESET_PASS cancelled pending native ring token; no ghost after reset");
 end else begin
  #190;
  if(core_seen!=1 || link_seen!=1)$fatal(1,"SAFE_LAND_EVENT_LOST edge=%0d core=%0d link=%0d",selected_edge,core_seen,link_seen);
  if(selected_edge==100 && first_link_ps!=86500)$fatal(1,"SAFE_LAND_LATENCY_MUTANT first_ps=%0d expected86500",first_link_ps);
  $display("SAFE_LAND_EVENT_PASS edge=%0d first_link_ps=%0d launch_ps=%0d",selected_edge,first_link_ps,416+833*selected_edge);
 end
 $finish;
end
endmodule
