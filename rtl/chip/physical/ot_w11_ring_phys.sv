`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 physical wrappers for the index ring blocks whose wide data buses would
// otherwise be tens of thousands of top-level pins (the quarter join: 69,632
// key bits; the ring K-port: 128 pseudo-channel ports).  Parameter-free tops at
// the full-shape configuration.  Every wide DATA bus of the block under test is
// kept at full width and driven from / captured into flip-flops:
//   * inputs: a 64-bit-a-cycle shift chain (ot_w11_phys_sin) loads one flop per
//     input bit (distinct drivers, so synthesis cannot merge the block's
//     per-bit logic); the chain stands in for the neighbour's output registers;
//   * outputs: a registered 8:1 XOR tree per level (ot_w11_phys_sout) down to 64
//     bits, a flop after every level, so it adds no path through the block.
// Control and narrow buses stay top-level pins.  The block's own paths
// (register to register, and the chain / tree flops to and from it) are the
// timing under test; the chain and tree cells are reported with the area.
// ---------------------------------------------------------------------------
module ot_w11_phys_sin #(parameter integer N = 1024) (
    input wire clk, input wire sen, input wire [63:0] sin, output reg [N-1:0] q);
    localparam integer NP = ((N + 63) / 64) * 64;
    reg [NP-1:0] c;
    always @(posedge clk) if (sen) c <= {c[NP-65:0], sin};
    always @* q = c[N-1:0];
endmodule

module ot_w11_phys_sout #(parameter integer N = 1024) (
    input wire clk, input wire [N-1:0] d, output wire [63:0] q);
    generate if (N <= 64) begin : g_leaf
        reg [63:0] r;
        always @(posedge clk) r <= 64'(d);
        assign q = r;
    end else begin : g_lvl
        localparam integer M = (N + 7) / 8;
        reg [M-1:0] r;
        integer i, j;
        always @(posedge clk)
            for (i = 0; i < M; i = i + 1) begin
                r[i] = 1'b0;
                for (j = 0; j < 8; j = j + 1) if (8 * i + j < N) r[i] = r[i] ^ d[8 * i + j];
            end
        ot_w11_phys_sout #(.N(M)) u_n (.clk(clk), .d(r), .q(q));
    end endgenerate
endmodule

// the quarter join (full width: 4 x 16 input keys, 64 output keys of 544 bits)
module ot_w11_quarter_join_phys (
    input  wire clk, rst_n, sen,
    input  wire [63:0] sin,
    output wire [63:0] sout,
    input  wire cmd_v,
    input  wire [29:0] cmd_nkeys,
    input  wire [39:0] cmd_skip,
    output wire busy, fault,
    input  wire [3:0] i_valid,
    output wire [3:0] i_ready,
    input  wire [63:0] i_kv,
    output wire o_valid,
    input  wire o_ready,
    output wire [63:0] o_kv,
    output wire [3:0] o_last,
    output wire [63:0] o_ref
);
    wire [4*16*544-1:0] i_key;
    wire [64*544-1:0] o_key;
    ot_w11_phys_sin #(.N(4*16*544)) u_in (.clk(clk), .sen(sen), .sin(sin), .q(i_key));
    ot_hdc_v41x_idx_quarter_join dut (
        .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_nkeys(cmd_nkeys), .cmd_skip(cmd_skip), .busy(busy),
        .fault(fault), .i_valid(i_valid), .i_ready(i_ready), .i_kv(i_kv), .i_key(i_key), .o_valid(o_valid),
        .o_ready(o_ready), .o_kv(o_kv), .o_last(o_last), .o_key(o_key), .o_ref(o_ref));
    ot_w11_phys_sout #(.N(64*544)) u_out (.clk(clk), .d(o_key), .q(sout));
endmodule

// the ring K-port with its writer (ot_hdc_v41x_idx_ring_port + ot_hdc_v41x_idx_ring_kwr) as the die
// tile instantiates it at full shape: 30-bit sectors, RSB 64, RTAIL 32, WIDE_REC, READ_FENCE 1
module ot_w11_ring_port_phys (
    input  wire clk, rst_n, sen,
    input  wire [63:0] sin,
    output wire [63:0] sout,
    input  wire w_v,
    output wire w_rdy,
    input  wire [29:0] w_csec, w_ssec,
    input  wire [2:0] w_sslot,
    input  wire [127:0] r_v,
    output wire [127:0] r_rdy,
    output wire [127:0] r_rsp_v,
    input  wire [127:0] r_rsp_rdy,
    output wire [127:0] h_v,
    input  wire [127:0] h_rdy,
    output wire [127:0] h_we,
    input  wire [127:0] h_wr_done,
    input  wire [127:0] h_rsp_v,
    output wire [127:0] h_rsp_rdy,
    output wire busy, fault
);
    localparam integer NP = 128, AW = 30, TW = 16, LW = 4;
    // wide inputs from the chain: the record key, the readers' request fields, the HBM responses
    localparam integer NI = 544 + NP * (AW + LW + TW) + NP * TW + NP * 256;
    wire [NI-1:0] win;
    ot_w11_phys_sin #(.N(NI)) u_in (.clk(clk), .sen(sen), .sin(sin), .q(win));
    wire [543:0]      w_key   = win[543:0];
    wire [NP*AW-1:0]  r_addr  = win[544 +: NP*AW];
    wire [NP*LW-1:0]  r_len   = win[544 + NP*AW +: NP*LW];
    wire [NP*TW-1:0]  r_tag   = win[544 + NP*(AW+LW) +: NP*TW];
    wire [NP*TW-1:0]  rsp_tag = win[544 + NP*(AW+LW+TW) +: NP*TW];
    wire [NP*256-1:0] rsp_d   = win[544 + NP*(AW+LW+2*TW) +: NP*256];
    wire [NP*AW-1:0]  h_addr;
    wire [NP*LW-1:0]  h_len;
    wire [NP*TW-1:0]  h_tag;
    wire [NP*256-1:0] h_wdata;
    wire [NP*32-1:0]  h_wstrb;
    wire [31:0] d0, d1, d2, d3, d4;
    wire [47:0] d5, d6;
    ot_hdc_v41x_idx_ring_port #(.NPC(32), .AW(AW), .TAGW(TW), .LENW(LW), .BEATW(4), .RSB(64), .RTAIL(32),
                                .RFQ(4), .READ_FENCE(1), .WIDE_REC(1)) dut (
        .clk(clk), .rst_n(rst_n), .w_v(w_v), .w_rdy(w_rdy), .w_csec(w_csec), .w_codes(w_key[511:0]),
        .w_ssec(w_ssec), .w_sslot(w_sslot), .w_scales(w_key[543:512]),
        .d_v(1'b0), .d_rdy(), .d_base('0), .d_n('0), .d_key('0),
        .r_v(r_v), .r_rdy(r_rdy), .r_addr(r_addr), .r_len(r_len), .r_tag(r_tag), .r_rsp_v(r_rsp_v),
        .r_rsp_rdy(r_rsp_rdy), .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag),
        .h_we(h_we), .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .h_rsp_v(h_rsp_v),
        .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(rsp_tag), .h_rsp_data(rsp_d), .busy(busy), .fault(fault),
        .dbg_records(d0), .dbg_writes(d1), .dbg_fifo_highwater(d2), .dbg_read_stalls(d3), .dbg_writer_stalls(d4),
        .dbg_migrations(d5), .dbg_copied_sectors(d6));
    ot_w11_phys_sout #(.N(NP * (AW + LW + TW + 256 + 32) + 5 * 32 + 2 * 48)) u_out (.clk(clk),
        .d({h_addr, h_len, h_tag, h_wdata, h_wstrb, d0, d1, d2, d3, d4, d5, d6}), .q(sout));
endmodule

// the reader's datapath: macro ROB (128 x ot_sram_1r1w_128x256_m1_r2c2), fold crossbar, scale buffer,
// output queue (ot_hdc_v41x_idx_kdata_m, one stack)
module ot_w11_kdata_m_phys #(parameter integer XP = 1) (
    input  wire clk, rst_n, sen,
    input  wire [63:0] sin,
    output wire [63:0] sout,
    input  wire [31:0] rsp_v, rsp_rdy,
    input  wire [127:0] rsp_beat,
    input  wire dr_scale, dr_quarter,
    input  wire [6:0] dr_slot,
    input  wire [1:0] dr_q,
    input  wire [4:0] dr_fold, dr_nkeys,
    input  wire [5:0] dr_sidx,
    output wire dr_ready, o_valid,
    input  wire o_ready,
    output wire [15:0] o_kv,
    output wire busy
);
    wire [32*16+32*256-1:0] win;
    ot_w11_phys_sin #(.N(32*16+32*256)) u_in (.clk(clk), .sen(sen), .sin(sin), .q(win));
    wire [16*544-1:0] o_key;
    ot_hdc_v41x_idx_kdata_m #(.NPC(32), .WB(128), .TAGW(16), .BEATW(4), .DW(256), .MACRO(1), .XP(XP)) dut (
        .clk(clk), .rst_n(rst_n), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(win[511:0]), .rsp_beat(rsp_beat),
        .rsp_data(win[512 +: 32*256]), .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot),
        .dr_q(dr_q), .dr_fold(dr_fold), .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready),
        .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_key(o_key), .busy(busy));
    ot_w11_phys_sout #(.N(16*544)) u_out (.clk(clk), .d(o_key), .q(sout));
endmodule
module ot_w11_kdata_m_x1_phys (
    input  wire clk, rst_n, sen, input wire [63:0] sin, output wire [63:0] sout,
    input  wire [31:0] rsp_v, rsp_rdy, input wire [127:0] rsp_beat, input wire dr_scale, dr_quarter,
    input  wire [6:0] dr_slot, input wire [1:0] dr_q, input wire [4:0] dr_fold, dr_nkeys, input wire [5:0] dr_sidx,
    output wire dr_ready, o_valid, input wire o_ready, output wire [15:0] o_kv, output wire busy);
    ot_w11_kdata_m_phys #(.XP(1)) u (.*);
endmodule
module ot_w11_kdata_m_x2_phys (
    input  wire clk, rst_n, sen, input wire [63:0] sin, output wire [63:0] sout,
    input  wire [31:0] rsp_v, rsp_rdy, input wire [127:0] rsp_beat, input wire dr_scale, dr_quarter,
    input  wire [6:0] dr_slot, input wire [1:0] dr_q, input wire [4:0] dr_fold, dr_nkeys, input wire [5:0] dr_sidx,
    output wire dr_ready, o_valid, input wire o_ready, output wire [15:0] o_kv, output wire busy);
    ot_w11_kdata_m_phys #(.XP(2)) u (.*);
endmodule

// the reader's control (ot_hdc_v41x_idx_kctl_ring: 32 request generators, entry state, drain) at the
// die configuration: 30-bit sectors, 23-bit blocks, ROB 128, lookahead 120.  Every port is a top-level
// pin except the return-queue handshake: rsp_v / rsp_tag are captured from and rsp_rdy is captured
// into flip-flops (the ring port's return-queue head and pop registers), so the combinational
// rsp_tag -> rsp_rdy gate is timed register to register instead of from an unbudgeted input to an
// unbudgeted output.  rsp_beat is not read by the control.
module ot_w11_kctl_ring_phys (
    input  wire clk, rst_n,
    input  wire cmd_v,
    input  wire [22:0] cmd_base, cmd_base2,
    input  wire [9:0] cmd_skip,
    input  wire [32:0] cmd_nkeys, cmd_nkeys2,
    output wire busy,
    output wire [31:0] req_v,
    input  wire [31:0] req_rdy,
    output wire [32*30-1:0] req_addr,
    output wire [32*4-1:0] req_len,
    output wire [32*16-1:0] req_tag,
    input  wire [31:0] rsp_v,
    output reg  [31:0] rsp_rdy_q,
    input  wire [32*16-1:0] rsp_tag,
    output wire dr_scale, dr_quarter,
    output wire [6:0] dr_slot,
    output wire [1:0] dr_q,
    output wire [4:0] dr_fold, dr_nkeys,
    output wire [5:0] dr_sidx,
    input  wire dr_ready
);
    reg  [31:0] rsp_v_q;
    reg  [32*16-1:0] rsp_tag_q;
    wire [31:0] rsp_rdy;
    always @(posedge clk) begin
        rsp_v_q <= rsp_v; rsp_tag_q <= rsp_tag; rsp_rdy_q <= rsp_rdy;
    end
    ot_hdc_v41x_idx_kctl_ring #(.NPC(32), .WB(128), .GA(120), .AW(30), .HW(23), .TAGW(16), .LENW(4), .BEATW(4)) dut (
        .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_base(cmd_base), .cmd_skip(cmd_skip), .cmd_nkeys(cmd_nkeys),
        .cmd_base2(cmd_base2), .cmd_nkeys2(cmd_nkeys2), .busy(busy), .req_v(req_v), .req_rdy(req_rdy),
        .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag), .rsp_v(rsp_v_q), .rsp_rdy(rsp_rdy),
        .rsp_tag(rsp_tag_q), .rsp_beat('0), .dr_scale(dr_scale), .dr_quarter(dr_quarter), .dr_slot(dr_slot),
        .dr_q(dr_q), .dr_fold(dr_fold), .dr_sidx(dr_sidx), .dr_nkeys(dr_nkeys), .dr_ready(dr_ready));
endmodule

// the quarter join with its handshakes captured in flip-flops: i_valid / o_ready come from, and
// i_ready goes to, registers (the streams' queue heads and the consumer's), so the combinational
// i_valid / o_ready -> take -> i_ready and beat-enable paths are timed register to register rather
// than between unbudgeted top-level pins.  Data buses as ot_w11_quarter_join_phys.
module ot_w11_join_hs_phys (
    input  wire clk, rst_n, sen,
    input  wire [63:0] sin,
    output wire [63:0] sout,
    input  wire cmd_v,
    input  wire [29:0] cmd_nkeys,
    input  wire [39:0] cmd_skip,
    output wire busy, fault,
    input  wire [3:0] i_valid,
    output reg  [3:0] i_ready_q,
    input  wire [63:0] i_kv,
    output wire o_valid,
    input  wire o_ready,
    output wire [63:0] o_kv,
    output wire [3:0] o_last,
    output wire [63:0] o_ref
);
    wire [4*16*544-1:0] i_key;
    wire [64*544-1:0] o_key;
    reg  [3:0] i_valid_q;
    reg  o_ready_q;
    wire [3:0] i_ready;
    always @(posedge clk) begin i_valid_q <= i_valid; o_ready_q <= o_ready; i_ready_q <= i_ready; end
    ot_w11_phys_sin #(.N(4*16*544)) u_in (.clk(clk), .sen(sen), .sin(sin), .q(i_key));
    ot_hdc_v41x_idx_quarter_join dut (
        .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_nkeys(cmd_nkeys), .cmd_skip(cmd_skip), .busy(busy),
        .fault(fault), .i_valid(i_valid_q), .i_ready(i_ready), .i_kv(i_kv), .i_key(i_key), .o_valid(o_valid),
        .o_ready(o_ready_q), .o_kv(o_kv), .o_last(o_last), .o_key(o_key), .o_ref(o_ref));
    ot_w11_phys_sout #(.N(64*544)) u_out (.clk(clk), .d(o_key), .q(sout));
endmodule

// the ring K-port with its writer, NARROW wrapper: the 128 ports' reader request fields
// (r_addr / r_len / r_tag) and HBM response fields (h_rsp_tag / h_rsp_data) are driven from 8
// chain-loaded bases per field, port p taking base p mod 8 rotated by p / 8 bits (every port's
// bus distinct and each port mux keeps its full width, sources fan out 16 ways instead of 1),
// and the write data / strobe, which the writer broadcasts identically to all 128 ports, are
// observed at port 0 only (reducing 128 identical copies through the XOR tree cancels them).
// 3,120 chain flops instead of 42,016.
module ot_w11_ring_port_nphys (
    input  wire clk, rst_n, sen,
    input  wire [63:0] sin,
    output wire [63:0] sout,
    input  wire w_v,
    output wire w_rdy,
    input  wire [29:0] w_csec, w_ssec,
    input  wire [2:0] w_sslot,
    input  wire [127:0] r_v,
    output wire [127:0] r_rdy,
    output wire [127:0] r_rsp_v,
    input  wire [127:0] r_rsp_rdy,
    output wire [127:0] h_v,
    input  wire [127:0] h_rdy,
    output wire [127:0] h_we,
    input  wire [127:0] h_wr_done,
    input  wire [127:0] h_rsp_v,
    output wire [127:0] h_rsp_rdy,
    output wire busy, fault
);
    localparam integer NP = 128, AW = 30, TW = 16, LW = 4, G = 8;
    localparam integer NI = 544 + G * (AW + LW + TW + TW + 256);
    wire [NI-1:0] win;
    ot_w11_phys_sin #(.N(NI)) u_in (.clk(clk), .sen(sen), .sin(sin), .q(win));
    wire [543:0] w_key = win[543:0];
    wire [G*AW-1:0]  b_addr = win[544 +: G*AW];
    wire [G*LW-1:0]  b_len  = win[544 + G*AW +: G*LW];
    wire [G*TW-1:0]  b_tag  = win[544 + G*(AW+LW) +: G*TW];
    wire [G*TW-1:0]  b_rtag = win[544 + G*(AW+LW+TW) +: G*TW];
    wire [G*256-1:0] b_dat  = win[544 + G*(AW+LW+2*TW) +: G*256];
    wire [NP*AW-1:0]  r_addr;
    wire [NP*LW-1:0]  r_len;
    wire [NP*TW-1:0]  r_tag, rsp_tag;
    wire [NP*256-1:0] rsp_d;
    genvar gp, gj;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
        localparam integer GG = gp % G, RT = gp / G;
        for (gj = 0; gj < AW; gj = gj + 1) begin : g_a
            assign r_addr[gp*AW + gj] = b_addr[GG*AW + (gj + RT) % AW];
        end
        for (gj = 0; gj < LW; gj = gj + 1) begin : g_l
            assign r_len[gp*LW + gj] = b_len[GG*LW + (gj + RT) % LW];
        end
        for (gj = 0; gj < TW; gj = gj + 1) begin : g_t
            assign r_tag[gp*TW + gj] = b_tag[GG*TW + (gj + RT) % TW];
            assign rsp_tag[gp*TW + gj] = b_rtag[GG*TW + (gj + RT) % TW];
        end
        for (gj = 0; gj < 256; gj = gj + 1) begin : g_d
            assign rsp_d[gp*256 + gj] = b_dat[GG*256 + (gj + RT) % 256];
        end
    end endgenerate
    wire [NP*AW-1:0]  h_addr;
    wire [NP*LW-1:0]  h_len;
    wire [NP*TW-1:0]  h_tag;
    wire [NP*256-1:0] h_wdata;
    wire [NP*32-1:0]  h_wstrb;
    wire [31:0] d0, d1, d2, d3, d4;
    wire [47:0] d5, d6;
    ot_hdc_v41x_idx_ring_port #(.NPC(32), .AW(AW), .TAGW(TW), .LENW(LW), .BEATW(4), .RSB(64), .RTAIL(32),
                                .RFQ(4), .READ_FENCE(1), .WIDE_REC(1)) dut (
        .clk(clk), .rst_n(rst_n), .w_v(w_v), .w_rdy(w_rdy), .w_csec(w_csec), .w_codes(w_key[511:0]),
        .w_ssec(w_ssec), .w_sslot(w_sslot), .w_scales(w_key[543:512]),
        .d_v(1'b0), .d_rdy(), .d_base('0), .d_n('0), .d_key('0),
        .r_v(r_v), .r_rdy(r_rdy), .r_addr(r_addr), .r_len(r_len), .r_tag(r_tag), .r_rsp_v(r_rsp_v),
        .r_rsp_rdy(r_rsp_rdy), .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag),
        .h_we(h_we), .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .h_rsp_v(h_rsp_v),
        .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(rsp_tag), .h_rsp_data(rsp_d), .busy(busy), .fault(fault),
        .dbg_records(d0), .dbg_writes(d1), .dbg_fifo_highwater(d2), .dbg_read_stalls(d3), .dbg_writer_stalls(d4),
        .dbg_migrations(d5), .dbg_copied_sectors(d6));
    ot_w11_phys_sout #(.N(NP * (AW + LW + TW) + 256 + 32 + 5 * 32 + 2 * 48)) u_out (.clk(clk),
        .d({h_addr, h_len, h_tag, h_wdata[255:0], h_wstrb[31:0], d0, d1, d2, d3, d4, d5, d6}), .q(sout));
endmodule
