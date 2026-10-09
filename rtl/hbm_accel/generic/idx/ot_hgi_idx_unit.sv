`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX unit (unit 9) die body, v1 (hgi-takeover 2026-10-09): the normative record bus (tools/hgi_die_dispatch.py
// 'idx' = {n_R, n_O, n_B, n_A, desc_R, desc_O, desc_B, desc_A, header 128, valid}) -> record decode -> engines, with a
// VM stream reader / writer on one hfd_hgi_vm packet client (one request outstanding).
//
//   op 2  IDX.TOPK: Codex's qualified ot_hgi_idx_topk_registered (full K 2,048, ties to the lowest index, NaN fails
//         closed).  A (VM FP32, m rows of n, any stride / istride) streams in one word a cycle through a one-sector
//         cache; ids go to O (VM U32), values to R (VM FP32) when R is present.  param[12] order = 1 (legal for k <= 8,
//         HGI-1 G15): the row's k results are emitted in ascending id order (a k <= 8 selection sort), values with
//         their ids.  order = 1 with k > 8, or a non-VM / wrong-format operand: E_RANGE -> record fault.
//   ops 0, 1, 3 (INDEX_Q, INDEX_SCORES, SELECT) and 4 (EHASH): NOT bound in v1 -> record fault (fail-closed).  The DS
//         native selector frame needs one frame record (spec amendment proposed: review_queue/hgi-die-gaps.md G18).
// Return {fault, done, ready}: ready = no record in flight.
module ot_hgi_idx_unit #(
    parameter integer MUT = 0           // bench mutants: 1 ascending sort compares scores instead of ids
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1236:0] rec,
    output reg  [2:0]    ret,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    // ---------------------------------------------------------------- record station
    reg busy, started, eng_done, eng_err;
    reg [31:0] w_sc;
    reg [11:0] o_k;                      // output index within the row (descending order)
    reg [127:0] hdr; reg [255:0] dA, dO, dR;
    wire [5:0]  op    = hdr[123:118];
    wire [6:0]  opnd  = hdr[99:93];
    wire [11:0] k     = hdr[75:64];
    wire        order = hdr[76];
    wire [39:0] a_base = dA[47:8]; wire [19:0] a_n = dA[67:48]; wire [19:0] a_m = dA[87:68];
    wire [31:0] a_str = dA[119:88]; wire [15:0] a_is = (dA[135:120] == 16'd0) ? 16'd1 : dA[135:120];
    wire [39:0] o_base = dO[47:8]; wire [31:0] o_str = dO[119:88];
    wire [39:0] r_base = dR[47:8]; wire [31:0] r_str = dR[119:88];
    wire has_r = opnd[5];
    wire legal = op == 6'd2 && opnd[0] && opnd[4] && dA[1:0] == 2'd1 && dA[4:2] == 3'd0 && dO[1:0] == 2'd1 &&
                 dO[4:2] == 3'd5 && (!has_r || (dR[1:0] == 2'd1 && dR[4:2] == 3'd0)) && hdr[88:77] == 12'd0 &&
                 (!order || (k != 0 && k <= 12'd8));
    // ---------------------------------------------------------------- engine
    reg  e_cmd_v; wire e_cmd_r, e_in_r, e_out_v, e_last, e_vv, e_done; wire [3:0] e_err;
    wire [31:0] e_id, e_sc, e_row;
    reg  e_in_v; reg [31:0] e_in;
    wire e_out_r;
    ot_hgi_idx_topk_registered #(.ENABLE(1'b1), .MAX_K(2048)) u_topk (.clk(clk), .rst_n(rst_n),
        .cmd_valid(e_cmd_v), .cmd_ready(e_cmd_r), .cmd_unit(4'd9), .cmd_op(6'd2), .cmd_param({13'd0, k}),
        .cmd_n({12'd0, a_n}), .cmd_m({12'd0, a_m}), .cmd_values(has_r),
        .in_valid(e_in_v), .in_ready(e_in_r), .in_score(e_in),
        .out_valid(e_out_v), .out_ready(e_out_r), .out_id(e_id), .out_score(e_sc), .out_row(e_row),
        .out_last(e_last), .out_values_valid(e_vv), .done(e_done), .error(e_err));
    // ---------------------------------------------------------------- output buffer (order = 1: k <= 8 ascending ids)
    reg [31:0] b_id [0:7]; reg [31:0] b_sc [0:7]; reg [7:0] b_v; reg [3:0] b_n; reg [31:0] b_row; reg b_full;
    // write queue entry being written: {is_r, word address, data}
    reg w_v; reg w_r; reg [39:0] w_a; reg [31:0] w_d; reg w_second; reg [11:0] w_idx; reg [31:0] w_cnt;
    // pick the lowest remaining id (ascending) or the next slot (descending order: emission order)
    reg [2:0] pick; reg found; integer i;
    always @* begin
        pick = 3'd0; found = 1'b0;
        for (i = 0; i < 8; i = i + 1)
            if (b_v[i]) begin
                if (!found) begin pick = i[2:0]; found = 1'b1; end
                else if (order && ((MUT == 1) ? (b_sc[i] < b_sc[pick]) : (b_id[i] < b_id[pick]))) pick = i[2:0];
            end
    end
    // engine output accepted: descending order -> straight to the write stage; ascending -> into the buffer
    assign e_out_r = busy && (order ? !b_full : (!w_v));
    // ---------------------------------------------------------------- reader (one-sector cache) and VM client
    reg [19:0] r_row, r_col; reg r_done; reg [39:0] r_word;
    reg [14:0] c_sec; reg c_ok; reg [255:0] c_dat;
    reg vm_pend, vm_rd;                                  // one VM request in flight; vm_rd: it is the reader's
    wire [39:0] rw_now = a_base + r_row * a_str + r_col * a_is;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; ret <= 3'b001; e_cmd_v <= 1'b0; e_in_v <= 1'b0; vmq <= 338'd0; vm_pend <= 1'b0;
            b_v <= 8'd0; b_n <= 4'd0; b_full <= 1'b0; w_v <= 1'b0; c_ok <= 1'b0; r_done <= 1'b1;
            started <= 1'b0; eng_done <= 1'b0; eng_err <= 1'b0; w_cnt <= 32'd0;
        end else begin
            ret[2:1] <= 2'b00; vmq[337] <= 1'b0;
            if (e_cmd_v && e_cmd_r) e_cmd_v <= 1'b0;
            if (e_in_v && e_in_r) e_in_v <= 1'b0;
            // record intake
            if (!busy && rec[0]) begin
                hdr <= rec[128:1]; dA <= rec[384:129]; dO <= rec[896:641]; dR <= rec[1152:897];
                busy <= 1'b1; ret[0] <= 1'b0; e_cmd_v <= 1'b0; r_row <= 20'd0; r_col <= 20'd0; r_done <= 1'b0;
                c_ok <= 1'b0; w_cnt <= 32'd0; b_v <= 8'd0; b_n <= 4'd0; b_full <= 1'b0; o_k <= 12'd0;
            end else if (busy && !e_cmd_v && r_row == 20'd0 && r_col == 20'd0 && !r_done && !e_in_v && !vm_pend && w_cnt == 32'd0 && !started) begin
                if (!legal) begin busy <= 1'b0; ret <= 3'b101; r_done <= 1'b1; end
                else begin e_cmd_v <= 1'b1; started <= 1'b1; end
            end
            // reader: next word of A into the engine
            if (busy && started && !r_done && !e_in_v) begin
                if (c_ok && c_sec == rw_now[17:3]) begin
                    e_in_v <= 1'b1; e_in <= c_dat[rw_now[2:0]*32 +: 32];
                    if (r_col + 20'd1 == a_n) begin
                        r_col <= 20'd0;
                        if (r_row + 20'd1 == a_m) r_done <= 1'b1; else r_row <= r_row + 20'd1;
                    end else r_col <= r_col + 20'd1;
                end else if (!vm_pend && !w_v) begin
                    vm_pend <= 1'b1; vm_rd <= 1'b1;
                    vmq <= {1'b1, 1'b0, {12'd0, rw_now[17:3], 5'd0}, 256'd0, 32'd0, 16'h0900};
                end
            end
            // engine output
            if (e_out_v && e_out_r) begin
                if (!order) begin
                    w_v <= 1'b1; w_r <= 1'b0; w_second <= has_r; w_d <= e_id; w_cnt <= w_cnt + 32'd1;
                    w_a <= o_base + e_row * o_str + o_k; w_idx <= o_k; w_sc <= e_sc; b_row <= e_row;
                    o_k <= e_last ? 12'd0 : o_k + 12'd1;
                end else begin
                    b_id[b_n[2:0]] <= e_id; b_sc[b_n[2:0]] <= e_sc; b_v[b_n[2:0]] <= 1'b1; b_row <= e_row;
                    if (e_last) begin b_full <= 1'b1; b_n <= 4'd0; end else b_n <= b_n + 4'd1;
                end
            end
            // ascending: drain the buffer lowest id first
            if (order && b_full && !w_v && found) begin
                w_v <= 1'b1; w_r <= 1'b0; w_second <= has_r; w_d <= b_id[pick]; w_cnt <= w_cnt + 32'd1;
                w_a <= o_base + b_row * o_str + b_n; w_idx <= b_n; w_sc <= b_sc[pick];
                b_v[pick] <= 1'b0; b_n <= b_n + 4'd1;
            end
            if (order && b_full && b_v == 8'd0 && !w_v) begin b_full <= 1'b0; b_n <= 4'd0; end
            // writer: one word per VM write (word mask)
            if (w_v && !vm_pend) begin
                vm_pend <= 1'b1; vm_rd <= 1'b0;
                vmq <= {1'b1, 1'b1, {12'd0, w_a[17:3], 5'd0}, {8{w_d}}, 32'hf << (w_a[2:0] * 4), 16'h0901};
                if (w_second) begin
                    w_second <= 1'b0; w_r <= 1'b1; w_d <= w_sc;
                    w_a <= r_base + b_row * r_str + w_idx;
                end else w_v <= 1'b0;
            end
            if (vmr[273]) begin
                vm_pend <= 1'b0;
                if (vm_rd) begin c_ok <= 1'b1; c_sec <= rw_now[17:3]; c_dat <= vmr[255:0]; end
            end
            // completion
            if (busy && started && e_done) eng_done <= 1'b1;
            if (busy && started && e_done && e_err != 4'd0) eng_err <= 1'b1;
            if (busy && eng_done && !w_v && !vm_pend && !b_full && !e_out_v) begin
                busy <= 1'b0; started <= 1'b0; eng_done <= 1'b0; eng_err <= 1'b0;
                ret <= eng_err ? 3'b101 : 3'b011;
            end
        end
    end
endmodule
`default_nettype wire
