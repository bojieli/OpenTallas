// Model: tools/hbm_collective_flight_model.py. Separate default-off successor.
`timescale 1ns/1ps
module ot_hbm_collective_protected_flight #(parameter integer ENABLE=0,W=545,D=14)(
 input wire clk,rst_n,in_v,output wire in_r,input wire [W-1:0] in_d,
 output wire out_v,input wire out_r,output wire [W-1:0] out_d,
 output wire quiet,fault
);
 generate if(!ENABLE)begin:g_off
  assign in_r=0;assign out_v=0;assign out_d=0;assign quiet=0;assign fault=0;
 end else begin:g_on
  import ot_gpu_w6_secded_pkg::*;
  localparam integer N=(W+1+63)/64;
  initial if(D<1||W<1)$fatal(1,"flight shape");
  wire [N*64-1:0] q[0:D-1];wire [N*72-1:0] code[0:D-1];
  wire [D-1:0] normal,failed,valid;
  wire healthy=&normal;
  wire advance=healthy&&(!valid[D-1]||out_r);
  assign fault=|failed;
  assign in_r=advance;
  assign out_v=healthy&&valid[D-1];
  assign quiet=healthy&&!(|valid);
  // Correction here preserves a stalled output's payload during a single-bit
  // upset. Permission remains suppressed throughout the bank's repair sequence.
  wire [N*64-1:0] corrected_output;
  for(genvar k=0;k<N;k=k+1)begin:g_decode
   wire [65:0] decoded=decode64(code[D-1][k*72+:72]);
   assign corrected_output[k*64+:64]=decoded[63:0];
  end
  assign out_d=corrected_output[W-1:0];
  for(genvar s=0;s<D;s=s+1)begin:g_stage
   localparam integer STAGE=s;
   wire [N*64-1:0] next_data;wire [N*72-1:0] next_code;
   assign valid[s]=q[s][W];
   if(s==0)begin:g_first
    assign next_data={{(N*64-W-1){1'b0}},in_v,(in_v?in_d:{W{1'b0}})};
   assign next_code=0;
   end else begin:g_next
    assign next_data=0;
    assign next_code=code[s-1];
   end
   ot_hbm_w2_protected_bank #(.WORDS(N)) u_bank(
    .clk(clk),.por_n(rst_n),.load(advance),.load_encoded(STAGE!=0),.fatal(fault),
    .d(next_data),.encoded_d(next_code),.q(q[s]),.encoded_q(code[s]),
    .normal(normal[s]),.fault(failed[s]),.repairing());
  end
 end endgenerate
endmodule
