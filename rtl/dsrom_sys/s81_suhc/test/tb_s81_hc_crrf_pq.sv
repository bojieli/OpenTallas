`timescale 1ns/1ps
// Lockstep + composition bench of the pin-register form of the forward column root (s81-suhc r10, 2026-10-13):
//   REF = ot_s81_hc_crootr_f PQ 0 (the v2 form that closed as s81hc_crrf{e,w}_ref-v2) + ot_s81_hc_crooty_yl (11 leaves)
//   NEW = ot_s81_hc_crootr_f PQ 1 (p_req: 11 pin flops fed from the W-face capture; no mid-height y relay) + 11 leaves,
//         leaf k asked by p_req[k]
// at the production parameters (NG 256, C 0 or 2: 11 slices, 2,816 b, YD 16, RF 5).  Contract: ch_fv, ch_fd and ch_rst
// equal on EVERY cycle (no latency difference at the tile's chain face), no p_flt on either side, under legal traffic:
// random forward beats, POST beats alone / back to back / in bursts that drain the FIFO, pushes that fill it, a reset in
// mid traffic.  Legal = a POST only when a slice pushed >= 4 cycles earlier is still unread, a push only when the FIFO
// has room even if the last 4 POSTs have not popped yet (NEW pops one cycle after REF).
// Negative controls (defines in the tile): OT_S81_HC_CRRF_MUT1 the request leaves one cycle early (PQ 0 timing without
// the relay), OT_S81_HC_CRRF_MUT2 the copy of slice LC/2 never asks.
module tb_s81_hc_crrf_pq #(parameter integer C = 0, NCYC = 60000);
    localparam integer LC = 11, YS = LC * 256, YD = 16, S_RD = 2, FVW = S_RD + 5;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + YS;
    localparam integer LAG = 4;
    reg clk = 0, srs = 0;
    always #1 clk = ~clk;
    reg  [YS-1:0]  y_s;
    reg            yacc;
    reg  [FVW-1:0] f_fv;
    reg  [FSW-1:0] f_fd;
    wire [LC-1:0]  r_req, n_req;
    wire [YS-1:0]  r_y, n_y;
    wire           r_flt, n_flt, r_rst, n_rst;
    wire [FVW-1:0] r_fv, n_fv;
    wire [FDW-1:0] r_fd, n_fd;
    ot_s81_hc_crootr_f #(.C(C), .PQ(0)) u_ref (.sk(clk), .srs(srs), .f_fv(f_fv), .f_fd(f_fd), .p_req(r_req), .p_y(r_y),
        .ch_rst(r_rst), .ch_fv(r_fv), .ch_fd(r_fd));
    ot_s81_hc_crooty_yl #(.C(C)) u_ref_y (.sk(clk), .srs(srs), .y_s(y_s), .yacc(yacc), .p_req(r_req), .p_y(r_y), .p_flt(r_flt));
    ot_s81_hc_crootr_f #(.C(C)) u_new (.sk(clk), .srs(srs), .f_fv(f_fv), .f_fd(f_fd), .p_req(n_req), .p_y(n_y),
        .ch_rst(n_rst), .ch_fv(n_fv), .ch_fd(n_fd));
    ot_s81_hc_crooty_yl #(.C(C)) u_new_y (.sk(clk), .srs(srs), .y_s(y_s), .yacc(yacc), .p_req(n_req), .p_y(n_y), .p_flt(n_flt));
    integer cyc = 0, bad = 0, chk = 0, mode = 0, left = 0, i;
    integer n_push = 0, n_pop = 0, n_b2b = 0, n_full = 0, n_post_out = 0, n_plain_out = 0, c_flt = 0, n_ych = 0, slices = 0, n_lead = 0;
    integer pushes = 0, pops = 0;                   // issued so far
    integer push_h [0:LAG], pop_h [0:LAG];          // issue counts LAG cycles back
    reg [LC-1:0] sl_seen = 0;
    reg [31:0] rnd;
    reg last_po = 0;
    initial begin y_s = 0; yacc = 0; f_fv = 0; f_fd = 0; for (i = 0; i <= LAG; i = i + 1) begin push_h[i] = 0; pop_h[i] = 0; end end
    wire quiet = cyc >= NCYC / 2 - 12 && cyc < NCYC / 2 + 16;
    always @(negedge clk) begin
        cyc <= cyc + 1;
        rnd = $urandom;
        if (cyc == 6) srs <= 1'b1;
        if (cyc == NCYC / 2) begin srs <= 1'b0; pushes = 0; pops = 0; for (i = 0; i <= LAG; i = i + 1) begin push_h[i] = 0; pop_h[i] = 0; end end
        if (cyc == NCYC / 2 + 8) srs <= 1'b1;
        for (i = 0; i < YS / 32; i = i + 1) y_s[32 * i +: 32] <= $urandom;
        for (i = 0; i < (FSW + 31) / 32; i = i + 1) f_fd[32 * i +: 32] <= $urandom;
        yacc <= 1'b0; f_fv <= 0;
        if (cyc > 14 && !quiet) begin : traffic
            reg pu, po;
            reg [FVW-1:0] v;
            if (left == 0) begin mode <= rnd[30:28] % 5; left <= 8 + rnd[27:20]; end else left <= left - 1;
            case (mode)
                0: begin pu = rnd[1:0] == 0; po = rnd[3:2] == 0; end                // sparse
                1: begin pu = 1'b1; po = rnd[2:0] == 0; end                         // fill
                2: begin pu = rnd[2:0] == 0; po = 1'b1; end                         // drain, POSTs back to back
                3: begin pu = 1'b1; po = 1'b1; end                                  // sustained push + pop
                default: begin pu = rnd[0]; po = rnd[1]; end
            endcase
            if (pushes - pop_h[LAG] >= YD) pu = 1'b0;                               // room even if the last LAG POSTs are still in flight
            if (push_h[LAG] - pops <= 0) po = 1'b0;                                 // a slice pushed >= LAG cycles ago is unread
            v = rnd[FVW+7:8]; v[S_RD] = po;
            if (rnd[7:5] == 0) v = {FVW{1'b0}};                                     // idle beats
            v[S_RD] = po;
            yacc <= pu; f_fv <= v;
            if (pu) begin pushes = pushes + 1; n_push <= n_push + 1; end
            if (po) begin pops = pops + 1; n_pop <= n_pop + 1; end
            if (po && last_po) n_b2b <= n_b2b + 1;
            if (pushes - pops == YD) n_full <= n_full + 1;
            last_po <= po;
        end else last_po <= 1'b0;
        for (i = LAG; i > 0; i = i - 1) begin push_h[i] = push_h[i-1]; pop_h[i] = pop_h[i-1]; end
        push_h[0] = pushes; pop_h[0] = pops;
    end
    reg [YS-1:0] last_y = 0;
    always @(posedge clk) begin
        chk <= chk + 1;
        if (n_fv !== r_fv || n_fd !== r_fd || n_rst !== r_rst) begin
            bad <= bad + 1;
            if (bad < 6) begin
                $display("mismatch cyc %0d: ch_fv %h/%h ch_rst %b/%b", cyc, n_fv, r_fv, n_rst, r_rst);
                for (i = 0; i < LC; i = i + 1) if (n_fd[O_D + 256 * i +: 256] !== r_fd[O_D + 256 * i +: 256]) $display("  y slice %0d of ch_fd differs", i);
                if (n_fd[O_D-1:0] !== r_fd[O_D-1:0]) $display("  ch_fd header differs");
            end
        end
        if (n_flt || r_flt) c_flt <= c_flt + 1;
        if (r_fv[S_RD]) begin
            n_post_out <= n_post_out + 1;
            if (r_fd[O_D +: YS] != last_y) begin
                n_ych <= n_ych + 1;
                for (i = 0; i < LC; i = i + 1) if (r_fd[O_D + 256 * i +: 256] != last_y[256 * i +: 256]) sl_seen[i] <= 1'b1;
            end
            last_y <= r_fd[O_D +: YS];
        end else if (r_fv != 0) n_plain_out <= n_plain_out + 1;
        if (|n_req && !(|r_req)) n_lead <= n_lead + 1;            // cycles in which only NEW asks (it asks one cycle later)
        if (cyc == NCYC) begin
            slices = 0; for (i = 0; i < LC; i = i + 1) slices = slices + sl_seen[i];
            $display("CRRF_PQ C=%0d: %0d mismatches / %0d compared cycles; pushes %0d POSTs %0d (back to back %0d) full %0d; chain POST beats %0d (y changed %0d) plain beats %0d; slices seen %0d/%0d; request-skew cycles %0d; p_flt cycles %0d",
                C, bad, chk, n_push, n_pop, n_b2b, n_full, n_post_out, n_ych, n_plain_out, slices, LC, n_lead, c_flt);
            if (bad == 0 && chk > NCYC - 4 && n_push > 5000 && n_pop > 5000 && n_b2b > 1000 && n_full > 100
                && n_post_out > 5000 && n_ych > 4000 && n_plain_out > 5000 && slices == LC && n_lead > 1000 && c_flt == 0) $display("CRRF_PQ PASS");
            else $display("CRRF_PQ FAIL");
            $finish;
        end
    end
endmodule
