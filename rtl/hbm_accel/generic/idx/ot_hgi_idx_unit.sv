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
//   op 0  IDX.INDEX (spec G18): one DS native selector frame through ot_hgi_idx_index (fs / qb / kin out, to / co in;
//         the selector hfd_idx_sel_native_qend and its four stack scorers are separate die blocks).
//   op 1  IDX.MERGE (proposed G20): ot_hgi_idx_merge, the exact k-way merge of G key-sorted runs in VM (TOPK_MERGE idiom).
//   op 3  IDX.OWNED (proposed G21): ot_hgi_idx_owned, the owned-row list + per-entry gathered-row table of ROW_GATHER (R3).
//   op 4 (EHASH, not bound here): record fault (fail-closed).
// Return {fault, done, ready}: ready = no record in flight.
module ot_hgi_idx_unit #(
    parameter integer MUT = 0           // bench mutants: 1 ascending sort compares scores instead of ids
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1818:0] rec,           // {die_id 8, pos 20, n_R, n_O, n_D, n_C, n_B, n_A, R, O, D, C, B, A, header, valid}
    output reg  [2:0]    ret,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    // native selector (IDX.INDEX)
    output wire [89:0]   sel_fs,
    output wire [1047:0] sel_qb,
    input  wire          sel_qbr,
    output wire [344:0]  sel_kin,
    input  wire [611:0]  sel_to,
    output wire          sel_toc,
    input  wire [71:0]   sel_co,
    output wire          sel_coc,
    input  wire [1:0]    sel_ev
);
    reg [337:0] vmq_t;
    wire [337:0] vmq_x, vmq_m, vmq_w;
    reg x_active, m_active, w_active;
    assign vmq = x_active ? vmq_x : m_active ? vmq_m : w_active ? vmq_w : vmq_t;
    // ---------------------------------------------------------------- record station
    reg busy, started, eng_done, eng_err;
    reg [31:0] w_sc;
    reg [11:0] o_k;                      // output index within the row (descending order)
    reg [127:0] hdr; reg [255:0] dA, dB, dC, dD, dO, dR; reg [19:0] rpos; reg [7:0] rdie;
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
    // ---------------------------------------------------------------- IDX.INDEX frame adapter (op 0)
    reg x_go; wire x_done, x_fault;
    wire [17:0] dB_b = dB[25:8], dC_b = dC[25:8], dD_b = dD[25:8], dD_s = dD[105:88];
    // legal: A VM FP32 n*m = 4,096, B VM FP32 >= 32, C VM U32 (keep_en), O VM U32, R VM FP32 (optional), D VM (cand_en)
    wire x_keep = hdr[77], x_cand = hdr[76];
    wire x_legal = opnd[0] && opnd[1] && opnd[4] && dA[1:0] == 2'd1 && dA[4:2] == 3'd0 && a_n * a_m == 20'd4096 &&
                   dB[1:0] == 2'd1 && dB[4:2] == 3'd0 && dO[1:0] == 2'd1 && dO[4:2] == 3'd5 &&
                   (!has_r || (dR[1:0] == 2'd1 && dR[4:2] == 3'd0)) && (!x_keep || (opnd[2] && dC[1:0] == 2'd1 && dC[67:48] != 20'd0 && dC[67:48] <= 20'd2048)) &&
                   (!x_cand || (opnd[3] && dD[1:0] == 2'd1)) && hdr[88:78] == 11'd0;
    ot_hgi_idx_index #(.MUT(MUT >= 2 ? MUT - 1 : 0)) u_index (.clk(clk), .rst_n(rst_n), .go(x_go), .k(k), .cand_en(x_cand),
        .keep_en(x_keep), .n(hdr[63:32]), .rank(rdie >= 8'd192 ? 7'(rdie - 8'd192) : rdie >= 8'd96 ? 7'(rdie - 8'd96) : rdie[6:0]),
        .pos(rpos), .a_base(a_base[17:0]), .b_base(dB_b), .c_base(dC_b), .o_base(o_base[17:0]), .r_base(r_base[17:0]),
        .d_base(dD_b), .d_stride(dD_s), .c_stride(dC[105:88]), .c_n(dC[59:48]), .has_r(has_r), .done(x_done), .fault(x_fault),
        .vmq(vmq_x), .vmr(x_active ? vmr : 274'd0), .fs(sel_fs), .qb(sel_qb), .qbr(sel_qbr), .kin(sel_kin), .to(sel_to),
        .toc(sel_toc), .co(sel_co), .coc(sel_coc), .ev(sel_ev));
    // ---------------------------------------------------------------- IDX.MERGE (op 1, proposed G20)
    reg m_go; wire m_done, m_fault;
    wire [19:0] mb_n = dB[67:48]; wire [19:0] mb_m = dB[87:68];
    wire m_legal = opnd[0] && opnd[1] && opnd[4] && dA[1:0] == 2'd1 && dA[4:2] == 3'd0 && dB[1:0] == 2'd1 &&
                   dB[4:2] == 3'd5 && mb_n == a_n && mb_m == a_m && a_m != 20'd0 && a_m <= 20'd128 &&
                   dO[1:0] == 2'd1 && dO[4:2] == 3'd5 && (!has_r || (dR[1:0] == 2'd1 && dR[4:2] == 3'd0)) &&
                   hdr[88:77] == 12'd0 && k != 12'd0 && k <= 12'd2048;
    ot_hgi_idx_merge #(.MUT(MUT == 4 ? 1 : 0)) u_merge (.clk(clk), .rst_n(rst_n), .go(m_go), .k(k), .key_id(hdr[76]),
        .g(a_m[7:0]), .n(a_n), .a_base(a_base[17:0]), .b_base(dB[25:8]), .o_base(o_base[17:0]), .r_base(r_base[17:0]),
        .a_str(a_str[17:0]), .b_str(dB[105:88]), .has_r(has_r), .done(m_done), .fault(m_fault),
        .vmq(vmq_m), .vmr(m_active ? vmr : 274'd0));
    // ---------------------------------------------------------------- IDX.OWNED (op 3, proposed G21)
    reg w_go; wire w_done, w_fault;
    wire w_legal = opnd[0] && opnd[3] && opnd[4] && opnd[5] && dA[1:0] == 2'd1 && dA[4:2] == 3'd5 && dO[1:0] == 2'd1 &&
                   dO[4:2] == 3'd5 && dR[1:0] == 2'd1 && dR[4:2] == 3'd5 && dD[1:0] == 2'd1 && dD[4:2] == 3'd5 &&
                   hdr[88] == 1'b0;
    ot_hgi_idx_owned u_owned (.clk(clk), .rst_n(rst_n), .go(w_go), .blk(hdr[71:64]), .grp(hdr[79:72]), .die(rdie), .batch(hdr[87:80]),
        .k(a_n), .a_base(a_base[17:0]), .o_base(o_base[17:0]), .r_base(r_base[17:0]), .d_base(dD[25:8]),
        .done(w_done), .fault(w_fault), .vmq(vmq_w), .vmr(w_active ? vmr : 274'd0));
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
            busy <= 1'b0; ret <= 3'b001; e_cmd_v <= 1'b0; e_in_v <= 1'b0; vmq_t <= 338'd0; vm_pend <= 1'b0; x_go <= 1'b0; x_active <= 1'b0; m_go <= 1'b0; m_active <= 1'b0; w_go <= 1'b0; w_active <= 1'b0;
            b_v <= 8'd0; b_n <= 4'd0; b_full <= 1'b0; w_v <= 1'b0; c_ok <= 1'b0; r_done <= 1'b1;
            started <= 1'b0; eng_done <= 1'b0; eng_err <= 1'b0; w_cnt <= 32'd0;
        end else begin
            ret[2:1] <= 2'b00; vmq_t[337] <= 1'b0; x_go <= 1'b0; m_go <= 1'b0; w_go <= 1'b0;
            if (e_cmd_v && e_cmd_r) e_cmd_v <= 1'b0;
            if (e_in_v && e_in_r) e_in_v <= 1'b0;
            // record intake
            if (!busy && rec[0]) begin
                hdr <= rec[128:1]; dA <= rec[384:129]; dB <= rec[640:385]; dC <= rec[896:641]; dD <= rec[1152:897];
                dO <= rec[1408:1153]; dR <= rec[1664:1409]; rpos <= rec[1810:1791]; rdie <= rec[1818:1811];
                busy <= 1'b1; ret[0] <= 1'b0; e_cmd_v <= 1'b0; r_row <= 20'd0; r_col <= 20'd0; r_done <= 1'b0;
                c_ok <= 1'b0; w_cnt <= 32'd0; b_v <= 8'd0; b_n <= 4'd0; b_full <= 1'b0; o_k <= 12'd0;
            end else if (busy && !e_cmd_v && r_row == 20'd0 && r_col == 20'd0 && !r_done && !e_in_v && !vm_pend && w_cnt == 32'd0 && !started) begin
                if (op == 6'd0 && x_legal) begin x_go <= 1'b1; x_active <= 1'b1; started <= 1'b1; r_done <= 1'b1; end
                else if (op == 6'd1 && m_legal) begin m_go <= 1'b1; m_active <= 1'b1; started <= 1'b1; r_done <= 1'b1; end
                else if (op == 6'd3 && w_legal) begin w_go <= 1'b1; w_active <= 1'b1; started <= 1'b1; r_done <= 1'b1; end
                else if (!legal) begin busy <= 1'b0; ret <= 3'b101; r_done <= 1'b1; end
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
                    vmq_t <= {1'b1, 1'b0, {12'd0, rw_now[17:3], 5'd0}, 256'd0, 32'd0, 16'h0900};
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
                vmq_t <= {1'b1, 1'b1, {12'd0, w_a[17:3], 5'd0}, {8{w_d}}, 32'hf << (w_a[2:0] * 4), 16'h0901};
                if (w_second) begin
                    w_second <= 1'b0; w_r <= 1'b1; w_d <= w_sc;
                    w_a <= r_base + b_row * r_str + w_idx;
                end else w_v <= 1'b0;
            end
            if (w_active && (w_done || w_fault)) begin
                w_active <= 1'b0; busy <= 1'b0; started <= 1'b0; ret <= w_fault ? 3'b101 : 3'b011;
            end
            if (m_active && (m_done || m_fault)) begin
                m_active <= 1'b0; busy <= 1'b0; started <= 1'b0; ret <= m_fault ? 3'b101 : 3'b011;
            end
            if (x_active && (x_done || x_fault)) begin
                x_active <= 1'b0; busy <= 1'b0; started <= 1'b0; ret <= x_fault ? 3'b101 : 3'b011;
            end
            if (vmr[273] && !x_active && !m_active && !w_active) begin
                vm_pend <= 1'b0;
                if (vm_rd) begin c_ok <= 1'b1; c_sec <= rw_now[17:3]; c_dat <= vmr[255:0]; end
            end
            // completion
            if (busy && started && !x_active && !m_active && !w_active && e_done) eng_done <= 1'b1;
            if (busy && started && e_done && e_err != 4'd0) eng_err <= 1'b1;
            if (busy && !x_active && !m_active && !w_active && eng_done && !w_v && !vm_pend && !b_full && !e_out_v) begin
                busy <= 1'b0; started <= 1'b0; eng_done <= 1'b0; eng_err <= 1'b0;
                ret <= eng_err ? 3'b101 : 3'b011;
            end
        end
    end
endmodule
`default_nettype wire
