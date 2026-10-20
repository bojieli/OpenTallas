`timescale 1ns/1ps
module tb_parent_earliest;
reg clk=0,rst_n=1;always #1 clk=~clk;
reg cfg_v=0,desc_v=0,launch_v=0;reg[7:0]cfg_target=164;reg[11:0]cfg_addr=0,desc_base=0;
reg[12:0]desc_limit=1;reg[15:0]desc_loops=1;reg[255:0]cfg_data=0;
wire configured,fault,active,done;
ot_hbm_hc_root_static #(.SAFE(1),.TAILC(1),.PTFS(1),.XRD(11),.XRU(11),.XRDQ(32'h060b060b),.XRUQ(32'h050a070b),.QDRLY(2)) dut (
 .clk(clk),.rst_n(rst_n),.tgt(8'd164),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.configured(configured),
 .qps_v(4'd0),.qps(128'd0),.qps_f(4'd0),.q_fault(4'd0),.gathered_mix_v(4'd0),.gathered_mix_row(20'd0),
 .gathered_mix_pos(12'd0),.gathered_mix_data(128'd0),.program_active(active),.program_done(done),.fault(fault));
integer req_phase=0;
integer edge_no=0,epoch=0,mut=0,child_edge=-1,ready_edge=-1,req_edge=-1,start_edge=-1,done_edge=-1;
reg tracking=0;
always @(posedge clk)begin
 if(tracking)edge_no=edge_no+1;
 #0.01;
 if(tracking)begin
 if(child_edge<0 && dut.g_tail[0].g_c.u_t.rst_pin===1'b1) child_edge=edge_no;
 if(ready_edge<0 && configured===1'b1) ready_edge=edge_no;
 if(start_edge<0 && dut.start_v===1'b1) start_edge=edge_no;
 if(done===1'b1)done_edge=edge_no;
 end
end
initial begin
if(!$value$plusargs("MUT=%d",mut))mut=0;
if(!$value$plusargs("REQUEST_PHASE=%d",req_phase))req_phase=0;
for(epoch=0;epoch<3;epoch=epoch+1)begin
 tracking=0;cfg_v=0;desc_v=0;launch_v=0;
 #0.17;rst_n=0;repeat(3)@(negedge clk);#0.19;rst_n=1;
 edge_no=0;child_edge=-1;ready_edge=-1;req_edge=-1;start_edge=-1;done_edge=-1;tracking=1;
 // First external cfg capture allowed by the exact target-local reset.
 wait(dut.g_ptf.u_ptgt.reset_live2===1'b1);@(negedge clk);
 cfg_data=0;cfg_data[255:240]=16'hc7a1;cfg_data[233:224]=0;cfg_data[19:0]=8;cfg_v=1;
 @(negedge clk);cfg_v=0;desc_v=1;
 @(negedge clk);desc_v=0;
 if(mut!=0)begin
   // Earliest descriptor capture: launch at edge8 precedes scan validation.
   launch_v=1;req_edge=edge_no+1;
   @(negedge clk);launch_v=0;
   repeat(10)@(negedge clk);
   if(fault!==1'b1)$fatal(1,"EARLY_MUTANT_ESCAPED");
   $display("PARENT_EARLIEST_TIGHT MUTANT_FAIL epoch=%0d child_ready=%0d request=%0d fault=%b",epoch,child_edge,req_edge,fault);
 end else begin
   if(req_phase==0) begin wait(configured===1'b1);@(negedge clk);end
   else begin
     if(req_phase<9)$fatal(1,"BAD_POSITIVE_PHASE");
     repeat(req_phase-8)@(negedge clk);
   end
   launch_v=1;req_edge=edge_no+1;
   @(negedge clk);launch_v=0;
   wait(done===1'b1);repeat(2)@(negedge clk);
   if(fault!==1'b0 || start_edge<0 || child_edge!=7 || req_edge<=child_edge || start_edge!=req_edge+1)
     $fatal(1,"PARENT_PROTOCOL_FAIL fault=%b child=%0d ready=%0d request=%0d start=%0d",fault,child_edge,ready_edge,req_edge,start_edge);
   $display("PARENT_EARLIEST_TIGHT PASS epoch=%0d child_ready=%0d configured=%0d request=%0d start=%0d done=%0d boot_extra=1 active_calendar_shift=0",epoch,child_edge,ready_edge,req_edge,start_edge,done_edge);
 end
end
if(mut==0)$display("PARENT_EARLIEST_TIGHT ALL_PASS epochs=3");else $display("PARENT_EARLIEST_TIGHT MUTANT_DETECTED epochs=3");$finish;
end
initial begin #2000;$fatal(1,"PARENT_PROTOCOL_WATCHDOG");end
endmodule
