(* keep_hierarchy, keep *)
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule

(* keep_hierarchy, keep *)
module ot_dp_rgate (input wire clk, input wire d, input wire run, output reg q);
    always @(posedge clk) q <= d & run;
endmodule

(* keep_hierarchy *)
module ot_dp_rsync_s2 (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    // Intentional reset CDC shift register; only this async_reg declaration
    // mixes asynchronous assertion with synchronous release/feedback.
    /* verilator lint_off SYNCASYNCNET */
    (* async_reg = "true" *) reg [1:0] p;
    /* verilator lint_on SYNCASYNCNET */
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) p <= 2'b0; else p <= {p[0], 1'b1};
    assign sync_rst_n = p[1];
endmodule

(* keep_hierarchy *)
module ot_dp_rsync_s3 (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    // Intentional reset CDC shift register; only this async_reg declaration
    // mixes asynchronous assertion with synchronous release/feedback.
    /* verilator lint_off SYNCASYNCNET */
    (* async_reg = "true" *) reg [2:0] p;
    /* verilator lint_on SYNCASYNCNET */
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) p <= 3'b0; else p <= {p[1:0], 1'b1};
    assign sync_rst_n = p[2];
endmodule

(* keep_hierarchy, keep *)
module ot_dp_lockq #(parameter integer STABLE = 16) (input wire clk, input wire d, input wire locked, output reg q);
    localparam integer CW = $clog2(STABLE + 1);
    (* async_reg = "true" *) reg [1:0] ls;
    reg [CW-1:0] cnt;
    wire stable = (cnt == STABLE);
    always @(posedge clk) begin
        if (!d) begin
            ls <= 2'b00;
            cnt <= {CW{1'b0}};
            q <= 1'b0;
        end else begin
            ls <= {ls[0], locked};
            if (!ls[1]) cnt <= {CW{1'b0}};
            else if (!stable) cnt <= cnt + 1'b1;
            q <= q | stable;
        end
    end
endmodule
module old_fe(input clk,arst_n,start_i,output rst_o_0,start_o_0,rst_o_1,start_o_1,mission);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 10 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    // START role mission: consumer taps = registered (reset AND run)
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw tap tap 0 depth 1 @ (155.5, 167.4)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run tap tap 0 depth 1 @ (155.5, 167.4)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (155.5, 167.4)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (155.5, 167.4)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (155.5, 167.4)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (155.5, 167.4)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 0 depth 4 @ (155.5, 167.4)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 0 depth 4 @ (155.5, 167.4)
    ot_dp_rgate u_rrl_4 (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(rst_n_t0));  // gated pad tap 0 depth 5 @ (155.5, 167.4)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_0), .q(rst_rl_5));  // raw tap tap 1 depth 2 @ (466.6, 167.4)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_5));  // run tap tap 1 depth 2 @ (466.6, 167.4)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));  // raw pad tap 1 depth 3 @ (466.6, 167.4)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_6));  // run pad tap 1 depth 3 @ (466.6, 167.4)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 1 depth 4 @ (466.6, 167.4)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 1 depth 4 @ (466.6, 167.4)
    ot_dp_rgate u_rrl_8 (.clk(clk), .d(rst_rl_7), .run(rn_rst_rl_7), .q(rst_n_t1));  // gated pad tap 1 depth 5 @ (466.6, 167.4)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_5), .q(rst_rl_9));  // raw tap tap 3 depth 3 @ (466.6, 502.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_9));  // run tap tap 3 depth 3 @ (466.6, 502.2)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 4 @ (466.6, 502.2)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 4 @ (466.6, 502.2)
    ot_dp_rgate u_rrl_11 (.clk(clk), .d(rst_rl_10), .run(rn_rst_rl_10), .q(rst_n_t3));  // gated pad tap 3 depth 5 @ (466.6, 502.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_9), .q(rst_rl_12));  // raw tap tap 5 depth 4 @ (466.6, 837.0)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_12));  // run tap tap 5 depth 4 @ (466.6, 837.0)
    ot_dp_rgate u_rrl_13 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t5));  // gated pad tap 5 depth 5 @ (466.6, 837.0)
    ot_dp_rgate u_rrl_14 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t7));  // gated tap tap 7 depth 5 @ (466.6, 1171.8)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_0), .q(rst_rl_15));  // raw tap tap 2 depth 2 @ (155.5, 502.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_15));  // run tap tap 2 depth 2 @ (155.5, 502.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 2 depth 3 @ (155.5, 502.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 2 depth 3 @ (155.5, 502.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw pad tap 2 depth 4 @ (155.5, 502.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run pad tap 2 depth 4 @ (155.5, 502.2)
    ot_dp_rgate u_rrl_18 (.clk(clk), .d(rst_rl_17), .run(rn_rst_rl_17), .q(rst_n_t2));  // gated pad tap 2 depth 5 @ (155.5, 502.2)
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_15), .q(rst_rl_19));  // raw pad tap 4 depth 3 @ (155.5, 837.0)
    wire rn_rst_rl_19;
    ot_dp_rrelay u_srl_19 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_19));  // run pad tap 4 depth 3 @ (155.5, 837.0)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));  // raw tap tap 4 depth 4 @ (155.5, 837.0)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_19), .q(rn_rst_rl_20));  // run tap tap 4 depth 4 @ (155.5, 837.0)
    ot_dp_rgate u_rrl_21 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t4));  // gated pad tap 4 depth 5 @ (155.5, 837.0)
    ot_dp_rgate u_rrl_22 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t6));  // gated tap tap 6 depth 5 @ (155.5, 1171.8)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_15), .q(rst_rl_23));  // raw wire tap None depth 3 @ (531.2, 502.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_23));  // run wire tap None depth 3 @ (531.2, 502.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw wire tap None depth 4 @ (613.0, 796.1)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run wire tap None depth 4 @ (613.0, 796.1)
    wire rr_t9;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rr_t9));  // raw tap tap 9 depth 5 @ (613.0, 1171.8)
    wire rn_rr_t9;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_24), .q(rn_rr_t9));  // run tap tap 9 depth 5 @ (613.0, 1171.8)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_root_n), .q(rst_rl_26));  // raw pad tap None depth 1 @ (374.3, 8.6)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(run_root), .q(rn_rst_rl_26));  // run pad tap None depth 1 @ (374.3, 8.6)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap None depth 2 @ (374.3, 8.6)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap None depth 2 @ (374.3, 8.6)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw wire tap None depth 3 @ (374.3, 8.6)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run wire tap None depth 3 @ (374.3, 8.6)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw wire tap None depth 4 @ (613.0, 136.1)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run wire tap None depth 4 @ (613.0, 136.1)
    wire rr_t8;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rr_t8));  // raw tap tap 8 depth 5 @ (613.0, 502.2)
    wire rn_rr_t8;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rr_t8));  // run tap tap 8 depth 5 @ (613.0, 502.2)
    assign rst_o_0 = rr_t8;  // registered reset out (wavefront) at (613.0, 502.2)
    assign start_o_0 = rn_rr_t8;  // registered START out beside rst_o_0
    assign rst_o_1 = rr_t9;  // registered reset out (wavefront) at (613.0, 1171.8)
    assign start_o_1 = rn_rr_t9;  // registered START out beside rst_o_1

