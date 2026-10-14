`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Per-bank Engram gather of the re-specified DeepSeek-V4.1 decode die:
// docs/ARCH_SPEC_V41.md section 6 item 8, gap-table row "Engram gather ingest".
//
// REQUIREMENT.  Per token 48 rows (24 hash columns x 2 Engram layers), one
// 264-B row per column bank, each column bank on its own ROM die
// (tools/hdc_v41_engram_rom_plan.py).  12,672 B must reach the consuming die
// within a quarter of the >= 3.57 us slack: 13.7 B/cycle.  One 256-bit beat
// stream at one beat per cycle carries a token in 48 x 8 = 384 cycles.
// This replaces the as-built flat 48 x 2,112-bit port (16,559 IO pins).
//
// TWO BLOCKS, one on each side of the links:
//
//   ot_hdc_v41x_egather_slice -- on each column-bank ROM die.  Takes one row id
//     per token (the hash unit's global row in the layer table, and the
//     token's slot tag), subtracts the column's first row (cfg_base, a strap),
//     reads the row from the ROM as BEATS beat-wide reads ({residue, beat}
//     address; 256 E4M3 codes per row, 32 per beat; the ROM's side byte on
//     beat 0 is the row's UE8M0 scale), and sends each beat as a 256-bit word
//     with a TAG = {slot, layer, column, beat, scale}.  Every beat is
//     self-describing, so the links and switches between the banks and the
//     consumer may merge and reorder beats freely.  ROM reads are issued only
//     against free beat-buffer entries (credit), so any ROM latency is safe;
//     the ROM must answer in order.
//
//   ot_hdc_v41x_egather_asm -- on the consuming die.  Allocates token slots
//     (tok_valid/tok_ready -> tok_tag, the tag the requester sends with the 48
//     row ids), accepts one beat per cycle IN ANY BANK ORDER, dequantises its
//     32 codes (E4M3 x 2^(scale-127) -> BF16, bit for bit the golden's
//     to_bf16((E4M3[codes] * np.exp2(sc)).astype(F)), tools/hdc_golden_v41.py
//     Model.engram_layer) and writes them as one 512-bit word of the vector
//     memory at word ((slot * NL + layer) * NC + column) * BEATS + beat -- the
//     48 rows in (layer, column) order, element 32*beat + i of a row in lane i.
//     rdy[s] rises when all NL * NC * BEATS words of slot s have been written;
//     rel_valid/rel_tag frees the slot.  fault: a beat for a free slot, a
//     column >= NC, or more beats than a token has.
//
// PROTOCOL.  Every channel is valid/ready; every output is a flop and every
// ready is registered (a producer may have one more beat in flight when ready
// drops, and the input buffer takes it).
// ---------------------------------------------------------------------------

// E4M3 code times 2^(scale - 127), rounded to BF16: the decode of
// rtl/hdc/v41/ot_hdc_engram_gather.sv (ot_hdc_engram_e4m3_bf16), split into two
// register stages so the assembler closes at 0.9 ns.  pre: the code's fields and
// E, the exponent of the significand's unit bit (value = sig * 2^E); post: the
// normal / subnormal / overflow encodings and the one round-to-nearest-even.
module ot_hdc_v41x_e4m3_pre (
    input  wire [7:0]  code,
    input  wire [7:0]  scale,
    output wire [19:0] pre                     // {s, nan, sig[3:0], p[1:0], E[10:0], 1'b0}
);
    wire       s = code[7];
    wire [3:0] e = code[6:3];
    wire [2:0] m = code[2:0];
    wire [3:0] sig = (e != 0) ? {1'b1, m} : {1'b0, m};
    wire signed [10:0] E = (e != 0) ? $signed({7'd0, e}) - 11'sd137 + $signed({3'd0, scale})
                                    : -11'sd136 + $signed({3'd0, scale});
    wire [1:0] p = sig[3] ? 2'd3 : sig[2] ? 2'd2 : sig[1] ? 2'd1 : 2'd0;
    assign pre = {s, (e == 4'hF && m == 3'h7), sig, p, E, 1'b0};
endmodule

module ot_hdc_v41x_e4m3_post (
    input  wire [19:0] pre,
    output reg  [15:0] bf16
);
    wire       s   = pre[19];
    wire       nan = pre[18];
    wire [3:0] sig = pre[17:14];
    wire [1:0] p   = pre[13:12];
    wire signed [10:0] E = pre[11:1];
    wire signed [10:0] X = E + $signed({9'd0, p});
    wire [3:0] nrm = sig << (2'd3 - p);               // 1.fff
    wire [7:0] xb = X[7:0] + 8'd127;
    wire signed [10:0] k = E + 11'sd133;              // >= -3 on every code and scale
    wire [1:0] r = (k < 0) ? (~k[1:0] + 2'd1) : 2'd0; // -k for k in -3..-1
    wire [3:0] q = sig >> r;
    wire [3:0] rem = sig & ((4'd1 << r) - 4'd1);
    wire [3:0] half = (r == 0) ? 4'd0 : (4'd1 << (r - 2'd1));
    wire       up = (r != 0) && ((rem > half) || (rem == half && q[0]));
    wire [7:0] sub = (k >= 0) ? ({4'd0, sig} << k[2:0]) : ({4'd0, q} + {7'd0, up});
    always @(*) begin
        if (nan)                           bf16 = {s, 15'h7FC0};
        else if (sig == 0)                 bf16 = {s, 15'd0};
        else if (X > 11'sd127)             bf16 = {s, 8'hFF, 7'd0};
        else if (X >= -11'sd126)           bf16 = {s, xb, nrm[2:0], 4'd0};
        else                               bf16 = {s, 7'd0, sub};
    end
endmodule

// ---------------------------------------------------------------------------
// Column-bank slice.  Beat tag layout (TAGW bits, MSB first):
//   {slot[TW], layer[LW], column[CW], beat[BTW], scale[8]}
// ---------------------------------------------------------------------------
module ot_hdc_v41x_egather_slice #(
    parameter integer RW    = 32,       // row id width (a layer table has 384M rows)
    parameter integer AW    = 24,       // residue width (a column bank has ~16.0M rows)
    parameter integer BEATS = 8,        // beats per row (256 codes: 8; the reduced vehicle's 32: 1)
    parameter integer TW    = 1,        // slot tag width
    parameter integer LW    = 1,        // layer id width
    parameter integer CW    = 5,        // column id width
    parameter integer DQ    = 4,        // beat buffer entries (power of two >= 2)
    parameter integer BTW   = (BEATS > 1) ? $clog2(BEATS) : 1,
    parameter integer TAGW  = TW + LW + CW + BTW + 8
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [RW-1:0]     cfg_base,          // straps: the column's first row, bank id
    input  wire [LW-1:0]     cfg_layer,
    input  wire [CW-1:0]     cfg_col,
    input  wire              req_valid,
    output reg               req_ready,
    input  wire [RW-1:0]     req_row,
    input  wire [TW-1:0]     req_tag,
    output reg               rom_re,
    output reg  [AW+BTW-1:0] rom_addr,          // {residue, beat}
    input  wire              rom_rvalid,
    input  wire [263:0]      rom_rdata,         // [255:0] 32 codes, [263:256] side byte (scale on beat 0)
    output reg               b_valid,
    input  wire              b_ready,
    output reg  [255:0]      b_data,
    output reg  [TAGW-1:0]   b_tag
);
    localparam integer QW = $clog2(DQ);
    // request buffer: two entries, ready registered
    reg  [RW+TW-1:0] rq [0:1];
    reg  [1:0]       rq_n;
    reg              rq_wp, rq_rp;
    wire             take;
    wire             acc_req = req_valid && req_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rq_n <= 2'd0; rq_wp <= 1'b0; rq_rp <= 1'b0; req_ready <= 1'b0; end
        else begin
            rq_n <= rq_n + {1'b0, acc_req} - {1'b0, take};
            if (acc_req) rq_wp <= ~rq_wp;
            if (take) rq_rp <= ~rq_rp;
            //: at most one more request may arrive in the cycle ready is seen high
            req_ready <= (rq_n + {1'b0, acc_req} - {1'b0, take}) == 2'd0;
        end
    end
    always @(posedge clk) if (acc_req) rq[rq_wp] <= {req_tag, req_row};
    // the row being read
    reg              cur_v;
    reg  [AW-1:0]    cur_res;
    reg  [TW-1:0]    cur_tag;
    reg  [BTW-1:0]   cur_beat;
    reg  [QW:0]      outst;                        // reads issued and beats held, not yet sent
    wire             send;
    wire             issue = cur_v && (outst < DQ);
    wire             last_beat = (cur_beat == BEATS - 1);
    assign take = (rq_n != 2'd0) && (!cur_v || (issue && last_beat));
    wire [RW-1:0]    hrow = rq[rq_rp][RW-1:0];
    wire [RW-1:0]    hres = hrow - cfg_base;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cur_v <= 1'b0; rom_re <= 1'b0; outst <= 0; end
        else begin
            rom_re <= issue;
            outst <= outst + {{QW{1'b0}}, issue} - {{QW{1'b0}}, send};
            if (take) cur_v <= 1'b1;
            else if (issue && last_beat) cur_v <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (take) begin
            cur_res <= hres[AW-1:0]; cur_tag <= rq[rq_rp][RW +: TW]; cur_beat <= {BTW{1'b0}};
        end else if (issue) cur_beat <= last_beat ? {BTW{1'b0}} : cur_beat + 1'b1;
        if (issue) rom_addr <= (BEATS > 1) ? {cur_res, cur_beat} : {cur_res, 1'b0};
    end
    // read metadata, in issue order (the ROM answers in order)
    reg  [TW+BTW-1:0] mq [0:DQ-1];
    reg  [QW-1:0]     mq_wp, mq_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mq_wp <= 0; mq_rp <= 0; end
        else begin
            if (issue) mq_wp <= mq_wp + 1'b1;
            if (rom_rvalid) mq_rp <= mq_rp + 1'b1;
        end
    end
    always @(posedge clk) if (issue) mq[mq_wp] <= {cur_tag, cur_beat};
    // return: capture, then the beat buffer
    reg              rv;
    reg  [263:0]     rd;
    reg  [TW+BTW-1:0] rm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rv <= 1'b0; else rv <= rom_rvalid;
    end
    always @(posedge clk) if (rom_rvalid) begin rd <= rom_rdata; rm <= mq[mq_rp]; end
    reg  [7:0]       scl;
    wire [BTW-1:0]   r_beat = rm[BTW-1:0];
    wire [7:0]       r_scale = (r_beat == 0) ? rd[263:256] : scl;
    always @(posedge clk) if (rv && r_beat == 0) scl <= rd[263:256];
    reg  [256+TAGW-1:0] bq [0:DQ-1];
    reg  [QW-1:0]       bq_wp, bq_rp;
    reg  [QW:0]         bq_n;
    wire                load = (bq_n != 0) && (!b_valid || b_ready);
    assign send = load;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin bq_wp <= 0; bq_rp <= 0; bq_n <= 0; b_valid <= 1'b0; end
        else begin
            if (rv) bq_wp <= bq_wp + 1'b1;
            if (load) bq_rp <= bq_rp + 1'b1;
            bq_n <= bq_n + {{QW{1'b0}}, rv} - {{QW{1'b0}}, load};
            if (load) b_valid <= 1'b1;
            else if (b_ready) b_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (rv) bq[bq_wp] <= {rm[TW+BTW-1:BTW], cfg_layer, cfg_col, r_beat, r_scale, rd[255:0]};
        if (load) {b_tag, b_data} <= bq[bq_rp];
    end
endmodule

// ---------------------------------------------------------------------------
// Consumer-side assembler.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_egather_asm #(
    parameter integer NL    = 2,
    parameter integer NC    = 24,
    parameter integer BEATS = 8,
    parameter integer TW    = 1,
    parameter integer LW    = 1,
    parameter integer CW    = 5,
    parameter integer BTW   = (BEATS > 1) ? $clog2(BEATS) : 1,
    parameter integer TAGW  = TW + LW + CW + BTW + 8,
    parameter integer NS    = 1 << TW,
    parameter integer TOT   = NL * NC * BEATS,  // words per token
    parameter integer VAW   = $clog2(NS * TOT)
) (
    input  wire              clk,
    input  wire              rst_n,
    // slot allocation
    input  wire              tok_valid,
    output reg               tok_ready,
    output reg  [TW-1:0]     tok_tag,
    // beats
    input  wire              b_valid,
    output reg               b_ready,
    input  wire [255:0]      b_data,
    input  wire [TAGW-1:0]   b_tag,
    // vector memory write port (512-bit words, 32 BF16)
    output reg               wr_valid,
    input  wire              wr_ready,
    output reg  [VAW-1:0]    wr_addr,
    output reg  [511:0]      wr_data,
    // completion
    output reg  [NS-1:0]     rdy,
    input  wire              rel_valid,
    input  wire [TW-1:0]     rel_tag,
    output reg               fault
);
    localparam integer CTW = $clog2(TOT + 1);
    localparam [CTW-1:0] TOTV = TOT;
    // -- slots
    reg  [NS-1:0] busy;
    reg  [CTW-1:0] cnt [0:NS-1];
    wire tok_acc = tok_valid && tok_ready;
    wire wr_acc  = wr_valid && wr_ready;
    reg  [TW-1:0] wslot, ds;                       // slot of the word at the write port / decode stage
    integer s;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= {NS{1'b0}}; tok_ready <= 1'b0; tok_tag <= {TW{1'b0}}; rdy <= {NS{1'b0}};
            for (s = 0; s < NS; s = s + 1) cnt[s] <= {CTW{1'b0}};
        end else begin
            for (s = 0; s < NS; s = s + 1) begin
                if (tok_acc && tok_tag == s) begin busy[s] <= 1'b1; cnt[s] <= {CTW{1'b0}}; end
                else if (rel_valid && rel_tag == s) busy[s] <= 1'b0;
                if (wr_acc && wslot == s && !(tok_acc && tok_tag == s)) cnt[s] <= cnt[s] + 1'b1;
                rdy[s] <= busy[s] && !(rel_valid && rel_tag == s) && (cnt[s] == TOTV);
            end
            if (tok_acc) tok_tag <= tok_tag + 1'b1;
            //: the next slot must be free and not the one being accepted
            tok_ready <= tok_acc ? !busy[tok_tag + 1'b1] : (!busy[tok_tag] || (rel_valid && rel_tag == tok_tag));
        end
    end
    // -- input buffer: 4 entries, ready registered with one entry of slack
    reg  [256+TAGW-1:0] iq [0:3];
    reg  [1:0]          iq_wp, iq_rp;
    reg  [2:0]          iq_n;
    wire                in_acc = b_valid && b_ready;
    wire                d_load;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iq_wp <= 2'd0; iq_rp <= 2'd0; iq_n <= 3'd0; b_ready <= 1'b0; end
        else begin
            if (in_acc) iq_wp <= iq_wp + 2'd1;
            if (h_load) iq_rp <= iq_rp + 2'd1;
            iq_n <= iq_n + {2'd0, in_acc} - {2'd0, h_load};
            b_ready <= (iq_n + {2'd0, in_acc} - {2'd0, h_load}) <= 3'd2;
        end
    end
    always @(posedge clk) if (in_acc) iq[iq_wp] <= {b_tag, b_data};
    // -- head register (the buffer's read mux ends here), then the decode stage
    reg                 hv;
    reg  [256+TAGW-1:0] h;
    wire                h_load;
    wire [255:0]   hc  = h[255:0];
    wire [7:0]     hsc = h[256 +: 8];
    wire [BTW-1:0] hbt = h[264 +: BTW];
    wire [CW-1:0]  hcl = h[264 + BTW +: CW];
    wire [LW-1:0]  hly = h[264 + BTW + CW +: LW];
    wire [TW-1:0]  hsl = h[264 + BTW + CW + LW +: TW];
    wire [32*20-1:0] pre;
    wire [511:0]     dec;
    genvar gq;
    // decode stage 1 (h -> m): fields and exponents; stage 2 (m -> d): encodings and rounding
    reg              mv;
    reg  [32*20-1:0] mp;
    reg  [VAW-1:0]   ma;
    reg  [TW-1:0]    ms;
    reg              mbad;
    generate for (gq = 0; gq < 32; gq = gq + 1) begin : g_dec
        ot_hdc_v41x_e4m3_pre  u_pre  (.code(hc[8*gq +: 8]), .scale(hsc), .pre(pre[20*gq +: 20]));
        ot_hdc_v41x_e4m3_post u_post (.pre(mp[20*gq +: 20]), .bf16(dec[16*gq +: 16]));
    end endgenerate
    reg            dv;
    reg  [511:0]   dd;
    reg  [VAW-1:0] da;
    reg            dbad;
    wire           m_load;
    wire           o_load = dv && (!wr_valid || wr_ready);
    assign d_load = mv && (!dv || o_load);
    assign m_load = hv && (!mv || d_load);
    assign h_load = (iq_n != 3'd0) && (!hv || m_load);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hv <= 1'b0; mv <= 1'b0; dv <= 1'b0; wr_valid <= 1'b0; end
        else begin
            if (h_load) hv <= 1'b1; else if (m_load) hv <= 1'b0;
            if (m_load) mv <= 1'b1; else if (d_load) mv <= 1'b0;
            if (d_load) dv <= 1'b1; else if (o_load) dv <= 1'b0;
            if (o_load) wr_valid <= 1'b1; else if (wr_ready) wr_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (h_load) h <= iq[iq_rp];
        if (m_load) begin
            mp <= pre; ms <= hsl;
            ma <= ((hsl * NL + hly) * NC + hcl) * BEATS + hbt;
            mbad <= !busy[hsl] || (hcl >= NC) || (hly >= NL) || (hbt >= BEATS);
        end
        if (d_load) begin dd <= dec; ds <= ms; da <= ma; dbad <= mbad; end
        if (o_load) begin wr_data <= dd; wr_addr <= da; wslot <= ds; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if ((o_load && dbad) || (wr_acc && cnt[wslot] == TOTV)) fault <= 1'b1;
    end
endmodule
