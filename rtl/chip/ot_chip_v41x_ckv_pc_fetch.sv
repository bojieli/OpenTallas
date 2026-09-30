`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Wide owned selected-CKV row fetch of one die (DeepSeek-V4.1, tensor group 4):
// P HBM request ports per stack (4P per die, e.g. P pseudo-channel groups of
// the die's K-side bus), each one 32-B sector per cycle, instead of the
// single-port ot_chip_v41x_ckv_sel_fetch (one sector per stack per cycle).
//
// Placement and row format are unchanged (ot_chip_v41x_ckv_selected_dma,
// docs/V41X_SELECTED_CKV_DMA.md): compressed row id g lives on
//   die = g[5:4], stack = g[7:6], local = (g >> 8) * 16 + g[3:0],
//   sectors base[stack] + 9 * local + 0..8 (512 E2M1 nibbles, then 32 E4M3
//   scales in sector 8).
// Port choice: port j = local mod P of the row's stack (P a power of two), so
// consecutive rows of a 16-row group use different ports.  The address sent
// on a port is the unchanged sector address; mapping it to a pseudo-channel
// is the controller's business.
//
// Per port (a replicated element): S row slots held in ONE 1R1W SRAM of
// S * 9 sectors x 256 bits (ot_sram_1r1w_256x256_m2_r2c2 when SRAM_MACRO = 1,
// S <= 28), allocated in dispatch order.  The port issues the slots' sectors
// in order, one per granted cycle, tag = {slot, sector}; responses may return
// in any order and are written straight into the SRAM; a slot is complete
// after nine.  Complete slots are read out in order (nine SRAM reads) into
// the port's 2,304-bit output register.  Every check of the DMA is kept:
// unpublished / out-of-context source, region bound, response tag/beat, NaN
// E4M3 scale in sector 8.
//
// Output: the 4P port registers go through a registered two-level select
// (4 ports -> stack register, 4 stacks -> output register, round robin at
// each level), one row per cycle, rows in any order (the collector places
// them by rank).
//
// Interfaces (as ot_chip_v41x_ckv_sel_fetch)
//   job     job_v/job_ready, window_count, published_source_count, per-stack
//           region base/count (current user and source layer).
//   ids     id_count/id_done, id_idx -> id_rank_in, id_gid (the die's owned
//           list of ot_chip_v41x_ckv_sel_ids; non-owned entries are skipped).
//   rows    o_v/o_ready, o_rank, o_gid, o_row (registered).
//   hbm     NP = 4P ports (port q = stack * P + j): m_v/m_rdy/m_addr/m_tag,
//           read responses s_v/s_tag/s_beat/s_data (one sector per port per
//           cycle, s_rdy held high).  TAGW = log2(S) + 4.
//   status  done, fault/fault_code {range, rsp, poison}, st_owned_rows.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_slot_ram #(
    parameter integer DEPTH = 144,
    parameter bit SRAM_MACRO = 0
) (
    input  wire clk,
    input  wire we,
    input  wire [7:0] waddr,
    input  wire [255:0] wdata,
    input  wire re,
    input  wire [7:0] raddr,
    output wire [255:0] rdata          // one cycle after re
);
    generate if (SRAM_MACRO) begin : g_macro
        ot_sram_1r1w_256x256_m2_r2c2 u_mem (
            .clk(clk), .r_ce_in(re), .r_addr_in(raddr), .rd_out(rdata),
            .w_ce_in(we), .w_addr_in(waddr), .wd_in(wdata), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end else begin : g_beh
        reg [255:0] mem [0:DEPTH-1];
        reg [255:0] q;
        always @(posedge clk) begin
            if (we) mem[waddr] <= wdata;
            if (re) q <= mem[raddr];
        end
        assign rdata = q;
    end endgenerate
endmodule

// One request port of the wide selected-CKV fetch: the replicated element.
//   dispatch  d_v (one row, only when d_free), d_rank, d_gid, d_a0 (first sector address).
//   hbm       m_v/m_rdy/m_addr/m_tag (tag {slot, sector}), s_v/s_tag/s_beat/s_data.
//   row out   o_v/o_take (registered 2,304-bit row, its rank and id).
//   S slots in one 1R1W SRAM of S*9 x 256 bits; issue, response write and readout in slot order.
//   The request port, the response port and the fault outputs are registered (one cycle each).
module ot_chip_v41x_ckv_pc_port #(
    parameter integer S = 16,
    parameter integer POS_W = 21,
    parameter integer HAW = 30,
    parameter integer K = 512,
    parameter bit SRAM_MACRO = 0,
    parameter integer SW = (S > 1) ? $clog2(S) : 1,
    parameter integer TAGW = SW + 4,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire clk, rst_n, run,
    input  wire d_v,
    input  wire [KW-1:0] d_rank,
    input  wire [POS_W-1:0] d_gid,
    input  wire [HAW-1:0] d_a0,
    output wire d_free,
    output reg  m_v,
    input  wire m_rdy,
    output reg  [HAW-1:0] m_addr,
    output reg  [TAGW-1:0] m_tag,
    input  wire s_v_in,
    input  wire [TAGW-1:0] s_tag_in,
    input  wire [3:0] s_beat_in,
    input  wire [255:0] s_data_in,
    output reg  o_v,
    input  wire o_take,
    output reg  [KW-1:0] o_rank,
    output reg  [POS_W-1:0] o_gid,
    output reg  [2303:0] o_row,
    output wire busy_any,
    output reg  fault_rsp,
    output reg  fault_poison
);
    // the HBM response is registered on entry (one cycle), the faults on exit
    reg s_v;
    reg [TAGW-1:0] s_tag;
    reg [3:0] s_beat;
    reg [255:0] s_data;
    reg poison;                          // NaN E4M3 scale byte in the incoming sector, found before the register
    integer b;
    reg poison_in;
    always @(*) begin
        poison_in = 1'b0;
        for (b = 0; b < 32; b = b + 1) if (s_data_in[8*b +: 7] == 7'h7f) poison_in = 1'b1;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s_v <= 1'b0; else s_v <= s_v_in;
    always @(posedge clk) begin
        s_tag <= s_tag_in; s_beat <= s_beat_in; s_data <= s_data_in; poison <= poison_in;
    end
    reg [S-1:0] busy, cmp;
    reg [3:0] got [0:S-1];
    reg [KW-1:0] rk [0:S-1];
    reg [POS_W-1:0] gd [0:S-1];
    reg [HAW-1:0] a0 [0:S-1];
    reg [SW-1:0] al, ip, rp;
    reg [3:0] isec;
    // the request leaves from an output register (m_v/m_addr/m_tag); the next one loads when it is
    // empty or accepted this cycle
    wire iss_v = run && busy[ip] && !cmp[ip];
    wire can_load = !m_v || m_rdy;
    wire grant = iss_v && can_load;
    wire [SW-1:0] rslot = s_tag[4 +: SW];
    wire [3:0] rsec = s_tag[3:0];
    wire rsp_bad = s_v && (rsec > 4'd8 || !busy[rslot] || s_beat != 0);
    wire rsp_poison = s_v && !rsp_bad && rsec == 4'd8 && poison;
    reg ro_act, ro_q;
    reg [3:0] ro_k, ro_kq;
    wire ro_start = run && !ro_act && !ro_q && busy[rp] && got[rp] == 4'd9 && !o_v;
    wire [255:0] rdata;
    ot_chip_v41x_ckv_slot_ram #(.DEPTH(S * 9), .SRAM_MACRO(SRAM_MACRO)) u_ram (
        .clk(clk), .we(s_v && !rsp_bad), .waddr(8'(32'(rslot) * 9 + 32'(rsec))), .wdata(s_data),
        .re(ro_act), .raddr(8'(32'(rp) * 9 + 32'(ro_k))), .rdata(rdata));
    assign d_free = !busy[al];
    assign busy_any = |busy || ro_act || ro_q || o_v || s_v || m_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault_rsp <= 1'b0; fault_poison <= 1'b0; end
        else begin fault_rsp <= rsp_bad; fault_poison <= rsp_poison; end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; cmp <= 0; al <= 0; ip <= 0; rp <= 0; isec <= 0;
            m_v <= 0; m_addr <= 0; m_tag <= 0;
            ro_act <= 0; ro_k <= 0; ro_q <= 0; ro_kq <= 0; o_v <= 0; o_rank <= 0; o_gid <= 0;
            for (i = 0; i < S; i = i + 1) got[i] <= 0;
        end else begin
            if (d_v) begin
                busy[al] <= 1'b1; cmp[al] <= 1'b0; got[al] <= 0;
                rk[al] <= d_rank; gd[al] <= d_gid; a0[al] <= d_a0;
                al <= SW'((32'(al) + 1) % S);
            end
            if (grant) begin
                m_v <= 1'b1; m_addr <= a0[ip] + HAW'(isec); m_tag <= {ip, isec};
                if (isec == 4'd8) begin
                    isec <= 0; cmp[ip] <= 1'b1; ip <= SW'((32'(ip) + 1) % S);
                end else isec <= isec + 1'b1;
            end else if (can_load) m_v <= 1'b0;
            if (s_v && !rsp_bad && !rsp_poison) got[rslot] <= got[rslot] + 1'b1;
            ro_q <= ro_act; ro_kq <= ro_k;
            if (ro_start) begin
                ro_act <= 1; ro_k <= 0; o_rank <= rk[rp]; o_gid <= gd[rp];
            end else if (ro_act) begin
                if (ro_k == 4'd8) begin
                    ro_act <= 0; busy[rp] <= 1'b0; got[rp] <= 0; rp <= SW'((32'(rp) + 1) % S);
                end else ro_k <= ro_k + 1'b1;
            end
            if (ro_q) begin
                for (i = 0; i < 9; i = i + 1) if (ro_kq == 4'(i)) o_row[256*i +: 256] <= rdata;
                if (ro_kq == 4'd8) o_v <= 1;
            end
            if (o_take) o_v <= 0;
        end
    end
endmodule

module ot_chip_v41x_ckv_pc_fetch #(
    parameter integer DIE_ID = 0,
    parameter integer P = 4,            // request ports per stack
    parameter integer S = 16,           // row slots per port
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer HAW = 30,
    parameter integer K = 512,
    parameter integer MAX_CONTEXT = 1048576,
    parameter bit SRAM_MACRO = 0,
    parameter integer NP = 4 * P,
    parameter integer LP = (P > 1) ? $clog2(P) : 1,
    parameter integer SW = (S > 1) ? $clog2(S) : 1,
    parameter integer TAGW = SW + 4,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  job_v,
    output wire                  job_ready,
    input  wire [7:0]            window_count,
    input  wire [POS_W-1:0]      published_source_count,
    input  wire [4*SEC_W-1:0]    region_base_sector,
    input  wire [4*SEC_W-1:0]    region_sector_count,
    input  wire [KW-1:0]         id_count,
    input  wire                  id_done,
    output wire [KW-1:0]         id_idx,
    input  wire [KW-1:0]         id_rank_in,
    input  wire [POS_W-1:0]      id_gid,
    output reg                   o_v,
    input  wire                  o_ready,
    output reg  [KW-1:0]         o_rank,
    output reg  [POS_W-1:0]      o_gid,
    output reg  [2303:0]         o_row,
    output reg                   done,
    output reg                   fault,
    output reg  [2:0]            fault_code,
    output reg  [31:0]           st_owned_rows,
    output wire [NP-1:0]         m_v,
    input  wire [NP-1:0]         m_rdy,
    output wire [NP*HAW-1:0]     m_addr,
    output wire [NP*TAGW-1:0]    m_tag,
    input  wire [NP-1:0]         s_v,
    input  wire [NP*TAGW-1:0]    s_tag,
    input  wire [NP*4-1:0]       s_beat,
    input  wire [NP*256-1:0]     s_data
);
    reg run;
    reg [KW-1:0] cur;
    reg [7:0] wcount;
    assign job_ready = !run;
    assign id_idx = cur;

    // ---- entry register and dispatch ----
    reg e_v;
    reg [KW-1:0] e_rank;
    reg [POS_W-1:0] e_gid;
    wire [1:0] e_stack = e_gid[7:6];
    wire [POS_W-1:0] e_local = ((e_gid >> 8) << 4) | POS_W'(e_gid[3:0]);
    wire [LP-1:0] e_j = (P > 1) ? LP'(e_local) : '0;
    wire [$clog2(NP+1)-1:0] e_port = ($clog2(NP+1))'(32'(e_stack) * P + 32'(e_j));
    wire [SEC_W-1:0] e_base = region_base_sector[e_stack*SEC_W +: SEC_W];
    wire [SEC_W-1:0] e_cnt = region_sector_count[e_stack*SEC_W +: SEC_W];
    wire [SEC_W+4:0] e_a0 = (SEC_W+5)'(e_base) + (SEC_W+5)'(e_local) * (SEC_W+5)'(9);
    wire e_range_bad = e_gid >= published_source_count || e_gid >= POS_W'(MAX_CONTEXT) ||
                       ((SEC_W+5)'(e_base) + (SEC_W+5)'(e_cnt)) >= ((SEC_W+5)'(1) << SEC_W) ||
                       e_a0 + (SEC_W+5)'(9) > (SEC_W+5)'(e_base) + (SEC_W+5)'(e_cnt);
    wire owned = e_gid[5:4] == 2'(DIE_ID);
    wire [NP-1:0] p_free;                          // port has a free slot
    wire dispatch = run && e_v && owned && !e_range_bad && p_free[e_port];
    wire skip = run && e_v && !owned;
    wire eload = run && cur < id_count && (!e_v || dispatch || skip);

    // ---- ports ----
    wire [NP-1:0] p_busy_any, p_fault_rsp, p_fault_poison, p_ov;
    wire [NP-1:0] p_take;
    wire [NP*KW-1:0] p_rank;
    wire [NP*POS_W-1:0] p_gid;
    wire [NP*2304-1:0] p_row;
    genvar q;
    generate for (q = 0; q < NP; q = q + 1) begin : g_port
        ot_chip_v41x_ckv_pc_port #(.S(S), .POS_W(POS_W), .HAW(HAW), .K(K), .SRAM_MACRO(SRAM_MACRO)) u_port (
            .clk(clk), .rst_n(rst_n), .run(run),
            .d_v(dispatch && e_port == q), .d_rank(e_rank), .d_gid(e_gid), .d_a0(HAW'(e_a0)), .d_free(p_free[q]),
            .m_v(m_v[q]), .m_rdy(m_rdy[q]), .m_addr(m_addr[q*HAW +: HAW]), .m_tag(m_tag[q*TAGW +: TAGW]),
            .s_v_in(s_v[q]), .s_tag_in(s_tag[q*TAGW +: TAGW]), .s_beat_in(s_beat[q*4 +: 4]),
            .s_data_in(s_data[q*256 +: 256]),
            .o_v(p_ov[q]), .o_take(p_take[q]), .o_rank(p_rank[q*KW +: KW]), .o_gid(p_gid[q*POS_W +: POS_W]),
            .o_row(p_row[q*2304 +: 2304]), .busy_any(p_busy_any[q]), .fault_rsp(p_fault_rsp[q]),
            .fault_poison(p_fault_poison[q]));
    end endgenerate

    // ---- registered two-level output select: 4 ports -> stack register -> output ----
    reg [3:0] sv;
    reg [KW-1:0] srank [0:3];
    reg [POS_W-1:0] sgid [0:3];
    reg [2303:0] srow [0:3];
    reg [LP-1:0] rr1 [0:3];
    reg [1:0] rr2;
    wire [3:0] s_take;
    reg [NP-1:0] take1;
    reg [LP-1:0] pick1 [0:3];
    reg [3:0] have1;
    integer st, k1, idx;
    always @(*) begin
        take1 = 0;
        for (st = 0; st < 4; st = st + 1) begin
            have1[st] = 1'b0; pick1[st] = 0;
            for (k1 = 0; k1 < P; k1 = k1 + 1) begin
                idx = (32'(rr1[st]) + k1) % P;
                if (!have1[st] && p_ov[st*P + idx]) begin have1[st] = 1'b1; pick1[st] = LP'(idx); end
            end
            if (have1[st] && (!sv[st] || s_take[st])) take1[st*P + 32'(pick1[st])] = 1'b1;
        end
    end
    assign p_take = take1;
    reg have2;
    reg [1:0] pick2;
    always @(*) begin
        have2 = 1'b0; pick2 = 0;
        for (k1 = 0; k1 < 4; k1 = k1 + 1) begin
            idx = (32'(rr2) + k1) % 4;
            if (!have2 && sv[idx]) begin have2 = 1'b1; pick2 = 2'(idx); end
        end
    end
    wire go2 = have2 && (!o_v || o_ready);
    assign s_take = go2 ? (4'b1 << pick2) : 4'b0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sv <= 0; rr2 <= 0; o_v <= 0; o_rank <= 0; o_gid <= 0;
            for (st = 0; st < 4; st = st + 1) rr1[st] <= 0;
        end else begin
            for (st = 0; st < 4; st = st + 1) begin
                if (take1 != 0 && |take1[st*P +: P]) begin
                    sv[st] <= 1'b1;
                    srank[st] <= p_rank[(st*P + 32'(pick1[st]))*KW +: KW];
                    sgid[st] <= p_gid[(st*P + 32'(pick1[st]))*POS_W +: POS_W];
                    srow[st] <= p_row[(st*P + 32'(pick1[st]))*2304 +: 2304];
                    rr1[st] <= LP'((32'(pick1[st]) + 1) % P);
                end else if (s_take[st]) sv[st] <= 1'b0;
            end
            if (go2) begin
                o_v <= 1'b1; o_rank <= srank[pick2]; o_gid <= sgid[pick2]; o_row <= srow[pick2];
                rr2 <= 2'((32'(pick2) + 1) % 4);
            end else if (o_ready) o_v <= 1'b0;
        end
    end

    // ---- job ----
`ifndef SYNTHESIS
    initial if (P < 1 || (P & (P - 1)) != 0 || S < 1 || S * 9 > 256 || (SRAM_MACRO && S * 9 > 256))
        $fatal(1, "wide CKV fetch parameter contract failed");
`endif
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; cur <= 0; wcount <= 0; e_v <= 0; e_rank <= 0; e_gid <= 0;
            done <= 0; fault <= 0; fault_code <= 0; st_owned_rows <= 0;
        end else begin
            if (|p_fault_rsp) begin fault <= 1; fault_code[1] <= 1; end
            if (|p_fault_poison) begin fault <= 1; fault_code[2] <= 1; end
            if (run && e_v && owned && e_range_bad) begin fault <= 1; fault_code[0] <= 1; end
            if (job_v && !run) begin
                run <= 1; cur <= 0; wcount <= window_count; done <= 0; e_v <= 0; st_owned_rows <= 0;
            end else if (run) begin
                if (eload) begin
                    e_v <= 1; e_rank <= id_rank_in; e_gid <= id_gid; cur <= cur + 1'b1;
                end else if (dispatch || skip) e_v <= 0;
                if (dispatch) st_owned_rows <= st_owned_rows + 1;
                if (cur == id_count && id_done && !e_v && p_busy_any == 0 && sv == 0 && !o_v) begin
                    run <= 0; done <= 1;
                end
            end
        end
    end
endmodule
