`timescale 1ns/1ps
// STORAGE LIFETIME ONLY: block IDs replace BF16 operands. No arithmetic claim.
// Same nonblocking write and combinational read semantics as attn_hdp.
module tb_pv_bank_lifetime;
parameter integer NBANK=4;
reg clk=0;always #5 clk=~clk;
reg [15:0] ab[0:NBANK-1][0:31];
integer cycle=0,errors=0,reads=0,writes=0,b,k,beat;
function automatic integer skew(input integer row);
skew=(row%8==0)?0:3*(row%8-1);
endfunction
initial for(b=0;b<NBANK;b=b+1)for(k=0;k<32;k=k+1)ab[b][k]=16'hffff;
always @(posedge clk)begin
  // Product input registers sample the old operand before an equal-edge write.
  for(b=0;b<20;b=b+1)for(k=0;k<32;k=k+1)for(beat=0;beat<8;beat=beat+1)
    if(cycle==b*8+7+beat+3+skew(k))begin
      reads=reads+1;
      if(ab[b%NBANK][k]!==16'(b))errors=errors+1;
    end
  for(b=0;b<20;b=b+1)for(k=0;k<32;k=k+1)
    if(cycle==b*8+k/4+2)begin ab[b%NBANK][k]<=16'(b);writes=writes+1;end
  if(cycle==200)begin
    if(NBANK==4&&errors!=0)$fatal(1,"four-bank overwrite");
    if(NBANK==3&&errors==0)$fatal(1,"negative control missed live overwrite");
    if(reads!=5120||writes!=640)$fatal(1,"incomplete event replay");
    $display("LIFETIME banks=%0d reads=%0d writes=%0d errors=%0d",NBANK,reads,writes,errors);$finish;
  end
  cycle=cycle+1;
end
endmodule
