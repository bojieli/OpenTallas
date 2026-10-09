`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 ARGMAX record adapter (hgi-adapters, 2026-10-09).  Unit 7 (ARGMAX.LOCAL) on the die's normative record bus
// (tools/hgi_die_dispatch.py 'argmax' = {n_O 21, n_A 21, desc_O 256, desc_A 256, header 128, valid}, 683 b, bit 0 first,
// return {fault, done, ready}) onto the EXISTING argmax engine ot_hgi_argmax18_m (GENERIC18 = 1, LP = 8: numpy argmax,
// lowest index on ties, the first NaN wins and is flagged, global id = local + RANK * imm_a) and one hfd_hgi_vm packet
// client (req {v, we, byte address, wdata 256, mask 32, tag 16} / rsp {v, tag, we, rdata 256}, one outstanding).
//   A (logits): VM FP32 one row (A.m 1, inner contiguous): read sector by sector, each 256-b sector IS one engine beat of
//     8 lanes (mask = the words of [A.base, A.base + n) in the sector); or STREAM: the su_red logit stream (the die's
//     523-b ARGMAX STREAM {in_v, in_last, mask 8, vals 256, bias 256, bias_en}) is passed to the engine for this record.
//   The engine's local index counts from the first sector's word 0, so id = engine id - (A.base mod 8).
//   O: VM, 2 words {value (FP32 bits), id (U32)} at O.base, O.base + O.istride (spec 6.6), written as word-masked
//     sector writes (one per word).
// Retire after both O words are written (the VM write responses).  Faults (rec fault + halt): unit != 7, op != 0, A / O
//   absent, A not VM / STREAM or not FP32, A.m != 1, A inner stride != 1, n = 0, O not VM, imm_a >= 2^18, the engine's
//   range fault (id >= 2^18).  A NaN row is NOT a fault (numpy semantics): it raises the sticky nan_flag.
// Latency: accept E0 (input register), decode E1, first VM read request E2.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_argmax_record #(
    parameter integer MUT_OFFSET = 0      // mutant: no A.base mod 8 correction
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    cfg_rank,
    input  wire [682:0]  rec,
    output reg  [2:0]    ret,             // {fault, done, ready}
    output reg           nan_flag,
    // VM packet client
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    // logit STREAM from su_red (used when A.space = STREAM)
    input  wire [522:0]  am_stream,
    // the engine (ot_hgi_argmax18_m GENERIC18 = 1, LP = 8)
    output reg           e_in_v, e_in_last, e_bias_en,
    output reg  [7:0]    e_mask,
    output reg  [255:0]  e_vals, e_bias,
    output reg  [6:0]    e_rank,
    output reg  [17:0]   e_imm,
    input  wire          e_out_v,
    input  wire [17:0]   e_out_idx,
    input  wire          e_out_nan, e_fault, e_range_fault,
    input  wire [31:0]   e_out_value
);
    reg busy, halt_q, stream_m;
    reg [127:0] hdr; reg [255:0] dA, dO; reg [20:0] nA;
    wire [39:0] a_base = dA[47:8];
    wire [39:0] o_base = dO[47:8];
    wire [15:0] o_is = dO[5] ? 16'd0 : (dO[135:120] == 16'd0) ? 16'd1 : dO[135:120];
    reg [682:0] rq; reg raw_v;              // input register (the record bus lands in a flop; decode next edge)
    wire [127:0] rh = rq[128:1];             // rec bit 0 = valid, header = rec[128:1]
    wire [255:0] rA = rq[384:129], rO = rq[640:385];
    wire [20:0]  rnA = rq[661:641];
    wire bad = (rh[127:124] != 4'd7) || (rh[123:118] != 6'd0) || !rh[93] || !rh[97] ||
               !(rA[1:0] == 2'd1 || rA[1:0] == 2'd2) || (rA[4:2] != 3'd0) || (rA[87:68] != 20'd1) ||
               (rA[1:0] == 2'd1 && (rA[5] || rA[135:120] > 16'd1)) || (rnA == 21'd0) || (rO[1:0] != 2'd1) ||
               (|rh[63:50]);
    // ---- reader state
    reg [39:0] w_end;                    // one past the last word
    reg [34:0] sec, sec_last;
    reg rd_pend, rd_done_all, got_out, wr_phase, wr_pend;
    reg [31:0] res_val, res_id;
    reg [1:0] wr_n;
    wire [39:0] sec_w0 = {sec, 3'b000};
    integer j;
    reg [7:0] msk;
    always @* begin
        for (j = 0; j < 8; j = j + 1)
            msk[j] = ({sec, 3'b000} + j >= a_base) && ({sec, 3'b000} + j < w_end);
    end
    // engine / VM inputs land in flops (registered boundary): the response and the result are used one edge later
    reg [273:0] vr; reg eo_v, eo_nan, eo_f, eo_rf; reg [17:0] eo_idx; reg [31:0] eo_val;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vr <= 274'd0; eo_v <= 1'b0; end
        else begin vr <= vmr; eo_v <= e_out_v; end
    always @(posedge clk) begin eo_nan <= e_out_nan; eo_f <= e_fault; eo_rf <= e_range_fault; eo_idx <= e_out_idx; eo_val <= e_out_value; end
    wire [39:0] wa = wr_n[0] ? (o_base + {24'd0, o_is}) : o_base;         // word address of the write in flight
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; halt_q <= 1'b0; ret <= 3'b001; raw_v <= 1'b0; rq <= 683'd0; nan_flag <= 1'b0; vmq <= 338'd0; stream_m <= 1'b0;
            e_in_v <= 1'b0; e_in_last <= 1'b0; e_bias_en <= 1'b0; e_mask <= 8'd0; e_vals <= 256'd0; e_bias <= 256'd0;
            e_rank <= 7'd0; e_imm <= 18'd0; rd_pend <= 1'b0; rd_done_all <= 1'b0; got_out <= 1'b0; wr_phase <= 1'b0;
            wr_pend <= 1'b0; wr_n <= 2'd0; hdr <= 0; dA <= 0; dO <= 0; nA <= 0; sec <= 0; sec_last <= 0; w_end <= 0;
            res_val <= 0; res_id <= 0;
        end else begin
            ret[2:1] <= 2'b00; vmq[337] <= 1'b0; e_in_v <= 1'b0; e_in_last <= 1'b0;
            if (rec[0] && ret[0]) begin ret[0] <= 1'b0; raw_v <= 1'b1; rq <= rec; end      // E0 accept (ready = idle)
            if (raw_v) begin                                                     // E1 decode
                raw_v <= 1'b0;
                if (bad) begin ret[2] <= 1'b1; halt_q <= 1'b1; end
                else begin
                    busy <= 1'b1; hdr <= rh; dA <= rA; dO <= rO; nA <= rnA; stream_m <= (rA[1:0] == 2'd2);
                    e_rank <= cfg_rank[6:0]; e_imm <= rh[49:32];
                    w_end <= rA[47:8] + {19'd0, rnA}; sec <= rA[47:11]; sec_last <= (rA[47:8] + {19'd0, rnA} - 40'd1) >> 3;
                    rd_pend <= 1'b0; rd_done_all <= 1'b0; got_out <= 1'b0; wr_phase <= 1'b0; wr_pend <= 1'b0; wr_n <= 2'd0;
                end
            end
            if (busy && !stream_m && !rd_done_all && !rd_pend) begin              // read request: sector sec
                vmq <= {1'b1, 1'b0, sec[26:0], 5'd0, 256'd0, 32'd0, 16'h7A00}; rd_pend <= 1'b1;
            end
            if (busy && rd_pend && vr[273] && !vr[256]) begin                  // read response: one engine beat
                rd_pend <= 1'b0; e_in_v <= 1'b1; e_vals <= vr[255:0]; e_mask <= msk; e_bias_en <= 1'b0;
                e_in_last <= (sec == sec_last);
                if (sec == sec_last) rd_done_all <= 1'b1; else sec <= sec + 35'd1;
            end
            if (busy && stream_m && !rd_done_all && am_stream[0]) begin           // STREAM beats from su_red
                e_in_v <= 1'b1; e_in_last <= am_stream[1]; e_mask <= am_stream[9:2]; e_vals <= am_stream[265:10];
                e_bias <= am_stream[521:266]; e_bias_en <= am_stream[522];
                if (am_stream[1]) rd_done_all <= 1'b1;
            end
            if (busy && eo_v && !got_out) begin
                got_out <= 1'b1; res_val <= eo_val;
                res_id <= {14'd0, eo_idx} - (MUT_OFFSET ? 32'd0 : {29'd0, stream_m ? 3'd0 : a_base[2:0]});
                if (eo_nan) nan_flag <= 1'b1;
                if (eo_rf || eo_f) begin ret[2] <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; end
                else wr_phase <= 1'b1;
            end
            if (busy && wr_phase && !wr_pend && wr_n != 2'd2) begin               // word-masked sector write
                vmq <= {1'b1, 1'b1, wa[29:3], 5'd0, {8{wr_n[0] ? res_id : res_val}}, (32'hF << (4 * wa[2:0])), 16'h7A01};
                wr_pend <= 1'b1;
            end
            if (busy && wr_pend && vr[273] && vr[256]) begin
                wr_pend <= 1'b0; wr_n <= wr_n + 2'd1;
                if (wr_n == 2'd1) begin busy <= 1'b0; ret[1] <= 1'b1; ret[0] <= 1'b1; wr_phase <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire
