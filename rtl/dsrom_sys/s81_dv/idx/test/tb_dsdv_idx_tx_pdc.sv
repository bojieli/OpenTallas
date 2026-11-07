`timescale 1ns/1ps
// DIE-S81-51/RF-C RE-FORM 11-03 (S81-056): lockstep bench of the re-formed dsdv_idx_tx_n32 (FACE = 1 input face flops,
// LKL = 1 negative-level lockup latch on every output) against the old form (FACE 0, LKL 0) on the same vi / vo stream.
// Claim: lo_new / st_new == lo_old / st_old delayed by exactly DLY_EXP ck edges (FACE = +1), bit-exact, every cycle after
// reset.  Stimulus: seeded constrained-random protocol beats (CTL job word on vo with UID, ingress capture beats of kind
// IK on vi (part 0 / part 1, lane cursor REBASE types 1 / 6), egress IDX words of kind EK tagged OT (type 3) and DONE
// (type 4)), plus random filler; several jobs per run.  Parameters = the kit spec (physical/ref_tile/s81dv_idxtxn32x).
// NEW_MUT (negative control): MUT of the new instance (3 = output grid one pitch late).  DLY_EXP 0 = wrong delay claim.
// Prints TB_IDXTX_PDC PASS / FAIL with cycle, mismatch and activity counts (lo beats, st changes).
module tb_dsdv_idx_tx_pdc;
    parameter integer DLY_EXP = 0;
    parameter integer NEW_MUT = 0;
    parameter integer NEW_LKL = 0;
    parameter integer NEW_PDC = 1;
    localparam integer V = 276;
    reg ck = 0, rst = 0;
    always #0.4165 ck = ~ck;
    reg [V-1:0] vi = 0, vo = 0;
    wire [V-1:0] lo_o, lo_n; wire [15:0] st_o, st_n;
    dsdv_idx_tx_n32_old #(.V(276), .IK(4), .EK(5), .UID(92), .D(8192), .IB(64), .SRAM_MACRO(1), .MUT(0), .RDL(1), .WDL(1),
        .WDC(1), .SCS(1), .RIL(1), .RHP(1), .FACE(2), .LKL(0), .MLK(0)) u_old (.ck(ck), .rst(rst), .vi(vi), .vo(vo), .lo(lo_o), .st(st_o));
    dsdv_idx_tx_n32 #(.V(276), .IK(4), .EK(5), .UID(92), .D(8192), .IB(64), .SRAM_MACRO(1), .MUT(NEW_MUT), .RDL(1), .WDL(1),
        .WDC(1), .SCS(1), .RIL(1), .RHP(1), .FACE(2), .LKL(NEW_LKL), .MLK(0), .PDC(NEW_PDC)) u_new (.ck(ck), .rst(rst), .vi(vi), .vo(vo), .lo(lo_n), .st(st_n));
    integer seed, ncyc, cyc = 0;
    reg [V+15:0] hist [0:7];
    longint curld = 0, bad = 0, lo_beats = 0, st_chg = 0, chk = 0, jobs = 0, idxw = 0;
    reg [15:0] st_prev = 0;
    reg [7:0] ot = 8'h3c;
    integer phase = 0, left = 0;
    function automatic [V-1:0] rnd();
        integer i; for (i = 0; i < V; i = i + 32) rnd[i +: 32] = $urandom; endfunction
    task automatic drive();
        reg [V-1:0] a, b; reg [185:0] p; integer r;
        a = 0; b = 0;
        if (cyc < 40) begin vi <= 0; vo <= 0; return; end
        r = $urandom % 100;
        // vi: ingress beats of kind 4 (60 %), other kinds (10 %), idle
        if (r < 60) begin
            a = rnd(); a[0] = 1; a[3:1] = 3'd4;
            if ($urandom % 8 == 0) begin a[6] = 0; a[7] = 1; a[19:16] = ($urandom % 2) ? 4'd1 : 4'd6; a[23:20] = 0; end
        end else if (r < 70) begin a = rnd(); a[0] = 1; end
        // vo: CTL job word (phase 0), egress beats with IDX words (phase 1), DONE (phase 2)
        if (phase == 0 && $urandom % 50 == 0) begin
            b = rnd(); b[0] = 1; b[3:1] = 3'd0; b[28:21] = 8'd92; b[31:29] = 3'd2;
            p = b[21 +: 186];
            p[40:31] = 10'($urandom % 24 + 1);          // K
            p[84:69] = 16'($urandom % 40 + 4);          // DLY
            p[87:85] = 3'($urandom % 3 + 1);            // R
            p[99:88] = 12'($urandom % 48 + 8);          // SM
            ot = 8'($urandom); p[68:61] = ot;           // OT
            b[21 +: 186] = p;
            phase = 1; left = 20 + $urandom % 40; jobs = jobs + 1;
        end else if (phase >= 1 && $urandom % 3 == 0) begin
            b = rnd(); b[0] = 1; b[3:1] = 3'd5;
            if ($urandom % 2 == 0) b[6] = 0;            // egress part 0
            else begin
                b[6] = 1; b[271:264] = ($urandom % 8 == 0) ? 8'($urandom) : ot;
                if (phase == 2) begin b[275:272] = 4'd4; phase = 0; end
                else begin b[275:272] = 4'd3; idxw = idxw + 1; left = left - 1; if (left <= 0) phase = 2; end
            end
        end else if ($urandom % 20 == 0) b = rnd();
        vi <= a; vo <= b;
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        void'($urandom(seed));
        rst = 0; repeat (12) @(posedge ck); rst = 1;
    end
    always @(posedge ck) begin
        integer k;
        cyc <= cyc + 1;
        // compare (sampled before this edge's updates): new now vs old DLY_EXP edges ago
        hist[0] <= {st_o, lo_o};
        for (k = 1; k < 8; k = k + 1) hist[k] <= hist[k - 1];
        if (rst && cyc > 40 + 8) begin
            chk <= chk + 1;
            if ({st_n, lo_n} !== ((DLY_EXP == 0) ? {st_o, lo_o} : hist[DLY_EXP - 1])) begin
                bad <= bad + 1;
                if (bad < 4) $display("TB_IDXTX_PDC mismatch cyc %0d lo %0d st %h/%h", cyc,
                    lo_n !== ((DLY_EXP == 0) ? lo_o : hist[DLY_EXP - 1][V-1:0]), st_n,
                    (DLY_EXP == 0) ? st_o : hist[DLY_EXP - 1][V +: 16]);
            end
            if (lo_o[0]) lo_beats <= lo_beats + 1;
            if (|u_old.g_face.g_fl.vi_g[7:0] && u_old.c_v && !u_old.c_p1 && u_old.c_sg) curld <= curld + 1;
            if (st_o !== st_prev) st_chg <= st_chg + 1;
            st_prev <= st_o;
        end
        if (rst) drive();
        if (cyc == ncyc) begin
            $display("TB_IDXTX_PDC seed %0d cycles %0d checked %0d jobs %0d idx_words %0d lo_beats %0d st_changes %0d mismatches %0d dly %0d new_mut %0d lkl %0d pdc %0d curld %0d",
                     seed, cyc, chk, jobs, idxw, lo_beats, st_chg, bad, DLY_EXP, NEW_MUT, NEW_LKL, NEW_PDC, curld);
            if (bad == 0 && lo_beats > 0) $display("TB_IDXTX_PDC PASS"); else $display("TB_IDXTX_PDC FAIL");
            $finish;
        end
    end
endmodule
