`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_capt_x8_x43 (claude S-VM-CAPT-X8, 2026-10-16): STATIC successor of the capture data half's intra-leaf crossing.
// Coordinator DECISION B: the 8 rows of dsfd_capt_x8_data_e / _w (dsfd_capt_row_local: dynamic 4-deep hold queue +
// pair packer + ot_ratio_cdc_fifo) become fixed-bank 3:4 transfers on the common epoch (the ot_s81_vm_x43 contract:
// 4 stream = 3 serial cycles = 3.333 ns, both clocks from one PLL), split per clock root into two single-clock hard
// leaves: dsfd_capt_x8x_t (ck, stream) and dsfd_capt_x8x_s (ckv, serial) with an abutting bank seam.  No queue, no
// pointer, no ready, no credit; the old split leaf failed FF hold -84 ps on 3,376 intra-leaf R2R crossings because the
// 256.67 ps 4:3 window cannot carry both the 100 ps hold and 150 ps setup cross-entry reserve.
//
// WHEN WORDS ARRIVE.  A row word is dsfd_capt_g2_dualho's per-root VM write {data32, addr19, v} from its wq flop: one
// per root per stream cycle at most, on ANY stream cycle (the field roots finish one row a cycle per root, the g2
// pipeline is fixed-latency; the S-FUNC compiler does not reserve a stream sample index for capture).  The VM's
// x43 drops index 1 as a schedule fault; here index 1 is NOT a fault: every sample index has its own bank, and the
// serial side reads two banks at serial edge 2 (the t_vm row already carries two words a serial cycle):
//     n = 0 of epoch E  -> bank b0 -> serial edge 2 of epoch E, t_vm row0 (lo)   window 2.222 ns, next write +1.111
//     n = 1 of epoch E  -> bank b1 -> serial edge 2 of epoch E, t_vm row1 (hi)   window 1.389 ns, next write +1.944
//     n = 2 of epoch E  -> bank b2 -> serial edge 0 of epoch E+1, row0           window 1.667 ns, next write +1.667
//     n = 3 of epoch E  -> bank b3 -> serial edge 1 of epoch E+1, row0           window 1.944 ns, next write +1.389
// So 4 words an epoch in, 3 serial reads (1 / 1 / 2 words) out: no word can be refused or dropped, and per-root word
// order is preserved (n0, n1 at edge 2 of E before n2 at edge 0 of E+1 before n3 at edge 1 of E+1).  The hold queue
// (hc / crdy / hovf) is therefore unnecessary and removed; t_ho stays the sticky schedule fault (see FAULTS).
//
// LATENCY (fixed, replaces the queue-dependent old one).  Bank sample edge n (= the edge the old fw pin register
// sampled f_w) -> serial stage A (x43 read edge, bank mux at the seam pins) -> serial stage B (t_vm output flops at
// the S face, one serial cycle later: the seam is on the E face and t_vm on the S face, so A and B are the two ends of
// the L-turn and every leaf pin is a flop):  n0 3.333 ns, n1 2.500, n2 2.778, n3 3.056 ns (= 4 / 3 / 3.33 / 3.67
// stream cycles).  tools/s81_ph/capx43_bench.sh measures the old row_local and this transfer on the same stimulus.
//
// STARTUP CONTRACT (as ot_s81_vm_x43): rst and rsv are released on the common epoch (the release precedes epoch edge
// 0 of both clocks).  Startup age: the stream counter's first sample index 0 is the 5th ck edge after the release
// (rst_s 2 + rst_h + row copy), the serial counter's first index 0 is the 4th ckv edge (rv_s 2 + row copy):
// 4 x 0.833 = 3 x 1.111 ns, the same epoch edge.  Bank valid bits reset to 0 under the stream reset, so the serial
// side's first reads of never-written banks deliver no word.
//
// FAULTS (stream domain, sticky, t_ho = registered OR, the old hovf/hq output edge): the serial side publishes per row
// a phase marker s_mark (high in serial cycle 1, i.e. [1.111, 2.222) ns) and its epoch parity s_par (toggles at
// serial edge 0).  The stream side samples s_mark at index 2 (must be 1) and at index 0 (must be 0), and s_par at
// index 2 (must equal the stream epoch parity), each a >= 0.556 ns window.  After one warm-up epoch any slip (phase or
// whole epoch) of the serial counter against the stream counter sets the row's sticky fault: a schedule violation is
// reported, never re-timed.  There is no other way to violate the schedule (every sample index is accepted).
//
// TWO SERIAL CLOCK ENTRIES (claude S-VM-CAPT-X8S2, 2026-10-16, split1016z): the serial leaf has two literal entries of
// the same ckv root, ckv[0] (stage A bank-read flops, row counters, s_mark / s_par, reset chain: the E-face seam
// column) and ckvb[0] (stage B t_vm output flops: the S-face band).  The die delivers ckv to both at phi - R_entry.
// One shared tree let the 832-flop S band pull the lower rows' stage-A leaves onto its late branch (split1016y s_e:
// stage-A clock 119..173 ps, rows 0-2 hold-padded 5 buffers, native capture 197.6).  Same logic and cycles: stage B
// still registers stage A one serial edge later.
//
// Mutant S81PH_CAPX_MUT_DROP1: the serial side never presents the n = 1 bank (t_vm row1 valid stays 0): words lost.
// ---------------------------------------------------------------------------------------------------------------

// stream side of one row: sample index, epoch parity, four banks {data51, v}, slip checks
module dsfd_capt_x43r_t (
    input  wire        ck,
    input  wire        rs_s,                 // leaf reset (rst_h copy), active low, synchronous release
    input  wire [51:0] f,                    // {data51, v} from the f_w pin
    output reg  [51:0] b0, b1, b2, b3,       // banks: v = bit 0 (reset), data no reset
    input  wire        s_mark, s_par,        // from the serial side of the same row
    output reg         flt
);
    (* keep *) reg rs_n;                     // row-local copy: 4th flop of the release chain
    always @(posedge ck or negedge rs_s) if (!rs_s) rs_n <= 1'b0; else rs_n <= 1'b1;
    reg [1:0] tp; reg te, warm, mk2, mk0, pq;
    wire [1:0] tn = tp + 2'd1;               // sample index of THIS edge (tp = 3 under reset)
    always @(posedge ck or negedge rs_n)
        if (!rs_n) begin
            tp <= 2'd3; te <= 1'b0; warm <= 1'b0; flt <= 1'b0;
            b0[0] <= 1'b0; b1[0] <= 1'b0; b2[0] <= 1'b0; b3[0] <= 1'b0;
        end else begin
            tp <= tn;
            case (tn)
                2'd0: begin te <= ~te; b0[0] <= f[0]; if (warm && mk0) flt <= 1'b1; end
                2'd1: b1[0] <= f[0];
                2'd2: b2[0] <= f[0];
                default: begin b3[0] <= f[0]; warm <= 1'b1;
                               if (warm && (!mk2 || pq != te)) flt <= 1'b1; end
            endcase
        end
    always @(posedge ck) begin
        case (tn)
            2'd0: b0[51:1] <= f[51:1];
            2'd1: b1[51:1] <= f[51:1];
            2'd2: b2[51:1] <= f[51:1];
            default: b3[51:1] <= f[51:1];
        endcase
        if (tn == 2'd2) begin mk2 <= s_mark; pq <= s_par; end
        if (tn == 2'd0) mk0 <= s_mark;
    end
endmodule

// serial side of one row: stage A (fixed-edge bank read, x43 order), stage B (t_vm output flops), marker / parity
module dsfd_capt_x43r_s (
    input  wire         ckv,                 // stage A, counters, marker / parity (entry ckv[0])
    input  wire         ckvb,                // stage B t_vm flops (entry ckvb[0]; same root, phase 0)
    input  wire         rv_s,                // leaf reset (rv_s[1]), active low, synchronous release
    input  wire [51:0]  b0, b1, b2, b3,
    output reg          s_mark, s_par,
    output wire [103:0] t_vm                 // {row1 data51, v1, row0 data51, v0}
);
    (* keep *) reg rv_n;                     // row-local copy: 3rd flop of the release chain
    always @(posedge ckv or negedge rv_s) if (!rv_s) rv_n <= 1'b0; else rv_n <= 1'b1;
    reg [1:0] sp;
    wire [1:0] sn = (sp == 2'd2) ? 2'd0 : sp + 2'd1;    // serial edge index of THIS edge (sp = 2 under reset)
    reg av0, av1, bv0, bv1; reg [50:0] ad0, ad1, bd0, bd1;
    always @(posedge ckv or negedge rv_n)
        if (!rv_n) begin sp <= 2'd2; s_mark <= 1'b0; s_par <= 1'b0; av0 <= 1'b0; av1 <= 1'b0; end
        else begin
            sp <= sn;
            s_mark <= sn == 2'd1;
            if (sn == 2'd0) s_par <= ~s_par;
            case (sn)
                2'd0: begin av0 <= b2[0]; av1 <= 1'b0; end
                2'd1: begin av0 <= b3[0]; av1 <= 1'b0; end
`ifdef S81PH_CAPX_MUT_DROP1
                default: begin av0 <= b0[0]; av1 <= 1'b0; end
