`timescale 1ns/1ps
`default_nettype none
module tb_static_load_decode;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,scheduled_v=0,sector_available=1;
 reg [255:0] sector=0;
 reg [2:0] src_format=0;
 reg [39:0] src_byte_offsets=0;
 reg [23:0] dst_word_lanes=0;
 reg [7:0] element_mask=0;
 reg [14:0] vm_sector_address=0;
 wire [280:0] vm_write;wire op_fault,fault;
 ot_hbm_static_load_decode #(.MUT(MUT)) dut(.*);
 // Actual unchanged native serial mover is the arithmetic lockstep reference.
 ot_hgi_dma_mover_serial gold(.clk(clk),.rst_n(rst_n),.mv_v(1'b0),.mv(227'd0),.fence_v(1'b0),
 .k_req_rdy(1'b1),.k_rsp_v(1'b0),.k_rsp_we(1'b0),.k_rsp_data(256'd0),.k_fault(1'b0),.vmr(274'd0));
 // Static native LOAD additionally supports UE8M0. Preserve its exact rule.
 ot_hbm_dma_convert_part static_gold(.clk(clk),.fmt_i(3'd0),.raw(32'd0),.q());
 reg [31:0] fp8_truth[0:255],i8_truth[0:255],ue8_truth[0:255];
 reg [280:0] expected[0:2];reg expected_bad[0:2];reg sticky=0;
 integer cycles=0,operations=0,compares=0,errors=0,badops=0;
 integer f,k,j,n,which,lim,off,lane,bytei;
 reg [31:0] raw,converted;reg bad;reg[280:0] packet;
 task step;
 begin
  packet=281'd0;packet[278:264]=vm_sector_address;
  bad=!sector_available||element_mask==0||!(src_format==0||src_format==1||src_format==2||src_format==4||src_format==5||src_format==6);
  for(integer a=0;a<8;a=a+1)if(element_mask[a])begin
   off=src_byte_offsets[a*5+:5];lane=dst_word_lanes[a*3+:3];raw=sector>>(off*8);
   if((src_format==0||src_format==5)&&(off%4)!=0)bad=1;
   if(src_format==1&&(off%2)!=0)bad=1;
   for(integer b=0;b<a;b=b+1)if(element_mask[b]&&dst_word_lanes[b*3+:3]==lane)bad=1;
   case(src_format)
    1:converted={raw[15:0],16'd0};
    2:converted=gold.e4m3_f(raw[7:0]);
    4:converted=gold.i8_f(raw[7:0]);
    6:converted=static_gold.decode_word(raw,3'd6);
    default:converted=raw;
   endcase
   packet[8+32*lane+:32]=converted;packet[lane]=1;
  end
  packet[280]=scheduled_v&&!bad;
  expected[2]=expected[1];expected[1]=expected[0];expected[0]=packet;
  expected_bad[2]=expected_bad[1];expected_bad[1]=expected_bad[0];expected_bad[0]=scheduled_v&&bad;
  if(!rst_n)begin
   for(integer a=0;a<3;a=a+1)begin expected[a]=0;expected_bad[a]=0;end
   sticky=0;
  end
  #5;clk=1;#1;
  sticky=sticky||expected_bad[2];
  if(vm_write[280]!==expected[2][280]||op_fault!==expected_bad[2]||fault!==sticky||
    (expected[2][280]&&vm_write!==expected[2]))begin
   errors=errors+1;
   if(errors<5)$display("MISMATCH cycle=%0d fmt=%0d expected=%h got=%h bad %b/%b sticky %b/%b",cycles,src_format,expected[2],vm_write,expected_bad[2],op_fault,sticky,fault);
   if(errors>=8)$fatal(1,"MUTANT_OR_FAILURE caught %0d mismatches",errors);
  end
  if(expected[2][280])compares=compares+8;
  if(expected_bad[2])badops=badops+1;
  if(scheduled_v)operations=operations+1;
  cycles=cycles+1;#4;clk=0;
 end
 endtask
 initial begin
  for(integer a=0;a<3;a=a+1)begin expected[a]=0;expected_bad[a]=0;end
  $readmemh("fp8_truth.mem",fp8_truth);$readmemh("i8_truth.mem",i8_truth);$readmemh("ue8_truth.mem",ue8_truth);
  for(k=0;k<256;k=k+1)begin
   if(gold.e4m3_f(8'(k))!==fp8_truth[k])$fatal(1,"Native FP8 reference differs from independent truth %0d",k);
   if(gold.i8_f(8'(k))!==i8_truth[k])$fatal(1,"Native INT8 reference differs from independent truth %0d",k);
   if(static_gold.decode_word(32'(k),3'd6)!==ue8_truth[k])$fatal(1,"Native UE8M0 reference differs from independent truth %0d",k);
  end
  step();step();rst_n=1;step();
  for(which=0;which<6;which=which+1)begin
   case(which)0:f=2;1:f=4;2:f=6;3:f=1;4:f=0;default:f=5;endcase
   lim=(f==1)?65536:((f==2||f==4||f==6)?256:4096);
   for(n=0;n<lim;n=n+1)begin
    src_format=3'(f);scheduled_v=1;sector_available=1;
    element_mask=(n%7==0)?8'h55:8'hff;vm_sector_address=15'(n);
    for(bytei=0;bytei<32;bytei=bytei+1)sector[bytei*8+:8]=8'(n+bytei);
    if(f==1)for(j=0;j<16;j=j+1)sector[j*16+:16]=16'(n+997*j);
    if(f==0||f==5)for(j=0;j<8;j=j+1)sector[j*32+:32]=$urandom();
    for(j=0;j<8;j=j+1)begin
     src_byte_offsets[j*5+:5]=(f==0||f==5)?5'(4*((j+n)%8)):(f==1)?5'(2*((j+n)%16)):5'((j+n)%32);
     dst_word_lanes[j*3+:3]=3'((j+n)%8);
    end
    step();
   end
  end
  // Existing unsupported formats, alignment, empty operation, duplicate word ownership and late sector all fault.
  for(k=0;k<20;k=k+1)begin
   src_format=(k%2==0)?3'd3:3'd7;scheduled_v=1;step();
  end
  src_format=0;src_byte_offsets=0;dst_word_lanes=0;element_mask=1;sector_available=0;step();
  sector_available=1;src_byte_offsets[4:0]=5'd1;step();
  src_format=1;step();src_byte_offsets=0;element_mask=3;step();element_mask=0;step();
  scheduled_v=0;repeat(4)step();
  rst_n=0;step();rst_n=1;repeat(4)step();
  if(errors!=0)$fatal(1,"FAIL %0d",errors);
  $display("PASS static_load_decode cycles=%0d scheduled_ops=%0d checked_words=%0d rejected_ops=%0d formats=6 latency=3",cycles,operations,compares,badops);
  $finish;
 end
endmodule
`default_nettype wire
