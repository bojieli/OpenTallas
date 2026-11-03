`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; integer checks=0,diff=0,c,i;
reg [567:0] w_gc_0_leaf_procdff_71558_Q; reg [2175:0] w_gc_0_leaf_procdff_71561_Q; reg [0:0] w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
reg [567:0] golden_q0; reg [2175:0] golden_k0; reg golden_v0;
always @(posedge clk) begin golden_q0<=w_gc_0_leaf_procdff_71558_Q[567:0]; golden_k0<=w_gc_0_leaf_procdff_71561_Q[2175:0]; golden_v0<=w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; end
reg [567:0] w_gc_1_leaf_procdff_71558_Q; reg [2175:0] w_gc_1_leaf_procdff_71561_Q; reg [0:0] w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
reg [567:0] golden_q1; reg [2175:0] golden_k1; reg golden_v1;
always @(posedge clk) begin golden_q1<=w_gc_1_leaf_procdff_71558_Q[567:0]; golden_k1<=w_gc_1_leaf_procdff_71561_Q[2175:0]; golden_v1<=w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q0, ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k0, ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v0, ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]
`ifdef MUT
 ^ 565'd1
`endif
; ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k0 <= w_gc_0_leaf_procdff_71561_Q[543:0]; ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k1 <= w_gc_0_leaf_procdff_71561_Q[543:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q0, ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k0, ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v0, ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k0 <= w_gc_0_leaf_procdff_71561_Q[543:0]; ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k1 <= w_gc_0_leaf_procdff_71561_Q[543:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q0, ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k0, ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v0, ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k0 <= w_gc_0_leaf_procdff_71561_Q[1087:544]; ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k1 <= w_gc_0_leaf_procdff_71561_Q[1087:544];
        ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q0, ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k0, ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v0, ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k0 <= w_gc_0_leaf_procdff_71561_Q[1087:544]; ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k1 <= w_gc_0_leaf_procdff_71561_Q[1087:544];
        ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q0, ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k0, ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v0, ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k0 <= w_gc_0_leaf_procdff_71561_Q[1631:1088]; ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k1 <= w_gc_0_leaf_procdff_71561_Q[1631:1088];
        ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q0, ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k0, ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v0, ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k0 <= w_gc_0_leaf_procdff_71561_Q[1631:1088]; ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k1 <= w_gc_0_leaf_procdff_71561_Q[1631:1088];
        ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q0, ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k0, ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v0, ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k0 <= w_gc_0_leaf_procdff_71561_Q[2175:1632]; ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k1 <= w_gc_0_leaf_procdff_71561_Q[2175:1632];
        ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q0, ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k0, ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v0, ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q0 <= w_gc_0_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q1 <= w_gc_0_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k0 <= w_gc_0_leaf_procdff_71561_Q[2175:1632]; ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k1 <= w_gc_0_leaf_procdff_71561_Q[2175:1632];
        ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v0 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v1 <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q0, ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k0, ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v0, ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k0 <= w_gc_1_leaf_procdff_71561_Q[543:0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k1 <= w_gc_1_leaf_procdff_71561_Q[543:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q0, ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k0, ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v0, ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k0 <= w_gc_1_leaf_procdff_71561_Q[543:0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k1 <= w_gc_1_leaf_procdff_71561_Q[543:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q0, ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k0, ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v0, ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k0 <= w_gc_1_leaf_procdff_71561_Q[1087:544]; ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k1 <= w_gc_1_leaf_procdff_71561_Q[1087:544];
        ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q0, ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k0, ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v0, ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k0 <= w_gc_1_leaf_procdff_71561_Q[1087:544]; ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k1 <= w_gc_1_leaf_procdff_71561_Q[1087:544];
        ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q0, ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k0, ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v0, ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k0 <= w_gc_1_leaf_procdff_71561_Q[1631:1088]; ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k1 <= w_gc_1_leaf_procdff_71561_Q[1631:1088];
        ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q0, ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k0, ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v0, ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k0 <= w_gc_1_leaf_procdff_71561_Q[1631:1088]; ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k1 <= w_gc_1_leaf_procdff_71561_Q[1631:1088];
        ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q0, ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k0, ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v0, ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k0 <= w_gc_1_leaf_procdff_71561_Q[2175:1632]; ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k1 <= w_gc_1_leaf_procdff_71561_Q[2175:1632];
        ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
    (* keep *) reg [564:0] ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q0, ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q1;
    (* keep *) reg [543:0] ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k0, ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k1;
    (* keep *) reg ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v0, ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v1;
    always @(posedge clk) begin
        ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q0 <= w_gc_1_leaf_procdff_71558_Q[564:0]; ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q1 <= w_gc_1_leaf_procdff_71558_Q[564:0];
        ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k0 <= w_gc_1_leaf_procdff_71561_Q[2175:1632]; ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k1 <= w_gc_1_leaf_procdff_71561_Q[2175:1632];
        ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v0 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0]; ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v1 <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];
    end
initial begin
for(c=0;c<64;c=c+1) begin @(negedge clk);
for(i=0;i<17;i=i+1) w_gc_0_leaf_procdff_71558_Q[i*32+:32]=$urandom; w_gc_0_leaf_procdff_71558_Q[564:544]=$urandom; w_gc_0_leaf_procdff_71558_Q[567:565]=0;
for(i=0;i<68;i=i+1) w_gc_0_leaf_procdff_71561_Q[i*32+:32]=$urandom; w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y=$urandom;
for(i=0;i<17;i=i+1) w_gc_1_leaf_procdff_71558_Q[i*32+:32]=$urandom; w_gc_1_leaf_procdff_71558_Q[564:544]=$urandom; w_gc_1_leaf_procdff_71558_Q[567:565]=0;
for(i=0;i<68;i=i+1) w_gc_1_leaf_procdff_71561_Q[i*32+:32]=$urandom; w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y=$urandom;
@(posedge clk); #1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k0 !== golden_k0[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_k1 !== golden_k0[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h0_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k0 !== golden_k0[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_k1 !== golden_k0[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k0h1_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k0 !== golden_k0[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_k1 !== golden_k0[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h0_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k0 !== golden_k0[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_k1 !== golden_k0[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k1h1_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k0 !== golden_k0[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_k1 !== golden_k0[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h0_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k0 !== golden_k0[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_k1 !== golden_k0[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k2h1_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k0 !== golden_k0[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_k1 !== golden_k0[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h0_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q0 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k0 !== golden_k0[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v0 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_q1 !== golden_q0[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_k1 !== golden_k0[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c0_k3h1_v1 !== golden_v0) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k0 !== golden_k1[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_k1 !== golden_k1[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h0_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k0 !== golden_k1[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_k1 !== golden_k1[543:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k0h1_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k0 !== golden_k1[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_k1 !== golden_k1[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h0_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k0 !== golden_k1[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_k1 !== golden_k1[1087:544]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k1h1_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k0 !== golden_k1[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_k1 !== golden_k1[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h0_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k0 !== golden_k1[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_k1 !== golden_k1[1631:1088]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k2h1_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k0 !== golden_k1[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_k1 !== golden_k1[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h0_v1 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q0 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k0 !== golden_k1[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v0 !== golden_v1) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_q1 !== golden_q1[564:0]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_k1 !== golden_k1[2175:1632]) diff=diff+1;
checks=checks+1;if(ownface_u_u_hb_idx_s_Q_r1c1_k3h1_v1 !== golden_v1) diff=diff+1;
$display("CAPTURE checks=%0d diff=%0d",checks,diff); end if(diff) $fatal(1,"private face mutant or mismatch"); $display("CAPTURE_EQ_PASS checks=%0d",checks); $finish; end endmodule
