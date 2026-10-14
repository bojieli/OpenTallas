`timescale 1ns/1ps
// Production PQ core, PHW9/SAW11/KMAX6144/R128. Wiring only at this level.
// Returns stay die-placed in twelve tier/half groups; ga_i contains four
// 4-bit tag counts per group. The core owns no 128-region return registers.
// Each child has its own die clock entry; the die must deliver phi-R.
// Functional candidate: ctl/AQ pin stages and clock closure are still owed.
module ot_s81_pq_core_native (
    input wire ck_ctl, ck_qb, ck_fault,
    input wire [1:0] ck_aq,
    input wire [3:0] ck_ix, ck_bc,
    input wire rst_n, go,
    input wire [8:0] i_ph,
    input wire [2:0] i_np,
    input wire [18:0] i_xbase, i_xps, i_obase, i_ops,
    input wire [1:0] i_fmt,
    output wire ready, idle,
    output wire x_re,
    output wire [18:0] x_addr,
    input wire x_rv,
    input wire [2047:0] x_q,
    // Distributed return groups: twelve counts/faults and configuration out.
    input wire [11:0] q2f_i,
    input wire [191:0] ga_i,
    output wire [457:0] mdr_o,
    input wire f_fault,
    output wire fault,
    output wire [31:0] phase_cycles,
    output wire ev_go, ev_end,
    output wire [1:0] ev_tag,
    output wire [1632:0] f_bus,
    output wire [9:0] rom_pa0, rom_pa1,
    input wire [63:0] rom_pq0, rom_pq1,
    output wire [10:0] rom_sa,
    input wire [47:0] rom_sq
`ifdef OT_PQ_BENCH_TELEMETRY
    , output wire [1:0] read_consumed, read_speculative
    , output wire [13:0] observed_k
    , output wire observed_load_active
    , output wire [383:0] ix_rows_read, ix_rows_written, qb_rows_read, qb_rows_written
    , output wire [6:0] aq0_write_row, aq1_write_row, aq0_read_row, aq1_read_row
    , output wire aq_request
    , output wire [1:0] aq_results
`endif
);
    wire aq_vin, ba_v;
    wire [1:0] aqf;
    wire [9:0] aqi;
    wire [7:0] ba_blk;
    wire [47:0] hw;
    wire [35:0] h_hi;
    wire [15:0] h_b0, h_b1;
    wire [608:0] bc_hr;
    wire [4:0] storage_fault;
    wire q_consume, b_consume;
    wire fault_to_ctl;
    ot_s81_pq_fault_pin u_fault (.clk(ck_fault), .rst_n(rst_n),
        .faults({f_fault, q2f_i, storage_fault}), .fault(fault_to_ctl));
    // RG11 selects exactly twelve count groups in this controller. The
    // group region census is external: each tier/half has 10 or 11 regions,
    // not eleven equal groups and a seven-region tail.
    ot_s81_pq_ctl_native #(.PHW(9), .SAW(11), .R(128), .VAW(19), .VRD(64), .KMAX(6144),
        .BST(2), .NSEG(8), .PQ(1), .RG(11), .XRV(1), .XCAP(16), .RPT(2), .BW(1633)) u_ctl (
        .clk(ck_ctl), .rst_n(rst_n), .go(go), .i_ph(i_ph), .i_np(i_np), .i_xbase(i_xbase),
        .i_xps(i_xps), .i_obase(i_obase), .i_ops(i_ops), .i_fmt(i_fmt),
        .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr), .x_rv(x_rv), .f_fault(fault_to_ctl),
        .fault(fault), .phase_cycles(phase_cycles), .ev_go(ev_go), .ev_end(ev_end), .ev_tag(ev_tag),
        .aq_vin(aq_vin), .aqf(aqf), .q_consume(q_consume), .b_consume(b_consume), .aqi_o(aqi), .ba_v_o(ba_v), .ba_blk_o(ba_blk),
        .hw_o(hw), .h_hi_o(h_hi), .h_b0_o(h_b0), .h_b1_o(h_b1), .mdr_o(mdr_o),
        .q2f_i(q2f_i), .ga_i(ga_i), .bc_hr_o(bc_hr),
        .rom_pa0(rom_pa0), .rom_pa1(rom_pa1), .rom_pq0(rom_pq0), .rom_pq1(rom_pq1),
        .rom_sa(rom_sa), .rom_sq(rom_sq));
`ifdef OT_PQ_BENCH_TELEMETRY
    assign read_consumed = {b_consume, q_consume};
    assign read_speculative = {u_ctl.hw[0] && u_ctl.h_fam && !b_consume,
                              u_ctl.hw[0] && !u_ctl.h_fam && !q_consume};
    assign observed_k = u_ctl.ld_kk;
    assign observed_load_active = u_ctl.ld_run;
    assign aq_request = aq_vin;
    assign aq_results = {g_aq[1].u_aq.vo, g_aq[0].u_aq.vo};
    assign aq0_write_row = g_aq[0].u_aq.r_wp;
    assign aq1_write_row = g_aq[1].u_aq.r_wp;
    assign aq0_read_row = g_aq[0].u_aq.r_rp;
    assign aq1_read_row = g_aq[1].u_aq.r_rp;
