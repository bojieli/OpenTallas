`timescale 1ns/1ps
module tb_qwen_dspark_w1_lookup;
 parameter integer BANK=0,MUT=0;
 reg clk=0,rst=0,iv=0,orr=0;always #0.555555 clk=~clk;
 reg [17:0] token;reg [63:0] id;
 wire ready,ov,last,fault;wire [2047:0] values;wire [7:0] osequence;wire [1:0] quarter;wire [63:0] oid;
 ot_qwen_dspark_w1_lookup #(.ENABLE(1),.BANK(BANK)) dut(.clk(clk),.rst_n(rst),.i_v(iv),.i_r(ready),.i_token(token),.i_id(id),.i_sequence(8'd209),
  .o_v(ov),.o_r(orr),.o_values(values),.o_sequence(osequence),.o_quarter(quarter),.o_id(oid),.o_last(last),.fault(fault));
 function automatic [7:0] byteval(input integer row,input integer col);byteval=8'((row*7+col*13)^32'hba57);endfunction
 for(genvar g=0;g<8;g=g+1)begin : initialize_macro
  integer a,b;reg [265:0] word;
  initial begin
   #0.01;
   for(a=0;a<4096;a=a+1)begin
    word=0;
    for(b=0;b<32;b=b+1)word[b*8+:8]=byteval(a,g*32+b);
    if(g==0)word[256+:8]=8'h80;
    if(g==1)word[256+:8]=8'h3f;
    if(MUT!=0&&g==0)word[0]=~word[0];
    // Program real NOR via-mask cells, not a bypass response stub.
    for(b=0;b<266;b=b+1)dut.rom_bank.banks[g].macro_inst.arr[a/8][b*8+a%8]=word[b];
   end
  end
 end
 function automatic [31:0] exact_code(input [7:0] c);
 integer mag,l,j;reg [31:0] f;
 begin mag=c[7]?(256-integer'(c)):integer'(c);l=0;for(j=0;j<8;j=j+1)if(mag&(1<<j))l=j;
 f=32'(mag)<<(23-l);exact_code=(mag==0)?32'b0:{c[7],8'(127+l),f[22:0]};end
 endfunction
 integer a,q,b,t,nrows;
 initial begin
  repeat(5)@(negedge clk);rst=1;repeat(4)@(negedge clk);
  nrows=(BANK==37)?384:4096;
  for(a=0;a<nrows;a=a+1)begin
   @(negedge clk);if(!ready)$fatal(1,"read lease unavailable");
   token=18'(BANK*4096+a);id=64'h1234fedc00000000+64'(a);iv=1;
   @(negedge clk);iv=0;t=0;
   while(!ov&&t<12)begin @(negedge clk);t=t+1;end
   if(!ov||ready||fault)$fatal(1,"macro response/finite credit invalid");
   for(q=0;q<4;q=q+1)begin
    t=0;while(!ov&&t<12)begin @(negedge clk);t=t+1;end
    if(!ov)$fatal(1,"converted quarter unavailable");
    repeat(3)begin
     @(negedge clk);
     if(!ov||quarter!==2'(q)||oid!==id||osequence!==8'd209||last!==(q==3))$fatal(1,"row/scale/identity/hold invalid %0d %0d",a,q);
     for(b=0;b<64;b=b+1)if(values[b*32+:32]!==exact_code(byteval(a,q*64+b)))$fatal(1,"ROM/dequant join payload mutant row=%0d byte=%0d",a,q*64+b);
    end
    orr=1;@(negedge clk);orr=0;
   end
  end
  @(negedge clk);iv=1;token=151936;@(negedge clk);iv=0;repeat(5)@(negedge clk);
  if(!fault||ov||ready)$fatal(1,"invalid vocabulary token was not blocked");
  $display("QWEN_W1_LOOKUP_PASS bank=%0d realmacros=8 rows=%0d codebytes=%0d stall_identity_scale=1 bounds_negative=1",BANK,nrows,nrows*256);
  $finish;
 end
endmodule
