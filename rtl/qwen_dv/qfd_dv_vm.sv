`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_vm -- the Q-DV slice's local memories (vector memory slice, constant memory, BF16 table, SU program store).
//
// Every array is the SAME 1R1W macro family the central VM uses (qvm_su_bank_native: ot_sram_1r1w_1024x256_m2_r2c2);
// one 256-b macro word = 8 FP32 = one SU vector of the 8-lane slice.  Fixed-latency, no ready / credit: every read
// answers exactly 2 edges after the lane's request register (macro read edge + one capture flop at the macro pins =
// ot_hdc_vstream_lane ML = 1); a schedule violation (operand vector spanning two words, read address outside the
// array, two writers in one bank on one edge, malformed table write) raises the sticky `fault`, never a stall.
//
//   Same-row read and write on one edge: the macro read is gated off (1R1W macros do not define it); the lane
//   operand of that edge is then the previous read word.  The SU issues reads for operands an op does not use
//   (vb/vc with ma/ad bypassing them), so this is legal; a CONSUMED operand on the row being written is a compiler
//   schedule error, exactly as in the central VM.
//   VM    3 operand replicas (A, B, C: one read port each) x 2 banks (element bit 3) x 1024 words x 8 FP32
//         = 16,384 FP32 per replica.  Every write goes to all three replicas.  Element e: bank e[3], word e[13:4],
//         lane e[2:0].  Write sources: SU lanes (8 el, one bank), 16-el words (station / AR return / D2D return:
//         both banks), single elements (reducer, scalar-tree r, root total).
//   CROM  2 banks x {lo, hi} x 1024 x 8 x 32 b = 16,384 (lo, hi) FP32 pairs (gamma / QK gains: lo; RoPE: lo = cos,
//         hi = sin).  Per-lane reads as the VM; written 16 pairs per edge by a stream table word.
//   BTAB  BF16 table (row scales; the SU weight-ROM operand port): 2 copies (station port, SU port) x 4 banks
//         (word bit [1:0]) x 128 x 256 b = 512 words x 16 BF16 = 8,192 BF16 per copy; written 4 words per edge.
//   PROG  SU instruction store: 2 banks (pidx bit 0) x 256 x 457 b (2 macros of 256 wide each) = 512 instructions;
//         written 2 instructions per edge.
// MUT (bench negative controls): 4 = CROM lo / hi swapped (cos <-> sin, gain <-> 0); 5 = the B operand port answers
// with the C replica's word (both must FAIL).
// =====================================================================================================================
module qfd_dv_vm #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // SU operand reads: per lane request (registered in the lane), answer 2 edges later
    input  wire [7:0]    a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]    cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    // BF16 table: SU weight-ROM port (word = element >> 4) and station scale port (word address)
    input  wire          bs_re,
    input  wire [23:0]   bs_addr,            // word index (element >> 4)
    output wire [255:0]  bs_q,
    input  wire          bt_re,
    input  wire [8:0]    bt_word,
    output wire [255:0]  bt_q,
    // SU program store
    input  wire          p_re,
    input  wire [8:0]    p_idx,
    output wire [456:0]  p_q,
    // writes (VM window addresses only: the slice top routes other windows elsewhere)
    input  wire [7:0]    su_we,
    input  wire [8*24-1:0] su_waddr,
    input  wire [8*32-1:0] su_wdata,
    input  wire          w16_we,
    input  wire [23:0]   w16_addr,
    input  wire [511:0]  w16_data,
    input  wire          w1_we,
    input  wire [23:0]   w1_addr,
    input  wire [31:0]   w1_data,
    // table writes from the stream tap: kind 1 CROM (16 pairs at 16-pair word tw_addr), 2 BTAB (4 words at 4-aligned
    // word tw_addr), 3 PROG (2 instructions at even pidx tw_addr)
    input  wire          tw_we,
    input  wire [1:0]    tw_kind,
    input  wire [23:0]   tw_addr,
    input  wire [1023:0] tw_data,
    output reg           fault
);
    integer l;
    // ------------------------------------------------------------------ read-side address check (lane 0 = reference)
    function automatic bad_vec(input [7:0] re, input [8*24-1:0] ad);
        integer k;
        begin
            bad_vec = 1'b0;
            for (k = 0; k < 8; k = k + 1)
                if (re[k] && (ad[24*k+4 +: 20] != ad[4 +: 20])) bad_vec = 1'b1;   // all lanes in lane 0's 16-el pair
            for (k = 0; k < 8; k = k + 1)
                if (re[k] && (ad[24*k+3] != ad[3])) bad_vec = 1'b1;               // ... and in lane 0's 8-el word
            if (re[0] && (ad[23:14] != 10'd0)) bad_vec = 1'b1;                    // VM window, inside 16,384 elements
            if (re != 8'd0 && !re[0]) bad_vec = 1'b1;                             // live lanes are a prefix from lane 0
        end
    endfunction
    // ------------------------------------------------------------------ VM: 3 replicas x 2 banks
    // write merge per bank (combinational from the registered sources; the macro samples next edge)
    reg  [1:0]   wb_we;
    reg  [9:0]   wb_row [0:1];
    reg  [255:0] wb_d [0:1], wb_m [0:1];
    reg          w_coll, w_bad;
    integer b;
    always @(*) begin
        w_coll = 1'b0; w_bad = 1'b0;
        for (b = 0; b < 2; b = b + 1) begin
            wb_we[b] = 1'b0; wb_row[b] = 10'd0; wb_d[b] = 256'd0; wb_m[b] = 256'd0;
        end
        // single element
        if (w1_we) begin
            if (w1_addr[23:14] != 10'd0) w_bad = 1'b1;
            wb_we[w1_addr[3]] = 1'b1; wb_row[w1_addr[3]] = w1_addr[13:4];
            wb_d[w1_addr[3]][32*w1_addr[2:0] +: 32] = w1_data;
            wb_m[w1_addr[3]][32*w1_addr[2:0] +: 32] = 32'hFFFF_FFFF;
        end
        // SU lanes (one 8-el word)
        if (su_we != 8'd0) begin
            for (l = 0; l < 8; l = l + 1)
                if (su_we[l] && (su_waddr[24*l+3 +: 21] != su_waddr[24*0+3 +: 21] || !su_we[0])) w_bad = 1'b1;
            if (su_waddr[23:14] != 10'd0) w_bad = 1'b1;
            if (wb_we[su_waddr[3]]) w_coll = 1'b1;
            wb_we[su_waddr[3]] = 1'b1; wb_row[su_waddr[3]] = su_waddr[13:4];
            wb_m[su_waddr[3]] = 256'd0; wb_d[su_waddr[3]] = 256'd0;
            for (l = 0; l < 8; l = l + 1)
                if (su_we[l]) begin
                    wb_d[su_waddr[3]][32*su_waddr[24*l +: 3] +: 32] = su_wdata[32*l +: 32];
                    wb_m[su_waddr[3]][32*su_waddr[24*l +: 3] +: 32] = 32'hFFFF_FFFF;
                end
        end
        // 16-element word (both banks)
        if (w16_we) begin
            if (w16_addr[3:0] != 4'd0 || w16_addr[23:14] != 10'd0) w_bad = 1'b1;
            if (wb_we != 2'b00) w_coll = 1'b1;
            for (b = 0; b < 2; b = b + 1) begin
                wb_we[b] = 1'b1; wb_row[b] = w16_addr[13:4];
                wb_d[b] = w16_data[256*b +: 256]; wb_m[b] = {256{1'b1}};
            end
        end
    end
    // read requests: lane 0's word, bank; per-lane element offsets travel to the capture stage
    wire [2:0] rq_re = {c_re[0], b_re[0], a_re[0]};
    wire [24*3-1:0] rq_a0 = {c_addr[23:0], b_addr[23:0], a_addr[23:0]};
    wire [3*256*2-1:0] vm_rd;                 // [op][bank]
    genvar op, bk;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rep
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
            ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck),
                .r_ce_in(rq_re[op] && rq_a0[24*op+3] == bk[0] && !(wb_we[bk] && wb_row[bk] == rq_a0[24*op+4 +: 10])),
                .r_addr_in(rq_a0[24*op+4 +: 10]),
                .rd_out(vm_rd[(2*op+bk)*256 +: 256]),
                .w_ce_in(wb_we[bk]), .w_addr_in(wb_row[bk]), .wd_in(wb_d[bk]), .w_mask_in(wb_m[bk]),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    // stage 1 (macro read edge): bank + lane offsets; stage 2: capture flops at the macro pins
    reg  [2:0]    s1_bank;
    reg  [3*24-1:0] s1_off;                    // [op][lane] 3-bit offsets
    reg  [3*512-1:0] cap;                       // [op] both banks' words captured
    reg  [2:0]    s2_bank;
    reg  [3*24-1:0] s2_off;
    always @(posedge ck) begin
        s1_bank <= {c_addr[3], b_addr[3], a_addr[3]};
        for (l = 0; l < 8; l = l + 1) begin
            s1_off[3*l +: 3]      <= a_addr[24*l +: 3];
            s1_off[24 + 3*l +: 3] <= b_addr[24*l +: 3];
            s1_off[48 + 3*l +: 3] <= c_addr[24*l +: 3];
        end
        cap <= vm_rd;
        s2_bank <= s1_bank; s2_off <= s1_off;
    end
    wire [255:0] wa = s2_bank[0] ? cap[256*1 +: 256] : cap[256*0 +: 256];
    wire [255:0] wbq = s2_bank[1] ? cap[256*3 +: 256] : cap[256*2 +: 256];
    wire [255:0] wc = s2_bank[2] ? cap[256*5 +: 256] : cap[256*4 +: 256];
    wire [255:0] wb_sel = (MUT == 5) ? wc : wbq;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_ext
        assign a_q[32*gl +: 32] = wa[32*s2_off[3*gl +: 3] +: 32];
        assign b_q[32*gl +: 32] = wb_sel[32*s2_off[24 + 3*gl +: 3] +: 32];
        assign c_q[32*gl +: 32] = wc[32*s2_off[48 + 3*gl +: 3] +: 32];
    end endgenerate
    // ------------------------------------------------------------------ CROM: 2 banks x {lo, hi}
    wire [4*256-1:0] cr_rd;                   // [bank][lo/hi]
    reg  [255:0] cw_lo [0:1], cw_hi [0:1];
    always @(*) begin
        for (b = 0; b < 2; b = b + 1)
            for (l = 0; l < 8; l = l + 1) begin
                cw_lo[b][32*l +: 32] = tw_data[64*(8*b+l) +: 32];
                cw_hi[b][32*l +: 32] = tw_data[64*(8*b+l) + 32 +: 32];
            end
    end
    wire cr_w = tw_we && tw_kind == 2'd1;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crom
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_lo[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk+1)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_hi[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg        c1_bank, c2_bank;
    reg [23:0] c1_off, c2_off;
    reg [1023:0] ccap;
    always @(posedge ck) begin
        c1_bank <= cr_addr[3];
        for (l = 0; l < 8; l = l + 1) c1_off[3*l +: 3] <= cr_addr[24*l +: 3];
        ccap <= cr_rd; c2_bank <= c1_bank; c2_off <= c1_off;
    end
    wire [255:0] clo = c2_bank ? ccap[256*2 +: 256] : ccap[256*0 +: 256];
    wire [255:0] chi = c2_bank ? ccap[256*3 +: 256] : ccap[256*1 +: 256];
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_cext
        wire [31:0] lo_e = clo[32*c2_off[3*gl +: 3] +: 32], hi_e = chi[32*c2_off[3*gl +: 3] +: 32];
        assign cr_q[64*gl +: 64] = (MUT == 4) ? {lo_e, hi_e} : {hi_e, lo_e};
    end endgenerate
    // ------------------------------------------------------------------ BTAB: 2 copies x 4 banks x 128 x 256
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [8:0] bs_word = bs_addr[8:0];        // the lane's weight-ROM word index (lane: cura >> log2(WR))
    wire [2*4*256-1:0] bt_rd;
    genvar cp;
    generate for (cp = 0; cp < 2; cp = cp + 1) begin : g_btc
        wire       re = (cp == 0) ? bt_re : bs_re;
        wire [8:0] wd = (cp == 0) ? bt_word : bs_word;
        for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(re && wd[1:0] == bk[1:0]), .r_addr_in(wd[8:2]),
                .rd_out(bt_rd[(4*cp+bk)*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
                .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    reg [1:0] t1_bank, t2_bank, s1b_bank, s2b_bank;
    reg [2047:0] btcap;
    always @(posedge ck) begin
        t1_bank <= bt_word[1:0]; s1b_bank <= bs_word[1:0];
        btcap <= bt_rd; t2_bank <= t1_bank; s2b_bank <= s1b_bank;
    end
    assign bt_q = btcap[256*t2_bank +: 256];
    assign bs_q = btcap[1024 + 256*s2b_bank +: 256];
    // ------------------------------------------------------------------ PROG: 2 banks x (256 + 201) x 256
    wire pw = tw_we && tw_kind == 2'd3;
    wire [4*256-1:0] p_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_prog
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in(tw_data[512*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk+1)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in({55'd0, tw_data[512*bk + 256 +: 201]}), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg p1_bank;
    reg [1023:0] pcap;
    reg p2_bank;
    always @(posedge ck) begin p1_bank <= p_idx[0]; pcap <= p_rd; p2_bank <= p1_bank; end
    wire [511:0] pw2 = p2_bank ? pcap[512 +: 512] : pcap[0 +: 512];
    assign p_q = {pw2[256 +: 201], pw2[255:0]};
    // ------------------------------------------------------------------ faults (sticky)
    wire rd_bad = bad_vec(a_re, a_addr) || bad_vec(b_re, b_addr) || bad_vec(c_re, c_addr) ||
                  (cr_re != 8'd0 && (!cr_re[0] || cr_addr[23:14] != 10'd0)) ||
                  (cr_re != 8'd0 && bad_vec(cr_re, cr_addr & {8{24'h003FFF}}));
    wire tw_bad = tw_we && ((tw_kind == 2'd0) || (tw_kind == 2'd1 && tw_addr[23:10] != 0) ||
                            (tw_kind == 2'd2 && (tw_addr[1:0] != 0 || tw_addr[23:9] != 0)) ||
                            (tw_kind == 2'd3 && tw_addr[23:8] != 0));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | rd_bad | w_bad | w_coll | tw_bad | (bs_re && bs_addr[23:9] != 0);
endmodule
