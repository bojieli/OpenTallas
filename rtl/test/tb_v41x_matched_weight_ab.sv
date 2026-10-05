`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Observation-only wrapper for the matched weight-source A/B
// (tools/rtl_v41x_matched_weight_ab.py).  It instantiates the unmodified
// two-package all-unit bench rtl/test/tb_hdc_v41x_array.sv and only READS its
// hierarchy: nothing here drives a signal of the bench.  Both arms are built
// from this file; the arm is selected by +define+HDC_W_HBM=0|1, and the
// weight-HBM counters below exist only with +define+AB_WHBM_PROBE (W_HBM=1),
// because arm A has no weight HBM to observe.
//
// Per package it counts, identically in both arms:
//   qe_issues   LINQ (weight-reading) QE instructions issued;
//   qrom_reads  quantised-weight words the QE read (ROM port in arm A, the
//               streamer's delivery port in arm B);
//   qgate_wait  cycles an instruction otherwise ready to issue was held ONLY
//               by the weight-supply gate q_gate (always 0 in arm A);
//   qgate_low   cycles in S_ISSUE with q_gate low for any reason.
// A line per token (ABTOK) snapshots the counters at the token's cycle.
// ---------------------------------------------------------------------------
module tb_v41x_matched_weight_ab #(
    parameter integer USERS = 1,
    parameter integer STALL = 0
) (input wire clk);
    tb_hdc_v41x_array #(.USERS(USERS), .STALL(STALL)) u (.clk(clk));

    localparam [3:0] S_ISSUE = 4'd6;  // ot_hdc_core_v41x state encoding
    // b2_p2p: two packages (the tool checks NODES == 2 in the generated configuration)
    longint qe_issues0 = 0, qrom_reads0 = 0, qgate_wait0 = 0, qgate_low0 = 0;
    longint qe_issues1 = 0, qrom_reads1 = 0, qgate_wait1 = 0, qgate_low1 = 0;

`define AB_COUNT(K) \
    always @(posedge clk) if (u.rst_n) begin \
        if (u.g_node[K].qrom_re) qrom_reads``K = qrom_reads``K + 1; \
        if (u.g_node[K].core.st == S_ISSUE && u.g_node[K].core.d_unit != 3'd0 && !u.g_node[K].core.d_skip) begin \
            if (!u.g_node[K].core.q_gate) qgate_low``K = qgate_low``K + 1; \
            if (u.g_node[K].core.waited && u.g_node[K].core.unit_ready && u.g_node[K].core.kv_gate) begin \
                if (!u.g_node[K].core.q_gate) qgate_wait``K = qgate_wait``K + 1; \
                else if (u.g_node[K].core.d_unit == 3'd3 && u.g_node[K].core.qe_mode == 2'd0) \
                    qe_issues``K = qe_issues``K + 1; \
            end \
        end \
    end
    `AB_COUNT(0)
    `AB_COUNT(1)

    always @(posedge clk) if (u.rst_n && u.tok_v)
        $display("ABTOK pos=%0d cycle=%0d qe_issues=%0d,%0d qrom_reads=%0d,%0d qgate_wait=%0d,%0d qgate_low=%0d,%0d",
                 u.tok_p, u.cyc, qe_issues0, qe_issues1, qrom_reads0, qrom_reads1,
                 qgate_wait0, qgate_wait1, qgate_low0, qgate_low1);

`ifdef AB_WHBM_PROBE
    longint h_rd, h_act, h_hit, h_conf, h_ref;
`define AB_HBM(K) \
    h_rd = 0; h_act = 0; h_hit = 0; h_conf = 0; h_ref = 0; \
    for (integer p = 0; p < 8; p = p + 1) begin \
        h_rd = h_rd + u.g_node[K].g_qs.u_hbm.st_rd[p]; h_act = h_act + u.g_node[K].g_qs.u_hbm.st_act[p]; \
        h_hit = h_hit + u.g_node[K].g_qs.u_hbm.st_hit[p]; h_conf = h_conf + u.g_node[K].g_qs.u_hbm.st_conf[p]; \
        h_ref = h_ref + u.g_node[K].g_qs.u_hbm.st_ref[p]; \
    end \
    $display("ABWHBM node=%0d sector_reads=%0d activates=%0d row_hits=%0d row_conflicts=%0d refreshes=%0d req_backpressure_cycles=%0d rd_lat_sum_ps=%0d rd_lat_max_ps=%0d fetched=%0d consumed=%0d fault_why=%0d", \
             K, h_rd, h_act, h_hit, h_conf, h_ref, u.g_node[K].g_qs.u_hbm.st_bp_cycles, \
             u.g_node[K].g_qs.u_hbm.st_rd_lat_sum, u.g_node[K].g_qs.u_hbm.st_rd_lat_max, \
             u.g_node[K].g_qs.qs_fetched, u.g_node[K].g_qs.qs_consumed, u.g_node[K].g_qs.qs_why);
`endif

    final begin
        $display("ABNODE node=0 qe_issues=%0d qrom_reads=%0d qgate_wait=%0d qgate_low=%0d",
                 qe_issues0, qrom_reads0, qgate_wait0, qgate_low0);
        $display("ABNODE node=1 qe_issues=%0d qrom_reads=%0d qgate_wait=%0d qgate_low=%0d",
                 qe_issues1, qrom_reads1, qgate_wait1, qgate_low1);
`ifdef AB_WHBM_PROBE
        `AB_HBM(0)
        `AB_HBM(1)
`endif
        $display("ABPROBE_DONE whbm=%0d", `HDC_W_HBM);
    end
endmodule
