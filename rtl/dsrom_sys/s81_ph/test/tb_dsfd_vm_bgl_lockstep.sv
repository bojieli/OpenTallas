// tb_dsfd_vm_bgl_lockstep (el1013-s81-bgq28): the 8-leaf dsfd_vm_bgq28h against the flat dsfd_vm_bgr (bgq28 parameters),
// same stimulus, flop memories on both sides.  f_* and o_v / o_d must be equal cycle for cycle at a fixed offset of
// DL = 10 cycles (hop 16 vs 6); the sticky status (o_f, o_o) is compared after the drain.  RANDOM stimulus over all 28
// ports (reads on ports 0..9 only) and all 32 bank ids; TRACE = 1 replays the PRODUCTION trace instead (+trace=FILE:
// the request bus at the head of slice 0 of dsfd_sp_vm_m, recorded by the master gate's tp / gold cases built with
// +define+OT_SPVM_BGTRACE; lines "cycle v we row mask d", idle cycles omitted).  PASS is refused without coverage.
module tb_dsfd_vm_bgl_lockstep #(parameter integer SEED = 1, parameter integer NCYC = 200000, parameter integer GRP = 1,
                                 parameter integer RATE = 8, parameter integer TRACE = 0, parameter integer MC_HOP = 0);
    localparam integer NP = 28, NPR = 10, RA = 14;
`ifdef OT_VMBGL_HOP1
    localparam integer DL = (MC_HOP == 2) ? 10 : 2; // 8 one-cycle leaves versus the six-cycle flat reference.
`else
    localparam integer DL = 10;
`endif
    reg clk = 0, rs = 0; always #5 clk = ~clk;
    reg [NP-1:0] i_v = 0, i_we = 0; reg [NP*RA-1:0] i_row = 0; reg [NP*4-1:0] i_m = 0; reg [NP*128-1:0] i_d = 0;
    wire [NP-1:0] av, awe, bv, bwe; wire [NP*RA-1:0] arow, brow; wire [NP*4-1:0] am, bm; wire [NP*128-1:0] ad, bd;
    wire [NPR-1:0] aov, bov; wire [NPR*128-1:0] aod, bod; wire [3:0] aof, bof; wire [2:0] aoo, boo;
    wire [1:0] grp = GRP;
    dsfd_vm_bgr #(.NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(4), .RQ(8), .MACRO(0), .DW(128), .NSTG(4), .EP(2)) u_flat (
        .ck(clk), .rs(rs), .grp(grp), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_m), .i_d(i_d),
        .f_v(av), .f_we(awe), .f_row(arow), .f_mask(am), .f_d(ad), .r_v(10'd0), .r_d(1280'd0), .r_f(4'd0), .r_o(3'd0),
        .o_v(aov), .o_d(aod), .o_f(aof), .o_o(aoo));
`ifdef OT_VMBGL_MC_PARENT
    dsfd_vm_bgq28h_mc24 #(.FORWARD_HOP(MC_HOP)) u_leaf (
        .ck_bank_l0(clk), .ck_bank_l1(clk), .ck_bank_l2(clk), .ck_bank_l3(clk), .ck_bank_l4(clk), .ck_bank_l5(clk), .ck_bank_l6(clk), .ck_bank_l7(clk), .ck_req_l0(clk), .ck_req_l1(clk), .ck_req_l2(clk), .ck_req_l3(clk), .ck_req_l4(clk), .ck_req_l5(clk), .ck_req_l6(clk), .ck_req_l7(clk), .ck_ret_l0(clk), .ck_ret_l1(clk), .ck_ret_l2(clk), .ck_ret_l3(clk), .ck_ret_l4(clk), .ck_ret_l5(clk), .ck_ret_l6(clk), .ck_ret_l7(clk),
