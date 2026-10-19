`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT-UNITS-SUDMA2 2026-10-19: WIDE VM read successor of ot_hnx_argmax_static_rows (that module unchanged).
// Delta: the reader reads a BEAT of up to WS = 8 consecutive sectors per edge (sectors cs .. cs+7 sit on the 8 distinct
// banks cs mod 8 of the slice, so one beat = one read on each bank: the full read bandwidth of the slice), and the
// closed engine runs at LP = 8 WS = 64 lanes (ot_hgi_argmax18_m GENERIC18, parameter only: lane j of beat b carries
// word index 64 b + j; per-lane strictly-greater update + registered lower-index tie tree -> numpy.argmax semantics
// for any LP). Beat b of row r: sectors sec0_r + 8 b ..; first-beat word mask off = a[2:0], last-beat mask on the
// last sector's last word and every sector past it. Row read period = max(nb_r, PMIN = 6) edges (nb_r = ceil(ns_r / 8)):
// the write-tag slot rule of the original (a slot is reused two rows later, >= 10 edges after its last use) needs
// >= 5 edges a row (the original n >= 33 rule); MEASURED: a 5-edge period FAULTS the hub (rows 4, n 64), so PMIN = 6.
// Timeline: S_0 = G+3, beat b of row r on S_r + b, S_{r+1} = S_r + max(nb_r, 6), L_r = S_r + nb_r + 9,
// out_v at L_r + ELAT (ELAT = 14 + log2(WS) = 17), W0 = L + ELAT + 1, W1 = W0 + 1, end = W1_{R-1} + ACK + 1.
// Row II = max(ceil(ns / 8), 6) edges (DS n 1,347: 22 or 23) instead of ns (169..170). WS 1 + PMIN 1 = the original.
// MUT (bench): 1 A row stride dropped; 2 O row stride dropped; 3 id word-offset from row 0; 4 beat bank rotation
// dropped (sector k of a beat taken from bank k); 5 last-beat sector mask dropped (sectors past the row end live).
// ---- original header (ot_hnx_argmax_static_rows):
// HBM-NEXT-UNITS-SUDMA 2026-10-19: hnx copy (sed rename) of rtl/hbm_accel/generic/ot_hbm_argmax_static_rows.sv
// H-MTP2/sudma 2026-10-16: P-row ARGMAX.LOCAL (VM mode) successor of ot_hbm_argmax_static (that module, its _sw and
// _sw_vm specialisations stay unchanged).  ISA form, no new opcode: the record carries R = P rows; row r reads its
// FP32 logit row at a_base + r*a_rs (n words, A row stride) and writes {value, id} at o_base + r*o_rs and
// o_base + r*o_rs + o_is.  The closed engine ot_hgi_argmax18_m (GENERIC18, LP 8) is used unchanged: it already
// restarts a row after in_last (fresh <= in_last), so the rows stream back to back through it.
// Static timeline (compiler-fixed, no credits / ready): G = edge sampling go, S_0 = G+3, row r reads ns_r sectors one
// a edge on S_r .. S_r+ns_r-1 with S_{r+1} = S_r + ns_r (no bubble between rows), L_r = S_r + ns_r + 9 (engine
// samples row r's last beat), engine out_v at exactly L_r + ELAT, W0_r = L_r + ELAT + 1, W1_r = W0_r + 1, cr sampled
// at W + ACK; done / fault at W1_{R-1} + ACK + 1.  rows = 1 is edge-for-edge ot_hbm_argmax_static mode 0.
// rows > 1 needs n >= 33 (ns >= 5): row r's writes use record-client tag slots {r[0], 0/1}, so a slot is reused two
// rows later, >= 10 edges after its last use (the hub releases a slot at W + 1 + RESP 9); and the next row's engine
// result never lands before this row's W1.
// Per-row state: A / O row address accumulators, read and write row counters, an ELAT-deep last-beat delay line.
// MUT (bench): 1 A row stride dropped; 2 O row stride dropped; 3 id word-offset correction taken from row 0.
module ot_hnx_argmax_wide_rows #(
    parameter integer WS = 8,          // sectors a beat (power of two, <= 8 = the slice's banks)
    parameter integer PMIN = 6,        // minimum read edges a row (write-tag slot reuse; 5 measured to FAULT the hub)
    parameter integer MUT = 0,
    parameter integer ACK = 12,
    parameter integer ELAT = 14 + $clog2(WS),
    parameter integer MAX_ROWS = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sid,
    input  wire [7:0]    die_id,
    input  wire          go,
    input  wire [3:0]    rows,
    input  wire [17:0]   imm_a,
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   a_rs,
    input  wire [17:0]   n,
    input  wire [17:0]   o_base,
    input  wire [15:0]   o_is,
    input  wire [17:0]   o_rs,
    output reg  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output reg  [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output reg           busy, done, fault, nan_flag
);
    initial if (MAX_ROWS < 1 || MAX_ROWS > 15 || ELAT < 2) $fatal(1, "bad rows / latency");
    localparam [2:0] E_IDLE=0, E_CHK=1, E_ROW=2, E_RD=3, E_RUN=4, E_END=5, E_PAD=6;
    reg [2:0] st; reg [5:0] cnt; reg flt;
    reg am_q; reg [17:0] imm_q, ab_q, n_q, ob_q, ars_q, ors_q; reg [15:0] ois_q; reg [3:0] nr_q; reg legal_q;
    wire [3:0] rm1 = rows - 4'd1;
    wire [21:0] a_last = 22'(a_base) + 22'(rm1) * 22'(a_rs) + 22'(n) - 22'd1;
    wire [21:0] o_last = 22'(o_base) + 22'(rm1) * 22'(o_rs);
    wire [21:0] o_last2 = o_last + 22'(o_is);
    wire legal = n != 18'd0 && imm_a < 18'd262143 && rows != 4'd0 && rows <= 4'(MAX_ROWS) &&
                 (rows == 4'd1 || n >= 18'd33) &&
                 (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid) &&
                 (rows == 4'd1 || a_last[21:16] == {4'd0, a_base[17:16]}) &&
                 o_base[17:16] == sid && o_last[21:16] == {4'd0, sid} && o_last2[21:16] == {4'd0, sid};
    always @(posedge clk) if (go && !busy) begin
        am_q <= a_mirror; imm_q <= imm_a; ab_q <= a_base; n_q <= n; ob_q <= o_base; ois_q <= o_is;
        ars_q <= a_rs; ors_q <= o_rs; nr_q <= rows; legal_q <= legal;
    end
    // ---------------------------------------------------------------- VM reader: a beat of <= WS sectors an edge
    localparam integer LP = 8 * WS;
    reg [14:0] i_sec; reg i_first; reg [17:0] ra, le; reg [3:0] rrow; reg [7:0] pc;
    wire rd_now = st == E_RD;
    wire [14:0] secl = le[17:3];
    wire [14:0] rem = secl - i_sec;                       // sectors after the beat's first
    wire rd_last = rd_now && rem < 15'(WS);               // the row's last beat
    wire [3:0] bcnt = rd_last ? 4'(rem) : 4'(WS - 1);     // sectors in this beat - 1
    wire [17:0] na = (MUT == 1) ? ra : ra + ars_q;     // next row's A base
    wire [17:0] nle = na + n_q - 18'd1;
    reg [15:0] dp [0:8];                                  // {v, cs3, first, last, off3, lastw3, cnt4}
    wire [15:0] di = dp[7];
    reg cap_v, cap_first, cap_last; reg [2:0] cap_off, cap_lastw; reg [3:0] cap_cnt; reg [LP*32-1:0] cap_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vm_rq <= 136'd0; cap_v <= 1'b0; for (integer d = 0; d < 9; d = d + 1) dp[d] <= 16'd0; end
        else begin
            vm_rq <= 136'd0; dp[0] <= 16'd0;
            for (integer d = 1; d < 9; d = d + 1) dp[d] <= dp[d-1];
            if (rd_now) begin
                for (integer k = 0; k < WS; k = k + 1) if (4'(k) <= bcnt) begin
                    vm_rq[17*((i_sec[2:0] + 3'(k)) & 3'(7)) +: 17] <= {1'b1, am_q, i_sec + 15'(k)};
                end
                dp[0] <= {1'b1, i_sec[2:0], i_first, rd_last, i_first ? ra[2:0] : 3'd0, le[2:0], bcnt};
            end
            cap_v <= di[15];
        end
    always @(posedge clk) begin
        for (integer k = 0; k < WS; k = k + 1)
            cap_d[256*k +: 256] <= vm_rr[257*((MUT == 4) ? k : ((di[14:12] + 3'(k)) & 3'(7))) +: 256];
        {cap_first, cap_last, cap_off, cap_lastw, cap_cnt} <= di[11:0];
    end
    reg rd_bad; reg [7:0] exp_bk;
    always @* begin
        rd_bad = 1'b0; exp_bk = 8'd0;
        for (integer k = 0; k < WS; k = k + 1) if (di[15] && 4'(k) <= di[3:0]) exp_bk[(di[14:12] + 3'(k)) & 3'(7)] = 1'b1;
        for (integer l = 0; l < 8; l = l + 1) if (vm_rr[257*l+256] != exp_bk[l]) rd_bad = 1'b1;
    end
    // ---------------------------------------------------------------- engine (closed, parameter LP = 8 WS only)
    reg e_v, e_last; reg [LP-1:0] e_m; reg [LP*32-1:0] e_vals;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin e_v <= 1'b0; e_last <= 1'b0; end
        else begin e_v <= cap_v; e_last <= cap_v && cap_last; end
    always @(posedge clk) begin
        for (integer k = 0; k < WS; k = k + 1)
            for (integer l = 0; l < 8; l = l + 1)
                e_m[8*k+l] <= ((MUT == 5) ? 1'b1 : (4'(k) <= cap_cnt)) && (!cap_first || k != 0 || l[2:0] >= cap_off) &&
                              (!cap_last || 4'(k) != cap_cnt || l[2:0] <= cap_lastw);
        e_vals <= cap_d;
    end
    wire o_v, o_nan, o_f, o_rf; wire [17:0] o_idx; wire [31:0] o_val;
    ot_hgi_argmax18_m #(.LP(LP), .GENERIC18(1)) u_e (.clk(clk), .rst_n(rst_n), .in_v(e_v), .in_last(e_last),
        .in_bias_en(1'b0), .in_mask(e_m), .in_vals(e_vals), .in_bias({LP*32{1'b0}}), .cfg_rank(die_id[6:0]), .cfg_imm_a(imm_q),
        .out_v(o_v), .out_idx(o_idx), .out_nan(o_nan), .fault(o_f), .out_range_fault(o_rf), .out_value(o_val));
    // the engine's out_v must rise exactly ELAT edges after it samples each row's last beat
    reg [ELAT-1:0] lx;
    always @(posedge clk or negedge rst_n) if (!rst_n) lx <= '0; else lx <= {lx[ELAT-2:0], e_v && e_last};
    // ---------------------------------------------------------------- per-row results and writes (W0 / W1 a row)
    reg [31:0] res_val, res_id; reg res_bad; reg w0p, w1p; reg [3:0] wrow; reg [17:0] oa, ob;
    wire [17:0] wa = w1p ? ob + {2'd0, ois_q} : ob;
    wire [31:0] wdat = w1p ? res_id : res_val;
    reg [2:0] ap [0:ACK]; reg cr_v; reg [15:0] cr_tag; reg cr_we; reg wr_now;
    wire [2:0] ax = ap[ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h1E80, ax[1:0]} || !cr_we));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_v <= 1'b0; for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0; end
        else begin
            cr_v <= cr[273]; ap[0] <= {wr_now, cq_seq};
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
        end
    always @(posedge clk) begin cr_tag <= cr[272:257]; cr_we <= cr[256]; end
    wire kill = flt || res_bad;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; nan_flag <= 1'b0; flt <= 1'b0; cq <= 338'd0;
            cq_seq <= 2'd0; wr_now <= 1'b0; cnt <= 6'd0; res_bad <= 1'b0; w0p <= 1'b0; w1p <= 1'b0; wrow <= 4'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0; w0p <= 1'b0; w1p <= w0p;
            if (busy && st != E_CHK && (ack_bad || rd_bad)) flt <= 1'b1;
            if (o_v != lx[ELAT-1]) flt <= 1'b1;
            if (busy && st != E_CHK && o_v) begin                 // L_r + ELAT: row wrow's engine result
                res_val <= o_val;
                res_id <= {14'd0, o_idx} - ((MUT == 3) ? {29'd0, ab_q[2:0]} : {29'd0, oa[2:0]});
                if (o_f || o_rf) res_bad <= 1'b1;
                if (o_nan) nan_flag <= 1'b1;
                oa <= oa + ars_q;
                w0p <= 1'b1;
            end
            if (w0p || w1p) begin                                  // W0 = L_r+ELAT+1, W1 = W0+1
                wr_now <= 1'b1; cq_seq <= {wrow[0], w1p};
                cq <= {1'b1, 1'b1, 11'd0, 1'b0, wa[17:3], 5'd0, {8{wdat}},
                       kill ? 32'd0 : (32'hF << (4 * wa[2:0])), {14'h1E80, wrow[0], w1p}};
            end
            if (w1p) begin
                wrow <= wrow + 4'd1;
                if (MUT != 2) ob <= ob + ors_q;
                if (wrow + 4'd1 == nr_q) begin cnt <= 6'(ACK); st <= E_END; end
            end
            case (st)
                E_IDLE: if (go) begin busy <= 1'b1; st <= E_CHK; end
                E_CHK: begin
                    flt <= 1'b0; res_bad <= 1'b0; ra <= ab_q; le <= ab_q + n_q - 18'd1; oa <= ab_q; ob <= ob_q;
                    wrow <= 4'd0; rrow <= 4'd0;
                    if (!legal_q) begin fault <= 1'b1; busy <= 1'b0; st <= E_IDLE; end
                    else st <= E_ROW;
                end
                E_ROW: begin i_sec <= ra[17:3]; i_first <= 1'b1; pc <= 8'd0; st <= E_RD; end
                E_RD: begin
                    pc <= pc + 8'd1;
                    if (rd_last) begin
                        if (rrow + 4'd1 == nr_q) st <= E_RUN;
                        else if (pc + 8'd1 >= 8'(PMIN)) begin       // next row starts on the next edge
                            rrow <= rrow + 4'd1; ra <= na; le <= nle; i_sec <= na[17:3]; i_first <= 1'b1; pc <= 8'd0;
                        end else st <= E_PAD;                        // short row: idle to PMIN edges
                    end else begin i_sec <= i_sec + 15'(WS); i_first <= 1'b0; end
                end
                E_PAD: begin
                    pc <= pc + 8'd1;
                    if (pc + 8'd1 >= 8'(PMIN)) begin
                        rrow <= rrow + 4'd1; ra <= na; le <= nle; i_sec <= na[17:3]; i_first <= 1'b1; pc <= 8'd0; st <= E_RD;
                    end
                end
                E_RUN: ;                                            // rows in the engine / writer
                E_END: if (cnt == 6'd0) begin                       // W1_{R-1} + ACK + 1
                    done <= !(flt || res_bad || ack_bad); fault <= flt || res_bad || ack_bad; busy <= 1'b0; st <= E_IDLE;
                end else cnt <= cnt - 6'd1;
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
