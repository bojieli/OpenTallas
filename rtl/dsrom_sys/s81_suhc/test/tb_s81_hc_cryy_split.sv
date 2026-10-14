`timescale 1ns/1ps
// Lockstep bench of the y slice leaves (s81hc-1013 r8): ot_s81_hc_crooty_yl (LC x ot_s81_hc_cryys, flop store) against
// ot_s81_hc_crooty_y (FIFO_SLICE 256: ot_fifo_sram_fwft over the 128 x 256 SRAM macro models) at the production
// parameters (NG 256, C 0 or 2: 11 slices, 2,816 b, YD 16).  Contract: p_y and p_flt equal on EVERY cycle from the first
// cycle (no latency difference), under legal traffic (occupancy 0 .. YD, bursts that fill the FIFO, drains, push and pop
// in one cycle, empty-FIFO bypass), a reset in mid traffic, and illegal traffic in the last eighth (pop on empty, push
// on full: sticky p_flt, pointers wrapping).  Negative controls (defines in the leaf): OT_S81_HC_CRYYS_MUT1 one stored
// bit of the odd words, OT_S81_HC_CRYYS_MUT2 p_y bit 30 on a pop.
module tb_s81_hc_cryy_split #(parameter integer C = 0, NCYC = 60000);
    localparam integer YS = 11 * 256, YD = 16;
    reg clk = 0, srs = 0;
    always #1 clk = ~clk;
    reg [YS-1:0] y_s;  reg yacc, p_req;
    wire [YS-1:0] r_y, n_y;  wire r_f, n_f;
    ot_s81_hc_crooty_y #(.C(C), .FIFO_SLICE(256)) u_ref (.sk(clk), .srs(srs), .y_s(y_s), .yacc(yacc), .p_req(p_req), .p_y(r_y), .p_flt(r_f));
    ot_s81_hc_crooty_yl #(.C(C)) u_new (.sk(clk), .srs(srs), .y_s(y_s), .yacc(yacc), .p_req({11{p_req}}), .p_y(n_y), .p_flt(n_f));
    integer cyc = 0, bad = 0, chk = 0, occ = 0, mode = 0, left = 0, i;
    integer n_push = 0, n_pop = 0, n_both = 0, n_full = 0, n_byp = 0, n_arr = 0, c_flt = 0, n_nz = 0, slices = 0;
    reg [10:0] sl_seen = 0;
    reg [31:0] rnd;
    wire ill = cyc > 7 * NCYC / 8;
    initial begin y_s = 0; yacc = 0; p_req = 0; end
    always @(negedge clk) begin
        cyc <= cyc + 1;
        rnd = $urandom;
        if (cyc == 6) srs <= 1'b1;
        if (cyc == NCYC / 2) begin srs <= 1'b0; occ <= 0; end                 // a reset in mid traffic
        if (cyc == NCYC / 2 + 8) srs <= 1'b1;
        for (i = 0; i < YS / 32; i = i + 1) y_s[32 * i +: 32] <= $urandom;
        yacc <= 1'b0; p_req <= 1'b0;
        if (cyc > 12 && !(cyc >= NCYC / 2 && cyc < NCYC / 2 + 12)) begin : traffic
            reg pu, po;
            if (left == 0) begin mode <= rnd[30:28] % 5; left <= 8 + rnd[27:20]; end else left <= left - 1;
            case (mode)
                0: begin pu = rnd[1:0] == 0; po = rnd[3:2] == 0; end                // sparse: empty-FIFO bypass
                1: begin pu = 1'b1; po = rnd[2:0] == 0; end                         // fill
                2: begin pu = rnd[2:0] == 0; po = 1'b1; end                         // drain
                3: begin pu = 1'b1; po = 1'b1; end                                  // sustained push + pop
                default: begin pu = rnd[0]; po = rnd[1]; end
            endcase
            if (!ill) begin
                if (occ >= YD) pu = 1'b0;                                           // legal: never push on full
                if (occ == 0) po = 1'b0;                                            //        never pop on empty
            end else begin
                if (occ >= YD && rnd[15:10] != 0) pu = 1'b0;                        // illegal: now and then
                if (occ == 0 && rnd[25:20] != 0) po = 1'b0;
            end
            // the note under ydata of the reference: a push is the data that entered two cycles before yacc's flop
            yacc <= pu; p_req <= po;
            occ <= occ + (pu ? 1 : 0) - (po ? 1 : 0);
            if (pu) n_push <= n_push + 1;
            if (po) n_pop <= n_pop + 1;
            if (pu && po) n_both <= n_both + 1;
            if (occ + (pu ? 1 : 0) - (po ? 1 : 0) == YD) n_full <= n_full + 1;
        end
    end
    reg [YS-1:0] last_y = 0;
    always @(posedge clk) begin
        chk <= chk + 1;
        if (n_y !== r_y || n_f !== r_f) begin
            bad <= bad + 1;
            if (bad < 6) begin
                $display("mismatch cyc %0d: p_flt %b/%b", cyc, n_f, r_f);
                for (i = 0; i < 11; i = i + 1) if (n_y[256 * i +: 256] !== r_y[256 * i +: 256]) $display("  slice %0d differs", i);
            end
        end
        if (n_f) c_flt <= c_flt + 1;
        if (n_y != last_y) begin
            n_nz <= n_nz + 1;
            for (i = 0; i < 11; i = i + 1) if (n_y[256 * i +: 256] != last_y[256 * i +: 256]) sl_seen[i] <= 1'b1;
        end
        last_y <= n_y;
        if (u_new.g_f[0].u_s.bypass) n_byp <= n_byp + 1;
        if (u_new.g_f[0].u_s.rd_arr) n_arr <= n_arr + 1;
        if (cyc == NCYC) begin
            slices = 0; for (i = 0; i < 11; i = i + 1) slices = slices + sl_seen[i];
            $display("CRYY_SPLIT C=%0d: %0d mismatches / %0d compared cycles; pushes %0d pops %0d (same cycle %0d) full %0d bypass %0d array reads %0d p_y changes %0d slices seen %0d/11 p_flt cycles %0d",
                C, bad, chk, n_push, n_pop, n_both, n_full, n_byp, n_arr, n_nz, slices, c_flt);
            if (bad == 0 && chk > NCYC - 4 && n_push > 5000 && n_pop > 5000 && n_both > 1000 && n_full > 100 && n_byp > 100
                && n_arr > 2000 && slices == 11 && c_flt > 100) $display("CRYY_SPLIT PASS");
            else $display("CRYY_SPLIT FAIL");
            $finish;
        end
    end
endmodule
