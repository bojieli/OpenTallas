`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011: ONE-STACK owned selected-CKV row fetch of an S81 scan-service slab.
// The dispatcher of ot_chip_v41x_ckv_pc_fetch (rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv, unchanged) cut to the single HBM
// stack the slab sits on: P request ports, each the unchanged replicated element ot_chip_v41x_ckv_pc_port (S row slots
// in one 1R1W SRAM, nine back-to-back sector reads per row, every DMA check kept).  Placement as the DMA:
//   row id g: die = g[5:4], stack = g[7:6], local = (g >> 8) * 16 + g[3:0], sectors base + 9 * local + 0..8.
// The id stream is the slab's OWNED list (ot_s81_svcq_rows: entries whose die == DIE_ID and stack == ST); an entry of
// another die / stack is a contract violation (fault[3], entry dropped, never fetched).
// Port j = local mod P.  Output: registered round-robin select over the P port registers, one row per cycle.
// ---------------------------------------------------------------------------
module ot_s81_svcq_selfetch #(
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer P = 8,
    parameter integer S = 16,
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer K = 512,
    parameter integer MAX_CONTEXT = 1048576,
    parameter bit SRAM_MACRO = 0,
    parameter integer LP = (P > 1) ? $clog2(P) : 1,
    parameter integer SW = (S > 1) ? $clog2(S) : 1,
    parameter integer TAGW = SW + 4,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  job_v,           // pulse: start a job (ignored while running -> fault[3])
    input  wire [POS_W-1:0]      published_source_count,
    input  wire [SEC_W-1:0]      region_base_sector,
    input  wire [SEC_W-1:0]      region_sector_count,
    input  wire [KW-1:0]         id_count,        // owned entries available
    input  wire                  id_done,         // id_count is final
    output wire [KW-1:0]         id_idx,
    input  wire [KW-1:0]         id_rank_in,      // one cycle after id_idx
    input  wire [POS_W-1:0]      id_gid,
    output reg                   o_v,
    input  wire                  o_ready,
    output reg  [KW-1:0]         o_rank,
    output reg  [POS_W-1:0]      o_gid,
    output reg  [2303:0]         o_row,
    output reg                   run,
    output reg                   done,
    output reg                   fault,
    output reg  [3:0]            fault_code,      // {foreign entry / job while running, poison, response, range}
    output wire [P-1:0]          m_v,
    input  wire [P-1:0]          m_rdy,
    output wire [P*HAW-1:0]      m_addr,
    output wire [P*TAGW-1:0]     m_tag,
    input  wire [P-1:0]          s_v,
    input  wire [P*TAGW-1:0]     s_tag,
    input  wire [P*4-1:0]        s_beat,
    input  wire [P*256-1:0]      s_data
);
    reg [KW-1:0] cur;
    assign id_idx = cur;
    reg e_v;
    reg [KW-1:0] e_rank;
    reg [POS_W-1:0] e_gid;
    wire [POS_W-1:0] e_local = ((e_gid >> 8) << 4) | POS_W'(e_gid[3:0]);
    wire [LP-1:0] e_port = (P > 1) ? LP'(e_local) : '0;
    wire [SEC_W+4:0] e_a0 = (SEC_W+5)'(region_base_sector) + (SEC_W+5)'(e_local) * (SEC_W+5)'(9);
    wire e_range_bad = e_gid >= published_source_count || e_gid >= POS_W'(MAX_CONTEXT) ||
                       ((SEC_W+5)'(region_base_sector) + (SEC_W+5)'(region_sector_count)) >= ((SEC_W+5)'(1) << SEC_W) ||
                       e_a0 + (SEC_W+5)'(9) > (SEC_W+5)'(region_base_sector) + (SEC_W+5)'(region_sector_count);
    wire foreign = e_gid[5:4] != 2'(DIE_ID) || e_gid[7:6] != 2'(ST);
    wire [P-1:0] p_free;
    wire dispatch = run && e_v && !foreign && !e_range_bad && p_free[e_port];
    wire drop = run && e_v && (foreign || e_range_bad);
    wire consume = dispatch || drop;
    reg rd_p, k_v;
    reg [KW-1:0] k_rank;
    reg [POS_W-1:0] k_gid;
    wire [1:0] occ_next = 2'(e_v && !consume) + 2'(k_v) + 2'(rd_p);
    wire issue = run && cur < id_count && occ_next <= 2'd1;

    wire [P-1:0] p_busy_any, p_fault_rsp, p_fault_poison, p_ov, p_take;
    wire [P*KW-1:0] p_rank;
    wire [P*POS_W-1:0] p_gid;
    wire [P*2304-1:0] p_row;
    genvar q;
    generate for (q = 0; q < P; q = q + 1) begin : g_port
        ot_chip_v41x_ckv_pc_port #(.S(S), .POS_W(POS_W), .HAW(HAW), .K(K), .SRAM_MACRO(SRAM_MACRO)) u_port (
            .clk(clk), .rst_n(rst_n), .run(run),
            .d_v(dispatch && e_port == LP'(q)), .d_rank(e_rank), .d_gid(e_gid), .d_a0(HAW'(e_a0)), .d_free(p_free[q]),
            .m_v(m_v[q]), .m_rdy(m_rdy[q]), .m_addr(m_addr[q*HAW +: HAW]), .m_tag(m_tag[q*TAGW +: TAGW]),
            .s_v_in(s_v[q]), .s_tag_in(s_tag[q*TAGW +: TAGW]), .s_beat_in(s_beat[q*4 +: 4]),
            .s_data_in(s_data[q*256 +: 256]),
            .o_v(p_ov[q]), .o_take(p_take[q]), .o_rank(p_rank[q*KW +: KW]), .o_gid(p_gid[q*POS_W +: POS_W]),
            .o_row(p_row[q*2304 +: 2304]), .busy_any(p_busy_any[q]), .fault_rsp(p_fault_rsp[q]),
            .fault_poison(p_fault_poison[q]));
    end endgenerate

    // registered round-robin select: P port registers -> output register
    reg [LP-1:0] rr;
    reg have;
    reg [LP-1:0] pick;
    integer k1, idx;
    always @(*) begin
        have = 1'b0; pick = 0;
        for (k1 = 0; k1 < P; k1 = k1 + 1) begin
            idx = (32'(rr) + k1) % P;
            if (!have && p_ov[idx]) begin have = 1'b1; pick = LP'(idx); end
        end
    end
    wire go = have && (!o_v || o_ready);
    assign p_take = go ? (P'(1) << pick) : '0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_v <= 0; o_rank <= 0; o_gid <= 0; rr <= 0; end
        else if (go) begin
            o_v <= 1'b1; o_rank <= p_rank[32'(pick)*KW +: KW]; o_gid <= p_gid[32'(pick)*POS_W +: POS_W];
            o_row <= p_row[32'(pick)*2304 +: 2304]; rr <= LP'((32'(pick) + 1) % P);
        end else if (o_ready) o_v <= 1'b0;
    end

    reg idle_q;
    wire idle_now = cur == id_count && id_done && !e_v && !k_v && !rd_p && p_busy_any == 0 && !o_v && !dispatch;
`ifndef SYNTHESIS
    initial if (P < 1 || (P & (P - 1)) != 0 || S < 1 || S * 9 > 256) $fatal(1, "svcq selfetch parameter contract");
