`timescale 1ps/1ps
module selected_source(input wire clk,rnx,rel,rpb,input wire [552:0] h0,output wire [275:0] ca,cb,output wire merr);
localparam integer IDX_EN=1,IDX_MRG=1,IDX_TP=0;
wire[275:0]tm=0;
wire iacc=!h0[0] && h0[3:1]==3'd5;
generate if (IDX_EN != 0) begin : g_irx
      localparam integer IJ = 12, IW = 23;             // 12 x 23 = 276 bits
      reg [275:0] ih, ca_q, cb_q;
      wire [IJ-1:0] sca, scb;
`ifdef OT_S81SL_LEP_MUT_IDXDMX
      wire to_ca = rel && iacc && (IDX_TP != 0 ? 1'b0 : !rpb);   // MUTANT: demux swapped
`else
      wire to_ca = rel && iacc && (IDX_TP != 0 || rpb);          // S81/IDXNET: a TP end hands every beat to ca
`endif
      wire to_cb = rel && iacc && !to_ca;
      always @(posedge clk) ih <= h0[4 +: 276];
      // S81/IDXNET (IDX_MRG 1): tm (the s_0S TP RX beats, a partition pin) -> pin flop tmp -> tmq + kept valid copies smc,
      // ORed into ca: tm pin -> ca 3 edges.  A tm beat and a pair-B tree beat in the same ca cycle is a sticky fault.
      wire [275:0] tmw; wire [IJ-1:0] smc;
      if (IDX_MRG != 0) begin : g_tm
        reg [275:0] tmp, tmq; reg me;
        always @(posedge clk) begin tmp <= tm; tmq <= tmp; end
        for (genvar j = 0; j < IJ; j = j + 1) begin : g_mc
`ifdef OT_S81SL_LEP_MUT_TPMRG
          (* keep=1 *) ot_s81sl_lep_idx_sel u_sm (.clk(clk), .rn(rnx), .d(1'b0), .q(smc[j]));   // MUTANT: tm never merged
`else
          (* keep=1 *) ot_s81sl_lep_idx_sel u_sm (.clk(clk), .rn(rnx), .d(tmp[0]), .q(smc[j]));
`endif
        end
        always @(posedge clk or negedge rnx) if (!rnx) me <= 1'b0; else if (smc[0] && sca[0]) me <= 1'b1;
        assign tmw = tmq; assign merr = me;
      end else begin : g_ntm
        assign tmw = 276'd0; assign smc = '0; assign merr = 1'b0;
      end
      for (genvar j = 0; j < IJ; j = j + 1) begin : g_j
        (* keep=1 *) ot_s81sl_lep_idx_sel u_sa (.clk(clk), .rn(rnx), .d(to_ca), .q(sca[j]));
        (* keep=1 *) ot_s81sl_lep_idx_sel u_sb (.clk(clk), .rn(rnx), .d(to_cb), .q(scb[j]));
        if (j == 0) begin : g_v
          always @(posedge clk or negedge rnx)
            if (!rnx) begin ca_q[0] <= 1'b0; cb_q[0] <= 1'b0; end
            else begin ca_q[0] <= (sca[0] && ih[0]) || (smc[0] && tmw[0]); cb_q[0] <= scb[0] && ih[0]; end
          always @(posedge clk) begin
            ca_q[IW-1:1] <= (ih[IW-1:1] & {(IW-1){sca[0]}}) | (tmw[IW-1:1] & {(IW-1){smc[0]}});
            cb_q[IW-1:1] <= ih[IW-1:1] & {(IW-1){scb[0]}};
          end
        end else begin : g_d
          always @(posedge clk) begin
            ca_q[j*IW +: IW] <= (ih[j*IW +: IW] & {IW{sca[j]}}) | (tmw[j*IW +: IW] & {IW{smc[j]}});
            cb_q[j*IW +: IW] <= ih[j*IW +: IW] & {IW{scb[j]}};
          end
        end
      end
      assign ca = ca_q; assign cb = cb_q;
    end else begin : g_nirx
      assign ca = 276'd0; assign cb = 276'd0; assign merr = 1'b0;
    end endgenerate
endmodule
module ot_s81sl_lep_idx_sel(input wire clk, input wire rn, input wire d, output reg q);
 always @(posedge clk or negedge rn) if (!rn) q <= 1'b0; else q <= d;
endmodule
