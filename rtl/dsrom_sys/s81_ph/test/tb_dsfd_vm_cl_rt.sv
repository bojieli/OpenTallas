// tb_dsfd_vm_cl_rt (el1013-s81-vmfe/B6, S3): the capture lane with its match / touch terms formed from registers
// (dsfd_vm_cl RT 1 = the M5 hard view dsfd_vm_clt) against the v3 expressions (RT 0 = the closed clt8a RTL), same
// stimulus, every output and the three re-formed vectors (a_hS, touchA, touchB) compared EVERY cycle.
// Stimulus: phases of 4,096 cycles; keys from a pool of 2 .. 49 rows (12 entries: small pools re-hit entries in the
// cycle after their allocation, large pools evict every cycle), element density 1/16 .. 16/16, port slot always / half
// the time, occasional range / alignment faults, a reset every 64 phases.
// PASS needs 0 mismatches AND the cover counts (rows written, evictions, forwarded touches of a just-allocated entry).
// Mutant OT_SPVM_MUT_CLRT (the forward dropped) must FAIL.
`timescale 1ns/1ps
module tb_dsfd_vm_cl_rt #(parameter integer NCYC = 1000000, parameter integer SEED = 1);
    reg clk = 1'b0; always #1 clk = ~clk;
    reg rn = 1'b0; reg [3:0] gid = 4'd5; reg [15:0] ev = 16'd0; reg [16*19-1:0] ea = 0; reg [16*32-1:0] ed = 0; reg sok = 1'b1;
    wire a_v, b_v; wire [13:0] a_row, b_row; wire [15:0] a_m, b_m; wire [511:0] a_d, b_d; wire [3:0] a_f, b_f;
    dsfd_vm_cl #(.RT(0)) u_ref (.clk(clk), .rn(rn), .gid(gid), .ev(ev), .ea(ea), .ed(ed), .slot_ok(sok),
        .w_v(a_v), .w_row(a_row), .w_m(a_m), .w_d(a_d), .flt(a_f));
    dsfd_vm_cl #(.RT(1)) u_dut (.clk(clk), .rn(rn), .gid(gid), .ev(ev), .ea(ea), .ed(ed), .slot_ok(sok),
        .w_v(b_v), .w_row(b_row), .w_m(b_m), .w_d(b_d), .flt(b_f));
    integer cyc = 0, nbad = 0, nout = 0, rows = 0, k, npool = 4, dens = 8, half = 0, fph = 0, ph = 0, rcnt = 8, sd;
    reg [9:0] pool [0:63];
    reg [9:0] key; reg bad_r, bad_a; reg [6:0] al;
    initial begin sd = SEED; for (k = 0; k < 64; k = k + 1) pool[k] = $urandom(sd); end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc % 4096 == 0) begin
            ph = cyc / 4096;
            npool = 2 + $urandom % 48; dens = 1 + $urandom % 16; half = (ph % 4 == 3); fph = (ph % 8 == 7);
            for (k = 0; k < 64; k = k + 1) pool[k] = $urandom;
            if (ph % 64 == 0) rcnt = 8;
        end
        if (rcnt != 0) begin rn <= 1'b0; rcnt = rcnt - 1; end else rn <= 1'b1;
        gid <= 4'd5;
        sok <= half ? $urandom % 2 : 1'b1;
        for (k = 0; k < 16; k = k + 1) begin
            key = pool[$urandom % npool];
            bad_r = fph && ($urandom % 8192 == 0); bad_a = fph && ($urandom % 8192 == 1);
            al = {4'd5, k[3:1]} ^ {6'd0, bad_a};
            ev[k] <= ($urandom % 16) < dens;
            ea[19*k +: 19] <= {bad_r, key, al, 1'($urandom)};
            ed[32*k +: 32] <= $urandom;
        end
        if (cyc > 4) begin
            if (a_v !== b_v || a_f !== b_f || (a_v && (a_row !== b_row || a_m !== b_m || a_d !== b_d))) begin
                nout = nout + 1; nbad = nbad + 1;
                if (nbad < 6) $display("MISMATCH out cyc %0d: v %b/%b row %h/%h m %h/%h flt %h/%h", cyc, a_v, b_v, a_row, b_row, a_m, b_m, a_f, b_f);
            end
            if (u_ref.touchA !== u_dut.touchA || u_ref.touchB !== u_dut.touchB) begin
                nbad = nbad + 1;
                if (nbad < 6) $display("MISMATCH touch cyc %0d: A %h/%h B %h/%h", cyc, u_ref.touchA, u_dut.touchA, u_ref.touchB, u_dut.touchB);
            end
            for (k = 0; k < 16; k = k + 1) if (u_ref.a_hS[k] !== u_dut.a_hS[k]) begin
                nbad = nbad + 1;
                if (nbad < 6) $display("MISMATCH a_hS[%0d] cyc %0d: %h/%h", k, cyc, u_ref.a_hS[k], u_dut.a_hS[k]);
            end
            if (a_v) rows = rows + 1;
        end
        if (cyc == NCYC) begin
            $display("CLRT cycles=%0d rows=%0d evictions=%0d forwarded=%0d mismatches=%0d out_mismatches=%0d flt=%h", cyc, rows,
                     u_dut.cov_ev, u_dut.cov_fw, nbad, nout, b_f);
            if (nbad == 0 && rows > 10000 && u_dut.cov_ev > 1000 && u_dut.cov_fw > 1000) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