`endif
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; cur <= 0; e_v <= 0; e_rank <= 0; e_gid <= 0; rd_p <= 0; k_v <= 0; k_rank <= 0; k_gid <= 0;
            idle_q <= 0; done <= 0; fault <= 0; fault_code <= 0;
        end else begin
            if (|p_fault_rsp) begin fault <= 1; fault_code[1] <= 1; end
            if (|p_fault_poison) begin fault <= 1; fault_code[2] <= 1; end
            if (run && e_v && e_range_bad && !foreign) begin fault <= 1; fault_code[0] <= 1; end
            if (run && e_v && foreign) begin fault <= 1; fault_code[3] <= 1; end
            if (job_v && run) begin fault <= 1; fault_code[3] <= 1; end
            if (job_v && !run) begin
                run <= 1; cur <= 0; done <= 0; e_v <= 0; rd_p <= 0; k_v <= 0; idle_q <= 0;
            end else if (run) begin
                rd_p <= issue;
                if (issue) cur <= cur + 1'b1;
                if (!e_v || consume) begin
                    if (k_v) begin
                        e_v <= 1; e_rank <= k_rank; e_gid <= k_gid;
                        k_v <= rd_p; k_rank <= id_rank_in; k_gid <= id_gid;
                    end else if (rd_p) begin
                        e_v <= 1; e_rank <= id_rank_in; e_gid <= id_gid;
                    end else e_v <= 0;
                end else if (rd_p) begin
                    k_v <= 1; k_rank <= id_rank_in; k_gid <= id_gid;
                end
                idle_q <= idle_now;
                if (idle_now && idle_q) begin run <= 0; done <= 1; end
            end
        end
    end
endmodule
