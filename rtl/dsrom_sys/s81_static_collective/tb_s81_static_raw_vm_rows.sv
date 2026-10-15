`timescale 1ns/1ps
module tb_s81_static_raw_vm_rows;
 parameter MUT=0;parameter REGISTER_VM_WRITES=1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[512:0]forced_crs=0;reg force_response=0;
 wire capture_payload_slot,capture_meta_slot;
 reg send_slot=0,send_last=0;reg[2:0]send_channel=0;
 wire vm_tx_valid,vm_tx_last;wire[2:0]vm_tx_channel;wire[551:0]vm_tx_payload;
 reg rx_slot=0,rx_valid=0,rx_last=0;reg[551:0]rx_payload=0;
 reg[13:0]rx_payload_row=4,rx_meta_row=5;reg[7:0]rx_tag=0;
 wire[1101:0]vm_write_sources;wire fault;
 reg read_control=0,read_meta=0;reg[13:0]read_row=0;reg[14:0]request_q=0;
 reg[13:0]capture_due=0,meta_due=0;
 wire[1:0]bank_valid;wire[1023:0]bank_data;
 reg[9:0]response_valid=0;reg[511:0]response_data[0:9];
 wire[512:0]f_crs=force_response?forced_crs:{response_data[9],response_valid[9]};
 assign capture_payload_slot=capture_due[13]&&!meta_due[13];
 assign capture_meta_slot=capture_due[13]&&meta_due[13];
 wire[1101:0]bridge_writes;
 s81_static_raw_vm_rows #(.MUT(MUT),.REGISTER_VM_WRITES(REGISTER_VM_WRITES)) dut(.*,.vm_write_sources(bridge_writes));
 generate if(REGISTER_VM_WRITES)begin:G_DIRECT
 assign vm_write_sources=bridge_writes;
 end else begin:G_PARENT_PIN
 reg[1101:0]pin_q;
 always @(posedge clk or negedge rst_n)if(!rst_n)pin_q<=0;else pin_q<=bridge_writes;
 assign vm_write_sources=pin_q;
 end endgenerate
 // Minimum mechanism: eight real SRAM128 macros (two banks x four slices).
 // Bank's own2-edge read + ten fixed declared service relay registers makes
 // actual request/return14-edge mapping with request register and consumer.
 // These relays test bridge timing; they do not replace full productionVM.
 genvar b,s;
 generate for(b=0;b<2;b=b+1)begin:B
  for(s=0;s<4;s=s+1)begin:S
   wire[550:0]wr=vm_write_sources[b*551+:551];
   wire rv;
   dsfd_vm_static_bank128 bank(.ck(clk),.rst_n(rst_n),
   .i_rv(request_q[0] && request_q[1]==1'(b)),.i_ra(request_q[10:2]),.i_rt(8'b0),
   .i_wv(wr[0]),.i_wa(wr[10:2]),.i_wd(wr[31+s*128+:128]),
   .i_wm(wr[15+s*4+:4]),.i_wt(wr[550:543]),
   .o_rv(rv),.o_rd(bank_data[b*512+s*128+:128]),.o_rt(),
   .o_commit(),.o_ca(),.o_cm(),.o_ct());
   if(s==0)assign bank_valid[b]=rv;
  end
 end endgenerate
 always @(posedge clk)begin
  if(!rst_n)begin request_q<=0;capture_due<=0;meta_due<=0;response_valid<=0;end
  else begin
   request_q<={read_row,read_control};capture_due<={capture_due[12:0],read_control};meta_due<={meta_due[12:0],read_meta};
   response_valid<={response_valid[8:0],|bank_valid};
   response_data[0]<=bank_valid[1]?bank_data[512+:512]:bank_data[0+:512];
   for(integer i=1;i<10;i=i+1)response_data[i]<=response_data[i-1];
  end
 end
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin
  rst_n=0;rx_slot=0;rx_valid=0;send_slot=0;read_control=0;force_response=0;
  step();rst_n=1;repeat(5)step();
 end endtask
 function automatic[551:0]value(input integer n);
 begin for(integer i=0;i<552;i=i+1)value[i]=((i*11+n*7)%23)<12;end endfunction
 integer n,checks=0;
 reg[551:0]expected;reg expected_last;
 initial begin
 reset();
 for(n=0;n<20;n=n+1)begin
  expected=value(n);expected_last=~expected[551];
  rx_slot=1;rx_valid=1;rx_payload=expected;rx_last=expected_last;rx_tag=8'(n);step();
  if(vm_write_sources[550:543]!==8'(n)||vm_write_sources[30:15]!==16'hffff||vm_write_sources[581:566]!==16'h3)$fatal(1,"real tuple tag/masks");
  if(vm_write_sources[551+31+:512]!=={471'b0,expected_last,expected[551:512]})$fatal(1,"metadata41 padding");
  rx_slot=0;rx_valid=0;repeat(5)step();
  read_row=4;read_meta=0;read_control=1;step();
  read_row=5;read_meta=1;step();read_control=0;read_meta=0;
  repeat(14)step();
  send_channel=3'(n%5);send_last=expected_last;send_slot=1;#1;
  if(!vm_tx_valid||vm_tx_payload!==expected||vm_tx_last!==expected_last||vm_tx_channel!==3'(n%5))$fatal(1,"actual SRAM553bit roundtrip record%0d",n);
  step();send_slot=0;if(fault)$fatal(1,"unexpected bridge fault");
  #1;if(vm_tx_valid)$fatal(1,"slot slid");checks=checks+1;
 end
 // A send without new loads faults and consumes the reserved edge.
 send_slot=1;#1;if(vm_tx_valid)$fatal(1,"stale buffer reused");step();send_slot=0;if(!fault)$fatal(1,"missingload fault");
 reset();force_response=1;forced_crs=513'b1;step();if(!fault)$fatal(1,"unexpected return");
 reset();force_response=1;forced_crs=0;read_control=1;read_meta=0;read_row=4;step();read_control=0;repeat(14)step();if(!fault)$fatal(1,"missing capture response");
 reset();read_control=1;read_meta=0;read_row=4;step();read_control=0;repeat(14)step();
 read_control=1;step();read_control=0;repeat(14)step();if(!fault)$fatal(1,"loaded overwrite");
 reset();rx_slot=1;rx_valid=0;step();if(!fault)$fatal(1,"missing RX");
 reset();rx_slot=1;rx_valid=1;rx_meta_row=4;step();if(!fault)$fatal(1,"write row alias");
 if(checks!=20)$fatal(1,"roundtrip count");
 $display("PASS rawVMrows20 actual SRAM553bit roundtrips,2reads/2writes perrecord,readcontrol+14 capture,exact masks and tags,faults");$finish;
 end
endmodule
