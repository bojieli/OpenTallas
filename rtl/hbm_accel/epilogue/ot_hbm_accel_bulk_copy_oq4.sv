`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_bulk_copy_oq4: ot_hbm_accel_bulk_copy (ENABLE = 1, SRAM_RING = 1, RING_MACRO = 1, the DS SM's
// configuration) with the output-queue pop taken out of the take loop, for the hierarchical SM element's front
// (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv). The original file is pinned by records and stays byte-identical.
//
// Original: take = head_full & (room | pop): the stream's pop (s_valid && s_ready, s_ready from the issue) fans out
// combinationally to every take copy, the ring pointers, the space / credit flags and the full-bit clear selects;
// in the 1.1 mm front this was the routed limiter (post-CTS -1.0 ns at SS, both densities).
// Here: the output queue has FOUR entries and take = head_full & room, both registered kept copies; room is
// "reserved entries < 4" made from the next-state count (which still subtracts this cycle's pop), so it is exact,
// not conservative: in the steady stream two reads are in flight and one line waits (3 reserved), so one line a
// cycle still leaves the ring. The pop only touches the queue's own count and read pointer.
// Same request / tag / order / data contract; the stream's line order is unchanged. Timing differs only under
// downstream back-pressure (one more line decoupled).
// ---------------------------------------------------------------------------
module ot_hbm_accel_bulk_copy_oq4 #(
    parameter integer ENABLE = 0,
    parameter integer LINE_BITS = 1024,     // 128 B, the SM's ingest per cycle
    parameter integer DEPTH     = 1024,     // staging lines (128 KB)
    parameter integer MAX_OUT   = 512,      // outstanding reads (tracker entries)
    parameter integer AW        = 32,       // line address
    parameter integer DQ        = 4,        // descriptor queue
    parameter integer SRAM_RING = 0,        // 1: the ring is LINE_BITS/256 hard SRAM macros (1024 deep)
    parameter integer RING_MACRO = 0        // ENABLE=1, SRAM_RING=1: 0 = one group of 1024x256 macros read every
                                            // cycle (SS clk->q 692 ps: one-cycle capture cannot meet 1.2 GHz SS);
                                            // 1 = even/odd slot groups of 512x256 macros, each read at most every
                                            // other cycle, captured two cycles after the read (DEPTH = 1024; the
                                            // 1.2 GHz SS configuration, multicycle constraint ot_hbm_accel_bulk_copy_mc2.sdc)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // descriptors
    input  wire                  d_valid,
    output wire                  d_ready,
    input  wire [AW-1:0]         d_base,
    input  wire [23:0]           d_lines,
    // read requests to the NoC / HBM controller
    output wire                  req_v,
    input  wire                  req_ready,
    output wire [AW-1:0]         req_addr,
    output wire [$clog2(DEPTH)-1:0] req_tag,
    // responses, any order
    input  wire                  rsp_v,
    input  wire [$clog2(DEPTH)-1:0] rsp_tag,
    input  wire [LINE_BITS-1:0]  rsp_data,
    // in-order stream to the tensor core
    output wire                  s_valid,
    input  wire                  s_ready,
    output wire [LINE_BITS-1:0]  s_data,
    output reg  [$clog2(MAX_OUT+1)-1:0] outstanding,
    output wire                  idle
);
    // the DS SM configuration only (ENABLE = 1, SRAM_RING = 1, RING_MACRO = 1); other values are not supported
    generate if (1) begin : g_lookahead
    // Look-ahead successor (HA3; retimed 2026-10-04 for 1.2 GHz SS). Same request/tag/order/data
    // contract and cycle behaviour as the original; the clock-limited loops are cut by:
    //  * head/next full flags carried in registers (no DEPTH:1 full-bit mux behind take); the
    //    look-ahead mux is addressed by registered next_slot/next2_slot;
    //  * full-bit set and clear both applied one edge late from registered, pre-decoded
    //    (32 x 32 one-hot) slot selects, so neither take nor the response tag fans out to DEPTH
    //    flops; the late set is covered by matching the registered response in the look-ahead;
    //  * request eligibility (active, ring space, outstanding credit) and the take condition (head
    //    full, output-queue room) as registered flags with next-state look-ahead, each held in
    //    several keep_hierarchy copies (ot_hbm_accel_bc_kreg) so every consumer group -- address,
    //    length, ring pointers, counters, each SRAM macro -- has its own local issue / take;
    //    the copies are bit-identical, so the cycle behaviour is unchanged;
    //  * the SRAM output queue is a three-entry queue written through per-64-bit registered write
    //    enables, read through a registered pointer.
    localparam integer TW = $clog2(DEPTH);
    localparam integer QW = (DQ <= 1) ? 1 : $clog2(DQ);
    localparam integer LO = TW / 2;                 // pre-decode split of a slot index
    localparam integer HI = TW - LO;
    localparam integer NBM = (LINE_BITS + 255) / 256;   // SRAM macros (when SRAM_RING)
    // issue groups: 0 req_v/act/last/descriptor queue, 1 a_addr low, 2 a_addr high, 3 a_left,
    // 4 alloc_p/ring-space flag, 5 outstanding/credit flag
    localparam integer NG = 6;
    // take groups: 0 cons_p/next slots/clear selects, 1 bank pointers, 2 head/next flags,
    // ring-space flag, output queue; 3.. one per SRAM macro read enable
    localparam integer NT = 3 + NBM;
    // ---- descriptor queue ----
    reg [AW-1:0] q_base [0:DQ-1];
    reg [23:0]   q_len  [0:DQ-1];
    reg [QW:0]   q_cnt;
    reg [QW-1:0] q_wp, q_rp;
    assign d_ready = (q_cnt < DQ);
    // ---- active descriptor ----
    reg [AW-1:0] a_addr;
    reg [23:0]   a_left;
    reg          last_q;                            // a_left == 1
    // ---- staging ring ----
    reg [DEPTH-1:0]     full;
    reg [TW:0]          alloc_p, cons_p;            // one extra bit: ring occupancy = alloc - cons
    reg  [TW:0]         used;                       // ring occupancy alloc_p - cons_p, kept as its own counter
    wire [NG-1:0] act_c, free_c, cred_c;            // copies: act ; used < DEPTH ; outstanding < MAX_OUT
    wire [NG-1:0] issue_c = act_c & free_c & cred_c & {NG{req_ready}};
    wire act = act_c[0];
    assign req_v = act_c[0] && free_c[0] && cred_c[0];
    assign req_addr = a_addr;
    assign req_tag = alloc_p[TW-1:0];
    wire [TW-1:0] cslot = cons_p[TW-1:0];
    wire [NT-1:0] hf_c;                             // copies of head_full
    wire [NT-1:0] rok_c;                            // copies of "output queue has room" (SRAM ring)
    wire pop_o;                                     // the output stream pops this cycle
    wire [NT-1:0] take_c = hf_c & rok_c;                    // a line leaves the ring this cycle (no pop term)
    wire take = take_c[0];
    wire head_full = hf_c[2];
    (* keep *) wire [TW:0] alloc_inc; assign alloc_inc = alloc_p + 1'b1;
    (* keep *) wire [TW:0] cons_inc;  assign cons_inc = cons_p + 1'b1;
    (* keep *) wire [TW:0] used_inc;  assign used_inc = used + 1'b1;
    (* keep *) wire [TW:0] used_dec;  assign used_dec = used - 1'b1;
    // address / remaining-line counters: an 8-bit low part steps on issue; the high part's
    // +1 / -1 is a register recomputed every cycle (or loaded with the descriptor), used only on
    // a low-part wrap, which is >= 256 issues after the high part last changed
    reg [AW-9:0] addr_hi_inc; reg [15:0] left_hi_dec;
    reg [AW-9:0] q_base_hinc [0:DQ-1]; reg [15:0] q_len_hdec [0:DQ-1];   // high-part +1/-1 made at enqueue
    reg [DQ-1:0] q_nz, q_one;                         // length != 0, length == 1, made at enqueue
    wire qne = (q_cnt != 0);
    wire [NG-1:0] load_c = ~act_c & {NG{qne}};
    wire load = load_c[0];
    localparam integer OW = $clog2(MAX_OUT+1);
    (* keep *) wire [OW-1:0] out_inc; assign out_inc = outstanding + 1'b1;
    (* keep *) wire [OW-1:0] out_dec; assign out_dec = outstanding - 1'b1;
    // look-ahead candidates for the eligibility flags, from registers only
    wire free_up = (used + 1'b1 < DEPTH), free_eq = (used < DEPTH), free_dn = (used - 1'b1 < DEPTH);
    wire cred_up = (outstanding + 1 < MAX_OUT), cred_eq = (outstanding < MAX_OUT), cred_dn = (outstanding - 1 < MAX_OUT);
    reg next_full;
    reg [TW-1:0] next_slot, next2_slot;
    (* keep *) wire [TW-1:0] n2_inc; assign n2_inc = next2_slot + 1'b1;
    reg rsp_q; reg [TW-1:0] rsp_tag_q;
    reg [(1<<HI)-1:0] set_hi, clr_hi; reg [(1<<LO)-1:0] set_lo, clr_lo;
    // next states of the duplicated flags
    reg act_nx, free_nx, cred_nx, hf_nx;
    always @* begin
        act_nx = load ? q_nz[q_rp] : (issue_c[0] && last_q) ? 1'b0 : act_c[0];
        case ({issue_c[4], take_c[2]})
            2'b10: free_nx = free_up;
            2'b01: free_nx = free_dn;
            default: free_nx = free_eq;
        endcase
        case ({issue_c[5], rsp_q})
            2'b10: cred_nx = cred_up;
            2'b01: cred_nx = cred_dn;
            default: cred_nx = cred_eq;
        endcase
        if (take_c[2]) hf_nx = next_full || (rsp_v && rsp_tag == next_slot);
        else hf_nx = head_full || (rsp_v && rsp_tag == cslot);
    end
    ot_hbm_accel_bc_kreg #(.W(NG), .RV({NG{1'b0}})) u_act_c (.clk(clk), .rst_n(rst_n), .d({NG{act_nx}}), .q(act_c));
    ot_hbm_accel_bc_kreg #(.W(NG), .RV({NG{1'b1}})) u_free_c (.clk(clk), .rst_n(rst_n), .d({NG{free_nx}}), .q(free_c));
    ot_hbm_accel_bc_kreg #(.W(NG), .RV({NG{MAX_OUT > 0}})) u_cred_c (.clk(clk), .rst_n(rst_n), .d({NG{cred_nx}}), .q(cred_c));
    ot_hbm_accel_bc_kreg #(.W(NT), .RV({NT{1'b0}})) u_hf_c (.clk(clk), .rst_n(rst_n), .d({NT{hf_nx}}), .q(hf_c));
    // Banked look-ahead: slots are consumed in order, so bank b (slot mod NBK) next needs the full
    // bit of its own in-order slot bank_ptr[b]; bank_full[b] registers full[bank_ptr[b]] every cycle
    // through a DEPTH/NBK:1 mux. bank_ptr[b] steps once per NBK takes and is next read as next2
    // >= NBK-2 cycles later. bank_full lags a response by three edges (late set + register), so the
    // look-ahead also matches the responses of the last two cycles.
    localparam integer NBK = 8;
    localparam integer BB = 3;
    reg [TW-BB-1:0] bank_ptr [0:NBK-1];
    reg [NBK-1:0] bank_full;
    reg rsp_qq; reg [TW-1:0] rsp_tag_qq;
    integer bk;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (bk = 0; bk < NBK; bk = bk + 1) bank_ptr[bk] <= 0;
            bank_full <= 0; rsp_qq <= 0; rsp_tag_qq <= 0;
        end else begin
            rsp_qq <= rsp_q; rsp_tag_qq <= rsp_tag_q;
            for (bk = 0; bk < NBK; bk = bk + 1) begin
                bank_full[bk] <= full[{bank_ptr[bk], bk[BB-1:0]}];
                if (take_c[1] && cslot[BB-1:0] == bk) bank_ptr[bk] <= bank_ptr[bk] + 1'b1;
            end
        end
    end
    integer k, kf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_slot <= 1; next2_slot <= 2; rsp_q <= 0; rsp_tag_q <= 0;
            set_hi <= 0; set_lo <= 0; clr_hi <= 0; clr_lo <= 0;
        end else begin
            if (take_c[0]) begin next_slot <= next2_slot; next2_slot <= n2_inc; end
            rsp_q <= rsp_v; rsp_tag_q <= rsp_tag;
            for (k = 0; k < (1<<HI); k = k + 1) begin
                set_hi[k] <= rsp_v && (rsp_tag[TW-1:LO] == k);
                clr_hi[k] <= take_c[0] && (cslot[TW-1:LO] == k);
            end
            for (k = 0; k < (1<<LO); k = k + 1) begin
                set_lo[k] <= (rsp_tag[LO-1:0] == k);
                clr_lo[k] <= (cslot[LO-1:0] == k);
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) next_full <= 0;
        else if (take_c[2])
            next_full <= bank_full[next2_slot[BB-1:0]] || (rsp_v && rsp_tag == next2_slot)
                      || (rsp_q && rsp_tag_q == next2_slot) || (rsp_qq && rsp_tag_qq == next2_slot);
        else if (rsp_v && rsp_tag == next_slot) next_full <= 1;
    end
    if (1) begin : g_sram
        // hard macros: the read lands two edges after the take (read latency 2) in a three-entry
        // queue, which keeps one line a cycle. +1 cycle from take to the stream output against the
        // original. RING_MACRO = 0: an unconditional capture register one edge after the read,
        // then the queue. RING_MACRO = 1: slot s lives in group s[0] (512 deep, address s >> 1);
        // consecutive takes alternate groups, so a group is read at most every other edge and its
        // output holds for two cycles: the queue entry captures it directly (a two-cycle path).
        localparam integer NB = NBM;
        localparam integer NW = NB * 4;            // 64-bit write-enable domains of the output queue
        localparam integer NG2 = (RING_MACRO == 0) ? 1 : 2;
        wire [NB*256-1:0] rd [0:NG2-1];
        wire [NB*256-1:0] wpad = {{(NB*256-LINE_BITS){1'b0}}, rsp_data};
        wire [NB*256-1:0] qin;                    // the line the queue entry captures
        reg [NB*256-1:0] oq0, oq1, oq2, oq3;
        reg [2:0] oq_n, res;                          // res = oq_n + rd_v + rd_v2 (entries reserved), <= 4
        reg [1:0] oq_wp, oq_rp;
        reg rd_v, rd_v2;
        assign pop_o = s_valid && s_ready;
        wire [2:0] res_nx = res + (take_c[2] ? 3'd1 : 3'd0) - (pop_o ? 3'd1 : 3'd0);
        ot_hbm_accel_bc_kreg #(.W(NT), .RV({NT{1'b1}})) u_rok_c (.clk(clk), .rst_n(rst_n),
            .d({NT{res_nx != 3'd4}}), .q(rok_c));
        genvar mb, gg;
        if (1) begin : g_m2
            // read group = the slot's parity, carried with the take for two edges (per-64-bit copies)
            wire [NW-1:0] par2;
            reg par1;
            always @(posedge clk or negedge rst_n) if (!rst_n) par1 <= 1'b0; else par1 <= cslot[0];
            ot_hbm_accel_bc_kreg #(.W(NW), .RV({NW{1'b0}})) u_par2 (.clk(clk), .rst_n(rst_n), .d({NW{par1}}), .q(par2));
            for (gg = 0; gg < 2; gg = gg + 1) begin : g_grp
                for (mb = 0; mb < NB; mb = mb + 1) begin : g_mb
                    ot_sram_1r1w_512x256_m1_r2c2 u_ring (
                        .clk(clk), .r_ce_in(take_c[3+mb] && cslot[0] == gg), .r_addr_in(cslot[TW-1:1]),
                        .rd_out(rd[gg][256*mb +: 256]),
                        .w_ce_in(rsp_v && rsp_tag[0] == gg), .w_addr_in(rsp_tag[TW-1:1]),
                        .wd_in(wpad[256*mb +: 256]), .w_mask_in({256{1'b1}}),
                        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
                end
            end
            for (mb = 0; mb < NW; mb = mb + 1) begin : g_sel
                assign qin[64*mb +: 64] = par2[mb] ? rd[1][64*mb +: 64] : rd[0][64*mb +: 64];
            end
        end
        // registered write-enable copies, one per 64-bit domain: we<k> = rd_v2 next cycle AND write pointer == k.
        // Each macro slice (4 domains) keeps its own copy of the read-valid pipe and write pointer, stepped by the
        // slice's own take copy, so no single cone fans out along the macro column (bit-identical copies).
        wire [NW-1:0] we0, we1, we2, we3;
        wire [1:0] wp_nx = rd_v2 ? oq_wp + 2'd1 : oq_wp;
        genvar sl;
        for (sl = 0; sl < NB; sl = sl + 1) begin : g_wsl
            wire rdv_s, rdv2_s; wire [1:0] wp_s;
            wire [1:0] wpn_s = rdv2_s ? wp_s + 2'd1 : wp_s;
            ot_hbm_accel_bc_kreg #(.W(1), .RV(1'b0)) u_rdv (.clk(clk), .rst_n(rst_n), .d(take_c[3+sl]), .q(rdv_s));
            ot_hbm_accel_bc_kreg #(.W(1), .RV(1'b0)) u_rdv2 (.clk(clk), .rst_n(rst_n), .d(rdv_s), .q(rdv2_s));
            ot_hbm_accel_bc_kreg #(.W(2), .RV(2'd0)) u_wp (.clk(clk), .rst_n(rst_n), .d(wpn_s), .q(wp_s));
            ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u_we0 (.clk(clk), .rst_n(rst_n), .d({4{rdv_s && wpn_s == 2'd0}}), .q(we0[4*sl +: 4]));
            ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u_we1 (.clk(clk), .rst_n(rst_n), .d({4{rdv_s && wpn_s == 2'd1}}), .q(we1[4*sl +: 4]));
            ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u_we2 (.clk(clk), .rst_n(rst_n), .d({4{rdv_s && wpn_s == 2'd2}}), .q(we2[4*sl +: 4]));
            ot_hbm_accel_bc_kreg #(.W(4), .RV(4'd0)) u_we3 (.clk(clk), .rst_n(rst_n), .d({4{rdv_s && wpn_s == 2'd3}}), .q(we3[4*sl +: 4]));
        end
        // the stream read select: one-hot read-pointer copies, one per 32-bit slice of the line (32 loads each)
        localparam integer NS = (LINE_BITS + 31) / 32;
        wire [1:0] rp_nx = pop_o ? oq_rp + 2'd1 : oq_rp;
        wire [4*NS-1:0] rpo;
        ot_hbm_accel_bc_kreg #(.W(4*NS), .RV({NS{4'b0001}})) u_rpo (.clk(clk), .rst_n(rst_n),
            .d({NS{rp_nx == 2'd3, rp_nx == 2'd2, rp_nx == 2'd1, rp_nx == 2'd0}}), .q(rpo));
        genvar rs;
        for (rs = 0; rs < NS; rs = rs + 1) begin : g_rs
            localparam integer LO_B = 32 * rs;
            localparam integer WB = (LINE_BITS - LO_B < 32) ? LINE_BITS - LO_B : 32;
            assign s_data[LO_B +: WB] = ({WB{rpo[4*rs]}} & oq0[LO_B +: WB]) | ({WB{rpo[4*rs+1]}} & oq1[LO_B +: WB]) |
                                        ({WB{rpo[4*rs+2]}} & oq2[LO_B +: WB]) | ({WB{rpo[4*rs+3]}} & oq3[LO_B +: WB]);
        end
        assign s_valid = oq_n != 0;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                oq_n <= 0; res <= 0; rd_v <= 1'b0; rd_v2 <= 1'b0; oq_wp <= 0; oq_rp <= 0;
            end else begin
                rd_v <= take_c[2]; rd_v2 <= rd_v;
                oq_n <= oq_n - (pop_o ? 3'd1 : 3'd0) + (rd_v2 ? 3'd1 : 3'd0);
                res <= res_nx;
                oq_wp <= wp_nx;
                oq_rp <= rp_nx;
            end
        end
        for (mb = 0; mb < NW; mb = mb + 1) begin : g_oq
            always @(posedge clk) begin
                if (we0[mb]) oq0[64*mb +: 64] <= qin[64*mb +: 64];
                if (we1[mb]) oq1[64*mb +: 64] <= qin[64*mb +: 64];
                if (we2[mb]) oq2[64*mb +: 64] <= qin[64*mb +: 64];
                if (we3[mb]) oq3[64*mb +: 64] <= qin[64*mb +: 64];
            end
        end
        assign idle = !act && (q_cnt == 0) && (outstanding == 0) && !rsp_q && (used == 0) && (oq_n == 0) && !rd_v && !rd_v2;
    end
    // descriptor queue and active-descriptor registers, each group driven by its own issue / load copy
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q_cnt <= 0; q_wp <= 0; q_rp <= 0; last_q <= 1'b0;
        end else begin
            q_cnt <= q_cnt + (d_valid && d_ready ? 1 : 0) - (load ? 1 : 0);
            if (d_valid && d_ready) q_wp <= (q_wp == DQ - 1) ? 0 : q_wp + 1'b1;
            if (load) begin
                last_q <= q_one[q_rp];
                q_rp <= (q_rp == DQ - 1) ? 0 : q_rp + 1'b1;
            end else if (issue_c[0]) last_q <= (a_left == 24'd2);
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) a_addr[7:0] <= 0;
        else if (load_c[1]) a_addr[7:0] <= q_base[q_rp][7:0];
        else if (issue_c[1]) a_addr[7:0] <= a_addr[7:0] + 8'd1;
    end
    // high-part +1 in two registered halves; held for the edge after a load (the stage registers
    // then still hold the previous descriptor), whose value came pre-incremented from the queue
    localparam integer HW = AW - 8, HL = HW / 2;
    reg [HL:0] hi_lo1; reg [HW-HL-1:0] hi_hi1; reg load_d1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hi_lo1 <= 0; hi_hi1 <= 0; load_d1 <= 1'b0; end
        else begin
            hi_lo1 <= {1'b0, a_addr[8 +: HL]} + 1'b1; hi_hi1 <= a_addr[AW-1:8+HL]; load_d1 <= load_c[2];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_addr[AW-1:8] <= 0; addr_hi_inc <= 1; end
        else begin
            if (load_c[2]) addr_hi_inc <= q_base_hinc[q_rp];
            else if (!load_d1) addr_hi_inc <= {hi_lo1[HL] ? hi_hi1 + 1'b1 : hi_hi1, hi_lo1[HL-1:0]};
            if (load_c[2]) a_addr[AW-1:8] <= q_base[q_rp][AW-1:8];
            else if (issue_c[2] && a_addr[7:0] == 8'hff) a_addr[AW-1:8] <= addr_hi_inc;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_left <= 0; left_hi_dec <= 16'hffff; end
        else begin
            left_hi_dec <= load_c[3] ? q_len_hdec[q_rp] : a_left[23:8] - 1'b1;
            if (load_c[3]) a_left <= q_len[q_rp];
            else if (issue_c[3]) a_left <= {(a_left[7:0] == 8'h00) ? left_hi_dec : a_left[23:8], a_left[7:0] - 8'd1};
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            alloc_p <= 0; cons_p <= 0; used <= 0; outstanding <= 0; full <= {DEPTH{1'b0}};
        end else begin
            if (issue_c[4]) alloc_p <= alloc_inc;
            case ({issue_c[4], take_c[2]})
                2'b10: used <= used_inc;
                2'b01: used <= used_dec;
                default: ;
            endcase
            if (take_c[0]) cons_p <= cons_inc;
            case ({issue_c[5], rsp_q})
                2'b10: outstanding <= out_inc;
                2'b01: outstanding <= out_dec;
                default: ;
            endcase
            // one-edge-late clear and set from the registered pre-decoded selects; a set wins
            for (kf = 0; kf < DEPTH; kf = kf + 1)
                if (set_hi[kf >> LO] && set_lo[kf % (1<<LO)]) full[kf] <= 1'b1;
                else if (clr_hi[kf >> LO] && clr_lo[kf % (1<<LO)]) full[kf] <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (d_valid && d_ready) begin q_base[q_wp] <= d_base; q_len[q_wp] <= d_lines;
            q_base_hinc[q_wp] <= d_base[AW-1:8] + 1'b1; q_len_hdec[q_wp] <= d_lines[23:8] - 1'b1;
            q_nz[q_wp] <= (d_lines != 0); q_one[q_wp] <= (d_lines == 24'd1); end
    end
    end endgenerate
endmodule
