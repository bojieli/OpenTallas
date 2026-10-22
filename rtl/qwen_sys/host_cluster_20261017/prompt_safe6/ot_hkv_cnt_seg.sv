// N36: exact event counter with registered carry at each 8-bit boundary.
// carry[g] == (&q[g*8-1:0]) after each edge; each q slice adds only eight bits.
module ot_hkv_cnt_seg #(parameter integer W=32, parameter integer CHUNK=8)(
 input wire clk,rst_n,en, output wire [W-1:0] q
);
 genvar g;
 generate for(g=0;g<(W+CHUNK-1)/CHUNK;g=g+1)begin:lane
  localparam integer L=g*CHUNK;
  localparam integer N=(W-L<CHUNK)?W-L:CHUNK;
  reg [N-1:0] count;
  wire inc;
  if(g==0)begin:first assign inc=en;end
  else begin:upper
   reg carry;
   localparam [L-1:0] PRE={{(L-1){1'b1}},1'b0};
   always @(posedge clk or negedge rst_n)
    if(!rst_n) carry<=1'b0;
    else if(en) carry<=(q[L-1:0]==PRE);
   assign inc=en&&carry;
  end
  always @(posedge clk or negedge rst_n)
   if(!rst_n)count<=0;
   else if(inc)count<=count+1'b1;
  assign q[L+:N]=count;
 end endgenerate
endmodule
