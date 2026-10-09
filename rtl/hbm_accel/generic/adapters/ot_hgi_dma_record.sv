`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA record adapter (hgi-adapters, 2026-10-09).  Unit 8 (DMA.LOAD / STORE / FENCE / KVWB_DS) of the normative
// sequencer dispatch onto a ROW-MOVE command port and a FENCE port of the die's DMA mover.  Decode + handshake only:
// the mover (svc native read / write clients + the VM packet client + the element format converters) is the engine.
//
// Move command (one per LOAD / STORE / KVWB_DS record):
//   227 b, LSB first: {src space 2, src fmt 3, src base 40, src stride 32, src istride 16, dst space 2, dst fmt 3,
//    dst base 40, dst stride 32, dst istride 16, m 20, n 21}  (spec 6.4 fields of the EFFECTIVE descriptors: the CP has already
//   applied L / L1 / DYN / the indexed id; istride 0 means 1, ibcast means 0)
//   LOAD  (op 0): A (HBM, or VM) -> O (VM); A.fmt in {FP32, BF16, FP8E4M3, INT8, U32} (decoded to the O word), O.fmt in
//                 {FP32, U32}, U32 only from U32 (hgi_sim u_dma_load);
//   STORE (op 1): A (VM, FP32 / U32) -> O (HBM, FP32 / BF16 / FP8E4M3 / U32) (hgi_sim u_dma_store, encode_fmt);
//   KVWB_DS (op 3): the DS window-ring write-back: A (VM, one row) -> slot (POS mod O.m) of ring O (HBM): dst base =
//                 O.base + (POS mod O.m) * O.stride, m 1.  POS = d_pos1 - 1; O.m must be a power of two (the DS ring).
//                 The product is a radix-16 iterative multiply (5 digits) -> KVWB issues 6 edges after decode.
//   n = effective n of A, which must equal O's; m = A.m = O.m (KVWB: A.m 1).
// FENCE (op 2): the fence port; the record retires when the mover reports every DMA write before it visible.
// Retire = the mover's done for the move (in order: one move outstanding) / fence_done.  Refusals (rec_fault, sticky
// halt): unit != 8, op > 3, a missing / wrong-space / wrong-format operand, n or m mismatch, KVWB ring not a power of 2.
// Latency: accept E0, decode E1, move_v E2 (KVWB: E7).  LEGACY = 1 adds the static legacy pass-through on both ports.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_record #(
    parameter integer MUT_SLOT = 0,       // mutant: KVWB slot = POS (no ring wrap)
    parameter integer MUT_EARLY = 0,      // mutant: retire on issue
    parameter integer LEGACY = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hgi_en,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_o,
    input  wire [20:0]   rec_n_a, rec_n_o,
    input  wire [20:0]   rec_pos1,
    output reg           rec_done,
    output reg           rec_fault,
    output wire          halted,
    // legacy (DS control path) mover / fence ports
    input  wire          lg_mv_v,
    output wire          lg_mv_rdy,
    input  wire [226:0]  lg_mv,
    input  wire          lg_fence_v,
    output wire          lg_fence_rdy,
    // mover ports
    output wire          mv_v,
    input  wire          mv_rdy,
    output wire [226:0]  mv,
    input  wire          mv_done,
    input  wire          mv_fault,
    output wire          fence_v,
    input  wire          fence_rdy,
    input  wire          fence_done
);
    wire hen = LEGACY ? hgi_en : 1'b1;
    reg          raw_v, busy, halt_q, iss, is_fence, kv, kv_iss, mul_run;
    reg  [127:0] hdr_q; reg [255:0] a_q, o_q; reg [20:0] na_q, no_q, pos1_q;
    reg  [226:0] mv_q;
    reg  [2:0]   dig;
    reg  [19:0]  slot; reg [31:0] ost; reg [51:0] prod;
    reg          in_done, in_fault, in_fdone;
    always @(posedge clk) begin in_done <= mv_done; in_fault <= mv_fault; in_fdone <= fence_done; end
    assign halted = halt_q;
    assign rec_rdy = hen && !raw_v && !busy && !halt_q;
    assign mv_v    = hen ? (iss && !is_fence) : lg_mv_v;
    assign mv      = hen ? mv_q : lg_mv;
    assign lg_mv_rdy = !hen && mv_rdy;
    assign fence_v = hen ? (iss && is_fence) : lg_fence_v;
    assign lg_fence_rdy = !hen && fence_rdy;
    // ---- decode
    wire [5:0] op = hdr_q[123:118];
    wire [6:0] opnd = hdr_q[99:93];
    wire [1:0] as = a_q[1:0], os = o_q[1:0];
    wire [2:0] af = a_q[4:2], of = o_q[4:2];
    wire [19:0] om = o_q[87:68];
    wire a_ok_load  = (as == 2'd0 || as == 2'd1) && (af == 3'd0 || af == 3'd1 || af == 3'd2 || af == 3'd4 || af == 3'd5);
    wire o_ok_load  = os == 2'd1 && (of == 3'd0 || of == 3'd5) && ((of == 3'd5) == (af == 3'd5));
    wire a_ok_store = as == 2'd1 && (af == 3'd0 || af == 3'd5);
    wire o_ok_store = os == 2'd0 && (of == 3'd0 || of == 3'd1 || of == 3'd2 || of == 3'd5) && ((of == 3'd5) == (af == 3'd5));
    wire shape_ok   = (na_q == no_q) && (a_q[87:68] == om);
    wire kv_ok      = (om != 20'd0) && ((om & (om - 20'd1)) == 20'd0) && (na_q == no_q) && (a_q[87:68] == 20'd1);
    wire bad = (hdr_q[127:124] != 4'd8) || (op > 6'd3) ||
               (op == 6'd0 && !(opnd[0] && opnd[4] && a_ok_load && o_ok_load && shape_ok)) ||
               (op == 6'd1 && !(opnd[0] && opnd[4] && a_ok_store && o_ok_store && shape_ok)) ||
               (op == 6'd3 && !(opnd[0] && opnd[4] && a_ok_store && o_ok_store && kv_ok));
    function automatic [15:0] ist(input [255:0] d);
        ist = d[5] ? 16'd0 : (d[135:120] == 16'd0) ? 16'd1 : d[135:120];
    endfunction
    wire [20:0] pos = pos1_q - 21'd1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            raw_v <= 1'b0; busy <= 1'b0; halt_q <= 1'b0; iss <= 1'b0; is_fence <= 1'b0; kv <= 1'b0; kv_iss <= 1'b0; mul_run <= 1'b0;
            rec_done <= 1'b0; rec_fault <= 1'b0; hdr_q <= 0; a_q <= 0; o_q <= 0; na_q <= 0; no_q <= 0; pos1_q <= 0;
            mv_q <= 0; dig <= 0; slot <= 0; ost <= 0; prod <= 0;
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0;
            hdr_q <= rec_hdr; a_q <= rec_a; o_q <= rec_o; na_q <= rec_n_a; no_q <= rec_n_o; pos1_q <= rec_pos1;  // pin flops
            if (rec_v && rec_rdy) raw_v <= 1'b1;
            if (raw_v) begin                                   // E1
                raw_v <= 1'b0;
                if (bad) begin rec_fault <= 1'b1; halt_q <= 1'b1; end
                else begin
                    busy <= 1'b1; is_fence <= (op == 6'd2); kv <= (op == 6'd3); kv_iss <= 1'b0;
                    mv_q <= {na_q, a_q[87:68], ist(o_q), o_q[119:88], o_q[47:8], of, os,
                             ist(a_q), a_q[119:88], a_q[47:8], af, as};
                    if (op == 6'd3) begin
                        slot <= MUT_SLOT ? pos[19:0] : (pos[19:0] & (om - 20'd1)); ost <= o_q[119:88];
                        prod <= 52'd0; dig <= 3'd5; mul_run <= 1'b1;
                    end else iss <= 1'b1;
                end
            end
            if (mul_run) begin                                 // dst base = O.base + slot * O.stride
                dig <= dig - 3'd1;
                prod <= (prod << 4) + ost * slot[4*(dig - 1) +: 4];
                if (dig == 3'd1) mul_run <= 1'b0;
            end
            if (kv && busy && !mul_run && !kv_iss && dig == 3'd0) begin   // fields: o base [137:98], m [205:186]
                mv_q[137:98] <= mv_q[137:98] + prod[39:0]; mv_q[205:186] <= 20'd1; iss <= 1'b1; kv_iss <= 1'b1;
            end
            if (iss && ((!is_fence && mv_rdy) || (is_fence && fence_rdy)) && hen) begin
                iss <= 1'b0;
                if (MUT_EARLY) begin rec_done <= 1'b1; busy <= 1'b0; kv <= 1'b0; end
            end
            if (busy && !iss && !mul_run && (!kv || kv_iss)) begin
                if (!is_fence && in_fault) begin rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; end
                else if ((!is_fence && in_done) || (is_fence && in_fdone)) begin
                    rec_done <= 1'b1; busy <= 1'b0; kv <= 1'b0;
                end
            end
        end
    end
endmodule
`default_nettype wire
