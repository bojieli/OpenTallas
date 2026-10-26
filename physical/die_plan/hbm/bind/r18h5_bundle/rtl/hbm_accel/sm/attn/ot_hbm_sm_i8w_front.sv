`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_sm_i8w_front (HBM-QINT8B 2026-10-20): the WIDE INT8 front of the static attention SM, 128 INT8 codes a cycle.
// Opt-in (ot_hbm_sm_attn_front_static #(.INT8W(1))); the default build does not instantiate it.
//
// Why: the narrow INT8 path (ot_smh_static_int8) turns one packed 128-code line into two BF16 lines on two edges, so
// Qwen INT8 is SM-front bound at 64 codes/edge (136 edges / 64-line block measured, HBM supplies ~104 B/edge).
// What: the SM's row bundles already go to the two sides of the column array separately (rl -> columns 3..0,
// rr -> columns 4..7), and a single-vector matvec uses only one column per side's x store.  Command mode 3 (a free
// non-attention encoding, a schedule fault before this revision) marks one packed line as TWO rows of ONE chunk:
// low 64 codes = row A (left side, x in column 0), high 64 codes = row B (right side, x in column 4).  Both halves are
// widened to BF16 here (the real converter arithmetic of ot_hbm_accel_int8_line, two registered stages, 128 lanes) and
// launched as ORDINARY fmt-0 BF16 row bundles (the closed tiles / XS / tcl / tct / BE see standard BF16 rows):
// exactness is the fmt-0 path's (codes exact in BF16, products exact in FP32, the golden chunk8 csum per row).
// Result: column 0 = row A, column 4 = row B under the row tag of A.  While the result mode (rmode) is set, rdata column 1
// carries column 4, so the VM writer (ot_hbm_sm_vm_wr_q, descriptor P = 2) stores row B as slot 1 = its natural VM
// address when the compiler pairs B = A + 8 * stride_row (SM-local rows).
// Timing: command + packet at t -> classified lanes at t+1 -> row bundles at the front pins at t+2 (the normal path
// takes longer; the compiler leaves the op gap).  No ready, credit or stall: a dual word whose packet is missing or
// mistagged, or a dual row meeting an in-flight normal / attention row at the pin mux, is a sticky fault.
// rmode: set by a valid dual word, cleared by any other valid word or an attention word; the compiler starts the next
// op only after the previous op's results have left (static schedule).
// SAFE-DESIGN: every output launches from a register (row_launch), the 6,544-bit pin mux select is 206 KEPT copies fed
// by 8 kept stage-1 copies (<= 26 loads), rmode has 2 kept copies (16 loads), no storage beyond the pipeline registers,
// one clock (the SM stream clock), static schedule (+0 cycles to the BF16 law: the compiler issues one line an edge).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_i8w_front (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [191:0]  command,
    input  wire [1098:0] packet,
    input  wire          attention,
    input  wire [3271:0] normal_l,
    input  wire [3271:0] normal_r,
    input  wire          attention_q,
    output wire [3271:0] ml,
    output wire [3271:0] mr,
    input  wire [255:0]  rdata_n,
    output wire [255:0]  rdata,
    output reg           fault
);
    wire dual = command[183:181] == 3'd3;
    wire dual_v = dual && command[25];
    // ---------------- stage 1: classify the 128 codes (ot_hbm_accel_int8_line classify) + the slot's control ----------
    function automatic [11:0] classify(input [7:0] code);
        reg [7:0] mag;
        reg [2:0] top;
        integer b;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            top = 0;
            for (b = 0; b < 8; b = b + 1) if (mag[b]) top = b[2:0];
            classify = {top, code[7], mag};
        end
    endfunction
    function automatic [15:0] encode(input [11:0] f);
        reg [7:0] shifted, exponent;
        begin
            exponent = 8'd127 + {5'd0, f[11:9]};
            shifted = f[7:0] << (3'd7 - f[11:9]);
            encode = (f[7:0] == 8'd0) ? 16'd0 : {f[8], exponent, shifted[6:0]};
        end
    endfunction
    reg [1535:0] s1_cls;
    reg          s1_first, s1_last;
    reg [15:0]   s1_tag;
    reg [6:0]    s1_xa;
    genvar ln;
    generate for (ln = 0; ln < 128; ln = ln + 1) begin : g_cls
`ifdef OT_I8W_MUT_SIGN
        always @(posedge clk) s1_cls[12*ln +: 12] <= classify(packet[8*ln +: 8] & 8'h7f);
`else
        always @(posedge clk) s1_cls[12*ln +: 12] <= classify(packet[8*ln +: 8]);
`endif
    end endgenerate
    always @(posedge clk) begin
        s1_first <= command[24]; s1_last <= command[23];
        s1_tag <= {command[22:11], command[10], command[9:7]};
        s1_xa <= command[6:0];
    end
    reg s1_v;
    (* keep *) reg [7:0] s1_sel;                     // 8 kept copies of the dual-word flag (each feeds <= 26 copies)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s1_sel <= 8'd0; end
        else begin s1_v <= dual_v; s1_sel <= {8{dual}}; end
    // ---------------- stage 2: widen (ot_hbm_accel_int8_line encode) into the launch registers ----------------------
    wire [2047:0] bf;
    generate for (ln = 0; ln < 128; ln = ln + 1) begin : g_enc
        assign bf[16*ln +: 16] = encode(s1_cls[12*ln +: 12]);
    end endgenerate
    // fmt-0 BF16 row control exactly as ot_hbm_accel_smh_fc_unpack builds it: {v_b 0, v_f, first, last, fp4 0, bf 1, tag}
    wire [21:0] ctl = {1'b0, s1_v, s1_first, s1_last, 1'b0, 1'b1, s1_tag};
    wire [3271:0] d_l, d_r;
    genvar j;
    generate for (j = 0; j < 4; j = j + 1) begin : g_row
        // sub-row j of a 64-code line = BF16 lanes 16j .. 16j+15 (the fmt-0 row field lw[256j +: 256])
        wire [255:0] lo = bf[256*j +: 256];
`ifdef OT_I8W_MUT_HALF
        wire [255:0] hi = bf[256*j +: 256];
`else
        wire [255:0] hi = bf[1024 + 256*j +: 256];
`endif
        ot_hbm_sm_attn_row_launch u_l (.clk(clk), .rst_n(rst_n), .d({ctl, lo, 532'd0, s1_v, s1_xa}), .q(d_l[818*j +: 818]));
        ot_hbm_sm_attn_row_launch u_r (.clk(clk), .rst_n(rst_n), .d({ctl, hi, 532'd0, s1_v, s1_xa}), .q(d_r[818*j +: 818]));
    end endgenerate
    // ---------------- the pin mux: dual rows replace the (idle) normal rows; kept select copies, <= 32 loads each -----
    localparam integer NCH = (3272 + 31) / 32;       // 103 chunks a side
    wire [NCH-1:0] sel_l, sel_r;
    genvar k;
    generate for (k = 0; k < NCH; k = k + 1) begin : g_sel
        localparam integer LO = 32 * k;
        localparam integer WD = (3272 - LO < 32) ? (3272 - LO) : 32;
        ot_hbm_accel_smh_kregk #(.W(1), .RST(1)) u_sl (.clk(clk), .rst_n(rst_n), .d(s1_sel[k % 8]), .q(sel_l[k]));
        ot_hbm_accel_smh_kregk #(.W(1), .RST(1)) u_sr (.clk(clk), .rst_n(rst_n), .d(s1_sel[(k + 4) % 8]), .q(sel_r[k]));
        assign ml[LO +: WD] = sel_l[k] ? d_l[LO +: WD] : normal_l[LO +: WD];
        assign mr[LO +: WD] = sel_r[k] ? d_r[LO +: WD] : normal_r[LO +: WD];
    end endgenerate
    // ---------------- result mode: column 4 (row B) leaves as column 1 (VM slot 1) ----------------------------------
    (* keep *) reg [1:0] rmode;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rmode <= 2'b00;
        else if (dual_v) rmode <= 2'b11;
        else if (command[25] || attention) rmode <= 2'b00;
`ifdef OT_I8W_MUT_NOSWAP
    wire [1:0] rm = 2'b00;
`else
    wire [1:0] rm = rmode;
`endif
    assign rdata = {rdata_n[255:64],
                    rm[1] ? rdata_n[159:144] : rdata_n[63:48],
                    rm[0] ? rdata_n[143:128] : rdata_n[47:32],
                    rdata_n[31:0]};
    // ---------------- faults (sticky; never a stall) ----------------
    wire [15:0] nv;
    generate for (j = 0; j < 4; j = j + 1) begin : g_nv
        assign nv[4*j +: 4] = {normal_l[818*j + 817], normal_l[818*j + 816], normal_r[818*j + 817], normal_r[818*j + 816]};
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else begin
            if (dual && (packet[1098] != command[29] || (command[29] && packet[1097:1088] != command[39:30]) ||
                         (command[25] && !command[29]) || command[28]))
                fault <= 1'b1;
            if (sel_l[0] && (|nv || attention_q)) fault <= 1'b1;
        end
endmodule
`default_nettype wire
