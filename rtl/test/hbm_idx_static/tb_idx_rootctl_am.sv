`timescale 1ns/1ps
`default_nettype none
// Bench 1 (lane HBM-IDXAM 10-18): ot_hbm_idx_rootctl_static_am (one clk, share = ot_hbm_idx_vm_share_static_am) vs the
// current ot_hbm_idx_rootctl_static (all eight clock pins on the same clk, share = ot_hbm_idx_vm_share_static) under the
// SAME random stimulus: programme writes + starts (incl. illegal starts/writes), selected_v / tree_ev / quadrant faults,
// TOPK records with random acks, random per-bank INDEX / ARGMAX bookings (rare double bookings in the second half -> sticky share fault) and random
// VM responses (valid + data every edge). Checked EVERY edge after reset release:
//   * every output except the ARGMAX face is identical (cq/cq_seq/topk_*, index_rr, vm_rq, sel/link/done/fault/ingest_v,
//     share_fault);
//   * argmax_m(edge s) == {valid8, OR of the 256-bit data of the lanes whose valid is set} of the reference argmax_rr
//     sampled at edge s-4 (the 4-edge equal-latency merge chain), i.e. with the one lane the static ARGMAX schedule books
//     per edge, argmax_m data == the old 8:1 select and the lane valid bits are the old valid bits in their positions.
// AMMUT forwarded to the DUT (1 pair-3 chain hop short, 2 lane valids mirrored, 3 data not owner-masked, 4 element order).
// r3 (lane HBM-IDXAM2 10-18, pin-registered boundary): the reference sees index_rq / argmax_rq ONE edge late (the DUT's
// request pin registers) and the DUT's registered outputs are compared one edge late: index_rr(t) == ref(t-1) (vm_rr
// pin register + own[7]), share_fault / fault / TOPK outputs (t) == ref(t-1); vm_rq, sel/link/done same edge; argmax_m
// == merge(ref argmax_rr) 3 edges later (vm_rr pin register + 2-stage tree; with the 1-edge request delay = the old 4).
// selected_v follows the selector's fixed schedule ({4{sel_op of 4 edges ago == 6}}); ingest_v must equal the
// reference's &selected_v every edge; in the last quarter selected_v is corrupted once and the DUT fault must rise
// 2 edges later and stay. TOPK is idle here (go = 0): its pin registers / RT_EXTRA are covered by tb_idx_rootctl_am_topk.
// AMMUT 6 (ingest_v one edge early) and 7 (owner tap own[6]) must FAIL here.
// VMX (VEH-TOPKFIX2 10-19): 1 = pin-registered d4g VM banks: REF rootctl #(.PIN_IN(1)) vs DUT rootctl_am #(.VM_RT(1),.CR_RT(1))
// (= die master ot_hbm_idx_rootctl_static_am_pin); same relations (both owner taps one edge later).
module tb_idx_rootctl_am;
`ifndef VMX
`define VMX 0
`endif
`ifndef NCYC
`define NCYC 40000
`endif
`ifndef AMMUT
`define AMMUT 0
`endif
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg program_we = 0, start = 0; reg [7:0] program_addr = 0; reg [255:0] program_data = 0; reg [11:0] length = 0;
    reg [3:0] selected_v = 0, tree_ev = 0, qfault = 0; reg sf = 0, lf = 0;
    reg topk_go = 0, topk_order = 0, topk_a_mirror = 0, topk_o_mirror = 0, topk_has_r = 0; reg [3:0] topk_k = 0;
    reg [19:0] topk_n = 0, topk_m = 0; reg [17:0] topk_a_base = 0, topk_a_str = 0, topk_o_base = 0, topk_o_str = 0, topk_r_base = 0, topk_r_str = 0;
    reg [273:0] cr = 0; reg [135:0] index_rq = 0, argmax_rq = 0; reg [2055:0] vm_rr = 0;
    reg [135:0] index_rq_d = 0, argmax_rq_d = 0;     // the DUT's request pin registers, for the reference
    always @(posedge clk) begin index_rq_d <= index_rq; argmax_rq_d <= argmax_rq; end
    // reference
    wire [3:0] so0, so1; wire [1:0] sp0, sp1; wire [7:0] sa0, sa1; wire lfl0, lfl1, le0, le1, lc0, lc1; wire [3:0] lg0, lg1;
    wire iv0, iv1, dn0, dn1, ft0, ft1; wire [337:0] cq0, cq1; wire [1:0] cs0, cs1; wire tb0, tb1, td0, td1, tf0, tf1;
    wire [2055:0] irr0, irr1, arr0; wire [263:0] am1; wire [135:0] vq0, vq1; wire shf0, shf1;
    ot_hbm_idx_rootctl_static #(.PIN_IN(`VMX)) ref_(.clk_program(clk), .clk_program_mem(clk), .clk_sel(clk), .clk_topk(clk), .clk_pair({4{clk}}),
        .rst_n(rst_n), .program_we(program_we), .program_addr(program_addr), .program_data(program_data), .start(start),
        .length(length), .sel_op(so0), .sel_pass(sp0), .sel_addr(sa0), .link_flush(lfl0), .link_emit(le0), .link_group(lg0),
        .link_clear(lc0), .selected_v(selected_v), .ingest_v(iv0), .tree_ev(tree_ev), .qfault(qfault), .sf(sf), .lf(lf),
        .done(dn0), .fault(ft0), .topk_go(topk_go), .topk_k(topk_k), .topk_order(topk_order), .topk_n(topk_n), .topk_m(topk_m),
        .topk_a_mirror(topk_a_mirror), .topk_a_base(topk_a_base), .topk_a_str(topk_a_str), .topk_o_mirror(topk_o_mirror),
        .topk_o_base(topk_o_base), .topk_o_str(topk_o_str), .topk_has_r(topk_has_r), .topk_r_base(topk_r_base),
        .topk_r_str(topk_r_str), .cq(cq0), .cq_seq(cs0), .cr(cr), .topk_busy(tb0), .topk_done(td0), .topk_fault(tf0),
        .index_rq(index_rq_d), .index_rr(irr0), .argmax_rq(argmax_rq_d), .argmax_rr(arr0), .vm_rq(vq0), .vm_rr(vm_rr), .share_fault(shf0));
    ot_hbm_idx_rootctl_static_am #(.AMMUT(`AMMUT), .VM_RT(`VMX), .CR_RT(`VMX)) dut(.clk(clk),
        .rst_n(rst_n), .program_we(program_we), .program_addr(program_addr), .program_data(program_data), .start(start),
        .length(length), .sel_op(so1), .sel_pass(sp1), .sel_addr(sa1), .link_flush(lfl1), .link_emit(le1), .link_group(lg1),
        .link_clear(lc1), .selected_v(selected_v), .ingest_v(iv1), .tree_ev(tree_ev), .qfault(qfault), .sf(sf), .lf(lf),
        .done(dn1), .fault(ft1), .topk_go(topk_go), .topk_k(topk_k), .topk_order(topk_order), .topk_n(topk_n), .topk_m(topk_m),
        .topk_a_mirror(topk_a_mirror), .topk_a_base(topk_a_base), .topk_a_str(topk_a_str), .topk_o_mirror(topk_o_mirror),
        .topk_o_base(topk_o_base), .topk_o_str(topk_o_str), .topk_has_r(topk_has_r), .topk_r_base(topk_r_base),
        .topk_r_str(topk_r_str), .cq(cq1), .cq_seq(cs1), .cr(cr), .topk_busy(tb1), .topk_done(td1), .topk_fault(tf1),
        .index_rq(index_rq), .index_rr(irr1), .argmax_rq(argmax_rq), .argmax_m(am1), .vm_rq(vq1), .vm_rr(vm_rr), .share_fault(shf1));
    function automatic [263:0] merge(input [2055:0] rr);
        integer l; begin
            merge = 264'd0;
            for (l = 0; l < 8; l = l + 1) begin merge[256+l] = rr[257*l+256]; if (rr[257*l+256]) merge[255:0] = merge[255:0] | rr[257*l +: 256]; end
        end endfunction
    // stimulus (driven on negedge)
    integer corrupt_at = 0;
    reg [3:0] sh [0:3];   // sel_op history (sh[k] = the sel_op registered k+1 edges before this posedge)
    initial for (integer i = 0; i < 4; i = i + 1) sh[i] = 0;
    always @(posedge clk) begin sh[3] = sh[2]; sh[2] = sh[1]; sh[1] = sh[0]; sh[0] = so0; end
    integer cyc = 0, b, w, act_am = 0, act_ix = 0, act_tk = 0, multi = 0, errs = 0, nchk = 0, nshf = 0, ncq = 0, nsel = 0;
    reg [2:0] pick; reg [15:0] sec;
    always @(negedge clk) begin
        cyc <= cyc + 1;
        program_we = 0; start = 0; topk_go = 0;
        if (rst_n) begin
            if ($urandom % 64 == 0) begin program_we = 1; program_addr = $urandom; for (w = 0; w < 8; w = w + 1) program_data[32*w +: 32] = $urandom; end
            if ($urandom % 200 == 0) begin start = 1; length = ($urandom % 16 == 0) ? 12'($urandom) : 12'(1 + $urandom % 300); end
            selected_v = {4{sh[3] == 4'd6}};
            if (!corrupt_at && cyc > 3 * `NCYC / 4 && sh[3] == 4'd6 && $urandom % 8 == 0) begin
                selected_v[$urandom % 4] = 1'b0; corrupt_at = cyc; end
            tree_ev = ($urandom % 512 == 0) ? 4'($urandom) : {4{$urandom % 2 == 0}};
            qfault = ($urandom % 2000 == 0) ? 4'($urandom) : 4'd0; sf = $urandom % 3000 == 0; lf = $urandom % 3000 == 0;
            if (0) begin
                topk_go = 1; topk_k = $urandom; topk_order = $urandom; topk_n = 1 + $urandom % 64; topk_m = 1 + $urandom % 8;
                topk_a_mirror = $urandom; topk_a_base = $urandom; topk_a_str = $urandom % 16; topk_o_mirror = $urandom;
                topk_o_base = $urandom; topk_o_str = $urandom % 16; topk_has_r = $urandom; topk_r_base = $urandom; topk_r_str = $urandom % 16;
            end
            cr = 0; if ($urandom % 3 == 0) begin cr[273] = $urandom; cr[272:257] = $urandom; cr[256] = $urandom; end
            index_rq = 0; argmax_rq = 0; sec = $urandom;
            for (b = 0; b < 8; b = b + 1) begin
                pick = $urandom % 8;
                if (pick == 1 || pick == 2) index_rq[17*b +: 17] = {1'b1, 16'($urandom)};
                if (pick == 3 || pick == 4) argmax_rq[17*b +: 17] = {1'b1, sec};
                if (pick == 5 && cyc > `NCYC / 2 && $urandom % 4000 == 0) begin index_rq[17*b +: 17] = {1'b1, 16'($urandom)}; argmax_rq[17*b +: 17] = {1'b1, sec}; end
            end
            for (b = 0; b < 8; b = b + 1) begin
                vm_rr[257*b+256] = $urandom % 2; for (w = 0; w < 8; w = w + 1) vm_rr[257*b + 32*w +: 32] = $urandom;
            end
        end
    end
    // checks (sampled on posedge, before the DUT's nonblocking updates)
    reg [263:0] hist [0:4]; integer h, nv, ning = 0, nflt = 0;
    reg [2055:0] irr0_d; reg shf0_d, ft0_d; reg [337:0] cq0_d; reg [1:0] cs0_d; reg tb0_d, td0_d, tf0_d;
    always @(posedge clk) begin
        for (h = 4; h > 0; h = h - 1) hist[h] = hist[h-1];
        hist[0] = merge(arr0);
        if (rst_n && cyc > 40) begin
            nchk = nchk + 1;
            if ({so0, sp0, sa0, lfl0, le0, lg0, lc0, dn0} !== {so1, sp1, sa1, lfl1, le1, lg1, lc1, dn1}) begin
                errs = errs + 1; if (errs < 6) $display("CTL differs @%0d", cyc); end
            if (iv0 !== iv1 && !(corrupt_at && cyc == corrupt_at + 1)) begin errs = errs + 1; if (errs < 6) $display("INGEST_V differs @%0d ref %b dut %b", cyc, iv0, iv1); end
            if (iv0) ning = ning + 1;
            if (!corrupt_at || cyc <= corrupt_at + 1) begin
                if (ft0_d !== ft1) begin errs = errs + 1; if (errs < 6) $display("FAULT differs @%0d", cyc); end
            end else if (cyc >= corrupt_at + 3) begin
                if (ft1 !== 1'b1) begin errs = errs + 1; if (errs < 6) $display("FAULT missing after selected_v corruption @%0d", cyc); end
                else nflt = nflt + 1;
            end
            if ({cq0_d, cs0_d, tb0_d, td0_d, tf0_d} !== {cq1, cs1, tb1, td1, tf1}) begin errs = errs + 1; if (errs < 6) $display("TOPK differs @%0d", cyc); end
            if ({irr0_d, vq0, shf0_d} !== {irr1, vq1, shf1}) begin errs = errs + 1; if (errs < 6) $display("INDEX/VM differs @%0d", cyc); end
            if (am1 !== hist[3]) begin errs = errs + 1; if (errs < 6) $display("ARGMAX_M differs @%0d got %h exp %h", cyc, am1[263:256], hist[4][263:256]); end
            nv = 0; for (b = 0; b < 8; b = b + 1) nv = nv + arr0[257*b+256];
            if (nv > 0) act_am = act_am + 1; if (nv > 1) multi = multi + 1;
            for (b = 0; b < 8; b = b + 1) if (irr0[257*b+256]) begin act_ix = act_ix + 1; b = 8; end
            if (shf0) nshf = nshf + 1; if (cq0[337]) ncq = ncq + 1; if (so0 != 0) nsel = nsel + 1;
        end
        irr0_d = irr0; shf0_d = shf0; ft0_d = ft0; cq0_d = cq0; cs0_d = cs0; tb0_d = tb0; td0_d = td0; tf0_d = tf0;
    end
    initial begin
        repeat (6) @(negedge clk); rst_n = 1;
        repeat (`NCYC) @(negedge clk);
        $display("cycles %0d checked %0d argmax_resp %0d (multi-lane %0d) index_resp %0d topk_writes %0d sel_ops %0d share_fault %0d ingest %0d corrupt@%0d fault_held %0d errors %0d",
                 cyc, nchk, act_am, multi, act_ix, ncq, nsel, nshf, ning, corrupt_at, nflt, errs);
        if (errs == 0 && act_am > 1000 && act_ix > 1000 && nsel > 0 && ning > 0 && corrupt_at > 0 && nflt > 0) $display("IDX_ROOTCTL_AM PASS"); else $display("IDX_ROOTCTL_AM FAIL");
        $finish;
    end
endmodule
`default_nettype wire
