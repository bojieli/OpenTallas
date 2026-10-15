`timescale 1ns/1ps
`default_nettype none
module tb_hbm_svc_static_sm_rows;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,open_v=0,open_bank=0,fill_v=0,fill_bank=0,read_v=0,read_bank=0,retire_v=0,retire_bank=0;
 reg [15:0] open_epoch=0,fill_epoch=0,read_epoch=0,retire_epoch=0;
 reg [6:0] open_count=0;reg [5:0] fill_row=0,read_row=0;reg [2:0] fill_part=0;
 reg [255:0] fill_data=0;reg [9:0] fill_tag=0,read_tag=0;
 wire [1:0] block_ready,bank_owned;wire fault;wire [1098:0] out_packet;
 ot_hbm_svc_static_sm_rows dut(.*);
 integer vectors=0,overlap=0,faults=0,fill_sectors=0;
 function automatic [9:0] tag_for(input integer b,input integer r);begin tag_for=10'h127+b*67+r*3;end endfunction
 function automatic [255:0] data_for(input integer b,input integer r,input integer p);
  integer k;begin for(k=0;k<8;k=k+1)data_for[k*32+:32]=32'hab138956^(b*32'h1248abcd)^(r*32'h10017)^(p*32'h17235469)^(k*32'h1234567);end
 endfunction
 function automatic [1098:0] packet_for(input integer b,input integer r);
  reg [255:0] scale;begin scale=data_for(b,r,4);packet_for={1'b1,tag_for(b,r),scale[63:0],data_for(b,r,3),data_for(b,r,2),data_for(b,r,1),data_for(b,r,0)};end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task reset_dut;begin rst_n=0;open_v=0;fill_v=0;read_v=0;retire_v=0;tick;tick;rst_n=1;tick;if(fault||bank_owned||block_ready||out_packet[1098])$fatal(1,"reset");end endtask
 task open_block(input bit b,input integer n);begin open_v=1;open_bank=b;open_epoch=b?16'h5678:16'h1234;open_count=n;tick;open_v=0;if(fault)$fatal(1,"open");end endtask
 task set_fill(input bit b,input integer r,input integer p);begin
  fill_v=1;fill_bank=b;fill_epoch=b?16'h5678:16'h1234;fill_row=r;fill_part=p;fill_data=data_for(b,r,p);fill_tag=tag_for(b,r);
 end endtask
 task set_read(input bit b,input integer r);begin read_v=1;read_bank=b;read_epoch=b?16'h5678:16'h1234;read_row=r;read_tag=tag_for(b,r);end endtask
 task check_read(input bit b,input integer r);begin
  if(out_packet!==packet_for(b,r))$fatal(1,"row payload/tag mismatch bank=%0d row=%0d scale=%h expected=%h",b,r,out_packet[1087:1024],packet_for(b,r));
  vectors=vectors+1;
 end endtask
 task expect_fault(input integer id);begin
  tick;if(!fault)$fatal(1,"fault missing case=%0d",id);
  fill_v=0;read_v=0;open_v=0;retire_v=0;tick;
  if(!fault||out_packet[1098])$fatal(1,"fault not sticky/fail closed case=%0d",id);faults=faults+1;
 end endtask
 integer r,j,n;
 initial begin
  reset_dut;open_block(0,16);open_block(1,64);
  // Part 2 is deliberately first; all five parts must agree on the row tag.
  for(r=0;r<16;r=r+1)for(j=0;j<5;j=j+1)begin
   set_fill(0,r,(j+2)%5);tick;fill_sectors=fill_sectors+1;
   if(fault||block_ready[0]!==(r==15&&j==4))$fatal(1,"bank0 ready before all five parts");
  end
  fill_v=0;
  // Real cross-bank 1R1W activity: one 1088-bit row every read edge while
  // the other bank consumes exactly five fill cycles per row.
  n=0;for(r=0;r<64;r=r+1)for(j=0;j<5;j=j+1)begin
   set_fill(1,r,(j+2)%5);set_read(0,n%16);tick;check_read(0,n%16);
   if(fault||block_ready[1]!==(r==63&&j==4))$fatal(1,"bank1 fill/read overlap fault");
   n=n+1;overlap=overlap+1;fill_sectors=fill_sectors+1;
  end
  fill_v=0;read_v=0;tick;if(out_packet[1098])$fatal(1,"valid after read pulse stopped");
  for(r=0;r<64;r=r+1)begin set_read(1,r);tick;check_read(1,r);end
  read_v=0;tick;if(out_packet[1098])$fatal(1,"extra row");
  retire_v=1;retire_bank=0;retire_epoch=16'h1234;tick;retire_v=0;
  if(bank_owned[0]||block_ready[0])$fatal(1,"retirement");
  open_block(0,1);if(block_ready[0])$fatal(1,"reopen retained validity");
  for(j=0;j<5;j=j+1)begin set_fill(0,0,j);tick;end
  fill_v=0;set_read(0,0);tick;check_read(0,0);read_v=0;tick;
  reset_dut;open_block(0,16);set_fill(0,0,0);tick;expect_fault(1); // duplicate
  reset_dut;open_block(0,16);set_fill(0,0,2);tick;set_fill(0,0,1);fill_tag=fill_tag^1;expect_fault(2);
  reset_dut;set_fill(1,0,0);expect_fault(3); // bank unowned
  reset_dut;open_block(0,16);set_read(0,0);expect_fault(4);
  reset_dut;open_block(0,16);set_fill(0,0,5);expect_fault(5);
  reset_dut;open_block(0,1);for(j=0;j<5;j=j+1)begin set_fill(0,0,j);tick;end
  fill_v=0;set_read(0,0);read_tag=read_tag^1;expect_fault(6);
  reset_dut;open_block(0,16);set_fill(0,0,0);fill_epoch=16'h9999;expect_fault(7);
  reset_dut;open_block(0,16);open_v=1;open_bank=0;open_epoch=16'h1234;open_count=16;expect_fault(8);
  $display("STATIC_SM_ROWS PASS rows=%0d crossbank_cycles=%0d initial_fill_sectors=%0d faults=%0d",vectors,overlap,fill_sectors,faults);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
