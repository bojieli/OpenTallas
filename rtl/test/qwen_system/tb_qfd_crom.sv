`timescale 1ns/1ps
// Exact bench of ot_qfd_crom (stream qwen-system 2026-10-08) against the stage-image golden of
// tools/qwen_system/crom_image.py build (crom_vectors.hex; macro via maps under +OT_ROM_DIR).
//   phase A: every vector (every stored word, ZERO / QSCALE words, the stage + head programs' own read vectors at
//            three positions; random lane masks), random bubbles; each answered lane must equal the golden word
//            5 edges after the strobe; no fault.
//   phase B: four fail-closed cases (out of range, head out of range, misaligned lane, rows disagree), each after a
//            reset: fault must rise with the named first-cause code; a clean vector must NOT fault.
// +VEC=<file> +OT_ROM_DIR=<dir> [+SEED=n].  Prints "CROM_RESULT pass=<0|1> vectors=.. lanes=.. mismatches=..".
`ifndef CROM_OREG
`define CROM_OREG 0
`endif
`ifndef CROM_IREL
`define CROM_IREL 0
`endif
`ifndef CROM_RSYNC
`define CROM_RSYNC 0
`endif
// drive-0158: the -cl options (OREG / IREL / RSYNC) shift the answer by OREG + IREL edges and the reset release by
// 4 edges (RSYNC); the bench follows the DUT's documented latency, it does not search for it.
module tb_qfd_crom;
    localparam integer SW = 64, AW = 24, LW = 6, LAT = 5 + `CROM_OREG + `CROM_IREL, RWAIT = (`CROM_RSYNC != 0) ? 4 : 0;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    reg  [SW-1:0]    re = 0;
    reg  [SW*AW-1:0] addr = 0;
    reg  [LW-1:0]    stage = 0;
    wire [SW*64-1:0] q;
    wire             fault;
    wire [1:0]       fcode;
    ot_qfd_crom #(.MUT(`MUT), .OREG(`CROM_OREG), .IREL(`CROM_IREL), .RSYNC(`CROM_RSYNC)) dut (.clk(clk), .rst_n(rst_n), .crom_re(re), .crom_addr(addr), .crom_stage(stage),
                                   .crom_q(q), .fault(fault), .fault_code(fcode));

    // expectation pipeline
    reg [SW*64-1:0] exp_p [0:LAT];
    reg [SW-1:0]    msk_p [0:LAT];
    reg             v_p   [0:LAT];
    integer k, lane, fd, rc, nvec = 0, nlanes = 0, nmis = 0, seed = 1, bub, ncyc = 0;
    reg [7:0]        f_st;
    reg [63:0]       f_re;
    reg [SW*AW-1:0]  f_a;
    reg [SW*64-1:0]  f_e;
    reg [1023:0]     vec, rom;
    reg              pass;

    task automatic step(input [SW-1:0] r, input [SW*AW-1:0] a, input [LW-1:0] s, input [SW*64-1:0] e, input v);
        begin
            re <= r; addr <= a; stage <= s;
            exp_p[0] = e; msk_p[0] = r; v_p[0] = v;
            @(posedge clk);
            ncyc = ncyc + 1;
            for (k = LAT; k > 0; k = k - 1) begin exp_p[k] = exp_p[k-1]; msk_p[k] = msk_p[k-1]; v_p[k] = v_p[k-1]; end
            // q after LAT edges: compare at the edge's output (sampled after the edge)
            #0.01;
            if (v_p[LAT]) for (lane = 0; lane < SW; lane = lane + 1)
                if (msk_p[LAT][lane]) begin
                    nlanes = nlanes + 1;
                    if (q[lane*64 +: 64] !== exp_p[LAT][lane*64 +: 64]) begin
                        if (nmis < 8) $display("MISMATCH vec~%0d lane %0d got %h exp %h", nvec - LAT, lane,
                                                q[lane*64 +: 64], exp_p[LAT][lane*64 +: 64]);
                        nmis = nmis + 1;
                    end
                end
        end
    endtask

    task automatic drain;
        integer dk;
        begin for (dk = 0; dk < LAT + 2; dk = dk + 1) step(0, 0, stage, {SW*64{1'b0}}, 0); end
    endtask

    function automatic [SW*AW-1:0] row_addrs(input integer base);
        integer j;
        begin for (j = 0; j < SW; j = j + 1) row_addrs[j*AW +: AW] = base + j; end
    endfunction

    task automatic fault_case(input [SW-1:0] r, input [SW*AW-1:0] a, input [LW-1:0] s, input [1:0] want, input string nm);
        begin
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; @(posedge clk); repeat (RWAIT) @(posedge clk);
            step(r, a, s, {SW*64{1'b0}}, 0);
            drain();
            if (want == 0 ? fault : !(fault && fcode == want)) begin
                $display("FAULT_CASE %s FAIL fault=%0d code=%0d want=%0d", nm, fault, fcode, want); pass = 0;
            end else $display("FAULT_CASE %s ok fault=%0d code=%0d", nm, fault, fcode);
        end
    endtask

    initial begin
        pass = 1;
        if (!$value$plusargs("VEC=%s", vec)) begin $display("need +VEC"); $finish; end
        if ($value$plusargs("SEED=%d", seed)) ;
        for (k = 0; k <= LAT; k = k + 1) v_p[k] = 0;
        repeat (4) @(posedge clk); rst_n = 1; @(posedge clk); repeat (RWAIT) @(posedge clk);
        fd = $fopen(vec, "r");
        if (fd == 0) begin $display("cannot open %0s", vec); $finish; end
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%h %h %h %h\n", f_st, f_re, f_a, f_e);
            if (rc != 4) begin $display("bad vector line rc=%0d at vector %0d", rc, nvec); pass = 0; rc = $fgetc(fd); end
            else begin
                step(f_re, f_a, f_st[LW-1:0], f_e, 1);
                nvec = nvec + 1;
                bub = $urandom(seed + nvec) % 8;
                if (bub == 0) step(0, $urandom, f_st[LW-1:0], {SW*64{1'b0}}, 0);   // a bubble (re = 0, junk address)
            end
        end
        drain();
        if (fault) begin $display("unexpected fault code %0d in phase A", fcode); pass = 0; end
        if (nmis != 0 || nlanes == 0) pass = 0;
        // phase B: fail closed
        fault_case({SW{1'b1}}, row_addrs(9473 + 64*77), 6'd5, 2'd0, "clean_rope");
        fault_case(64'h1, {{(SW-1)*AW{1'b0}}, 24'd541953}, 6'd3, 2'd1, "out_of_range");
        fault_case(64'h1, {{(SW-1)*AW{1'b0}}, 24'd4096}, 6'd36, 2'd1, "head_out_of_range");
        fault_case(64'h1, {{(SW-1)*AW{1'b0}}, 24'd9473 + 24'd64*5 + 24'd4}, 6'd0, 2'd2, "misaligned");
        begin : dis
            reg [SW*AW-1:0] aa; aa = row_addrs(9473 + 64*5); aa[1*AW +: AW] = 9473 + 64*7 + 1;
            fault_case(64'hf, aa, 6'd0, 2'd3, "rows_disagree");
        end
        fault_case(64'h1, {{(SW-1)*AW{1'b0}}, 24'd0}, 6'd37, 2'd1, "stage_out_of_range");
        $display("CROM_RESULT pass=%0d vectors=%0d lanes=%0d mismatches=%0d cycles=%0d mut=%0d", pass, nvec, nlanes,
                 nmis, ncyc, `MUT);
        $finish;
    end
endmodule
