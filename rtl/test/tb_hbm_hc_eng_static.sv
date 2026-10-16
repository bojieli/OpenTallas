`timescale 1ns/1ps
// H-NETLIST/hceng 2026-10-16: bench of the die master ot_hbm_hc_eng_static (full-form HC.HC_MIX, W 256, K 20,480).
// Vectors and the static event programme come from tools/rtl_hbm_hc_eng_static_gate.py (golden hdc_golden_v41 chunk8
// mixes + the codex tail reference). The programme is installed through the engine's programme pins, the bases /
// scales table through its table pins; the four quadrant clients are modelled as wave sources that present wave n of
// a schedule entry on x_wave in cycle t == T + 4n (t = the engine programme's edge counter), exactly the hc_<q> reader
// cadence (one 32-sector wave every 4 edges). Checks: every projection mix (o_valid) and every result pin word
// against the golden; any engine fault is fatal. Prints the measured event times.
module tb_hbm_hc_eng_static;
    localparam integer K = 20480;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer nwords = 0, nsched = 0, ngm = 0, npos = 1, nemit = 0, tb0 = 0, mode = 0, mutant = 0;
    reg [255:0] prog [0:1023]; reg [255:0] tbl [0:15];
    reg [31:0] wmem [0:24*K-1]; reg [31:0] xmem [0:8*K-1]; reg [31:0] expmix [0:8*24-1]; reg [31:0] exptail [0:8*24-1];
    integer sq [0:63], sT [0:63], scnt [0:63], skind [0:63], ssrc [0:63], sword [0:63];
    integer gq [0:63], gT [0:63], gpos [0:63], grow [0:63]; reg [31:0] gdat [0:63];
    integer fd, rc, i, n;
    reg cfg_we = 0; reg [9:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg start_v = 0; reg tbl_we = 0; reg [9:0] tbl_addr = 0; reg [255:0] tbl_data = 0;
    reg [3:0] x_wave_v; reg [39:0] x_wave_word; reg [32767:0] x_wave;
    reg [3:0] gm_v; reg [19:0] gm_row; reg [11:0] gm_pos; reg [127:0] gm_data;
    wire [3:0] result_v; wire [11:0] result_position; wire [3071:0] result; wire pa, pd, fault;
`ifdef MUT
    localparam integer MUTP = `MUT;
`else
    localparam integer MUTP = 0;
