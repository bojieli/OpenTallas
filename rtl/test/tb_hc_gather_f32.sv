`timescale 1ns/1ps
// HBM-HCBANK6 10-20: ot_hgi_hc_gathered_mix_reader_f32_static (native32 rebuild) against ot_hgi_hc_gathered_mix_reader_static
// #(RESP_PHASE 23, EXTB 1, RSC 24) in lockstep: random launches (legal / illegal bounds / while active), random strides and
// bases (return sectors crossing banks), LG returns on the reference's expected edges with random data (plus rare stray
// valids), every output compared on every edge.  +define+MUT=1: response prediction one edge late (must FAIL).
`ifndef MUT
`define MUT 0
`endif
module tb_hc_gather_f32;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg launch = 0, bnd = 0; reg [3:0] npos = 0; reg [15:0] base = 0, stride = 0;
    reg [2055:0] rr;
    wire [135:0] rq0, rq1; wire [7:0] rd0, rd1; wire v0, v1, d0, d1, f0, f1; wire [4:0] r0, r1; wire [2:0] p0, p1; wire [31:0] g0, g1;
    ot_hgi_hc_gathered_mix_reader_static #(.RESP_PHASE(23), .EXTB(1), .RSC(24)) ref0 (.clk(clk), .rst_n(rst_n), .launch(launch),
        .npos(npos), .base_sector(base), .position_stride_sector(stride), .bounds_i(bnd), .local_rq(rq0), .local_read(rd0),
        .local_rr(rr), .gathered_mix_v(v0), .gathered_mix_row(r0), .gathered_mix_pos(p0), .gathered_mix_data(g0), .done(d0), .fault(f0));
    ot_hgi_hc_gathered_mix_reader_f32_static #(.RESP_PHASE(23), .MUT(`MUT)) dut (.clk(clk), .rst_n(rst_n), .launch(launch),
        .launch_c({11{launch}}), .npos(npos), .base_sector(base), .position_stride_sector(stride), .bounds_i(bnd), .local_rq(rq1),
        .local_read(rd1), .local_rr(rr), .gathered_mix_v(v1), .gathered_mix_row(r1), .gathered_mix_pos(p1), .gathered_mix_data(g1),
        .done(d1), .fault(f1));
    integer cyc = 0, bad = 0, nv = 0, nd = 0, nf = 0;
    reg [7:0] ev;
    always @* begin ev = 0; for (integer j = 0; j < 3; j = j + 1) if (ref0.response_slot) ev[3'(ref0.return_sector + 16'(j))] = 1'b1; end
    always @(negedge clk) begin
        for (integer b = 0; b < 8; b = b + 1) begin
            for (integer w = 0; w < 8; w = w + 1) rr[b*257 + w*32 +: 32] = $urandom;
            rr[b*257 + 256] = ev[b] ^ ($urandom % 4000 == 0);
        end
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        if (cyc % 3000 == 2990) rst_n <= 0;            // faults are sticky: periodic reset
        if (cyc % 3000 == 2994) rst_n <= 1;
        launch <= 0;
        if (rst_n && ($urandom % (ref0.active ? 400 : 12) == 0)) begin
            launch <= 1; npos <= 4'($urandom % 10); base <= 16'($urandom); stride <= 16'($urandom % 64);
            bnd <= ($urandom % 8 != 0);
        end
        if (rst_n) begin
            if ({rq0, rd0, v0, r0, p0, g0, d0, f0} !== {rq1, rd1, v1, r1, p1, g1, d1, f1}) begin
                bad <= bad + 1; if (bad < 5) $display("MISMATCH cyc=%0d v %b/%b row %0d/%0d data %h/%h f %b/%b rd %h/%h", cyc, v0, v1, r0, r1, g0, g1, f0, f1, rd0, rd1);
            end
            if (v0) nv <= nv + 1; if (d0) nd <= nd + 1; if (f0) nf <= nf + 1;
        end
        if (cyc == 200000) begin
            if (bad == 0 && nd > 100 && nv > 10000) $display("GATHER_F32 PASS MUT=%0d mixv=%0d done=%0d faultedges=%0d", `MUT, nv, nd, nf);
            else $display("GATHER_F32 FAIL MUT=%0d bad=%0d mixv=%0d done=%0d", `MUT, bad, nv, nd);
            $finish;
        end
    end
endmodule