`else
                default: begin av0 <= b0[0]; av1 <= b1[0]; end
`endif
            endcase
        end
    always @(posedge ckvb or negedge rv_n) if (!rv_n) begin bv0 <= 1'b0; bv1 <= 1'b0; end else begin bv0 <= av0; bv1 <= av1; end
    always @(posedge ckvb) begin bd0 <= ad0; bd1 <= ad1; end
    always @(posedge ckv) begin
        case (sn)
            2'd0: ad0 <= b2[51:1];
            2'd1: ad0 <= b3[51:1];
            default: begin ad0 <= b0[51:1]; ad1 <= b1[51:1]; end
        endcase
    end
    assign t_vm = {bd1, bv1, bd0, bv0};
endmodule

// ck leaf: 8 rows of banks, reset release chain, registered fault OR.  Every output from a flop.
module dsfd_capt_x8x_t (
    input  wire [0:0]   ck, rst,
    input  wire [415:0] f_w,                 // 8 x {data51, v} (dsfd_capt_g2_dualho t_w half)
    output wire [8*208-1:0] b,               // row r: [208 r +: 208] = {b3, b2, b1, b0}
    input  wire [7:0]   s_mark, s_par,
    output wire [0:0]   t_ho
);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    (* keep *) reg [1:0] rst_h;
    always @(posedge ck[0] or negedge rst_s[1]) if (!rst_s[1]) rst_h <= 2'b00; else rst_h <= 2'b11;
    wire [7:0] flt;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_r
        wire [51:0] b0, b1, b2, b3;
        dsfd_capt_x43r_t u_t (.ck(ck[0]), .rs_s(rst_h[g / 4]), .f(f_w[52 * g +: 52]), .b0(b0), .b1(b1), .b2(b2), .b3(b3),
            .s_mark(s_mark[g]), .s_par(s_par[g]), .flt(flt[g]));
        assign b[208 * g +: 208] = {b3, b2, b1, b0};
    end endgenerate
    reg hq;
    always @(posedge ck[0] or negedge rst_h[0]) if (!rst_h[0]) hq <= 1'b0; else hq <= |flt;
    assign t_ho = hq;
