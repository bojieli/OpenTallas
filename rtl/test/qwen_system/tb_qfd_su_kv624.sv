`timescale 1ns/1ps
module tb_qfd_su_kv624;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg [63:0] mask;reg [1535:0]addr;reg [2047:0]data;
 wire [63:0] om;wire [23:0]a0,a1;wire[511:0]od;wire fault;
 ot_qfd_su_kv624 #(.MUT_ADDR(MUT)) dut(.clk(clk),.rst_n(rst_n),.i_mask(mask),.i_addr(addr),.i_data(data),
  .o_mask(om),.o_a0(a0),.o_a1(a1),.o_data(od),.fault(fault));
 function automatic [31:0] from_code(input [7:0] c);
  reg [3:0]e;reg[2:0]m;reg[7:0]fe;reg[22:0]fm;
  begin
   e=c[6:3];m=c[2:0];
   if(e!=0)begin fe={4'd0,e}+8'd120;fm={m,20'd0};end
   else if(m[2])begin fe=120;fm={m[1:0],21'd0};end
   else if(m[1])begin fe=119;fm={m[0],22'd0};end
   else if(m[0])begin fe=118;fm=0;end else begin fe=0;fm=0;end
   from_code={c[7],fe,fm};
  end
 endfunction
 integer v,i,stride,base,checks=0;reg [7:0]code;
 initial begin
  mask=0;addr=0;data=0;repeat(4)@(negedge clk);rst_n=1;
  for(v=0;v<512;v=v+1)begin
   @(negedge clk);stride=v[0]?1:16;base=v[0]?2097152+v*32:v*1024;
   mask=(v%3==0)?64'hffffffffffffffff:(v%3==1)?64'haaaaaaaaaaaaaaaa:64'h8000000180000001;
   for(i=0;i<64;i=i+1)begin
    addr[24*i+:24]=24'(base+(i/32)*65536+(i%32)*stride);
    code=8'(v+i*7);data[32*i+:32]=from_code(code);
   end
   repeat(2)@(negedge clk);
   if(MUT!=0)begin
    if(fault&&om==0)begin $display("NEG_DETECTED KV624 address mutation");$finish;end
    $fatal(1,"mutant survived");
   end
   if(fault||om!=mask||a0!=base||a1!=base+65536)$fatal(1,"descriptor mismatch v%0d",v);
   for(i=0;i<64;i=i+1)if(mask[i])begin
    code=8'(v+i*7);if(od[8*i+:8]!==code)$fatal(1,"codec mismatch");checks=checks+1;
   end
  end
  @(negedge clk);mask=1;data[31:0]=32'h3f800001;repeat(2)@(negedge clk);
  if(!fault||om!=0)$fatal(1,"off-grid value released");
  $display("PASS KV624 vectors512 active_lane_codes%0d all256codes K/V sparse/full masks; off-grid fail-closed",checks);
  rst_n=0;repeat(3)@(negedge clk);rst_n=1;
  mask=3;addr[23:0]=0;addr[47:24]=17;data[31:0]=0;data[63:32]=0;
  repeat(3)@(negedge clk);if(!fault||om!=0)$fatal(1,"nonrepresentable address silently aliased");
  $display("PASS KV624 nonrepresentable address fail-closed");$finish;
 end
endmodule
