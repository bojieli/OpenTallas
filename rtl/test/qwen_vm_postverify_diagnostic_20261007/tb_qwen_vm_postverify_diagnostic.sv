`timescale 1ns/1ps
// Diagnostic mechanism test only. Known/unknown/corrupt VERIFY observations are
// injected explicitly; these injections do NOT certify a real SRAM readback.
module tb_qwen_vm_postverify_diagnostic;
parameter STRICT=1,CASE=0;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg[3:0]wr_v=0;
wire[3:0]accepted,acked;
wire fault,rf,cf;
wire[907:0]owners;wire[59:0]addresses;wire[63:0]masks;
localparam [511:0] PAYLOAD={16{32'h4a719ec3}};
ot_qwen_checked_vm_bank_simdiag #(.SIM_FAIL_CLOSED(STRICT)) dut(
 .clk(clk),.rst_n(rst_n),.rd_v(1'b0),.rd_base_word(15'd0),.rd_owner(227'd0),
 .rd_accept_v(),.rd_out_v(),.rd_out_rot(),.rd_out_bank_words(),.rd_out_owner(),.rd_fault(rf),
 .wr_v(wr_v),.wr_word_addr(60'd0),.wr_word_data({1536'd0,PAYLOAD}),.wr_lane_mask(64'hffff),.wr_owner(908'h5),
 .wr_accept_v(accepted),.wr_ack_v(acked),.wr_ack_owner(owners),.wr_ack_word_addr(addresses),.wr_ack_lane_mask(masks),
 .wr_fault(fault),.rw_collision_fault(cf));
integer cycles=0,rawacks=0,checkedacks=0;reg injected=0;
always @(posedge clk)begin
 if(rst_n)begin
  cycles=cycles+1;
  if(|dut.raw_ack)rawacks=rawacks+1;
  if(|acked)checkedacks=checkedacks+1;
 end
end
initial begin
 repeat(3)@(negedge clk);rst_n=1;wr_v=1;
 @(posedge clk);if(accepted!==1)$fatal(1,"write not accepted");
 @(negedge clk);wr_v=0;
 if(CASE==3)begin
  wait(|dut.raw_ack);force dut.raw_ack_owner[226:0]=227'bx;injected=1;
 end
 if(CASE!=3 || !STRICT)begin
  wait(dut.state==11); // Actual VERIFY after actual postcommit SRAM read.
  if(CASE==1)force dut.decoded[511:0]=512'bx;
  else if(CASE==2)force dut.decoded[511:0]=(PAYLOAD ^ 512'b1);
  else force dut.decoded[511:0]=PAYLOAD;
  injected=1;
 end
 // Existing model checked response is28 edges; allow a full additional28
 // edge service interval to observe absence of publication after fault.
 repeat(56)@(posedge clk);
 #1;
 if(!injected || rawacks!=1)$fatal(1,"required real rawACK/injection absent");
 if(CASE==0 || (!STRICT && (CASE==1 || CASE==3)))begin
  if(fault || checkedacks!=1 || owners[226:0]!==227'd5 || addresses[14:0]!==0 || masks[15:0]!==16'hffff)$fatal(1,"expected known or legacy-X diagnostic outcome missing");
  $display("PASS observed_ACK strict=%0d case=%0d raw=%0d checked=%0d diagnostic_only",STRICT,CASE,rawacks,checkedacks);
 end else begin
  if(!fault || checkedacks!=0 || acked!=0)$fatal(1,"diagnostic did not suppress checked ACK");
  $display("PASS fail_closed strict=%0d case=%0d raw=%0d checked=%0d diagnostic_only",STRICT,CASE,rawacks,checkedacks);
 end
 $finish;
end
// Protocol deadlock check, derived from one28-edge write plus56 observation
// edges, three reset edges and low-phase issue/injection alignment allowance.
initial begin repeat(100)@(posedge clk);$fatal(1,"one-command diagnostic failed to terminate");end
endmodule
