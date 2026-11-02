`timescale 1ns/1fs
// Exact selected native calendar, not a behavioural replacement or global PW.
module tb_calendar_slot;
reg core=0;
always begin #0.416 core=~core; #0.417 core=~core; end
reg fdi=0;
always #0.5 fdi=~fdi;
reg rst_n=0,slot=0;
integer selected_edge=100,core_index=-1,core_seen=0,link_seen=0;
wire w_slot,r_slot,wr_v,rd_v,w_version,r_version;
wire [5:0] w_addr,r_addr,wr_slot,rd_slot;
ot_coll_lcal_tx #(.KC(4),.KW(2),.SAFE_RING(0),.LAND_CORE(0)) dut (
 .clk(core),.lck(fdi),.rs_c(rst_n),.rs_l(rst_n),.rs_l2(rst_n),.slot(slot),
 .w_slot(w_slot),.w_addr(w_addr),.w_version(w_version),
 .r_slot(r_slot),.r_addr(r_addr),.r_version(r_version),
 .wr_v(wr_v),.wr_slot(wr_slot),.rd_v(rd_v),.rd_slot(rd_slot));
always @(posedge core) begin
 core_index=core_index+1;
 if(rst_n && w_slot)core_seen=core_seen+1;
 slot<=rst_n && core_index==selected_edge;
end
always @(negedge fdi)if(rst_n && r_slot)link_seen=link_seen+1;
initial begin
 if(!$value$plusargs("SLOT_EDGE=%d",selected_edge))selected_edge=100;
 #10;rst_n=1;
 #190;
 if(core_seen!=1)$fatal(1,"SOURCE_SLOT_NOT_PRESENT core=%0d",core_seen);
 if(link_seen!=1)$fatal(1,"FDI_SLOT_SAMPLE_MISSED selected=%0d core_seen=%0d link_seen=%0d",selected_edge,core_seen,link_seen);
 $display("FDI_SLOT_PHASE_PASS edge=%0d core833ps FDI1000ps nativeKC4 core_seen=%0d link_seen=%0d",selected_edge,core_seen,link_seen);
 $finish;
end
endmodule
