`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_v41_rom_elem_cfg_rw: writes EVERY configuration entry (cfg_a = 0 .. 31) of a V4.1 ROM element and
// reads every decoded configuration register back (hierarchical reads of the element's own registers),
// against a model of the documented map (rtl/v41rom/ot_v41_rom_elem_w10.sv header):
//   a <  NSEG          segment a:   s_row[a], s_idx, s_n, s_fp4, s_lo, s_hi, s_base, s_bf
//   NSEG <= a < 2NSEG  class a-NSEG: c_v, c_u0, c_nu, c_s0, c_s1, c_bf
//   a == 2NSEG         qlast, plast (MTP), pbase
//   2NSEG < a <= 3NSEG (NB = 2) the second macro's row of segment a-2NSEG-1: s_row[NSEG + a-2NSEG-1]
//   a > 3NSEG          outside the contract: must change nothing
// Sequences: ascending, descending, 400 random writes (repeats, every order), each followed by a full read-back.
// QPIPE copies (qp / qz with QK > 0) also check the delayed output-table shadow (so_row / so_idx / so_n).
// The pre-fix decode (2NSEG+1+s -> s_row[NSEG + s[SW-1:0] - 1]) fails on s = NSEG-1 (second macro's segment 7
// never written, first macro's segment 7 clobbered) and on every a > 3NSEG.
//   built by tools/dsrom_elem_cfg_rw.py: +define+ELEM=<module> [+define+QSH] [+define+ELEM_PARAMS=,...]
// ---------------------------------------------------------------------------
`ifndef ELEM
`define ELEM ot_v41_rom_elem_w10
`endif
`ifndef ELEM_PARAMS
`define ELEM_PARAMS
`endif
`ifndef ELEM_BASE
`define ELEM_BASE .MTP(1), .EARLY(1), .FAST(1), .PP(1)
`endif
module tb_v41_rom_elem_cfg_rw;
    localparam integer NSEG = 8, NB = 2, SW = 3;
    reg clk = 1'b0;
    always #1 clk = ~clk;
    reg rst_n = 1'b0;
    reg cfg_v = 1'b0;
    reg [4:0] cfg_a = 5'd0;
    reg [47:0] cfg_d = 48'd0;
    `ELEM #(.NSEG(NSEG), .NB(NB), `ELEM_BASE `ELEM_PARAMS) dut (
`ifdef PIN    // the QPIPE copies name their boundary inputs *_pin
        .clk(clk), .rst_n_pin(rst_n), .cfg_v_pin(cfg_v), .cfg_a_pin(cfg_a), .cfg_d_pin(cfg_d),
        .go_pin(1'b0), .go_bf_pin(1'b0), .xs_v_pin(1'b0), .xb_v_pin(1'b0));
`else
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d),
        .go(1'b0), .go_bf(1'b0), .xs_v(1'b0), .xb_v(1'b0));
`endif

    // model of the decoded state
    reg [47:0] m_seg [0:NSEG-1];
    reg [47:0] m_cls [0:NSEG-1];
    reg [47:0] m_ctl;
    reg [15:0] m_row2 [0:NSEG-1];
    reg        k_seg [0:NSEG-1];
    reg        k_cls [0:NSEG-1];
    reg        k_row2 [0:NSEG-1];
    reg        k_ctl;
    integer errors = 0, writes = 0, checks = 0, i, j, r, n_out = 0;

    task automatic wr(input [4:0] a, input [47:0] d);
        begin
            @(negedge clk);
            cfg_v = 1'b1; cfg_a = a; cfg_d = d;
            @(negedge clk);
            cfg_v = 1'b0;
            writes = writes + 1;
            if (a < NSEG) begin m_seg[a] = d; k_seg[a] = 1'b1; end
            else if (a < 2 * NSEG) begin m_cls[a - NSEG] = d; k_cls[a - NSEG] = 1'b1; end
            else if (a == 2 * NSEG) begin m_ctl = d; k_ctl = 1'b1; end
            else if (a <= 3 * NSEG) begin m_row2[a - 2 * NSEG - 1] = d[15:0]; k_row2[a - 2 * NSEG - 1] = 1'b1; end
            else n_out = n_out + 1;
        end
    endtask

    task automatic chk(input [255:0] what, input integer idx, input [63:0] got, input [63:0] exp);
        begin
            checks = checks + 1;
            if (got !== exp) begin
                errors = errors + 1;
                if (errors <= 20) $display("MISMATCH %0s[%0d] got %h exp %h", what, idx, got, exp);
            end
        end
    endtask

    task automatic readback(input [255:0] tag);
        integer s;
        begin
            repeat (8) @(negedge clk);      // QPIPE shadows trail by QK cycles
            for (s = 0; s < NSEG; s = s + 1) begin
                if (k_seg[s]) begin
                    chk("s_row", s, dut.s_row[s], m_seg[s][15:0]);
                    chk("s_idx", s, dut.s_idx[s], m_seg[s][20:16]);
                    chk("s_n", s, dut.s_n[s], m_seg[s][25:21]);
                    chk("s_fp4", s, dut.s_fp4[s], m_seg[s][26]);
                    chk("s_lo", s, dut.s_lo[s], m_seg[s][27]);
                    chk("s_hi", s, dut.s_hi[s], m_seg[s][28]);
                    chk("s_base", s, dut.s_base[s], m_seg[s][41:29]);
                    chk("s_bf", s, dut.s_bf[s], m_seg[s][42]);