`ifdef OT_PQ_REFERENCE
    assign ix_rows_read = 0; assign ix_rows_written = 0;
    assign qb_rows_read = 0; assign qb_rows_written = 0;
`else
    genvar z;
    generate for (z = 0; z < 4; z = z + 1) begin : g_coverage
        assign ix_rows_read[96*z +: 96] =
            g_ix[z].u_ix.g_read_group[0].g_bank[0].rows_read & g_ix[z].u_ix.g_read_group[0].g_bank[1].rows_read &
            g_ix[z].u_ix.g_read_group[1].g_bank[0].rows_read & g_ix[z].u_ix.g_read_group[1].g_bank[1].rows_read &
            g_ix[z].u_ix.g_read_group[2].g_bank[0].rows_read & g_ix[z].u_ix.g_read_group[2].g_bank[1].rows_read &
            g_ix[z].u_ix.g_read_group[3].g_bank[0].rows_read & g_ix[z].u_ix.g_read_group[3].g_bank[1].rows_read;
        assign ix_rows_written[96*z +: 96] = g_ix[z].u_ix.g_read_group[0].g_bank[0].written;
        assign qb_rows_read[96*z +: 96] = u_qb.g_bank[z].rows_read;
        assign qb_rows_written[96*z +: 96] = u_qb.g_bank[z].written;
    end endgenerate
`endif
`endif
    wire [511:0] aq_q;
    wire [19:0] aq_e;
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_aq
        ot_dsrom_aq12t u_aq (.clk(ck_aq[g]), .rst_n(rst_n), .v(aq_vin), .x(x_q[1024*g +: 1024]),
            .vo(), .q(aq_q[256*g +: 256]), .e(aq_e[10*g +: 10]), .y(), .fault(aqf[g]));
    end endgenerate
    wire [255:0] hq0, hq1;
    wire [9:0] he0, he1;
    ot_s81_pq_qb_sram u_qb (.clk(ck_qb), .rst_n(rst_n), .consume(q_consume), .aqi_d(aqi), .aq_q(aq_q), .aq_e(aq_e),
        .h_b0(h_b0), .h_b1(h_b1), .hw_sv(hw[13:12]), .hq0(hq0), .hq1(hq1), .he0(he0), .he1(he1),
        .fault(storage_fault[4]));
    wire [1023:0] bt_d;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ix
        wire [255:0] d;
        ot_s81_pq_ix_sram u_ix (.clk(ck_ix[g]), .rst_n(rst_n), .consume(b_consume), .par(g >= 2),
            .xw(x_q[1024*(g % 2) +: 1024]), .ba_v(ba_v), .ba_blk(ba_blk), .h_hi(h_hi), .hw7(hw[7:1]),
            .bt_d(d), .fault(storage_fault[g]));
        genvar u;
        for (u = 0; u < 4; u = u + 1) begin : g_u
            assign bt_d[256*u + 64*g +: 64] = d[64*u +: 64];
        end
    end endgenerate
    wire [1632:0] bc [0:4];
    assign bc[0] = {bc_hr[608:578], hq0, he0, hq1, he1, bc_hr[45:0], bt_d};
    generate for (g = 0; g < 4; g = g + 1) begin : g_bc
        ot_v41_pqc_bcrel #(.W(1633), .RT(18), .RB(1063)) u_rel (
            .clk(ck_bc[g]), .rst_n(rst_n), .d(bc[g]), .q(bc[g + 1]));
    end endgenerate
    assign f_bus = bc[4];
endmodule

// All fault reduction state belongs to this hardened leaf, not its parent.
module ot_s81_pq_fault_pin (
    input wire clk, rst_n,
    input wire [17:0] faults,
    output reg fault
);
    reg [17:0] captured;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin captured <= 0; fault <= 0; end
        else begin captured <= faults; fault <= fault || |captured; end
endmodule
