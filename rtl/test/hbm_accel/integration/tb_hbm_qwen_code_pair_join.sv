`timescale 1ps/1fs
module tb_hbm_qwen_code_pair_join;
 import ot_hbm_r14_pkg::*;
 reg sc=0,cc=0,por=0;always #512 sc=~sc;always #416.666 cc=~cc;
 reg sv=0,published=0,rv=0;owned_t o;identity_t expected;
 reg[23:0] addr=0,base=0;reg[1:0] kind=2;
 wire sr,ready,fault,empty;wire[1:0] rsp;wire[511:0] data;wire[2:0] bank;
 reg[255:0] payload[0:1023];string image;integer w,p;integer edges=0;
 always @(posedge cc)edges<=edges+1;
 ot_hbm_qwen_code_pair_join #(.ENABLE(1),.NSEG(1)) dut(
 .service_clk(sc),.core_clk(cc),.por_n(por),.service_v(sv),.service_r(sr),.service_owned(o),
 .installed(1'b1),.span_stack(2'd3),.first_sector(34'h20000000),.span_rows(14'd512),.first_row(13'd100),
 .operation(64'd77),.phase(32'd9),.rank(7'd0),.hardware_owner_valid(1'b1),.expected_identity(expected),
 .seg_base(base),.seg_len(24'd512),.seg_sidx(32'd0),.seg_kind(kind),.installed_segment(3'd0),
 .installed_base(base),.installed_length(24'd512),.installed_sidx(32'd0),.installed_kind(kind),.published(published),
 .read_v(rv),.virtual_address(addr),.read_ready(ready),.read_response_valid(rsp),.read_data(data),.read_bank(bank),
 .consumer_enable(1'b1),.response_ready(2'b11),.rom_rd(),.tile_response_valid(),.fault(fault),.crossing_empty(empty));
 task cedge;begin @(posedge cc);#1;end endtask
 task transfer(input integer n);
 begin
 @(negedge sc);o='0;o.id.stack=3;o.id.sector=34'h20000000+n;
 o.id.producer=64'h12345678;o.id.transport=9;o.id.caller=16'h8123;
 o.id.client=16;o.id.irs_serial=n+1;o.physical_tag=12'(n);o.beat=5'(n%16);
 o.data=payload[n];expected=o.id;sv=1;
 @(posedge sc);while(!sr)begin @(posedge sc);if(fault)$fatal(1,"delivery fault n=%0d",n);end
 @(negedge sc);sv=0;@(posedge sc);#1;
 end endtask
 task read_word(input integer n);
 begin
 @(negedge cc);addr=base+n;rv=1;#1;if(!ready)$fatal(1,"unready published word");
 cedge();if(rsp!=0)$fatal(1,"original one-edge timing incorrectly reused");
 @(negedge cc);rv=0;cedge();
 if(rsp!=3||data!={payload[2*n+1],payload[2*n]})$fatal(1,"source byte mismatch word%0d",n);
 cedge();if(rsp!=0)$fatal(1,"response valid repeated");
 end endtask
 initial begin
 if(!$value$plusargs("payload=%s",image))$fatal(1,"actual source payload required");
 $readmemh(image,payload);o='0;expected='0;repeat(3)cedge();por=1;
 // No physical SRAM preload: all 1024 sectors travel through the real CDC.
 for(w=0;w<1024;w=w+1)transfer(w);
 while(!empty)cedge();
 @(negedge cc);rv=1;#1;if(ready)$fatal(1,"private visibility is not global publication");
 cedge();@(negedge cc);rv=0;published=1;cedge();
 for(w=0;w<512;w=w+1)read_word(w);
 // Same installed compact span in virtual bank4: no row13 bank truncation.
 @(negedge cc);base=24'd16384;addr=base;#1;if(bank!=4)$fatal(1,"virtual bank lost");
 read_word(0);read_word(511);
 @(negedge cc);addr=24'd20480;rv=1;#1;if(ready||!fault)$fatal(1,"out of five-bank namespace accepted");
 $display("PASS_CODE_JOIN actual_source_sectors=1024 actual_CDC=1 data_comparisons=514 read_edges=2 unpublished_hold=1 bank4_translation=1 fulltile_arithmetic=0 core_edges=%0d",edges);
 $finish;
 end
endmodule
