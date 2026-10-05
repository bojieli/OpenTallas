`timescale 1ns/1ps
// Performance and bit-exactness bench of ot_hdc_v41x_hcp (hyper-connection
// projection).  Behavioural weight and x banks (8 each, fixed read latency ML)
// hold every case's operands in the engine's layout; the cases run back to
// back, each command presented as soon as cmd_ready allows.  Every result is
// compared, in order, with the golden's (tools/rtl_hdc_v41x_hcp_campaign.py).
// Files (run directory):
//   hcp_meta.mem  {ncase, wd, xd, nexp} (32-bit words)
//   hcp_cmd.mem   per case 8 words: npos, nout, nchunk, scale, nf, eps, wbase, xbase
//   hcp_w.mem     binary32, index ((bank * wd + word) * W + lane)
//   hcp_x.mem     BF16,     index ((bank * xd + word) * W + lane)
//   hcp_exp.mem   per result {pos[7:0], idx[7:0], value[31:0]}
// +STALL=<0..99> percent of cycles o_ready is low; +SEED; +MAXCYC (timeout).
// Prints one CASE line per case and one HCP summary line.
module tb_hdc_v41x_hcp #(
    parameter integer W   = 8,
    parameter integer TL  = 9,
    parameter integer ML  = 2,
    parameter integer MAXW = 1 << 22,
    parameter integer MAXX = 1 << 20,
    parameter integer MAXE = 1 << 14,
    parameter integer MAXC = 256
) (input wire clk);
    localparam integer AW = 16;
    reg [31:0] meta [0:3];
    reg [31:0] cmdm [0:8*MAXC-1];
    reg [31:0] wmem [0:MAXW-1];
    reg [15:0] xmem [0:MAXX-1];
    reg [47:0] expm [0:MAXE-1];
    integer ncase, wd, xd, nexp, stall = 0, maxcyc = 50000000;
    reg [31:0] seed = 32'h2468ace1;
    initial begin
        $readmemh("hcp_meta.mem", meta);
        ncase = meta[0]; wd = meta[1]; xd = meta[2]; nexp = meta[3];
        $readmemh("hcp_cmd.mem", cmdm, 0, 8 * ncase - 1);
        $readmemh("hcp_w.mem", wmem, 0, 8 * wd * W - 1);
        $readmemh("hcp_x.mem", xmem, 0, 8 * xd * W - 1);
        $readmemh("hcp_exp.mem", expm, 0, nexp - 1);
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 50000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h2468ace1;
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg rst_n = 1'b0;
    reg        cmd_valid = 1'b0;
    wire       cmd_ready;
    reg [3:0]  cmd_npos;
    reg [5:0]  cmd_nout;
    reg [15:0] cmd_nchunk;
    reg        cmd_scale;
    reg [31:0] cmd_nf, cmd_eps;
    reg [AW-1:0] cmd_wbase, cmd_xbase;
    wire [7:0] w_re, x_re;
    wire [8*AW-1:0] w_addr, x_addr;
    reg  [8*W*32-1:0] w_pipe [0:ML-1];
    reg  [8*W*16-1:0] x_pipe [0:ML-1];
    wire o_valid, o_last, fault, idle;
    reg  o_ready = 1'b1;
    wire [2:0] o_pos;
    wire [4:0] o_idx;
    wire [31:0] o_data;
    ot_hdc_v41x_hcp #(.W(W), .TL(TL), .PMAX(8), .OMAX(32), .AW(AW), .CW(16), .ML(ML), .DF(32)) dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_npos(cmd_npos),
        .cmd_nout(cmd_nout), .cmd_nchunk(cmd_nchunk), .cmd_scale(cmd_scale), .cmd_nf(cmd_nf),
        .cmd_eps(cmd_eps), .cmd_wbase(cmd_wbase), .cmd_xbase(cmd_xbase),
        .w_re(w_re), .w_addr(w_addr), .w_data(w_pipe[ML-1]), .x_re(x_re), .x_addr(x_addr),
        .x_data(x_pipe[ML-1]), .o_valid(o_valid), .o_ready(o_ready), .o_pos(o_pos), .o_idx(o_idx),
        .o_data(o_data), .o_last(o_last), .fault(fault), .idle(idle));

    // banks: data visible ML cycles after the address
    integer k, l, m;
    reg [8*W*32-1:0] wrd;
    reg [8*W*16-1:0] xrd;
    always @(posedge clk) begin
        for (k = 0; k < 8; k = k + 1)
            for (l = 0; l < W; l = l + 1) begin
                wrd[32*(W*k + l) +: 32] = wmem[(k * wd + w_addr[AW*k +: AW]) * W + l];
                xrd[16*(W*k + l) +: 16] = xmem[(k * xd + x_addr[AW*k +: AW]) * W + l];
            end
        w_pipe[0] <= wrd;
        x_pipe[0] <= xrd;
        for (m = 1; m < ML; m = m + 1) begin
            w_pipe[m] <= w_pipe[m-1];
            x_pipe[m] <= x_pipe[m-1];
        end
    end

    integer cyc = 0, ci = 0, ei = 0, errors = 0, faults = 0, got = 0, cstart = 0, first_out = -1;
    integer case_out = 0, case_base = 0, cexp = 0, cerr = 0, bad_order = 0;
    integer pos_last [0:7];
    integer t0 = -1;
    reg [47:0] ex;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        seed <= xs(seed);
        o_ready <= (stall == 0) ? 1'b1 : ((seed % 100) >= stall);
        // commands
        if (cmd_valid && cmd_ready) begin
            cmd_valid <= 1'b0;
            cstart <= cyc;
            if (t0 < 0) t0 <= cyc;
        end
        if (rst_n && !cmd_valid && ci < ncase && (ci == 0 || case_out == cexp) && cyc > 8) begin
            if (ci > 0) begin
                // previous case finished: report it
            end
            cmd_npos <= cmdm[8*ci + 0]; cmd_nout <= cmdm[8*ci + 1]; cmd_nchunk <= cmdm[8*ci + 2];
            cmd_scale <= cmdm[8*ci + 3]; cmd_nf <= cmdm[8*ci + 4]; cmd_eps <= cmdm[8*ci + 5];
            cmd_wbase <= cmdm[8*ci + 6]; cmd_xbase <= cmdm[8*ci + 7];
            cexp <= cmdm[8*ci + 0] * cmdm[8*ci + 1];
            case_out <= 0; cerr <= 0; first_out <= -1;
            cmd_valid <= 1'b1;
            ci <= ci + 1;
        end
        if (fault && rst_n && cyc > 6) faults <= faults + 1;
        if (rst_n && o_valid && o_ready) begin
            ex = expm[ei];
            if (o_data !== ex[31:0] || o_pos !== ex[42:40] || o_idx !== ex[36:32]) begin
                errors <= errors + 1; cerr <= cerr + 1;
                if (errors < 20)
                    $display("MISMATCH case %0d result %0d: pos %0d idx %0d got %08x exp pos %0d idx %0d %08x",
                             ci - 1, ei, o_pos, o_idx, o_data, ex[47:40], ex[39:32], ex[31:0]);
            end
            if (o_last !== (case_out + 1 == cexp)) bad_order <= bad_order + 1;
            if (first_out < 0) first_out <= cyc - cstart;
            pos_last[o_pos] = cyc - cstart;
            ei <= ei + 1;
            got <= got + 1;
            case_out <= case_out + 1;
            if (case_out + 1 == cexp) begin
                $write("CASE %0d npos=%0d nout=%0d nchunk=%0d scale=%0d errors=%0d first=%0d last=%0d pos_last=",
                       ci - 1, cmd_npos, cmd_nout, cmd_nchunk, cmd_scale, cerr + ((o_data !== ex[31:0]) ? 1 : 0),
                       (first_out < 0) ? cyc - cstart : first_out, cyc - cstart);
                for (k = 0; k < cmd_npos; k = k + 1) $write("%0d,", pos_last[k]);
                $write("\n");
            end
        end
        if (ci == ncase && ei == nexp && !cmd_valid) begin
            $display("HCP W=%0d lanes=%0d cases=%0d results=%0d errors=%0d faults=%0d order=%0d cycles=%0d",
                     W, 8 * W, ncase, got, errors, faults, bad_order, cyc - t0);
            $finish;
        end
        if (cyc > maxcyc) begin
            $display("HCP TIMEOUT results=%0d of %0d case %0d", ei, nexp, ci);
            $finish;
        end
    end
endmodule
