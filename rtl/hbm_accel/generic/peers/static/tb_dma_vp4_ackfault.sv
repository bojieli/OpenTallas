`timescale 1ns/1ps
// The pin-registered posted-ack boundary reports malformed over-ack one edge later.
// This is an explicit fault-interface change; normal fence/data edges remain exact.
module tb_dma_vp4_ackfault;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg[31:0]cycle=0;reg[11:0]wa=0;
wire old_fault,new_fault;
always @(posedge clk)cycle<=cycle+1;
ot_hgi_dma_back_static_cursor ref_i(.clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(1'b0),.mv(227'd0),.issue_at(32'd0),.drain_at(32'd0),.mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.rr(2056'd0),.wb_ready(1'b1),.wa(wa),.mv_fault(old_fault));
ot_hgi_dma_back_static_vp4_banks dut(.clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.cycle(cycle),.mv_v(1'b0),.mv(227'd0),.issue_at(32'd0),.drain_at(32'd0),.mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.rr(2056'd0),.wb_ready(1'b1),.wa(wa),.mv_fault(new_fault));
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 repeat(3)@(negedge clk);wa=1;
 @(posedge clk);#1;
 if(old_fault!==1||new_fault!==0)$fatal(1,"unexpected first ack fault edge old=%b new=%b",old_fault,new_fault);
 @(negedge clk);wa=0;
 @(posedge clk);#1;
 if(old_fault!==1||new_fault!==1)$fatal(1,"registered ack fault missing old=%b new=%b",old_fault,new_fault);
 $display("DMA_VP4_ACK_FAULT PASS checks=4 extra_fault_edges=1");$finish;
end
endmodule
