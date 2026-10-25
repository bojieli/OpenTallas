`timescale 1ns/1ps
`default_nettype none
// HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_idx_rootctl_static_am quadrant straps (SID / NQ / NL) lockstep bench.
//   B2 0: DUT at default straps (SID 0, NQ 4, NL 4) vs REF = the UNCHANGED as-built r18h5 master (source d34578d6f,
//         module renamed ot_hbm_idx_rootctl_static_am_ref). Proves the defaults bit-exact.
//   B2 1: DUT #(.SID(3), .NQ(2), .NL(1)) (the B2 NW + NE die root) vs REF3 = the as-built text with its literal strap
//         'localparam SID = 2'd0' set to 2'd3 (module ot_hbm_idx_rootctl_static_am_ref3), the as-built 4-list check
//         faces fed so they are the 2-quadrant semantics: tree_ev = {t1, t0, t1, t0}, qfault = {2'b00, q1, q0},
//         selected_v = {4{sv}}.
//   DIE 0: AMMUT 0 / SEL_LAT 4 / VM_RT 0 / CR_RT 0 / RSTL 0 / FAN32 0;  DIE 1: the r18h5 die instance parameters
//         SEL_LAT 40, VM_RT 75, CR_RT 36, RSTL 1, FAN32 1.
// EVERY output is compared EVERY edge after reset release (!==): sel_op/pass/addr, link_*, ingest_v, done, fault, cq,
// cq_seq, topk_busy/done/fault, index_rr, argmax_m, vm_rq, share_fault.
// Stimulus: NEP episodes, each with its own reset: calendar programme rows written while idle + starts (length 1..256,
// only after the previous programme retired),
// random INDEX / ARGMAX bookings and VM responses every edge, random hub acks, TOPK descriptors every ~300 edges whose
// sectors are the strap (60 %), 0 (20 %) or random, selected_v = {NL{ingest_v}} (always consistent), tree_ev all ones,
// sf / lf rare pulses. Episode anomaly (episode % 5): 1 = tree_ev lane NQ-1 dropped for one edge (agree fault);
// 2 = qfault lane NQ-1 pulse; 3 = selected_v corrupted for one edge; 0 / 4 none.
// B2MUT 1..4 (forwarded to the DUT, B2 1 only) must FAIL.
module tb_idx_rootctl_nq;
`ifndef B2
`define B2 0
`endif
`ifndef DIE
`define DIE 0
`endif
`ifndef B2MUT
`define B2MUT 0
`endif
`ifndef NEP
`define NEP 20
`endif
`ifndef EPL
`define EPL 5000
`endif
    localparam integer SL = `DIE ? 40 : 4, VR = `DIE ? 75 : 0, CRT = `DIE ? 36 : 0, RS = `DIE ? 1 : 0, F3 = `DIE ? 1 : 0;
    localparam integer NQ = `B2 ? 2 : 4, NL = `B2 ? 1 : 4;
    localparam [1:0] SID = `B2 ? 2'd3 : 2'd0;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg program_we = 0, start = 0; reg [7:0] program_addr = 0; reg [255:0] program_data = 0; reg [11:0] length = 0;
    reg [NL-1:0] selected_v = 0; reg [NQ-1:0] tree_ev = 0, qfault = 0; reg sf = 0, lf = 0;
    reg topk_go = 0, topk_order = 0, topk_a_mirror = 0, topk_o_mirror = 0, topk_has_r = 0; reg [3:0] topk_k = 0;
    reg [19:0] topk_n = 0, topk_m = 0; reg [17:0] topk_a_base = 0, topk_a_str = 0, topk_o_base = 0, topk_o_str = 0, topk_r_base = 0, topk_r_str = 0;
    reg [273:0] cr = 0; reg [135:0] index_rq = 0, argmax_rq = 0; reg [2055:0] vm_rr = 0;
    // reference check faces
    wire [3:0] r_sv, r_te, r_qf;
    generate if (`B2) begin : g_b2f
        assign r_sv = {4{selected_v[0]}}; assign r_te = {tree_ev, tree_ev}; assign r_qf = {2'b00, qfault};
    end else begin : g_4f
        assign r_sv = selected_v; assign r_te = tree_ev; assign r_qf = qfault;
    end endgenerate
    wire [3:0] so0, so1; wire [1:0] sp0, sp1; wire [7:0] sa0, sa1; wire lfl0, lfl1, le0, le1, lc0, lc1; wire [3:0] lg0, lg1;
    wire iv0, iv1, dn0, dn1, ft0, ft1; wire [337:0] cq0, cq1; wire [1:0] cs0, cs1; wire tb0, tb1, td0, td1, tf0, tf1;
    wire [2055:0] irr0, irr1; wire [263:0] am0, am1; wire [135:0] vq0, vq1; wire shf0, shf1;
`define RPORTS .clk(clk), .rst_n(rst_n), .program_we(program_we), .program_addr(program_addr), .program_data(program_data), \
        .start(start), .length(length), .sel_op(so0), .sel_pass(sp0), .sel_addr(sa0), .link_flush(lfl0), .link_emit(le0), \
        .link_group(lg0), .link_clear(lc0), .selected_v(r_sv), .ingest_v(iv0), .tree_ev(r_te), .qfault(r_qf), .sf(sf), .lf(lf), \
        .done(dn0), .fault(ft0), .topk_go(topk_go), .topk_k(topk_k), .topk_order(topk_order), .topk_n(topk_n), .topk_m(topk_m), \
        .topk_a_mirror(topk_a_mirror), .topk_a_base(topk_a_base), .topk_a_str(topk_a_str), .topk_o_mirror(topk_o_mirror), \
        .topk_o_base(topk_o_base), .topk_o_str(topk_o_str), .topk_has_r(topk_has_r), .topk_r_base(topk_r_base), \
        .topk_r_str(topk_r_str), .cq(cq0), .cq_seq(cs0), .cr(cr), .topk_busy(tb0), .topk_done(td0), .topk_fault(tf0), \
        .index_rq(index_rq), .index_rr(irr0), .argmax_rq(argmax_rq), .argmax_m(am0), .vm_rq(vq0), .vm_rr(vm_rr), .share_fault(shf0)
    generate if (`B2) begin : g_ref3
        ot_hbm_idx_rootctl_static_am_ref3 #(.SEL_LAT(SL), .VM_RT(VR), .CR_RT(CRT), .RSTL(RS), .FAN32(F3)) ref_(`RPORTS);
    end else begin : g_ref
        ot_hbm_idx_rootctl_static_am_ref #(.SEL_LAT(SL), .VM_RT(VR), .CR_RT(CRT), .RSTL(RS), .FAN32(F3)) ref_(`RPORTS);
    end endgenerate
    ot_hbm_idx_rootctl_static_am #(.SEL_LAT(SL), .VM_RT(VR), .CR_RT(CRT), .RSTL(RS), .FAN32(F3), .SID(SID), .NQ(NQ), .NL(NL),
        .B2MUT(`B2MUT)) dut(
        .clk(clk), .rst_n(rst_n), .program_we(program_we), .program_addr(program_addr), .program_data(program_data),
        .start(start), .length(length), .sel_op(so1), .sel_pass(sp1), .sel_addr(sa1), .link_flush(lfl1), .link_emit(le1),
        .link_group(lg1), .link_clear(lc1), .selected_v(selected_v), .ingest_v(iv1), .tree_ev(tree_ev), .qfault(qfault),
        .sf(sf), .lf(lf), .done(dn1), .fault(ft1), .topk_go(topk_go), .topk_k(topk_k), .topk_order(topk_order), .topk_n(topk_n),
        .topk_m(topk_m), .topk_a_mirror(topk_a_mirror), .topk_a_base(topk_a_base), .topk_a_str(topk_a_str),
        .topk_o_mirror(topk_o_mirror), .topk_o_base(topk_o_base), .topk_o_str(topk_o_str), .topk_has_r(topk_has_r),
        .topk_r_base(topk_r_base), .topk_r_str(topk_r_str), .cq(cq1), .cq_seq(cs1), .cr(cr), .topk_busy(tb1),
        .topk_done(td1), .topk_fault(tf1), .index_rq(index_rq), .index_rr(irr1), .argmax_rq(argmax_rq), .argmax_m(am1),
        .vm_rq(vq1), .vm_rr(vm_rr), .share_fault(shf1));
    // ------------------------------------------------------------------ stimulus (negedge)
    integer ep = 0, ecyc = 0, anomaly_at = 0, w, nchk = 0, errs = 0, ngo = 0, ntkf = 0, ntkd = 0, nflt = 0, ncq = 0, nsel6 = 0, nstart = 0, nclean = 0;
    function automatic [17:0] addr_s(input [1:0] s); addr_s = {s, 16'($urandom % 2048)}; endfunction
    function automatic [1:0] pick_sec(input integer r);
        pick_sec = (r < 60) ? SID : (r < 80) ? 2'd0 : 2'($urandom);
    endfunction
    integer cal_free = 0;
    always @(negedge clk) begin
        program_we = 0; start = 0; topk_go = 0; sf = 0; lf = 0;
        ecyc = ecyc + 1;
        if (ecyc == 1) begin rst_n = 0; cal_free = 0; anomaly_at = `EPL / 2 + ($urandom % (`EPL / 4)); end
        if (ecyc == 9) rst_n = 1;
        if (ecyc == `EPL) begin ecyc = 0; ep = ep + 1; end
        // calendar: write rows 0..31 early, then start whenever the programme is idle
        if (rst_n && ecyc > 12 && ecyc < 12 + 32) begin
            program_we = 1; program_addr = 8'(ecyc - 13);
            for (w = 0; w < 8; w = w + 1) program_data[32*w +: 32] = $urandom;
        end
        // start only when the previous programme has retired (a start while active is a legal sticky calendar fault that
        // would mask the episode's anomaly)
        if (rst_n && ecyc > 50 && ecyc > cal_free && $urandom % 64 == 0 && !program_we) begin
            start = 1; length = 12'(1 + $urandom % 256); nstart = nstart + 1; cal_free = ecyc + length + 8;
        end
        // TOPK descriptor
        if (rst_n && ecyc > 50 && $urandom % 300 == 0) begin
            topk_go = 1; ngo = ngo + 1;
            topk_k = 4'(1 + $urandom % 8); topk_order = $urandom; topk_n = 20'(topk_k + $urandom % 24); topk_m = 20'(1 + $urandom % 3);
            topk_a_mirror = ($urandom % 4 == 0); topk_a_base = addr_s(topk_a_mirror ? 2'd0 : pick_sec($urandom % 100));
            topk_a_str = 18'($urandom % 64); topk_o_mirror = ($urandom % 16 == 0); topk_o_base = addr_s(pick_sec($urandom % 100));
            topk_o_str = 18'($urandom % 64); topk_has_r = $urandom; topk_r_base = addr_s(pick_sec($urandom % 100));
            topk_r_str = 18'($urandom % 64);
        end
        index_rq = {$urandom, $urandom, $urandom, $urandom, $urandom};
        argmax_rq = {$urandom, $urandom, $urandom, $urandom, $urandom};
        for (w = 0; w < 65; w = w + 1) vm_rr[32*w +: 32] = (32*w + 32 <= 2056) ? $urandom : vm_rr[32*w +: 32];
        vm_rr[2055:2048] = $urandom;
        for (w = 0; w < 9; w = w + 1) cr[32*w +: 32] = (32*w + 32 <= 274) ? $urandom : cr[32*w +: 32];
        cr[273:256] = $urandom;
        if ($urandom % 997 == 0) sf = 1;
        if ($urandom % 991 == 0) lf = 1;
        tree_ev = {NQ{1'b1}};
        qfault = '0;
        selected_v = {NL{iv0}};
        if (ecyc == anomaly_at && ep % 5 >= 1 && ep % 5 <= 3 && ft0 === 1'b0) nclean = nclean + 1;
        if (ecyc == anomaly_at) case (ep % 5)
            1: tree_ev[NQ-1] = 1'b0;
            2: qfault[NQ-1] = 1'b1;
            3: selected_v[NL-1] = ~iv0;
            default: ;
        endcase
        if (ep == `NEP) begin
            $display("IDX_ROOTCTL_NQ B2=%0d DIE=%0d B2MUT=%0d episodes=%0d checks=%0d errors=%0d topk_go=%0d topk_fault=%0d topk_done=%0d cq_v=%0d fault_edges=%0d sel_op6=%0d starts=%0d anomalies_on_clean_fault=%0d",
                `B2, `DIE, `B2MUT, ep, nchk, errs, ngo, ntkf, ntkd, ncq, nflt, nsel6, nstart, nclean);
            $display("IDX_ROOTCTL_NQ %s checks=%0d errors=%0d", (errs == 0 && nchk > 0) ? "PASS" : "FAIL", nchk, errs);
            $finish;
        end
    end
    // ------------------------------------------------------------------ checks (posedge sampled just before the edge)
    always @(posedge clk) if (rst_n && ecyc > 10) begin
        nchk = nchk + 1;
        if (tf0) ntkf = ntkf + 1; if (td0) ntkd = ntkd + 1; if (cq0[337]) ncq = ncq + 1; if (ft0) nflt = nflt + 1;
        if (so0 == 4'd6) nsel6 = nsel6 + 1;
        if ({so0, sp0, sa0, lfl0, le0, lg0, lc0, iv0, dn0, ft0} !== {so1, sp1, sa1, lfl1, le1, lg1, lc1, iv1, dn1, ft1} ||
            {cq0, cs0, tb0, td0, tf0, shf0} !== {cq1, cs1, tb1, td1, tf1, shf1} ||
            irr0 !== irr1 || am0 !== am1 || vq0 !== vq1) begin
            errs = errs + 1;
            if (errs <= 5) $display("MISMATCH ep=%0d ecyc=%0d ctl %h/%h fault %b/%b topk %b%b%b/%b%b%b cq %0d idx %0d am %0d vq %0d",
                ep, ecyc, {so0, sp0, sa0, lfl0, le0, lg0, lc0, iv0, dn0}, {so1, sp1, sa1, lfl1, le1, lg1, lc1, iv1, dn1},
                ft0, ft1, tb0, td0, tf0, tb1, td1, tf1, cq0 !== cq1, irr0 !== irr1, am0 !== am1, vq0 !== vq1);
        end
    end
endmodule
`default_nettype wire
