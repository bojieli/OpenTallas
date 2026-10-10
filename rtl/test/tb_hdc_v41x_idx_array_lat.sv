`timescale 1ns/1ps
// W11 streaming-domain copy of rtl/test/tb_hdc_v41x_idx_array.sv driving the _l (latency-parameterised) unit.
// Bit-exactness, order and timing bench of ot_hdc_v41x_idx_array_l against
// tools/hdc_golden_v41.py (chunk8), driven by tools/rtl_w11_idx_array.py.
//   arr_q.mem   per token, IH lines {w[15:0], scales[NB*8], codes[NB*128]}
//   arr_n.mem   per token, its beat count (32 bits)
//   arr_k.mem   per beat slot (NS*NK slots per beat, slot order)
//               {kv, index[IW], ref, keep, key[NB*136]}
//   arr_e.mem   per slot {fault, score[15:0]}
// Per token: wait for ql_ready, load the query (IH cycles), stream the beats,
// wait for the token's last score beat.  Plusargs NTOK, NSLOT, SEED, BUBBLE
// and ORDY (1/16ths of cycles the source withholds a beat / the sink
// refuses).  Every valid slot's score, fault and index is compared; beats must
// come out in the order they went in, with the last tag on the final beat.
module tb_hdc_v41x_idx_array #(
    parameter integer NS = 2,
    parameter integer NK = 4,
    parameter integer IH = 32,
    parameter integer NB = 4,
    parameter integer IW = 30,
    parameter integer MD = 64,
    parameter integer FPL = 3,              // element arithmetic latencies (3/3/3 = as built)
    parameter integer FML = 3,
    parameter integer QL = 3,
    parameter integer SAFE_QUERY_GATE = 0,
    parameter integer MAXT = 64,
    parameter integer MAXS = 1 << 17
) (input wire clk);
    localparam integer KW = NB * 136;
    localparam integer QW = 16 + NB * 8 + NB * 128;
    localparam integer W = NS * NK;
    localparam integer SW = 1 + IW + 2 + KW;
    reg [QW-1:0] qm [0:MAXT*IH-1];
    reg [31:0]   nm [0:MAXT-1];
    reg [SW-1:0] km [0:MAXS-1];
    reg [16:0]   em [0:MAXS-1];
    integer ntok = 0, nslot = 0, bubble = 0, ordy = 0;
    reg [31:0] seed = 32'h2468ace1, seed2 = 32'h1f2e3d4c;
    initial begin
        if (!$value$plusargs("NTOK=%d", ntok)) ntok = 0;
        if (!$value$plusargs("NSLOT=%d", nslot)) nslot = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h2468ace1;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("ORDY=%d", ordy)) ordy = 0;
        seed2 = seed ^ 32'h5a5a1234;
        $readmemh("arr_q.mem", qm, 0, ntok * IH - 1);
        $readmemh("arr_n.mem", nm, 0, ntok - 1);
        $readmemh("arr_k.mem", km, 0, nslot - 1);
        $readmemh("arr_e.mem", em, 0, nslot - 1);
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg rst_n = 1'b0;
    reg              ql_v = 1'b0;
    wire             ql_ready;
    reg [7:0]        ql_head = 0;
    reg [NB*128-1:0] ql_codes = 0;
    reg [NB*8-1:0]   ql_sc = 0;
    reg [15:0]       ql_w = 0;
    reg              i_valid = 1'b0;
    wire             i_ready;
    reg [NS-1:0]     i_last = 0;
    reg [W-1:0]      i_kv = 0, i_ref = 0, i_keep = 0;
    reg [W*IW-1:0]   i_index = 0;
    reg [W*KW-1:0]   i_key = 0;
    wire             o_valid;
    reg              o_ready = 1'b0;
    wire [NS-1:0]    o_last;
    wire [W-1:0]     o_kv, o_fault;
    wire [W*16-1:0]  o_score;
    wire [W*IW-1:0]  o_index;
    wire             protocol_fault;
    wire [7:0] query_head_for_dut = ($test$plusargs("MUT_QUERY_HEAD") && ql_head == 8'd7) ? 8'd8 : ql_head;
    ot_hdc_v41x_idx_array_l #(.NS(NS), .NK(NK), .NB(NB), .IH(IH), .IW(IW), .MD(MD), .FPL(FPL), .FML(FML), .QL(QL), .SAFE_QUERY_GATE(SAFE_QUERY_GATE)) dut (
        .clk(clk), .rst_n(rst_n), .ql_v(ql_v), .ql_ready(ql_ready), .ql_head(query_head_for_dut),
        .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
        .i_valid(i_valid), .i_ready(i_ready), .i_last(i_last), .i_kv(i_kv), .i_ref(i_ref),
        .i_keep(i_keep), .i_index(i_index), .i_key(i_key),
        .o_valid(o_valid), .o_ready(o_ready), .o_last(o_last), .o_kv(o_kv), .o_fault(o_fault),
        .o_score(o_score), .o_index(o_index), .protocol_fault(protocol_fault));

    localparam integer RB = 1024;
    integer acc_t [0:RB-1];
    integer cyc = 0, st = 0, tok = 0, qh = 0, bbase = 0, bnext = 0, bend = 0, bout = 0;
    integer beats_in = 0, beats_out = 0, errors = 0, checked = 0, faults_ok = 0, refused = 0, masked = 0;
    integer in_stall = 0, out_stall = 0, lat, lat_min = 1 << 30, lat_max = 0;
    integer t_q0 = 0, t_first = 0, t_last_in = 0, t_last_out = 0, tok_cycles = 0, tok_span = 0;
    integer j, sl, si;
    integer s_checked [0:NS-1];
    integer s_errors [0:NS-1];
    initial for (si = 0; si < NS; si = si + 1) begin s_checked[si] = 0; s_errors[si] = 0; end
    reg [SW-1:0] kd;
    reg [16:0] e;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        // ---- sink ----
        if (rst_n) begin
            seed2 = xs(seed2);
            o_ready <= !(ordy > 0 && (seed2[7:4] < ordy));
        end
        if (o_valid && !o_ready) out_stall = out_stall + 1;
        if (o_valid && o_ready) begin
            lat = cyc - acc_t[beats_out % RB];
            if (lat < lat_min) lat_min = lat;
            if (lat > lat_max) lat_max = lat;
            if (o_last !== {NS{bout == bend - 1}}) begin
                errors = errors + 1;
                if (errors <= 10) $display("LAST-TAG beat %0d got %b", bout, o_last);
            end
            for (j = 0; j < W; j = j + 1) begin
                si = errors;
                sl = bout * W + j;
                kd = km[sl];
                e = em[sl];
                if (o_kv[j] !== kd[SW-1]) begin
                    errors = errors + 1;
                    if (errors <= 10) $display("KV-SLOT beat %0d slot %0d", bout, j);
                end else if (kd[SW-1]) begin
                    checked = checked + 1;
                    s_checked[j / NK] = s_checked[j / NK] + 1;
                    if (kd[KW+1]) refused = refused + 1;
                    if (!kd[KW]) masked = masked + 1;
                    if (o_index[IW*j +: IW] !== kd[KW+2 +: IW]) begin
                        errors = errors + 1;
                        if (errors <= 10) $display("INDEX beat %0d slot %0d got %0d exp %0d", bout, j,
                                                   o_index[IW*j +: IW], kd[KW+2 +: IW]);
                    end else if (e[16]) begin
                        if (o_fault[j] && o_score[16*j +: 16] == 16'd0) faults_ok = faults_ok + 1;
                        else begin
                            errors = errors + 1;
                            if (errors <= 10) $display("MISS-FAULT slot %0d idx %0d got %h", sl,
                                                       kd[KW+2 +: IW], o_score[16*j +: 16]);
                        end
                    end else if (o_fault[j] || o_score[16*j +: 16] !== e[15:0]) begin
                        errors = errors + 1;
                        if (errors <= 10) $display("MISMATCH slot %0d idx %0d got %h f%0d exp %h", sl,
                                                   kd[KW+2 +: IW], o_score[16*j +: 16], o_fault[j], e[15:0]);
                    end
                end
                if (errors != si) s_errors[j / NK] = s_errors[j / NK] + 1;
            end
            bout = bout + 1;
            beats_out = beats_out + 1;
            t_last_out = cyc;
        end
        // ---- source ----
        if (rst_n) begin
            ql_v <= 1'b0;
            case (st)
                0: begin                                   // next token: load q once permitted
                    if (tok >= ntok) st = 9;
                    else if (ql_ready && !ql_v) begin
                        st = 3; qh = 0; t_q0 = cyc + 1;
                    end
                end
                3: begin
                    ql_v <= 1'b1;
                    ql_head <= qh[7:0];
                    {ql_w, ql_sc, ql_codes} <= qm[tok * IH + qh];
                    if (qh == IH - 1) begin
                        st = 1;
                        bend = bbase + nm[tok];
                        bnext = bbase;
                        bout = bbase;
                        t_first = -1;
                    end else qh = qh + 1;
                end
                1: begin                                   // stream beats
                    if (i_valid && i_ready) begin
                        acc_t[beats_in % RB] = cyc;
                        beats_in = beats_in + 1;
                        if (t_first < 0) t_first = cyc;
                        t_last_in = cyc;
                        bnext = bnext + 1;
                    end else if (i_valid && !i_ready) in_stall = in_stall + 1;
                    if (bnext >= bend) begin
                        i_valid <= 1'b0;
                        st = 2;
                    end else begin
                        seed = xs(seed);
                        if (bubble > 0 && seed[7:4] < bubble) i_valid <= 1'b0;
                        else begin
                            i_valid <= 1'b1;
                            i_last <= {NS{bnext == bend - 1}};
                            for (j = 0; j < W; j = j + 1) begin
                                kd = km[bnext * W + j];
                                i_kv[j] <= kd[SW-1];
                                i_index[IW*j +: IW] <= kd[KW+2 +: IW];
                                i_ref[j] <= kd[KW+1];
                                i_keep[j] <= kd[KW];
                                i_key[KW*j +: KW] <= kd[KW-1:0];
                            end
                        end
                    end
                end
                2: begin                                   // drain the token
                    if (bout >= bend) begin
                        tok_cycles = tok_cycles + (t_last_out - t_q0 + 1);
                        tok_span = tok_span + (t_last_in - t_first + 1);
                        bbase = bend;
                        tok = tok + 1;
                        st = 0;
                    end
                end
                default: begin
                    for (si = 0; si < NS; si = si + 1)
                        $display("V41XARRSLICE s=%0d checked=%0d errors=%0d", si, s_checked[si], s_errors[si]);
                    $display("V41XARR slots=%0d checked=%0d errors=%0d faults_expected_and_raised=%0d refused=%0d masked=%0d beats_in=%0d beats_out=%0d span=%0d in_stall=%0d out_stall=%0d lat_min=%0d lat_max=%0d tok_cycles=%0d cycles=%0d",
                             nslot, checked, errors, faults_ok, refused, masked, beats_in, beats_out, tok_span,
                             in_stall, out_stall, lat_min, lat_max, tok_cycles, cyc);
                    $finish;
                end
            endcase
        end
        if (cyc > 50000000) begin
            $display("V41XARR TIMEOUT checked=%0d", checked);
            $finish;
        end
    end
endmodule
