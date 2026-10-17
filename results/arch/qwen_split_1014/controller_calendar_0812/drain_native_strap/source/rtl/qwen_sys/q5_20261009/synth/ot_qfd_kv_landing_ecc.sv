// Function-inline exact source for package-incompatible synthesis.
`timescale 1ns/1ps
// Native HBM return correction BEFORE crossing into the core-domain landing
// FIFO. One prepaid controller credit remains occupied until real retirement.
// A UE quarantines that credit; it cannot be recycled as successful delivery.
// Cold reset requires the parent's positive all-copy/PHY drain fence.
module ot_qfd_kv_landing_ecc #(parameter integer ENABLE=0, MUT=0, INTERLEAVED=1, PIPE=2)(
 input wire hclk,h_rst_n,
 input wire i_v,input wire [287:0] i_code,
 input wire [16:0] i_sec,input wire [7:0] i_row,
 output wire o_v,output wire [255:0] o_data,
 output reg [16:0] o_sec,output reg [7:0] o_row,
 output wire ce,ue,output wire fault,output wire [31:0] ce_count
);
 // el1011-q-kvd 2026-10-12 (PIPE 2, default): registered-boundary pipeline.  M5 re-route qfd_q5_landing_ecc_m5-m5-8dcfc40b3
 // failed TT -169.88 entirely input->reg (0.2 T input budget + the whole SECDED decode before the first flop).  Now:
 //   P0  pin flops: i_v (reset) and i_code / i_sec / i_row captured every edge, no enable, no logic (io_flop_at_pins);
 //   P1  per 72-b word the 7-b Hamming syndrome + overall parity (XOR trees only), registered with the code word;
 //   P2  correction (syndrome -> one-hot flip), CE/UE classification, output registers (unchanged semantics).
 // +2 hclk landing latency (o_v / ce / ue / fault / ce_count all move together; the parent's prepaid landing credit is
 // held 2 hclk longer, LD = 64 slots absorb it).  PIPE 0 keeps the original one-register structure.
 // Bit-exact: syn64 / fix64 below are decode64 split at the syndrome register.
 function automatic [7:0] syn64(input [71:0] code);   // {overall, syndrome}
  integer p,k;reg [6:0] s;begin s=0;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)s[k]=s[k]^code[p-1];
   syn64={^code,s};
  end
 endfunction
 function automatic [65:0] fix64(input [71:0] code,input [7:0] so);   // {ue, corrected, data} == decode64(code)
  reg [71:0] c;reg [6:0] s;reg ov,ue_,co;reg [63:0] d;integer p,j;begin
   c=code;s=so[6:0];ov=so[7];ue_=0;co=0;
   if(s!=0)begin
    if(ov&&s<=71)begin for(p=1;p<=71;p=p+1)if(s==p)c[p-1]=~c[p-1];co=1;end
    else ue_=1;
   end else if(ov)begin c[71]=~c[71];co=1;end
   d=0;j=0;for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin d[j]=c[p-1];j=j+1;end
   fix64={ue_,co,d};
  end
 endfunction
 function automatic [71:0] unpack(input [71:0] s);
  integer p,j,k;begin j=0;k=0;unpack=0;
   for(p=1;p<=71;p=p+1)
    if((p&(p-1))!=0)begin unpack[p-1]=s[j];j=j+1;end
    else begin unpack[p-1]=s[64+k];k=k+1;end
   unpack[71]=s[71];
  end
 endfunction
 function automatic [63:0] unpack_data(input [71:0] code);
  integer p,j;begin j=0;unpack_data=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin unpack_data[j]=code[p-1];j=j+1;end
  end
 endfunction
 // ECC storage layout is {32 check bits,256 data bits}; no assumed free PHY
 // sideband. The parent must bind real check storage and every check pin.
 reg dv,dc,du,sticky;
 reg [255:0] corrected;
 reg [31:0] count;
 reg [255:0] decoded;
 reg any_ce,any_ue;
 // e_* : the word entering the decode (P0 pin flops when PIPE != 0, the ports otherwise)
 wire e_v;wire [287:0] e_code;wire [16:0] e_sec;wire [7:0] e_row;
 // f_* : the word entering the correction (P1 registers when PIPE == 2), with its per-word {overall, syndrome}
 wire f_v;wire [287:0] f_code;wire [31:0] f_so;wire [16:0] f_sec;wire [7:0] f_row;
 reg [287:0] e_cw;   // the 4 x 72-b codewords of e_code in Hamming position order
 reg [31:0] e_so;
 integer w;
 always @* begin
  for(w=0;w<4;w=w+1)begin
   e_cw[w*72+:72]=(INTERLEAVED!=0)?e_code[w*72+:72]:unpack({e_code[256+w*8+:8],e_code[w*64+:64]});
   e_so[w*8+:8]=syn64(e_cw[w*72+:72]);
  end
 end
 generate if (PIPE != 0) begin : g_p0
  reg p0_v;reg [287:0] p0_code;reg [16:0] p0_sec;reg [7:0] p0_row;
  always @(posedge hclk or negedge h_rst_n) if(!h_rst_n) p0_v<=1'b0; else p0_v<=i_v;
  always @(posedge hclk) begin p0_code<=i_code;p0_sec<=i_sec;p0_row<=i_row;end
  assign e_v=p0_v;assign e_code=p0_code;assign e_sec=p0_sec;assign e_row=p0_row;
 end else begin : g_np0
  assign e_v=i_v;assign e_code=i_code;assign e_sec=i_sec;assign e_row=i_row;
 end endgenerate
 generate if (PIPE >= 2) begin : g_p1
  reg p1_v;reg [287:0] p1_cw;reg [31:0] p1_so;reg [16:0] p1_sec;reg [7:0] p1_row;
  always @(posedge hclk or negedge h_rst_n) if(!h_rst_n) p1_v<=1'b0; else p1_v<=e_v;
  always @(posedge hclk) begin p1_cw<=e_cw;p1_so<=e_so;p1_sec<=e_sec;p1_row<=e_row;end
  assign f_v=p1_v;assign f_code=p1_cw;assign f_so=p1_so;assign f_sec=p1_sec;assign f_row=p1_row;
 end else begin : g_np1
  assign f_v=e_v;assign f_code=e_cw;assign f_so=e_so;assign f_sec=e_sec;assign f_row=e_row;
 end endgenerate
 always @* begin
  decoded=0;any_ce=0;any_ue=0;
  for(w=0;w<4;w=w+1)begin : decode_word
   reg [65:0] d;
   d=fix64(f_code[w*72+:72],f_so[w*8+:8]);
   decoded[w*64+:64]=(MUT!=0)?unpack_data(f_code[w*72+:72]):d[63:0];
   any_ce=any_ce|d[64];any_ue=any_ue|d[65];
  end
 end
 always @(posedge hclk or negedge h_rst_n)
  if(!h_rst_n)begin dv<=0;dc<=0;du<=0;sticky<=0;count<=0;end
  else begin
   dv<=(ENABLE!=0)&&f_v;dc<=(ENABLE!=0)&&f_v&&any_ce;du<=(ENABLE!=0)&&f_v&&any_ue;
   if((ENABLE!=0)&&f_v&&any_ue)sticky<=1;
   if((ENABLE!=0)&&f_v&&any_ce&&!any_ue)count<=count+1'b1;
  end
 always @(posedge hclk)if(f_v)corrected<=decoded;
 assign ce_count=count;
 always @(posedge hclk) if(f_v) begin o_sec<=f_sec;o_row<=f_row;end
 assign fault=(ENABLE!=0)&&sticky;
 assign ce=(ENABLE!=0)&&dc;
 assign ue=(ENABLE!=0)&&du;
 assign o_v=(ENABLE!=0)&&dv&&!du&&!sticky;
 assign o_data=corrected;
endmodule
