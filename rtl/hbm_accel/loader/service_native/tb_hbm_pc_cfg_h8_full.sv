`timescale 1ns/1ps
// Actual controller fills all 32 pending identities on a fixed request calendar.
// The declared external DRAM boundary deliberately withholds every response.
module tb;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0; integer cycle=0,checks=0;
  initial begin repeat(5)@(negedge clk);rst_n=1;end
  always @(posedge clk)if(rst_n)cycle<=cycle+1;
  wire k_v=rst_n && cycle>=40 && cycle<2088 && (cycle-40)%64==0;
  wire k_rdy,pc_fault;wire [5:0]owner_fault_split;
  ot_hbm_svc_pc_ctrl_leaf_cfg_h8 dut(.clk(clk),.rst_n(rst_n),.pc_id(5'd9),.refresh_reload(8'd151),
    .k_v(k_v),.k_rdy(k_rdy),.k_we(1'b0),.k_addr(30'd36),.k_len(4'd1),.k_tag(17'(cycle)),.k_wdata(256'd0),.k_wstrb(32'd0),
    .kr_rdy(1'b1),.dram_rvalid(1'b0),.dram_rdata(256'd0),.pc_fault(pc_fault),.owner_fault_split(owner_fault_split));
  reg [20:0]first_identity;
  always @(negedge clk)if(rst_n && cycle>12)begin
    if(k_v && !k_rdy)$fatal(1,"PC_H8_FULL_CALENDAR cycle=%0d",cycle);
    if(pc_fault || owner_fault_split!=0)$fatal(1,"PC_H8_FULL_FAULT cycle=%0d",cycle);
    if(cycle>6000)$fatal(1,"PC_H8_FULL_NOT_REACHED pending=%0d",dut.pending_count);
  end
  initial begin
    wait(dut.pending_count==32);@(negedge clk); first_identity=dut.pending_identity[0];
    repeat(200)begin
      @(negedge clk);checks=checks+1;
      if(dut.pending_count!=32 || dut.pending_identity[0]!==first_identity)
        $fatal(1,"PC_H8_FULL_LIVE_ENTRY_OVERWRITTEN checks=%0d",checks);
    end
    $display("PC_H8_FULL PASS checks=%0d pending=32 requests=32",checks);$finish;
  end
endmodule