`endif
    ot_hbm_hc_eng_static #(.MUT(MUTP)) dut (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_v(start_v), .start_base(10'd0), .start_limit(11'(nwords)), .start_loops(16'd1),
        .tbl_we(tbl_we), .tbl_addr(tbl_addr), .tbl_data(tbl_data),
        .x_wave_v(x_wave_v), .x_wave_word(x_wave_word), .x_wave(x_wave),
        .gathered_mix_v(gm_v), .gathered_mix_row(gm_row), .gathered_mix_pos(gm_pos), .gathered_mix_data(gm_data),
        .result_v(result_v), .result_position(result_position), .result(result),
        .program_active(pa), .program_done(pd), .fault(fault));
    wire busy = dut.u_seq.busy;
    wire [19:0] t = dut.u_seq.t;
    // ---- quadrant wave sources and gathered-mix words (functions of the programme edge counter)
    always @* begin
        x_wave_v = 0; x_wave_word = 0; x_wave = 0; gm_v = 0; gm_row = 0; gm_pos = 0; gm_data = 0;
        if (busy) begin
            for (integer s = 0; s < nsched; s = s + 1)
                if (t >= sT[s] && (t - sT[s]) % 4 == 0 && (t - sT[s]) / 4 < scnt[s]) begin : src
                    integer m, q;
                    m = (t - sT[s]) / 4; q = sq[s];
                    x_wave_v[q] = 1'b1;
                    x_wave_word[q*10 +: 10] = 10'(sword[s] + m);
                    for (integer l = 0; l < 256; l = l + 1)
                        x_wave[q*8192 + l*32 +: 32] = skind[s] ? wmem[(ssrc[s] + m)*256 + l] : xmem[(ssrc[s] + m)*256 + l];
                end
            for (integer g = 0; g < ngm; g = g + 1)
                if (t == gT[g]) begin
                    gm_v[gq[g]] = 1'b1; gm_row[gq[g]*5 +: 5] = 5'(grow[g]); gm_pos[gq[g]*3 +: 3] = 3'(gpos[g]);
                    gm_data[gq[g]*32 +: 32] = gdat[g];
                end
        end
    end
    // ---- checks
    integer mixseen = 0, mixbad = 0, outseen = 0, outbad = 0, cyc = 0, last_out_t = 0, first_out_t = -1;
    integer last_mix_t = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && fault) begin
            $display("HC_ENG_FAULT t=%0d seq=%0d ing=%0d core=%0d mix=%0d tbl=%0d tail=%0d tfl=%0d", t, dut.seq_fault,
                dut.ing_fault, dut.core_fault, dut.mix_fault, dut.tbl_fault, dut.tail_fault, dut.tfl);
            $fatal(1, "engine fault");
        end
        if (mode == 1 && dut.u_core.raw_wv) $display("PROBE raw t=%0d ss=%0d pos=%0d idx=%0d", t,
            dut.u_core.raw_w[40], dut.u_core.raw_w[32 + 5 +: 3], dut.u_core.raw_w[32 +: 5]);
        if (dut.o_valid) begin
            mixseen = mixseen + 1; last_mix_t = t;
            if (dut.o_data !== expmix[dut.o_pos*24 + dut.o_idx]) begin
                mixbad = mixbad + 1;
                if (mixbad < 6) $display("MIX_MISMATCH pos%0d row%0d got=%08x exp=%08x", dut.o_pos, dut.o_idx,
                    dut.o_data, expmix[dut.o_pos*24 + dut.o_idx]);
            end
        end
        for (integer q = 0; q < 4; q = q + 1) if (result_v[q]) begin : chk
            integer p; p = result_position[q*3 +: 3];
            outseen = outseen + 1; last_out_t = t; if (first_out_t < 0) first_out_t = t;
            for (integer j = 0; j < 24; j = j + 1) if (result[q*768 + j*32 +: 32] !== exptail[p*24 + j]) begin
                outbad = outbad + 1;
                if (outbad < 6) $display("TAIL_MISMATCH q%0d pos%0d word%0d got=%08x exp=%08x", q, p, j,
                    result[q*768 + j*32 +: 32], exptail[p*24 + j]);
            end
        end
        if (cyc > 40000) $fatal(1, "watchdog");
    end
    initial begin
        if (!$value$plusargs("NWORDS=%d", nwords)) $fatal(1, "NWORDS");
        rc = $value$plusargs("NSCHED=%d", nsched); rc = $value$plusargs("NGM=%d", ngm);
        rc = $value$plusargs("NPOS=%d", npos); rc = $value$plusargs("NEMIT=%d", nemit);
        rc = $value$plusargs("TB=%d", tb0); rc = $value$plusargs("MODE=%d", mode);
        $readmemh("prog.mem", prog); $readmemh("tbl.mem", tbl);
        $readmemh("wmem.mem", wmem); $readmemh("xmem.mem", xmem);
        $readmemh("expmix.mem", expmix); $readmemh("exptail.mem", exptail);
        fd = $fopen("sched.txt", "r");
        for (i = 0; i < nsched; i = i + 1) rc = $fscanf(fd, "%d %d %d %d %d %d\n", sq[i], sT[i], scnt[i], skind[i], ssrc[i], sword[i]);
        $fclose(fd);
        fd = $fopen("gm.txt", "r");
        for (i = 0; i < ngm; i = i + 1) rc = $fscanf(fd, "%d %d %d %d %d\n", gq[i], gT[i], gpos[i], grow[i], gdat[i]);
        $fclose(fd);
        repeat (5) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (i = 0; i < nwords; i = i + 1) begin
            @(negedge clk); cfg_we = 1; cfg_addr = 10'(i); cfg_data = prog[i];
        end
        for (i = 0; i < 12; i = i + 1) begin
            @(negedge clk); cfg_we = 0; tbl_we = 1; tbl_addr = 10'(i); tbl_data = tbl[i];
        end
        @(negedge clk); cfg_we = 0; tbl_we = 0; repeat (4) @(negedge clk);
        start_v = 1; @(negedge clk); start_v = 0;
        wait (busy);
        wait (!busy);
        repeat (40) @(posedge clk);
        $display("HC_ENG_DONE mode=%0d npos=%0d mixes=%0d mixbad=%0d outs=%0d outbad=%0d TB=%0d last_mix_t=%0d first_out_t=%0d last_out_t=%0d HC_MIX_CYCLES=%0d",
            mode, npos, mixseen, mixbad, outseen, outbad, tb0, last_mix_t, first_out_t, last_out_t, last_out_t - tb0);
        if (mode == 1) $finish;
        if (mixbad || outbad || outseen != nemit || (mode == 0 && mixseen != 24 * npos)) $fatal(1, "HC_ENG FAIL");
        $display("HC_ENG PASS");
        $finish;
    end
endmodule
