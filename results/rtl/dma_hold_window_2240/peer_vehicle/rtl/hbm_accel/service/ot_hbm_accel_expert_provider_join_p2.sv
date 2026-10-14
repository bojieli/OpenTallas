`timescale 1ps/1fs
`default_nettype none
// Consumer seam only: no calendar, quota, owner copy, FIFO or payload register.
// full73 is the actual protected caller frame, held through consumer drain.
// Gibbs mints ordinals at PHY READ acceptance; both ordinal outputs stay separate.
module ot_hbm_accel_expert_provider_join_p2 #(parameter ENABLE=0,NP=32)(
 input wire service_clk,por_n,
 input wire held_frame_valid,input wire [72:0] held_frame,
 input wire provider_fault,
 input wire [NP-1:0] provider_issue_v,provider_return_v,
 input wire [NP*16-1:0] provider_next_ordinal,caller_next_ordinal,
 input wire [NP*16-1:0] provider_return_ordinal,
 input wire [NP*73-1:0] provider_return_frame,
 input wire [NP*256-1:0] provider_return_data,
 output wire [NP-1:0] issue_v,rsp_v,
 output wire [NP*16-1:0] rsp_ordinal,
 output wire [NP*256-1:0] rsp_data,
 output wire fault
);
 generate if(!ENABLE)begin:off
  assign issue_v=0;assign rsp_v=0;assign rsp_ordinal=0;assign rsp_data=0;assign fault=0;
 end else begin:on
  (* keep=1 *) reg poison,poison_n;
  wire [NP-1:0] mismatch;
  for(genvar p=0;p<NP;p++)begin:pc
   assign mismatch[p]=(provider_issue_v[p]&&
       provider_next_ordinal[p*16+:16]!=caller_next_ordinal[p*16+:16])||
       (provider_return_v[p]&&provider_return_frame[p*73+:73]!=held_frame);
  end
  wire event_bad=provider_fault||(|mismatch)||
      ((|provider_issue_v|| |provider_return_v)&&!held_frame_valid);
  assign fault=poison||(poison!=~poison_n)||event_bad;
  assign issue_v=provider_issue_v&{NP{!fault}};
  assign rsp_v=provider_return_v&{NP{!fault}};
  assign rsp_ordinal=provider_return_ordinal;
  assign rsp_data=provider_return_data;
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin poison<=0;poison_n<=1;end
   else if(fault)begin poison<=1;poison_n<=0;end
 end endgenerate
endmodule
`default_nettype wire
