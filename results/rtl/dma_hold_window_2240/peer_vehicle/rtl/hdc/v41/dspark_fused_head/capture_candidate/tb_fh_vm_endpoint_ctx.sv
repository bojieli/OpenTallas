`timescale 1ns/1ps
module tb_fh_vm_endpoint_ctx;
 import ot_dsrom_vm_pkg::*;
 reg fast_clk=0,cold_n=0,request_accept=0,request_warm=0,checked_reply_capture=0,published_reply_v=0;
 reg [31:0] native_ordinal=32'h12345678;
 reg [46:0] request_owner=47'h1234ab78;reg [7:0] request_id=8'h95;
 reg [3:0] head_we=0;reg [95:0] head_addr=0;reg [63:0] head_mask=0;reg [2047:0] head_data=0;
 reply_t checked_reply;wire bounds_fault,endpoint_fault,head_ack_v;
 wire [7:0] head_ack_id;wire [23:0] head_ack_word;wire [15:0] head_ack_mask;
 request_t captured_request,captured_request_check;
 reply_t captured_reply,captured_reply_check;
 integer checks=0;
 ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1)) dut(.*);
 always #5 fast_clk=~fast_clk;
 task reset_owner;
  begin @(negedge fast_clk);cold_n=0;request_accept=0;checked_reply_capture=0;published_reply_v=0;
   head_we=0;@(negedge fast_clk);cold_n=1;end
 endtask
 task capture(input bit warm);
  begin
   @(negedge fast_clk);head_we=4'b0001;head_addr={72'bx,24'h345};head_mask={48'bx,16'h0004};
   head_data={1984'bx,32'hf00d4321,64'bx};request_warm=warm;request_accept=1;
   @(posedge fast_clk);#1;
   if(endpoint_fault||captured_request.wd[512+64+:32]!==32'hf00d4321||
       captured_request.wa!==(75'(15'h345)<<15)||captured_request.wm!==(80'(16'h4)<<16)||
       captured_request.owner!==request_owner||captured_request.ordinal!==native_ordinal||captured_request.we!==5'b00010||captured_request.re!==0||
       captured_request!==~captured_request_check)$fatal(1,"native capture/masked X/port mapping");
   checks++;
   @(negedge fast_clk);request_accept=0;head_we=0;
  end
 endtask
 task publish(input bit bad);
  begin
   @(negedge fast_clk);checked_reply='0;checked_reply.owner=request_owner^(bad?47'd1:47'd0);
   checked_reply.ordinal=native_ordinal;checked_reply.visible=captured_request.we;
   checked_reply.wa=captured_request.wa;checked_reply.wm=captured_request.wm;checked_reply_capture=1;
   @(negedge fast_clk);checked_reply_capture=0;published_reply_v=1;#1;
  end
 endtask
 initial begin
  checked_reply=0;reset_owner;
  capture(0);publish(0);#1;if(head_ack_v||endpoint_fault)$fatal(1,"ordinary write ACKs warm debt");checks++;
  reset_owner;capture(1);publish(0);
  if(!head_ack_v||head_ack_id!==8'h95||head_ack_word!==24'h345||head_ack_mask!==16'h4)
   $fatal(1,"checked native visibility tuple not bound");checks++;
  @(posedge fast_clk);#1;if(head_ack_v)$fatal(1,"held publication repeated ACK");
  repeat(7)begin @(posedge fast_clk);#1;if(head_ack_v||endpoint_fault)$fatal(1,"held publication loses identity/once state");end
  checks++;
  reset_owner;capture(1);publish(1);#1;if(head_ack_v)$fatal(1,"bad full owner published");
  @(posedge fast_clk);#1;if(!endpoint_fault||head_ack_v)$fatal(1,"bad identity not quarantined");checks++;
  reset_owner;
  @(negedge fast_clk);head_we=1;head_addr[23:0]=24'h8000;request_accept=1;
  @(posedge fast_clk);#1;if(!bounds_fault||!endpoint_fault||captured_request.we)$fatal(1,"native bounds silently truncated");checks++;
  reset_owner;
  $display("PASS head native endpoint G4W16 ports1..4 masked-X/fullowner/ordinal/word/mask/held-once/bounds checks=%0d",checks);$finish;
 end
endmodule