`elsif OT_VMBGL_ENTRIES
    dsfd_vm_bgq28h_pc u_leaf (
        .ck_l0(clk), .ck_l1(clk), .ck_l2(clk), .ck_l3(clk), .ck_l4(clk), .ck_l5(clk), .ck_l6(clk), .ck_l7(clk),
`else
    dsfd_vm_bgq28h u_leaf (
        .ck(clk),
`endif
        .rs(rs), .grp(grp), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_m), .i_d(i_d),
        .f_v(bv), .f_we(bwe), .f_row(brow), .f_mask(bm), .f_d(bd), .r_v(10'd0), .r_d(1280'd0), .r_f(4'd0), .r_o(3'd0),
        .o_v(bov), .o_d(bod), .o_f(bof), .o_o(boo));
    // flat outputs delayed DL cycles
    localparam integer FW = NP*(2+RA+4+128), RWD = NPR*129;
    reg [FW-1:0] fq [0:DL-1]; reg [RWD-1:0] rq [0:DL-1];
    wire [FW-1:0] fa = {av, awe & av, arow, am, ad}, fb = {bv, bwe & bv, brow, bm, bd};
    wire [RWD-1:0] ra = {aov, aod}, rb = {bov, bod};
    integer k, p, cyc = 0, nerr = 0, nops = 0, nrd = 0, nret = 0, ndup = 0; integer cb [0:7]; integer cp [0:NP-1];
    reg [4:0] bk; reg [4:0] seen [0:NPR-1]; reg run = 0;
    always @(posedge clk) begin
        fq[0] <= fa; rq[0] <= ra;
        for (k = 1; k < DL; k = k + 1) begin fq[k] <= fq[k-1]; rq[k] <= rq[k-1]; end
        cyc <= cyc + 1;
        if (run && cyc > 40) begin
            // forward bus: valid always; payload only where valid (non-reset payload flops differ at start-up)
            if (fq[DL-1][FW-1 -: NP] !== fb[FW-1 -: NP]) begin nerr = nerr + 1; if (nerr < 5) $display("MISMATCH f_v cyc %0d", cyc); end
            for (p = 0; p < NP; p = p + 1) if (bv[p]) begin
                if (fq[DL-1][FW-1-NP-p] !== fb[FW-1-NP-p] || fq[DL-1][NP*132 + p*RA +: RA] !== brow[p*RA +: RA]
                    || fq[DL-1][NP*128 + p*4 +: 4] !== bm[p*4 +: 4] || fq[DL-1][p*128 +: 128] !== bd[p*128 +: 128]) begin
                    nerr = nerr + 1; if (nerr < 5) $display("MISMATCH f payload port %0d cyc %0d", p, cyc);
                end
            end
            if (rq[DL-1] !== rb) begin nerr = nerr + 1; if (nerr < 5) $display("MISMATCH o_v/o_d cyc %0d", cyc); end
            nret = nret + $countones(bov);
        end
    end
    integer s, tfd, tc, tc0, tcur, tlines, npu, own, cov_bad;
    string tfile;
    reg [NP-1:0] tv, twe; reg [NP*RA-1:0] trow; reg [NP*4-1:0] tm; reg [NP*128-1:0] td;
    // coverage counters of the op just driven on port pp (ports are visited in ascending order within a cycle)
    task automatic count_op(input integer pp);
        reg [4:0] b; integer kk;
        begin
            b = i_row[pp*RA +: 5];
            if (i_v[pp]) begin
                nops = nops + 1; cp[pp] = cp[pp] + 1;
                if (b[4:3] == GRP) begin
                    cb[b[2:0]] = cb[b[2:0]] + 1;
                    if (!i_we[pp]) begin
                        nrd = nrd + 1;
                        for (kk = 0; kk < pp && kk < NPR; kk = kk + 1) if (i_v[kk] && !i_we[kk] && seen[kk] == b) ndup = ndup + 1;
                    end
                end
            end
            if (pp < NPR) seen[pp] = b;
        end
    endtask
    initial begin
        s = SEED; for (k = 0; k < 8; k = k + 1) cb[k] = 0; for (k = 0; k < NP; k = k + 1) cp[k] = 0;
        repeat (20) @(posedge clk); rs = 1; repeat (20) @(posedge clk); run = 1;
        if (TRACE != 0) begin
            if (!$value$plusargs("trace=%s", tfile)) begin $display("NO_TRACE"); $display("FAIL"); $finish; end
            tfd = $fopen(tfile, "r");
            if (tfd == 0) begin $display("NO_TRACE %0s", tfile); $display("FAIL"); $finish; end
            tc0 = -1; tcur = 0; tlines = 0;
            while ($fscanf(tfd, "%d %h %h %h %h %h\n", tc, tv, twe, trow, tm, td) == 6) begin
                if (tc0 < 0) tc0 = tc;
                while (tcur < tc - tc0) begin @(negedge clk); i_v = 0; tcur = tcur + 1; end
                @(negedge clk); tcur = tcur + 1; tlines = tlines + 1;
                i_v = tv; i_we = twe; i_row = trow; i_m = tm; i_d = td;
                for (p = 0; p < NP; p = p + 1) count_op(p);
            end
            $display("TRACE lines %0d span %0d cycles", tlines, tcur);
        end else
        repeat (NCYC) begin
            @(negedge clk);
            for (p = 0; p < NP; p = p + 1) begin
                i_v[p] = ($urandom(s) % RATE) == 0; s = s + 1;
                i_we[p] = (p >= NPR) ? 1'b1 : $urandom(s + 7) % 2;
                bk = $urandom(s + 11) % 32;
                i_row[p*RA +: RA] = {4'd0, 5'($urandom(s + 13) % 32), bk};
                i_m[p*4 +: 4] = $urandom(s + 17) % 16;
                i_d[p*128 +: 128] = {$urandom(s + 19), $urandom(s + 23), $urandom(s + 29), $urandom(s + 31)};
                count_op(p);
            end
        end
        @(negedge clk); i_v = 0; repeat (200) @(posedge clk);
        if (aof !== bof || aoo !== boo) begin nerr = nerr + 1; $display("MISMATCH status flat %h/%0d leaf %h/%0d", aof, aoo, bof, boo); end
        $display("RESULT cycles %0d ops %0d own_reads %0d returned %0d same_cycle_same_bank_reads %0d status %h max_occ %0d errors %0d",
                 NCYC, nops, nrd, nret, ndup, bof, boo, nerr);
        begin : cov
            integer bad; bad = 0;
            npu = 0; for (k = 0; k < NP; k = k + 1) if (cp[k] >= 100) npu = npu + 1;
            for (k = 0; k < 8; k = k + 1) if (cb[k] < 100) bad = bad + 1;
            if (TRACE != 0) begin
                // production shape: ports, banks and collisions are whatever the master issues (census printed); floors
                // on ops, own-group ops and returned slots only.  TRACE 1 = the master's gold run, 2 = its short tp run
                own = 0; for (k = 0; k < 8; k = k + 1) own = own + cb[k];
                $display("TRACE_COVERAGE ports_used %0d of %0d ops %0d own_group_ops %0d own_reads %0d returned %0d", npu, NP, nops, own, nrd, nret);
                bad = 0;
                if (TRACE == 1 && (nops < 5000 || own < 500 || nret < 1000)) bad = 1;
                if (TRACE != 1 && (nops < 500 || own < 50 || nret < 100)) bad = 1;
            end else begin
                if (npu != NP) bad = bad + 1;
                if (nrd < 1000 || nret < 1000 || ndup < 20 || boo < 2) bad = bad + 1;
            end
            cov_bad = bad;
            if (bad != 0) $display("COVERAGE_REFUSED %0d items", bad);
        end
        // one verdict line only ($finish does not end the block under Verilator: the first version printed FAIL then PASS)
        if (nerr == 0 && cov_bad == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