`ifdef QSH
                    chk("so_row", s, dut.so_row[s], m_seg[s][15:0]);
                    chk("so_idx", s, dut.so_idx[s], m_seg[s][20:16]);
                    chk("so_n", s, dut.so_n[s], m_seg[s][25:21]);
`endif
                end
                if (k_row2[s]) begin
                    chk("s_row2", s, dut.s_row[NSEG + s], m_row2[s]);
`ifdef QSH
                    chk("so_row2", s, dut.so_row[NSEG + s], m_row2[s]);
`endif
                end
                if (k_cls[s]) begin
                    chk("c_v", s, dut.c_v[s], m_cls[s][0]);
                    chk("c_u0", s, dut.c_u0[s], m_cls[s][8:1]);
                    chk("c_nu", s, dut.c_nu[s], m_cls[s][15:9]);
                    chk("c_s0", s, dut.c_s0[s], m_cls[s][16 +: SW]);
                    chk("c_s1", s, dut.c_s1[s], m_cls[s][19 +: SW]);
                    chk("c_bf", s, dut.c_bf[s], m_cls[s][22]);
                end
            end
            if (k_ctl) begin
                chk("qlast", 0, dut.qlast, m_ctl[2:0]);
                chk("plast", 0, dut.plast, m_ctl[5:3]);
`ifndef NO_PBASE
                chk("pbase", 0, dut.pbase, m_ctl[19:6]);
`endif
            end
            $display("READBACK %0s writes=%0d checks=%0d errors=%0d", tag, writes, checks, errors);
        end
    endtask

    integer seed = 20261004;
    initial begin
        for (i = 0; i < NSEG; i = i + 1) begin k_seg[i] = 0; k_cls[i] = 0; k_row2[i] = 0; end
        k_ctl = 0;
        void'($urandom(seed));
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);
        // ascending: a > 3NSEG come last and must not disturb anything (the pre-fix decode wrote them)
        for (i = 0; i < 32; i = i + 1) wr(i[4:0], {$urandom, $urandom});
        readback("ascending");
        // descending: the first macro's segment rows are written after the second macro's
        for (i = 31; i >= 0; i = i - 1) wr(i[4:0], {$urandom, $urandom});
        readback("descending");
        // second-macro rows then first-macro rows, as tools/rtl_v41_rom_array.py emits (2NSEG+1+slot before slot)
        for (i = 0; i < NSEG; i = i + 1) begin
            wr(5'(2 * NSEG + 1 + i), {$urandom, $urandom});
            wr(i[4:0], {$urandom, $urandom});
        end
        readback("emitter_order");
        for (r = 0; r < 400; r = r + 1) begin
            j = $urandom % 32;
            wr(j[4:0], {$urandom, $urandom});
            if (r % 50 == 49) readback("random");
        end
        if (errors == 0 && checks > 0) $display("PASS writes=%0d checks=%0d out_of_contract=%0d", writes, checks, n_out);
        else $display("FAIL writes=%0d checks=%0d errors=%0d", writes, checks, errors);
        $finish;
    end
endmodule

// behavioural macro stubs (configuration decode only: no read data is checked)
module ot_rom_4096x274_m8 #(parameter INSTANCE = "") (input wire clk, ce_in, input wire [11:0] addr_in,
                                                     output reg [273:0] rd_out);
    always @(posedge clk) if (ce_in) rd_out <= 274'd0;
endmodule
module ot_rom_8192x274_m8 #(parameter INSTANCE = "") (input wire clk, ce_in, input wire [12:0] addr_in,
                                                     output reg [273:0] rd_out);
    always @(posedge clk) if (ce_in) rd_out <= 274'd0;
endmodule
