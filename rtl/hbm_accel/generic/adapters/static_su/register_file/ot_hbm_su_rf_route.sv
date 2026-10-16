`timescale 1ns/1ps
`default_nettype none
// Physical RF route candidate: one existing 48-bit hard relay per stage.
// Bits [40:0] are {valid, RF address8, FP32 data}; seven spare pins tie low.
// Every stage has its own actual clock/reset input. STAGES is selected from
// source/destination pins and legal relay homes, never inferred from this RTL.
// FLOWS (H-SM 2026-10-15): per-stage relay master from the direction of travel at the stage's home (bits [2k+1:2k] of
// stage k: 0 WE, 1 EW, 2 SN, 3 NS); generated per die route by tools/hbm_static/su_rf_route_flows.py
// (ot_hbm_su_rf_route_flows_v5.svh, compact660_v5: STAGES = RF_RELAY = 36 on all 16 routes). Default: FLOW on every stage.
module ot_hbm_su_rf_route #(
 parameter integer STAGES=1, FLOW=0, MUT=0,
 parameter [2*STAGES-1:0] FLOWS={STAGES{FLOW[1:0]}}
)(input wire [STAGES-1:0] stage_clk,stage_rst_n,
  input wire [40:0] tuple_in,output wire [40:0] tuple_out);
 initial if(STAGES<1 || FLOW<0 || FLOW>3)$fatal(1,"RF route requires stages and an explicit legal flow");
 wire [40:0] packet [0:STAGES];
 assign packet[0]=tuple_in;
 for(genvar k=0;k<STAGES;k=k+1)begin:g_stage
  wire [40:0] source_packet=(MUT==1&&k==STAGES/2)?packet[k]^41'h1:
                            (MUT==2&&k==STAGES/2)?{1'b0,packet[k][39:0]}:packet[k];
  wire [47:0] padded={7'd0,source_packet};
  wire [47:0] landed;
  localparam [1:0] SF=FLOWS[2*k+:2];
  if(SF==2'd0)begin:g_we
   hbfd_rly_48_WE u_relay(.ck(stage_clk[k]),.rs(stage_rst_n[k]),.i(padded),.o(landed));
  end else if(SF==2'd1)begin:g_ew
   hbfd_rly_48_EW u_relay(.ck(stage_clk[k]),.rs(stage_rst_n[k]),.i(padded),.o(landed));
  end else if(SF==2'd2)begin:g_sn
   hbfd_rly_48_SN u_relay(.ck(stage_clk[k]),.rs(stage_rst_n[k]),.i(padded),.o(landed));
  end else begin:g_ns
   hbfd_rly_48_NS u_relay(.ck(stage_clk[k]),.rs(stage_rst_n[k]),.i(padded),.o(landed));
  end
  assign packet[k+1]=landed[40:0];
 end
 assign tuple_out=packet[STAGES];
endmodule
`default_nettype wire
