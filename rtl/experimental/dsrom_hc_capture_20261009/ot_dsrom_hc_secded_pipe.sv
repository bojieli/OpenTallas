`timescale 1ns/1ps
// Two-cycle SECDED: balanced syndrome reduction, then correction/registered
// delivery. Only validity needs reset; protected storage remains upstream.
module ot_dsrom_hc_secded_pipe(
 input wire clk,rst_n,valid_in,input wire [71:0] c,
 output reg valid_out,output reg [63:0] d,output reg ce,ue
);
 wire [6:0] syndrome;
 wire overall=^c;
 genvar k,p;
 generate for(k=0;k<7;k=k+1) begin:g_syndrome
  wire [70:0] terms;
  for(p=1;p<=71;p=p+1) begin:g_terms
   assign terms[p-1]=((p & (1<<k))!=0)?c[p-1]:1'b0;
  end
  assign syndrome[k]=^terms;
 end endgenerate
 reg [71:0] code_q;
 reg [6:0] syndrome_q;
 reg overall_q,valid_q;
 wire correct=overall_q && syndrome_q!=0 && syndrome_q<=71;
 wire corrected=correct || (overall_q && syndrome_q==0);
 wire uncorrectable=syndrome_q!=0 && !correct;
 wire [70:0] fixed_code;
 generate for(p=1;p<=71;p=p+1) begin:g_correct
  assign fixed_code[p-1]=code_q[p-1] ^ (correct && syndrome_q==p);
 end endgenerate
 // Non-power-of-two positions carry the 64 payload bits, ascending order.
 function automatic [63:0] payload(input [70:0] x);
  integer pos,j;
  begin
   payload=0;j=0;
   for(pos=1;pos<=71;pos=pos+1)
    if((pos & (pos-1))!=0) begin payload[j]=x[pos-1];j=j+1;end
  end
 endfunction
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin valid_q<=0;valid_out<=0;end
  else begin valid_q<=valid_in;valid_out<=valid_q;end
 always @(posedge clk) begin
  if(valid_in) begin code_q<=c;syndrome_q<=syndrome;overall_q<=overall;end
  if(valid_q) begin d<=payload(fixed_code);ce<=corrected;ue<=uncorrectable;end
 end
endmodule

// Two-cycle response encoder. Stage one stores payload and Hamming parity;
// stage two forms the overall parity from those registered values.
module ot_dsrom_hc_secded_encode_pipe(
 input wire clk,rst_n,valid_in,input wire [63:0] d,
 output reg valid_out,output reg [71:0] c
);
 function automatic [70:0] place_payload(input [63:0] x);
  integer pos,j;
  begin
   place_payload=0;j=0;
   for(pos=1;pos<=71;pos=pos+1)
    if((pos & (pos-1))!=0) begin place_payload[pos-1]=x[j];j=j+1;end
  end
 endfunction
 wire [70:0] placed=place_payload(d);
 wire [6:0] parity;
 genvar k,p;
 generate for(k=0;k<7;k=k+1) begin:g_parity
  wire [70:0] terms;
  for(p=1;p<=71;p=p+1) begin:g_terms
   assign terms[p-1]=((p & (1<<k))!=0)?placed[p-1]:1'b0;
  end
  assign parity[k]=^terms;
 end endgenerate
 reg [63:0] payload_q;
 reg [6:0] parity_q;
 reg valid_q;
 wire [70:0] code_payload=place_payload(payload_q);
 wire [70:0] code_with_parity;
 generate for(p=1;p<=71;p=p+1) begin:g_code
  if((p & (p-1))==0) begin:g_check
   assign code_with_parity[p-1]=parity_q[$clog2(p)];
  end else begin:g_data
   assign code_with_parity[p-1]=code_payload[p-1];
  end
 end endgenerate
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin valid_q<=0;valid_out<=0;end
  else begin valid_q<=valid_in;valid_out<=valid_q;end
 always @(posedge clk) begin
  if(valid_in) begin payload_q<=d;parity_q<=parity;end
  if(valid_q) c<={(^payload_q)^(^parity_q),code_with_parity};
 end
endmodule
