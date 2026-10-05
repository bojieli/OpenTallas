`timescale 1ns/1ps
import ot_rom_coll_pkg::*;
// ---------------------------------------------------------------------------
// TP4 bench of the S81 head argmax with the L1 fused draft head
// (ot_dsrom_s81_head_amax_fh): four ranks chained in ascending vocabulary order
// (rank 0 FIRST), R = 128 return lanes a beat, row = beat * 128 + lane, 32,320 rows a
// rank (129,280), the final ARGMAX record broadcast back to every rank.
//   op 1  capture = 1, fuse = 0: +LG=<hex> (129,280 FP32 words) as the ROM field's
//         accepted writes (the verify / lm_head pass); its argmax is the as-built one.
//   op 2  capture = 0, fuse = 1: +MK=<hex> (the Markov rows); FH = 1 adds the captured
//         LG row first (add(LG, markov)) before the argmax; FH = 0 argmaxes MK alone.
// Prints OP lines (id, value, cycles) and writes every fused lane value of op 2 to
// +DUMP=<file> ("row bits", hex) for the bit-for-bit check against the golden.
// ---------------------------------------------------------------------------
module tb_dsrom_s81_fused_head_tp4 #(
    parameter integer FH = 1,
    parameter integer R = 128, AW = 30, NW = 21, ROWS = 32320,
    parameter integer OBASE = 486848
) (input wire clk);
    localparam integer NB = (ROWS + R - 1) / R;
    localparam [46:0] OWNER = 47'h1_2345_6789;
    reg [31:0] lg [0:4*ROWS-1];
    reg [31:0] mk [0:4*ROWS-1];
    reg rst_n = 0;
    reg [3:0] start = 0;
    reg cap = 0, fus = 0;
    reg wv = 0;
    integer beat = 0;
    reg [1:0] op = 0;                       // 1: LG pass, 2: Markov pass
    wire [3:0] busy, seen, any, flt, up_rdy, dn_v, fin_rdy;
    wire [4*NW-1:0] idx;
    wire [4*32-1:0] val;
    wire [4*512-1:0] dn_d;
    wire [3:0] dn_l;
    wire [4*47-1:0] dn_id;
    reg fin_v = 0;
    reg [511:0] fin_d = 0;
    genvar r;
    generate for (r = 0; r < 4; r = r + 1) begin : g_rank
        reg [R-1:0] m;
        reg [R*AW-1:0] a;
        reg [R*32-1:0] b;
        integer l, row;
        always @* begin
            m = 0; a = 0; b = 0;
            for (l = 0; l < R; l = l + 1) begin
                row = beat * R + l;
                if (wv && row < ROWS) begin
                    m[l] = 1'b1;
                    a[AW*l +: AW] = AW'(OBASE + row);
                    b[32*l +: 32] = (op == 1) ? lg[r*ROWS + row] : mk[r*ROWS + row];
                end
            end
        end
        ot_dsrom_s81_head_amax_fh #(.R(R), .AW(AW), .NW(NW), .RANK(r), .FH(FH), .ROWS(ROWS)) u (
            .clk(clk), .rst_n(rst_n), .start(start[r]), .capture(cap), .fuse(fus), .identity(OWNER),
            .nout(NW'(ROWS)), .obase(AW'(OBASE)), .write_valid(m), .write_accept(m), .write_address(a),
            .write_bits(b),
            .upstream_valid((r == 0) ? 1'b0 : dn_v[(r == 0) ? 0 : r - 1]), .upstream_ready(up_rdy[r]),
            .upstream_data((r == 0) ? 512'd0 : dn_d[((r == 0) ? 0 : r - 1)*512 +: 512]),
            .upstream_last((r == 0) ? 1'b0 : dn_l[(r == 0) ? 0 : r - 1]),
            .upstream_identity((r == 0) ? OWNER : dn_id[((r == 0) ? 0 : r - 1)*47 +: 47]),
            .downstream_valid(dn_v[r]), .downstream_ready((r == 3) ? 1'b1 : up_rdy[(r == 3) ? 0 : r + 1]),
            .downstream_data(dn_d[r*512 +: 512]), .downstream_last(dn_l[r]), .downstream_identity(dn_id[r*47 +: 47]),
            .final_valid(fin_v), .final_ready(fin_rdy[r]), .final_data(fin_d), .final_identity(OWNER),
            .busy(busy[r]), .result_seen(seen[r]), .am_idx(idx[r*NW +: NW]), .am_val(val[r*32 +: 32]),
            .am_any(any[r]), .fault(flt[r]));
    end endgenerate

    string lgf, mkf, dumpf;
    integer fd = 0;
    initial begin
        if (!$value$plusargs("LG=%s", lgf) || !$value$plusargs("MK=%s", mkf) || !$value$plusargs("DUMP=%s", dumpf))
            $fatal(1, "+LG +MK +DUMP required");
        $readmemh(lgf, lg);
        $readmemh(mkf, mk);
        fd = $fopen(dumpf, "w");
    end
    // every fused lane value of op 2, as the argmax receives it
    genvar d;
    generate for (d = 0; d < 4; d = d + 1) begin : g_dump
        always @(posedge clk) if (FH != 0 && op == 2 && g_rank[d].u.fo_v) begin : dl
            integer l;
            for (l = 0; l < R; l = l + 1)
                if (g_rank[d].u.fo_mask[l])
                    $fwrite(fd, "%0h %08h\n", g_rank[d].u.p_ids[5][32*l +: 32], g_rank[d].u.f_bits[32*l +: 32]);
        end
    end endgenerate

    integer cyc = 0, t_start = 0, t_lastbeat = 0, t_fin = 0, st = 0;
    integer t_dn [0:3];
    integer q;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        start <= 0;
        if (cyc == 4) rst_n <= 1;
        if (|flt) $fatal(1, "fault ranks %b at cycle %0d op %0d", flt, cyc, op);
        if (cyc > 400000) $fatal(1, "timeout");
        for (q = 0; q < 4; q = q + 1) if (dn_v[q] && t_dn[q] < 0) t_dn[q] = cyc;
        if (dn_v[3] && !fin_v) begin fin_v <= 1; fin_d <= dn_d[3*512 +: 512]; t_fin = cyc; end
        case (st)
        0: if (cyc == 10) begin op <= 1; cap <= 1; fus <= 0; start <= 4'hF; st <= 1; end
        1, 4: begin                           // started: stream the beats
            if (!wv && beat == 0 && busy == 4'hF) begin wv <= 1; t_start = cyc; for (q = 0; q < 4; q = q + 1) t_dn[q] = -1; end
            else if (wv) begin
                if (beat == NB - 1) begin wv <= 0; beat <= 0; t_lastbeat = cyc; st <= st + 1; end
                else beat <= beat + 1;
            end
        end
        2, 5: if (fin_v && busy == 4'd0) begin
            if (seen != 4'hF || any != 4'hF) $fatal(1, "result not seen by every rank");
            for (q = 1; q < 4; q = q + 1)
                if (idx[q*NW +: NW] != idx[0 +: NW] || val[q*32 +: 32] != val[0 +: 32]) $fatal(1, "ranks disagree");
            $display("OP %0d fh=%0d id=%0d val=%08h beats=%0d first_beat=%0d last_beat=%0d dn0=%0d dn1=%0d dn2=%0d dn3=%0d final=%0d done=%0d",
                     op, FH, idx[0 +: NW], val[0 +: 32], NB, t_start, t_lastbeat, t_dn[0], t_dn[1], t_dn[2], t_dn[3], t_fin, cyc);
            fin_v <= 0;
            if (st == 2) begin op <= 2; cap <= 0; fus <= 1; start <= 4'hF; st <= 4; end
            else begin $fclose(fd); $display("DONE"); $finish; end
        end
        default: ;
        endcase
    end
endmodule
