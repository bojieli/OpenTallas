`timescale 1ns/1ps
// Exact non-reflected CRC as a parallel GF(2) matrix. A serial RTL recurrence
// unrolls into ~90 reconvergent XOR levels at DW567; balanced reductions below
// express the same polynomial with ceil(log2(DW)) XOR levels, without latency.
// CRC16/CCITT or CRC32/IEEE, all-ones seed, no final complement.
module ot_qwen_crc_parallel #(parameter integer DW=567,CW=16)(
 input wire [DW-1:0] d,output wire [CW-1:0] q
);
 localparam [CW-1:0] POLY=CW==32 ? CW'(32'h04c11db7):CW'(16'h1021);
 function automatic [DW-1:0] mask(input integer ob);
  integer i;reg [CW-1:0] c;
  begin
   c=POLY;
   for(i=0;i<DW;i=i+1)begin
    mask[i]=c[ob];
    c={c[CW-2:0],1'b0}^(c[CW-1]?POLY:{CW{1'b0}});
   end
  end
 endfunction
 function automatic [CW-1:0] seed;
  integer i;reg [CW-1:0] c;
  begin
   c={CW{1'b1}};
   for(i=0;i<DW;i=i+1)c={c[CW-2:0],1'b0}^(c[CW-1]?POLY:{CW{1'b0}});
   seed=c;
  end
 endfunction
 localparam [CW-1:0] INIT=seed();
 for(genvar b=0;b<CW;b=b+1)begin:g_bit
  localparam [DW-1:0] M=mask(b);
  assign q[b]=^(d&M)^INIT[b];
 end
endmodule