assign mission = rst_n_t2;
endmodule
module fixed_fe(input clk,arst_n,start_i,output rst_o_0,start_o_0,rst_o_1,start_o_1,mission);
    // OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry relayed + synchronous relay tree carrying reset AND run (START broadcast), depth 5 to all 10 taps, hops <= 405 um; every tap releases 6 clocks after the LATER of the entry reset release and the entry START
    wire rst_root_n, run_root;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register of the SYNCHRONOUS reset input (neighbour's rst_o)
    ot_dp_rrelay u_run_in (.clk(clk), .d(start_i), .q(run_root));  // pin register of the SYNCHRONOUS START input (neighbour's start_o)
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    // START role mission: consumer taps = registered (reset AND run)
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw tap tap 0 depth 1 @ (155.5, 167.4)
    wire rn_rst_rl_0;
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_rst_rl_0));  // run tap tap 0 depth 1 @ (155.5, 167.4)
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 0 depth 2 @ (155.5, 167.4)
    wire rn_rst_rl_1;
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_1));  // run pad tap 0 depth 2 @ (155.5, 167.4)
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 0 depth 3 @ (155.5, 167.4)
    wire rn_rst_rl_2;
    ot_dp_rrelay u_srl_2 (.clk(clk), .d(rn_rst_rl_1), .q(rn_rst_rl_2));  // run pad tap 0 depth 3 @ (155.5, 167.4)
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 0 depth 4 @ (155.5, 167.4)
    wire rn_rst_rl_3;
    ot_dp_rrelay u_srl_3 (.clk(clk), .d(rn_rst_rl_2), .q(rn_rst_rl_3));  // run pad tap 0 depth 4 @ (155.5, 167.4)
    ot_dp_rgate u_rrl_4 (.clk(clk), .d(rst_rl_3), .run(rn_rst_rl_3), .q(rst_n_t0));  // gated pad tap 0 depth 5 @ (155.5, 167.4)
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_0), .q(rst_rl_5));  // raw tap tap 1 depth 2 @ (466.6, 167.4)
    wire rn_rst_rl_5;
    ot_dp_rrelay u_srl_5 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_5));  // run tap tap 1 depth 2 @ (466.6, 167.4)
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));  // raw pad tap 1 depth 3 @ (466.6, 167.4)
    wire rn_rst_rl_6;
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_6));  // run pad tap 1 depth 3 @ (466.6, 167.4)
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));  // raw pad tap 1 depth 4 @ (466.6, 167.4)
    wire rn_rst_rl_7;
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_rst_rl_6), .q(rn_rst_rl_7));  // run pad tap 1 depth 4 @ (466.6, 167.4)
    ot_dp_rgate u_rrl_8 (.clk(clk), .d(rst_rl_7), .run(rn_rst_rl_7), .q(rst_n_t1));  // gated pad tap 1 depth 5 @ (466.6, 167.4)
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_5), .q(rst_rl_9));  // raw tap tap 3 depth 3 @ (466.6, 502.2)
    wire rn_rst_rl_9;
    ot_dp_rrelay u_srl_9 (.clk(clk), .d(rn_rst_rl_5), .q(rn_rst_rl_9));  // run tap tap 3 depth 3 @ (466.6, 502.2)
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));  // raw pad tap 3 depth 4 @ (466.6, 502.2)
    wire rn_rst_rl_10;
    ot_dp_rrelay u_srl_10 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_10));  // run pad tap 3 depth 4 @ (466.6, 502.2)
    ot_dp_rgate u_rrl_11 (.clk(clk), .d(rst_rl_10), .run(rn_rst_rl_10), .q(rst_n_t3));  // gated pad tap 3 depth 5 @ (466.6, 502.2)
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_9), .q(rst_rl_12));  // raw tap tap 5 depth 4 @ (466.6, 837.0)
    wire rn_rst_rl_12;
    ot_dp_rrelay u_srl_12 (.clk(clk), .d(rn_rst_rl_9), .q(rn_rst_rl_12));  // run tap tap 5 depth 4 @ (466.6, 837.0)
    ot_dp_rgate u_rrl_13 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t5));  // gated pad tap 5 depth 5 @ (466.6, 837.0)
    ot_dp_rgate u_rrl_14 (.clk(clk), .d(rst_rl_12), .run(rn_rst_rl_12), .q(rst_n_t7));  // gated tap tap 7 depth 5 @ (466.6, 1171.8)
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_0), .q(rst_rl_15));  // raw tap tap 2 depth 2 @ (155.5, 502.2)
    wire rn_rst_rl_15;
    ot_dp_rrelay u_srl_15 (.clk(clk), .d(rn_rst_rl_0), .q(rn_rst_rl_15));  // run tap tap 2 depth 2 @ (155.5, 502.2)
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));  // raw pad tap 2 depth 3 @ (155.5, 502.2)
    wire rn_rst_rl_16;
    ot_dp_rrelay u_srl_16 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_16));  // run pad tap 2 depth 3 @ (155.5, 502.2)
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));  // raw pad tap 2 depth 4 @ (155.5, 502.2)
    wire rn_rst_rl_17;
    ot_dp_rrelay u_srl_17 (.clk(clk), .d(rn_rst_rl_16), .q(rn_rst_rl_17));  // run pad tap 2 depth 4 @ (155.5, 502.2)
    ot_dp_rgate u_rrl_18 (.clk(clk), .d(rst_rl_17), .run(rn_rst_rl_17), .q(rst_n_t2));  // gated pad tap 2 depth 5 @ (155.5, 502.2)
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_15), .q(rst_rl_19));  // raw pad tap 4 depth 3 @ (155.5, 837.0)
    wire rn_rst_rl_19;
    ot_dp_rrelay u_srl_19 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_19));  // run pad tap 4 depth 3 @ (155.5, 837.0)
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));  // raw tap tap 4 depth 4 @ (155.5, 837.0)
    wire rn_rst_rl_20;
    ot_dp_rrelay u_srl_20 (.clk(clk), .d(rn_rst_rl_19), .q(rn_rst_rl_20));  // run tap tap 4 depth 4 @ (155.5, 837.0)
    ot_dp_rgate u_rrl_21 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t4));  // gated pad tap 4 depth 5 @ (155.5, 837.0)
    ot_dp_rgate u_rrl_22 (.clk(clk), .d(rst_rl_20), .run(rn_rst_rl_20), .q(rst_n_t6));  // gated tap tap 6 depth 5 @ (155.5, 1171.8)
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_15), .q(rst_rl_23));  // raw wire tap None depth 3 @ (531.2, 502.2)
    wire rn_rst_rl_23;
    ot_dp_rrelay u_srl_23 (.clk(clk), .d(rn_rst_rl_15), .q(rn_rst_rl_23));  // run wire tap None depth 3 @ (531.2, 502.2)
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));  // raw wire tap None depth 4 @ (613.0, 796.1)
    wire rn_rst_rl_24;
    ot_dp_rrelay u_srl_24 (.clk(clk), .d(rn_rst_rl_23), .q(rn_rst_rl_24));  // run wire tap None depth 4 @ (613.0, 796.1)
    wire rr_t9;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rr_t9));  // raw tap tap 9 depth 5 @ (613.0, 1171.8)
    wire rn_rr_t9;
    ot_dp_rrelay u_srl_25 (.clk(clk), .d(rn_rst_rl_24), .q(rn_rr_t9));  // run tap tap 9 depth 5 @ (613.0, 1171.8)
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_root_n), .q(rst_rl_26));  // raw pad tap None depth 1 @ (374.3, 8.6)
    wire rn_rst_rl_26;
    ot_dp_rrelay u_srl_26 (.clk(clk), .d(run_root), .q(rn_rst_rl_26));  // run pad tap None depth 1 @ (374.3, 8.6)
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));  // raw pad tap None depth 2 @ (374.3, 8.6)
    wire rn_rst_rl_27;
    ot_dp_rrelay u_srl_27 (.clk(clk), .d(rn_rst_rl_26), .q(rn_rst_rl_27));  // run pad tap None depth 2 @ (374.3, 8.6)
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));  // raw wire tap None depth 3 @ (374.3, 8.6)
    wire rn_rst_rl_28;
    ot_dp_rrelay u_srl_28 (.clk(clk), .d(rn_rst_rl_27), .q(rn_rst_rl_28));  // run wire tap None depth 3 @ (374.3, 8.6)
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));  // raw wire tap None depth 4 @ (613.0, 136.1)
    wire rn_rst_rl_29;
    ot_dp_rrelay u_srl_29 (.clk(clk), .d(rn_rst_rl_28), .q(rn_rst_rl_29));  // run wire tap None depth 4 @ (613.0, 136.1)
    wire rr_t8;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rr_t8));  // raw tap tap 8 depth 5 @ (613.0, 502.2)
    wire rn_rr_t8;
    ot_dp_rrelay u_srl_30 (.clk(clk), .d(rn_rst_rl_29), .q(rn_rr_t8));  // run tap tap 8 depth 5 @ (613.0, 502.2)
    assign rst_o_0 = rr_t8;  // registered reset out (wavefront) at (613.0, 502.2)
    assign start_o_0 = rn_rr_t8;  // registered START out beside rst_o_0
    assign rst_o_1 = rr_t9;  // registered reset out (wavefront) at (613.0, 1171.8)
    assign start_o_1 = rn_rr_t9;  // registered START out beside rst_o_1

assign mission = rst_n_t2;
endmodule
module tb;
reg clk=0,arst_n=0,start_i=0;wire[4:0] a,b;integer i;
old_fe u_old(clk,arst_n,start_i,a[0],a[1],a[2],a[3],a[4]);
fixed_fe u_fixed(clk,arst_n,start_i,b[0],b[1],b[2],b[3],b[4]);
always #5 clk=~clk;
initial begin
 for(i=0;i<500;i=i+1) begin
 @(negedge clk);arst_n=(i<12)?0:$random;start_i=(i<12)?0:$random;
 @(posedge clk);#1;if(i>12 && a!==b) $fatal(1,"FE reset mismatch at edge%0d",i);
 end
 $display("LOCKSTEP_PASS FE graph500edges6cycle_release addedcycles0");$finish;
end
endmodule
