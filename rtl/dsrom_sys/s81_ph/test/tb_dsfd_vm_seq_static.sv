`timescale 1ns/1ps
// tb_dsfd_vm_seq_static (claude S81 VM owner r7, 2026-10-14): exact bench of the static VM sequencer engine 12.
// A bench-side offline scheduler (the role of the compiler) builds an immutable calendar: per job a compiler-assigned
// counter slot, ARM pin cycle, every operand element's commit on its ACTUAL native observation port (slice g, bank =
// row[4:0] ^ {row[7:5],00}, address row[13:5]; at most one commit per port per cycle; partial masks split a row's
// words over several commits), a CHECK pin at/after the last commit, legal reads after the CHECK, native codes 4..7.
// Checks, every cycle: c_done == exactly the expected {v, tag} (DLAT 7 after each command pin; the stimulus is driven after the previous edge, nothing else);
// t_inp_su / t_inp_hc == the contract window [CHECK + 7, next ARM of that slot + 3); final sticky fault vector == the
// mode's expected set (0 in the base mode).  +mode: 0 base, 1 dropped commit, 2 duplicated commit, 3 early read,
// 4 re-ARM before CHECK, 5 CHECK client mismatch, 6 CHECK of an unarmed slot.  +seed, +jobs.
module tb_dsfd_vm_seq_static;
    localparam integer MAXC = 60000, MAXE = 1200000, MAXJ = 2000, DLAT = 7;
    reg ck = 1'b0; reg rst = 1'b0;
    always #0.4167 ck = ~ck;
    reg  [84:0] c_cmd; wire [8:0] c_done; wire [1:0] c_st;
    reg  [127:0] o_cv; reg [1151:0] o_ca; reg [511:0] o_cm; reg [31:0] o_rv; reg [447:0] o_rr;
    wire v_cv; wire [83:0] v_cd; reg v_dv; reg [7:0] v_dt; reg v_flt;
    wire t_inp_su, t_inp_hc;
    dsfd_vm_seq_static u (.ck(ck), .rst(rst), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .o_cv(o_cv), .o_ca(o_ca), .o_cm(o_cm), .o_rv(o_rv), .o_rr(o_rr),
        .v_cv(v_cv), .v_cd(v_cd), .v_dv(v_dv), .v_dt(v_dt), .v_flt(v_flt), .t_inp_su(t_inp_su), .t_inp_hc(t_inp_hc));

    // ---------------- calendar storage
    reg [84:0]  cmd_at [0:MAXC-1];
    reg [127:0] occ    [0:MAXC-1];
    reg [31:0]  rocc   [0:MAXC-1];
    reg [447:0] rrow   [0:MAXC-1];
    reg [8:0]   dn_at  [0:MAXC-1];
    reg         vdv_at [0:MAXC-1];
    reg [1:0]   inp_at [0:MAXC-1];         // {hc, su}
    integer     ehead  [0:MAXC-1];
    integer     enext  [0:MAXE-1];
    reg [6:0]   eport  [0:MAXE-1];         // 0..127
    reg [8:0]   eaddr  [0:MAXE-1];
    reg [3:0]   emask  [0:MAXE-1];
    integer ne, ncmd, last_cycle;
    // job table
    integer j_s [0:MAXJ-1], j_arm [0:MAXJ-1], j_chk [0:MAXJ-1], j_base [0:MAXJ-1], j_nr [0:MAXJ-1], j_cl [0:MAXJ-1];
    integer j_e0 [0:MAXJ-1], j_e1 [0:MAXJ-1];
    integer blk_free [0:1023];             // 16-row block: earliest legal ARM pin
    integer slot_free [0:3], slot_last [0:3];
    integer mode, seed, seed0, njobs, rnd;
    reg [10:0] exp_flt, allow;

    function integer urand(input integer n); begin rnd = $random(seed); urand = (rnd < 0 ? -rnd : rnd) % n; end endfunction
    function [4:0] bank_of(input [13:0] r); bank_of = r[4:0] ^ {r[7:5], 2'b00}; endfunction

    task automatic put_cmd(input integer at, input [23:0] arg, output integer pin);
        integer c; begin
            c = at; while (cmd_at[c][84]) c = c + 1;
            cmd_at[c] = {1'b1, ncmd[0], 10'(urand(1024)), 21'(urand(2097152)), 21'(ncmd), arg, 7'(ncmd % 128)};
            dn_at[c + DLAT + 1] = {1'b1, ncmd[0], 7'(ncmd % 128)};
            ncmd = ncmd + 1; pin = c; if (c + DLAT + 1 > last_cycle) last_cycle = c + DLAT + 1;
        end
    endtask
    task automatic put_commit(input integer from, input integer port, input [8:0] a, input [3:0] m, output integer at);
        integer c; begin
            if (ne >= MAXE - 1) $fatal(1, "MAXE exceeded");
            c = from; while (occ[c][port]) c = c + 1;
            occ[c][port] = 1'b1; eport[ne] = port[6:0]; eaddr[ne] = a; emask[ne] = m;
            enext[ne] = ehead[c]; ehead[c] = ne; ne = ne + 1; at = c;
            if (c > last_cycle) last_cycle = c;
        end
    endtask
    task automatic put_read(input integer at, input [13:0] r);
        integer c, q; begin
            c = at; q = 8 * (r[1:0]) + urand(8);
            while (rocc[c][q]) c = c + 1;
            rocc[c][q] = 1'b1; rrow[c][14*q +: 14] = r;
        end
    endtask

    integer next_b16 = 0;
    integer i, k, c, g, s, jb, pin, at, lastc, b16, nr, cl, rr, ok, m1, nat_out, tries;
    reg [13:0] row; reg [3:0] mm;
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("jobs=%d", njobs)) njobs = 600;
        for (c = 0; c < MAXC; c = c + 1) begin
            cmd_at[c] = 0; occ[c] = 0; rocc[c] = 0; rrow[c] = 0; dn_at[c] = 0; vdv_at[c] = 0; inp_at[c] = 0; ehead[c] = -1;
        end
        for (i = 0; i < 1024; i = i + 1) blk_free[i] = 0;
        for (s = 0; s < 4; s = s + 1) begin slot_free[s] = 0; slot_last[s] = -1; end
        ne = 0; ncmd = 0; last_cycle = 0; exp_flt = 11'd0; allow = 11'd0; nat_out = 0;
        // ---------------- offline schedule
        c = 20;
        for (jb = 0; jb < njobs; jb = jb + 1) begin
            s = jb % 4; cl = urand(2);
            case (urand(8)) 0: nr = 1 + urand(16); 1, 2, 3: nr = 16 * (1 + urand(4)); 4, 5: nr = 1 + urand(96);
                6: nr = 16 * (1 + urand(16)); default: nr = (urand(16) == 0) ? 1024 : 32; endcase
            // range: aligned base, inside 16384
            tries = 0;
            b16 = urand(1024 - (nr + 15) / 16 + 1);
            // compiler-style packing: often the operand starts right after the previous one (adjacent armed ranges)
            if (urand(2) == 0 && next_b16 + (nr + 15) / 16 <= 1024) b16 = next_b16;
            next_b16 = b16 + (nr + 15) / 16;
            // ARM pin: slot free, every covered 16-row block free
            at = (c > slot_free[s]) ? c : slot_free[s];
            for (k = b16; k < b16 + (nr + 15) / 16; k = k + 1) if (blk_free[k] > at) at = blk_free[k];
            put_cmd(at, {3'(s), 1'(cl), 10'(b16), 10'(nr - 1)}, pin);
            j_s[jb] = s; j_arm[jb] = pin; j_base[jb] = 16 * b16; j_nr[jb] = nr; j_cl[jb] = cl; j_e0[jb] = ne;
            // commits: every row, every slice; 1 or 2 commits per (row, slice) partitioning the 4 words
            lastc = pin;
            for (rr = 0; rr < nr; rr = rr + 1) begin
                row = 14'(16 * b16 + rr);
                for (g = 0; g < 4; g = g + 1) begin
                    if (urand(4) == 0) begin
                        mm = 4'(1 + urand(14));
                        put_commit(pin + 1 + urand(3) + rr / 32, 32 * g + bank_of(row), row[13:5], mm, k); if (k > lastc) lastc = k;
                        put_commit(pin + 1 + urand(3) + rr / 32, 32 * g + bank_of(row), row[13:5], ~mm, k); if (k > lastc) lastc = k;
                    end else begin
                        put_commit(pin + 1 + urand(2) + rr / 32, 32 * g + bank_of(row), row[13:5], 4'hF, k); if (k > lastc) lastc = k;
                    end
                end
            end
            j_e1[jb] = ne;
            put_cmd(lastc + urand(3), {3'(s), 1'(cl), 10'h3FF, 10'h3FF}, pin);
            j_chk[jb] = pin;
            // legal reads after the CHECK
            m1 = pin;
            for (k = 0; k < 1 + urand(3); k = k + 1) begin
                at = pin + 1 + urand(4); put_read(at, 14'(16 * b16 + urand(nr))); if (at + 4 > m1) m1 = at + 4;
            end
            for (k = b16; k < b16 + (nr + 15) / 16; k = k + 1) blk_free[k] = m1 + 1;
            slot_free[s] = pin + 1;
            // contract window of t_inp: [CHECK + 7, next ARM of slot + 3)
            if (slot_last[s] >= 0) for (k = j_chk[slot_last[s]] + 7; k < j_arm[jb] + 3; k = k + 1) inp_at[k][j_cl[slot_last[s]]] = 1'b1;
            slot_last[s] = jb;
            // native op now and then
            if (urand(5) == 0) begin
                put_cmd(c + urand(8), {3'(4 + 2*urand(2)), 21'(urand(2097152))}, pin);
                k = pin + 3 + urand(20); while (vdv_at[k]) k = k + 1; vdv_at[k] = 1'b1;
            end
            c = c + 1 + urand(nr / 8 + 2);
            if (last_cycle > MAXC - 2000) begin njobs = jb + 1; end
        end
        for (s = 0; s < 4; s = s + 1) if (slot_last[s] >= 0)
            for (k = j_chk[slot_last[s]] + 7; k < last_cycle + 24; k = k + 1) inp_at[k][j_cl[slot_last[s]]] = 1'b1;
        // ---------------- fault injection (one job in the middle)
        jb = njobs / 2;
        case (mode)
            1: begin emask[j_e0[jb] + 3] = 4'h0; exp_flt[0] = 1'b1; end                       // a commit carries no words
            2: begin k = j_chk[jb] - 1; while (occ[k][eport[j_e0[jb]]]) k = k - 1;           // the same commit twice
                     if (k <= j_arm[jb]) $fatal(1, "no room for the duplicate");
                     occ[k][eport[j_e0[jb]]] = 1'b1; eport[ne] = eport[j_e0[jb]]; eaddr[ne] = eaddr[j_e0[jb]]; emask[ne] = emask[j_e0[jb]];
                     enext[ne] = ehead[k]; ehead[k] = ne; ne = ne + 1; exp_flt[1] = 1'b1; exp_flt[0] = 1'b1; end
            3: begin k = 0; while (k < 8 && rocc[j_chk[jb]][k]) k = k + 1;                 // read at the CHECK pin
                     if (k == 8) $fatal(1, "no read port at the CHECK pin");
                     rocc[j_chk[jb]][k] = 1'b1; rrow[j_chk[jb]][14*k +: 14] = 14'(j_base[jb]); exp_flt[7] = 1'b1; end
            4: begin allow[0] = 1'b1; k = j_arm[jb] + 1; while (cmd_at[k][84]) k = k + 1;                    // re-ARM before the CHECK
                     if (k >= j_chk[jb]) $fatal(1, "no room for the re-ARM");
                     cmd_at[k] = {1'b1, 1'b0, 52'd0, 3'(j_s[jb]), 1'(j_cl[jb]), 10'(j_base[jb] / 16), 10'(j_nr[jb] - 1), 7'd127};
                     dn_at[k + DLAT + 1] = {1'b1, 1'b0, 7'd127}; exp_flt[4] = 1'b1; end
            5: begin cmd_at[j_chk[jb]][27] = ~cmd_at[j_chk[jb]][27]; exp_flt[3] = 1'b1; end   // CHECK client mismatch
            6: begin k = 5; while (cmd_at[k][84]) k = k + 1;                                 // CHECK of an unarmed slot
                     if (k >= j_arm[0]) $fatal(1, "no room for the unarmed CHECK");
                     cmd_at[k] = {1'b1, 1'b0, 52'd0, 3'd0, 1'b0, 10'h3FF, 10'h3FF, 7'd126};
                     dn_at[k + DLAT + 1] = {1'b1, 1'b0, 7'd126}; exp_flt[2] = 1'b1; end
            default: ;
        endcase
        $display("TB_VMSS schedule: mode %0d seed %0d jobs %0d commands %0d commits %0d cycles %0d", mode, seed0, njobs, ncmd, ne, last_cycle);
    end

    // ---------------- drive / check
    integer cyc, errs, ndone, ninp, e, maxc;
    reg [127:0] cv; reg [1151:0] ca; reg [511:0] cm;
    initial begin
        errs = 0; ndone = 0; ninp = 0;
        c_cmd = 0; o_cv = 0; o_ca = 0; o_cm = 0; o_rv = 0; o_rr = 0; v_dv = 0; v_dt = 0; v_flt = 0;
        #0.1;
        repeat (4) @(posedge ck);
        #0.05 rst = 1'b1;
        repeat (4) @(posedge ck);
        for (cyc = 0; cyc < last_cycle + 24; cyc = cyc + 1) begin
            #0.05;
            c_cmd = cmd_at[cyc];
            cv = 0; ca = 0; cm = 0;
            e = ehead[cyc];
            while (e >= 0) begin cv[eport[e]] = 1'b1; ca[9*eport[e] +: 9] = eaddr[e]; cm[4*eport[e] +: 4] = emask[e]; e = enext[e]; end
            o_cv = cv; o_ca = ca; o_cm = cm; o_rv = rocc[cyc]; o_rr = rrow[cyc];
            v_dv = vdv_at[cyc]; v_dt = 8'd0;
            #0.3;                                   // sample this cycle's registered outputs
            if (c_done !== dn_at[cyc]) begin
                errs = errs + 1;
                if (errs < 10) $display("TB_VMSS ERROR cycle %0d c_done %h expected %h", cyc, c_done, dn_at[cyc]);
            end
            if (c_done[8]) ndone = ndone + 1;
            if (mode == 0 && {t_inp_hc, t_inp_su} !== inp_at[cyc]) begin
                errs = errs + 1;
                if (errs < 10) $display("TB_VMSS ERROR cycle %0d t_inp {hc,su} %b expected %b", cyc, {t_inp_hc, t_inp_su}, inp_at[cyc]);
            end
            if (inp_at[cyc] != 0) ninp = ninp + 1;
            if (mode == 0 && c_st !== 2'b10 && cyc > 2) begin
                errs = errs + 1;
                if (errs < 10) $display("TB_VMSS ERROR cycle %0d c_st %b flt %b", cyc, c_st, u.flt);
            end
            @(posedge ck);
        end
        if ((u.flt & ~allow) !== exp_flt) begin errs = errs + 1; $display("TB_VMSS ERROR fault vector %b expected %b", u.flt, exp_flt); end
        if (mode != 0 && c_st[0] !== 1'b1) begin errs = errs + 1; $display("TB_VMSS ERROR fault not on c_st"); end
        $display("TB_VMSS RESULT mode %0d cycles %0d commands %0d dones %0d commits %0d inp_cycles %0d errors %0d",
                 mode, cyc, ncmd, ndone, ne, ninp, errs);
        if (errs == 0) $display("TB_VMSS PASS mode %0d", mode); else $display("TB_VMSS FAIL mode %0d", mode);
        $finish;
    end
endmodule
