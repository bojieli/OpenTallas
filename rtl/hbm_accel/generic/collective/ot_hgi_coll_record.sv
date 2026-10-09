`timescale 1ns/1ps
// HGI-1 collective record binding (hgi-takeover, 2026-10-09).
//
// Binds one normative record from the HGI-1 sequencer (ot_hgi_seq, main ef3135b44: u_v / u_rdy, d_hdr, d_desc
// {I,R,O,D,C,B,A}, d_n 7 x 21, u_done / u_fault) to the collective engine.  The die taps unit 6 of the dispatch:
// header, the A, O and I effective descriptors and their effective counts (960 bits, tools/hgi_die_dispatch.py).
//
//   record station (registered) -> ot_hgi_coll_decode (unchanged, GX11 reject) -> backend:
//     ALL_REDUCE_SUM (op 0), GROUP_REDUCE_MCAST (op 4): endpoint control {rank, gsz, mcast_all, mcast_group_size,
//                       pf = A.n / 16 flits}, go / start_ready, done_valid / done_ready, fault / fault_ack;
//                       A and O effective bases go to the SU inject / deliver addressing (ep_a_base, ep_o_base).
//     ROW_GATHER (op 5): row formatter start {G, B, destinations, row count, row words = ceil(A.n * bits(A.fmt) /
//                       512), context rows = A.m}, done / fault.
//     ALL_GATHER, TOPK_MERGE, ARGMAX_MERGE (ops 1-3): no generic backend is installed on this collective yet; the
//                       record retires with u_fault (fail-closed, no silent completion).
//   Any decode error, endpoint fault or formatter fault retires the record with u_fault (sticky until rst_n: the CP
//   halts; recovery is the drained reset, HGI-1 MX-1).
//
// Every output is a flop; every input is captured before use.  Added edges: record station 1 + decode 2 (priced in
// ot_hgi_coll_decode) + backend issue 1; completion 1.
module ot_hgi_coll_record #(
    parameter integer MUT_PF = 0,          // mutant: pf from A.n without the /16 flit conversion
    parameter integer MUT_DONE = 0         // mutant: retire on issue instead of on endpoint completion
) (
    input  wire          clk,
    input  wire          rst_n,
    // static configuration (config master)
    input  wire [7:0]    cfg_coll_group_size,
    input  wire [7:0]    cfg_die_id,
    // record (unit 6 of the sequencer dispatch)
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a,
    input  wire [255:0]  rec_o,
    input  wire [255:0]  rec_i,
    input  wire [20:0]   rec_n_a,
    input  wire [20:0]   rec_n_o,
    input  wire [20:0]   rec_n_i,
    output reg           rec_done,
    output reg           rec_fault,
    // collective endpoint control (ot_hbm_accel_tu_endpoint_psg)
    output reg  [7:0]    ep_rank,
    output reg  [7:0]    ep_mcast_group_size,
    output reg           ep_mcast_all,
    output reg  [3:0]    ep_gsz,
    output reg           ep_byp,         // exact gather bypass (ALL_GATHER)
    output reg  [15:0]   ep_pf,
    output reg           ep_go,
    input  wire          ep_start_ready,
    input  wire          ep_done_valid,
    output reg           ep_done_ready,
    input  wire          ep_fault,
    output reg  [39:0]   ep_a_base,
    output reg  [39:0]   ep_o_base,
    // row formatter (ot_hgi_coll_row_formatter)
    output reg           rf_start_v,
    input  wire          rf_start_r,
    output reg  [7:0]    rf_group_size,
    output reg  [7:0]    rf_owner_block,
    output reg  [7:0]    rf_destinations,
    output reg  [20:0]   rf_row_count,
    output reg  [15:0]   rf_row_words,
    output reg  [31:0]   rf_context_rows,
    input  wire          rf_done_v,
    output reg           rf_done_r,
    input  wire          rf_fault
);
    localparam S_IDLE = 3'd0, S_DEC = 3'd1, S_WAITDEC = 3'd2, S_EPGO = 3'd3, S_EPRUN = 3'd4, S_RFGO = 3'd5,
               S_RFRUN = 3'd6, S_HALT = 3'd7;
    reg [2:0] st;
    // record station
    reg [127:0] hdr_q;
    reg [255:0] a_q, i_q;
    reg [39:0]  o_base_q;
    reg [20:0]  n_a_q, n_i_q;
    reg [7:0]   g_q, die_q;
    reg         in_ep_fault, in_ep_done, in_ep_ready, in_rf_start_r, in_rf_done, in_rf_fault;
    always @(posedge clk) begin
        in_ep_fault <= ep_fault; in_ep_done <= ep_done_valid; in_ep_ready <= ep_start_ready;
        in_rf_start_r <= rf_start_r; in_rf_done <= rf_done_v; in_rf_fault <= rf_fault;
        g_q <= cfg_coll_group_size; die_q <= cfg_die_id;
    end
    assign rec_rdy = (st == S_IDLE);
    wire [6:0] opnd = hdr_q[99:93];
    // decoder (count from the I table when I's n_sel is N_FROM_VM: the sequencer resolved it into rec_n_i)
    wire        dc_cmd_r, dc_bv, dc_ev;
    wire [5:0]  dc_op;
    wire [3:0]  dc_gsz;
    wire [7:0]  dc_g, dc_rank, dc_group, dc_sub, dc_blk, dc_dest;
    wire [20:0] dc_rows;
    reg         dc_cmd_v;
    ot_hgi_coll_decode #(.ENABLE(1)) u_dec (
        .clk(clk), .rst_n(rst_n), .coll_group_size(g_q), .die_id(die_q),
        .cmd_v(dc_cmd_v), .cmd_r(dc_cmd_r), .hdr(hdr_q),
        .selected_count({11'd0, n_i_q}), .selected_count_valid(opnd[6] && i_q[206:201] == 6'd63),
        .backend_v(dc_bv), .backend_r(st == S_WAITDEC), .backend_op(dc_op), .backend_gsz(dc_gsz),
        .backend_group_size(dc_g), .backend_rank(dc_rank), .backend_group(dc_group), .backend_subgroup(dc_sub),
        .backend_owner_block(dc_blk), .backend_destinations(dc_dest), .backend_row_count(dc_rows),
        .error_v(dc_ev), .error_r(st == S_WAITDEC));
    // A row length in 512-bit words: n * bits(fmt) / 512, rounded up
    wire [2:0]  a_fmt = a_q[4:2];
    wire [5:0]  a_bits = (a_fmt == 3'd0 || a_fmt == 3'd5) ? 6'd32 : (a_fmt == 3'd1) ? 6'd16 : (a_fmt == 3'd3) ? 6'd4 : 6'd8;
    wire [25:0] a_rowbits = n_a_q * a_bits;
    wire [16:0] a_rowwords = (a_rowbits + 26'd511) >> 9;
    wire        pf_bad = (n_a_q[3:0] != 4'd0) || (n_a_q == 21'd0) || (n_a_q[20:4] > 17'hFFFF);
    // ALL_GATHER (bypass): pf = A row bits / 512 in any element format; a partial flit or an empty row faults
    wire        pfg_bad = (a_rowbits[8:0] != 9'd0) || (n_a_q == 21'd0) || (a_rowwords > 17'hFFFF);
    // endpoint rank = the die's position on the 96-rank TU fabric (die mod 96: groups of 1..8 stay aligned)
    wire [7:0]  rank96 = (die_q >= 8'd192) ? die_q - 8'd192 : (die_q >= 8'd96) ? die_q - 8'd96 : die_q;
    // GROUP_REDUCE_MCAST: the endpoint's gsz is the reduction sub-group s (2 / 4 / 8), the outer group is G
    wire [3:0]  sub_gsz = (dc_sub == 8'd2) ? 4'd1 : (dc_sub == 8'd4) ? 4'd2 : 4'd3;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; dc_cmd_v <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0;
            ep_go <= 1'b0; ep_done_ready <= 1'b0; rf_start_v <= 1'b0; rf_done_r <= 1'b0;
            ep_rank <= 8'd0; ep_mcast_group_size <= 8'd96; ep_mcast_all <= 1'b0; ep_gsz <= 4'hF; ep_pf <= 16'd0; ep_byp <= 1'b0;
            ep_a_base <= 40'd0; ep_o_base <= 40'd0;
            rf_group_size <= 8'd96; rf_owner_block <= 8'd8; rf_destinations <= 8'd0; rf_row_count <= 21'd0;
            rf_row_words <= 16'd0; rf_context_rows <= 32'd0;
            hdr_q <= 128'd0; a_q <= 256'd0; i_q <= 256'd0; o_base_q <= 40'd0; n_a_q <= 21'd0; n_i_q <= 21'd0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; ep_go <= 1'b0; ep_done_ready <= 1'b0; rf_done_r <= 1'b0;
            case (st)
                S_IDLE: if (rec_v) begin
                    hdr_q <= rec_hdr; a_q <= rec_a; i_q <= rec_i; o_base_q <= rec_o[47:8];
                    n_a_q <= rec_n_a; n_i_q <= rec_n_i; st <= S_DEC;
                end
                S_DEC: begin dc_cmd_v <= 1'b1; if (dc_cmd_v && dc_cmd_r) begin dc_cmd_v <= 1'b0; st <= S_WAITDEC; end end
                S_WAITDEC: if (dc_ev) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (dc_bv) begin
                        if (dc_op == 6'd0 || dc_op == 6'd4) begin
                            if (pf_bad) begin rec_fault <= 1'b1; st <= S_HALT; end
                            else begin
                                ep_rank <= rank96; ep_gsz <= (dc_op == 6'd4) ? sub_gsz : dc_gsz; ep_mcast_all <= (dc_op == 6'd4);
                                ep_mcast_group_size <= dc_g; ep_byp <= 1'b0;
                                ep_pf <= MUT_PF ? n_a_q[15:0] : n_a_q[19:4];
                                ep_a_base <= a_q[47:8]; ep_o_base <= o_base_q; st <= S_EPGO;
                            end
                        end else if (dc_op == 6'd1) begin   // ALL_GATHER: exact bypass over the group (G = 96: outer group)
                            if (pfg_bad) begin rec_fault <= 1'b1; st <= S_HALT; end
                            else begin
                                ep_rank <= rank96; ep_byp <= 1'b1;
                                ep_gsz <= (dc_g == 8'd96) ? 4'd3 : dc_gsz; ep_mcast_all <= (dc_g == 8'd96);
                                ep_mcast_group_size <= dc_g;
                                ep_pf <= MUT_PF ? n_a_q[15:0] : a_rowwords[15:0];
                                ep_a_base <= a_q[47:8]; ep_o_base <= o_base_q; st <= S_EPGO;
                            end
                        end else if (dc_op == 6'd5) begin
                            rf_group_size <= dc_g; rf_owner_block <= dc_blk; rf_destinations <= dc_dest;
                            rf_row_count <= dc_rows; rf_row_words <= a_rowwords[15:0];
                            rf_context_rows <= {12'd0, a_q[87:68]}; rf_start_v <= 1'b1; st <= S_RFGO;
                        end else begin rec_fault <= 1'b1; st <= S_HALT; end   // ops 2-3: merge stage not installed yet
                    end
                S_EPGO: if (in_ep_fault) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (in_ep_ready) begin
                        ep_go <= 1'b1;
                        if (MUT_DONE) begin rec_done <= 1'b1; st <= S_IDLE; end else st <= S_EPRUN;
                    end
                S_EPRUN: if (in_ep_fault) begin rec_fault <= 1'b1; st <= S_HALT; end
                    else if (in_ep_done && !ep_done_ready) begin ep_done_ready <= 1'b1; rec_done <= 1'b1; st <= S_IDLE; end
                S_RFGO: if (in_rf_start_r) begin rf_start_v <= 1'b0; st <= S_RFRUN; end
                S_RFRUN: if (in_rf_done && !rf_done_r) begin
                        rf_done_r <= 1'b1;
                        if (in_rf_fault) begin rec_fault <= 1'b1; st <= S_HALT; end
                        else begin rec_done <= 1'b1; st <= S_IDLE; end
                    end
                S_HALT: ;   // sticky: the CP halts; only rst_n (drained reset) leaves
                default: st <= S_HALT;
            endcase
        end
    end
endmodule