endmodule

// ckv leaf: 8 rows of fixed-edge reads + t_vm output flops, reset release chain.  Every output from a flop.
module dsfd_capt_x8x_s (
    input  wire [0:0]   ckv, ckvb, rsv,      // ckv[0]: stage A / counters / reset chain; ckvb[0]: stage B (t_vm)
    input  wire [8*208-1:0] b,
    output wire [7:0]   s_mark, s_par,
    output wire [831:0] t_vm
);
    reg [1:0] rv_s;
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_r
        dsfd_capt_x43r_s u_s (.ckv(ckv[0]), .ckvb(ckvb[0]), .rv_s(rv_s[1]), .b0(b[208 * g +: 52]), .b1(b[208 * g + 52 +: 52]),
            .b2(b[208 * g + 104 +: 52]), .b3(b[208 * g + 156 +: 52]), .s_mark(s_mark[g]), .s_par(s_par[g]),
            .t_vm(t_vm[104 * g +: 104]));
    end endgenerate
endmodule

// physical identities (one hard master per face variant; same logic)
module dsfd_capt_x8x_t_e (input wire [0:0] ck, rst, input wire [415:0] f_w, output wire [1663:0] b,
    input wire [7:0] s_mark, s_par, output wire [0:0] t_ho);
    dsfd_capt_x8x_t u (.ck(ck), .rst(rst), .f_w(f_w), .b(b), .s_mark(s_mark), .s_par(s_par), .t_ho(t_ho));
endmodule
module dsfd_capt_x8x_t_w (input wire [0:0] ck, rst, input wire [415:0] f_w, output wire [1663:0] b,
    input wire [7:0] s_mark, s_par, output wire [0:0] t_ho);
    dsfd_capt_x8x_t u (.ck(ck), .rst(rst), .f_w(f_w), .b(b), .s_mark(s_mark), .s_par(s_par), .t_ho(t_ho));
endmodule
module dsfd_capt_x8x_s_e (input wire [0:0] ckv, ckvb, rsv, input wire [1663:0] b, output wire [7:0] s_mark, s_par,
    output wire [831:0] t_vm);
    dsfd_capt_x8x_s u (.ckv(ckv), .ckvb(ckvb), .rsv(rsv), .b(b), .s_mark(s_mark), .s_par(s_par), .t_vm(t_vm));
endmodule
module dsfd_capt_x8x_s_w (input wire [0:0] ckv, ckvb, rsv, input wire [1663:0] b, output wire [7:0] s_mark, s_par,
    output wire [831:0] t_vm);
    dsfd_capt_x8x_s u (.ckv(ckv), .ckvb(ckvb), .rsv(rsv), .b(b), .s_mark(s_mark), .s_par(s_par), .t_vm(t_vm));
endmodule
`default_nettype wire
