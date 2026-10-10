`timescale 1ns/1ps
module tb_hbm_loader_kport_address;
 reg[36:0] a=0;reg[35:0] capacity=36'd22500000000;
 wire[1:0] stack;wire[4:0] pc;wire[29:0] s;wire valid;
 ot_hbm_loader_kport_address #(.ENABLE(1)) dut(a,capacity,stack,pc,s,valid);
 integer st,p,b,col,r,i,n=0;reg[14:0] row;reg[2:0] hi;reg[1:0] lo;reg[4:0] hi5;reg[29:0] encoded;
 initial begin
  // Independent inverse of controller fields, as documented by canonicalmap.
  // FullPC/fullbank/allfourstack, rowandcolumn corner samples.
  capacity=36'h800000000;
  for(st=0;st<4;st=st+1)for(p=0;p<32;p=p+1)for(b=0;b<32;b=b+1)
  for(i=0;i<8;i=i+1)begin
   case(i)0:row=0;1:row=1;2:row=31;3:row=32;4:row=255;5:row=8191;6:row=16384;7:row=32767;endcase
   col=(i*5)%32;hi=3'(b>>2)^row[4:2];lo=2'(b)^row[1:0];hi5={row[1:0],hi};
   encoded={row,hi,5'(col),5'(p)^5'(col)^hi5,lo};
   a={2'(st),encoded,5'b0};#1;
   if(!valid||stack!=st||pc!=p||s!=encoded)$fatal(1,"canonicalmapping mismatch");n=n+1;
  end
  capacity=36'd22500000000;
  for(st=0;st<4;st=st+1)begin
   a={2'(st),35'd22499999968};#1;if(!valid)$fatal(1,"lastsector rejected");
   a={2'(st),35'd22500000000};#1;if(valid)$fatal(1,"capacityoverflow accepted");
   a={2'(st),35'd22500000001};#1;if(valid)$fatal(1,"misalignment accepted");
   a={2'(st),35'd4294967296};#1;if(!valid||stack!=st||s!=30'd134217728)$fatal(1,"highaddress truncated");
  end
  capacity=0;a=0;#1;if(valid)$fatal(1,"undefinedcapacity accepted");
  capacity=36'h800000001;#1;if(valid)$fatal(1,"unrepresentablecapacity accepted");
  $display("LOADER_KPORT_ADDRESS PASS canonical_cases=%0d stacks=4 address_bits=37",n);$finish;
 end
endmodule
