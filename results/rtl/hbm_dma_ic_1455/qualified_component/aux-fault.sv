`timescale 1ns/1ps
module tb_dma_vp4_native_fault;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg[31:0] cycle=0;reg[7:0] rr=0;
wire new_fault;
always @(posedge clk)cycle<=cycle+1;
ot_hgi_dma_back_static_vp4_controller_ic dut(.clk(clk),.rst_n(rst_n),.cycle_in(cycle),.mv_v(1'b0),.mv(227'd0),.issue_at(32'd0),.drain_at(32'd0),.mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.rr_valid_i(rr),.wb_ready(1'b1),.wa(12'd0),.mv_fault(new_fault));
integer checks=0;
initial begin
 repeat(3)@(negedge clk);#1;rst_n=1;
 @(posedge clk);#1;if(dut.reset_ready!==0)$fatal(1,"reset released before two edges");checks++;
 @(posedge clk);#1;if(dut.reset_ready!==1)$fatal(1,"reset did not release at two edges");checks++;
 repeat(3)@(negedge clk);
 for(integer b=0;b<8;b++)begin
  #1;rr=8'd1<<b;
  @(posedge clk);#1;if(new_fault!==0)$fatal(1,"response fault capture edge wrong bank%0d",b);checks++;
  @(negedge clk);#1;rr=0;
  @(posedge clk);#1;if(new_fault!==1)$fatal(1,"response fault not reported +1edge bank%0d",b);checks++;
  @(negedge clk);#1;rst_n=0;
  #1;if(new_fault!==0)$fatal(1,"reset must assert asynchronously");checks++;
  @(negedge clk);#1;rst_n=1;repeat(3)@(negedge clk);
 end
 $display("DMA_NATIVE_FAULT_PASS banks=8 checks=%0d reset_release_edges=2 malformed_response_fault_extra_edges=1 normal_execution_extra_edges=0",checks);$finish;
end
endmodule
