`timescale 1ns/1ps
module tb_hbm_qwen_code_leaf_map;
 import ot_hbm_r14_pkg::*;
 reg clk=0,por=0;always #5 clk=~clk;
 owned_t o;identity_t expected;
 reg ov=0,hv=0,visible=0;wire ready,v,fault;wire[592:0] packet;
 reg[336:0] key=0;
 ot_hbm_qwen_code_leaf_map #(.ENABLE(1)) dut(
 .clk(clk),.por_n(por),.owned_v(ov),.owned_r(ready),.owned(o),.owned_we(1'b0),.owned_credit(1'b0),
 .installed_span_valid(1'b1),.span_stack(2'd3),.span_first_sector(34'h20000000),.span_rows(14'd512),.span_first_row(13'd100),.span_first_column(12'd0),
 .operation(64'd77),.phase(32'd9),.global_rank(7'd3),.hardware_owner_valid(hv),.expected_identity(expected),
 .leaf_v(v),.leaf_packet(packet),.private_visible(visible),.private_visible_key(key),.fault(fault));
 task step;begin @(posedge clk);#1;end endtask
 initial begin
 o='0;o.id.stack=3;o.id.sector=34'h20000201;o.id.producer=64'habcdef1234567890;o.id.transport=123;o.id.caller=16'h8123;o.id.client=16;o.id.irs_serial=777;o.physical_tag=12'habc;o.beat=7;o.data=256'h0123456789abcdef;
 expected=o.id;repeat(2)step();por=1;ov=1;repeat(2)step();if(v||ready||fault)$fatal(1,"hold absent actual issuer");
 @(negedge clk);hv=1;#1;
 if(!v||packet[489:477]!=356||packet[476:465]!=1||packet[464:0]!=o)$fatal(1,"normalized sector must NOTaddbeat or truncate data");
 if(ready)$fatal(1,"acceptance not SRAMvisible");
 key={64'd77,32'd9,7'd3,13'd356,12'd1,o.id,o.physical_tag,o.beat};
 visible=1;#1;if(!ready)$fatal(1,"matching privatevisible receipt");step();
 @(negedge clk);visible=0;ov=0;step();if(fault)$fatal(1,"healthy route");
 @(negedge clk);ov=1;key[336]=~key[336];visible=1;#1;if(ready)$fatal(1,"foreign operation accepted");step();if(!fault)$fatal(1,"foreign key did not retainfault");
 $display("PASS_CODE_PAIR_NORMALIZED_BEAT_ROW13_COL12_DATA_PRIVATE_VISIBLE_FOREIGN_HOLD");$finish;
 end
endmodule
