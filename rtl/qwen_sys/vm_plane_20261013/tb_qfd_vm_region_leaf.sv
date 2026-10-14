`timescale 1ns/1ps
// Region leaf miter (claude/qwen-tp8-vm-rtl, RTL-B 2026-10-13): ot_qfd_vm_region_leaf (leaf instances and wires only:
// bctl_t, sctl_t, rr4_t, rr2_t, delay1_t / delay2_t and the closed bank_t / su_t / xfifo8_t / su1024_t) against the FLAT REFERENCE
// ot_qfd_vm_region_quarter, same xorshift64 stimulus on every input, xo / ro / so / ovf compared on EVERY clock
// from the first one (reset included).
//   main run      random reads / writes / masks / data on all 8 banks and both SU row banks, random row reads and SU
//                 answers, me stalls 1 in 4 (MEREG = 1: me_in is me one edge early), x beats on a LEGAL push / pop
//                 schedule (the FIFO runs up to NPP - 3 beats deep; the pop pin carries random garbage on non-engine
//                 edges, which both sides must ignore); ovf must stay 0.
//   overflow run  OVFMODE 0: pushes with no pop until ovf; OVFMODE 1: pops on the drained FIFO until ovf.  ovf must
//                 rise, on the same clock in both.
// Non-vacuity refusal: a run with too few pushes / pops / row reads / SU answers / stalls / output changes / nonzero
// compared words, or whose ovf never rose in the overflow run, prints FAIL.
// LEAF_MUT 1..12 (see ot_qfd_vm_region_leaf) must FAIL.
// DEPTH / LAW / DEPTHS / LAWS (2026-10-13 VERIF): the memory depths of the region.  Defaults 8 / 3 / 8 / 3 = the bench
// shape (same stimulus stream as before); 174 / 8 / 695 / 10 = the ROUTED parameters of the leaves (bctl_t LAW 8, sctl_t
// LAWS 10, bank_t DEPTH 174 LAW 8, su_t DEPTHS 695 LAWS 10): every line address is then drawn per bank below the depth.
// The overflow run must see ovf rise, not start with it: at most 158 of its 160 clocks (a FIFO left one beat deep by
// the main run underflows after 4 pops: 156 clocks, seen at the routed depths with SEED 2; the bound was 150).
// ROW_MUT / SU_MUT: the rr2_t (half select) / su1024_t leaf mutants of ot_qfd_vm_region_leaf (must FAIL).
module tb_qfd_vm_region_leaf;
    parameter integer CYCLES = 6000, SEED = 1, LEAF_MUT = 0, OVFMODE = 0, NPP = 12;
    parameter integer DEPTH = 8, LAW = 3, DEPTHS = 8, LAWS = 3, ROW_MUT = 0, SU_MUT = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0, me_in = 0;
    reg [7:0] re = 0, we = 0;
    reg [8*LAW-1:0] ra = 0, wl = 0;
    reg [127:0] wm = 0; reg [4095:0] wd = 0;
    reg xv = 0, rq = 0, pop = 0; reg [2:0] rqb = 0;
    reg [5:0] sre = 0; reg [6*LAWS-1:0] sra = 0; reg [2:0] sv = 0;
    reg [1:0] swe = 0; reg [2*LAWS-1:0] swl = 0; reg [31:0] swm = 0; reg [1023:0] swd = 0;
    wire [4095:0] xo, r_xo; wire [511:0] ro, r_ro; wire [3071:0] so, r_so; wire ovf, r_ovf;
    ot_qfd_vm_region_leaf #(.DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(0), .NPP(NPP), .MEREG(1),
        .LEAF_MUT(LEAF_MUT), .ROW_MUT(ROW_MUT), .SU_MUT(SU_MUT)) candidate (.*);
    ot_qfd_vm_region_quarter #(.DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(0), .NPP(NPP), .MEREG(1)) reference (
        .clk(clk), .rst_n(rst_n), .me_in(me_in), .re(re), .ra(ra), .we(we), .wl(wl), .wm(wm), .wd(wd),
        .xv(xv), .rq(rq), .rqb(rqb), .sre(sre), .sra(sra), .sv(sv), .swe(swe), .swl(swl), .swm(swm), .swd(swd),
        .pop(pop), .xo(r_xo), .ro(r_ro), .so(r_so), .ovf(r_ovf));
    // xorshift64 ($urandom(seed) re-seeds on every call under Verilator: never use it)
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc, w, errors = 0, checks = 0;
    integer pushes = 0, pops = 0, rowreads = 0, suans = 0, stalls = 0, moves = 0, garbage = 0, deep = 0;
    integer xo_chg = 0, ro_chg = 0, so_chg = 0, nonzero = 0, ovf_cmp = 0, sched_err = 0, e_xo = 0, e_ro = 0, e_so = 0, e_ovf = 0;
    integer ptime [0:65535];
    reg me_prev = 0;
    reg [4095:0] l_xo = 0; reg [511:0] l_ro = 0; reg [3071:0] l_so = 0;
    task automatic drive_common;
        begin
            me_prev = me_in;
            me_in = ((rnd(0) % 4) != 0);
            if (!me_in) stalls = stalls + 1; else moves = moves + 1;
            re = rnd(0); we = rnd(0) & rnd(0);
            ra = rnd(0); wl = rnd(0);
            for (w = 0; w < 4; w = w + 1) wm[w*32 +: 32] = rnd(0) | rnd(0);
            for (w = 0; w < 128; w = w + 1) wd[w*32 +: 32] = rnd(0);
            rq = ((rnd(0) % 3) == 0); rqb = rnd(0);
            sre = rnd(0); sra = rnd(0); swe = rnd(0); swl = rnd(0); swm = rnd(0) | rnd(0);
            if (DEPTH != 8 || DEPTHS != 8) begin      // routed depths: one in-range line per bank port
                for (w = 0; w < 8; w = w + 1) begin ra[w*LAW +: LAW] = rnd(0) % DEPTH; wl[w*LAW +: LAW] = rnd(0) % DEPTH; end
                for (w = 0; w < 6; w = w + 1) sra[w*LAWS +: LAWS] = rnd(0) % DEPTHS;
                for (w = 0; w < 2; w = w + 1) swl[w*LAWS +: LAWS] = rnd(0) % DEPTHS;
            end
            sv = ((rnd(0) % 3) == 0) ? rnd(0) : 3'd0;
            for (w = 0; w < 32; w = w + 1) swd[w*32 +: 32] = rnd(0);
            if (rq) rowreads = rowreads + 1;
            if (sv != 0) suans = suans + 1;
        end
    endtask
    task automatic check;
        begin
            @(posedge clk); #1;
            checks = checks + 1;
            if (xo !== r_xo) e_xo = e_xo + 1;
            if (ro !== r_ro) e_ro = e_ro + 1;
            if (so !== r_so) e_so = e_so + 1;
            if (ovf !== r_ovf) e_ovf = e_ovf + 1;
            if (xo !== r_xo || ro !== r_ro || so !== r_so || ovf !== r_ovf) begin
                errors = errors + 1;
                if (errors < 4) $display("region_leaf mismatch cyc %0d xo %0d ro %0d so %0d ovf %0d", cyc,
                    xo !== r_xo, ro !== r_ro, so !== r_so, ovf !== r_ovf);
            end
            if (r_xo !== l_xo) xo_chg = xo_chg + 1;
            if (r_ro !== l_ro) ro_chg = ro_chg + 1;
            if (r_so !== l_so) so_chg = so_chg + 1;
            for (w = 0; w < 128; w = w + 1) if (r_xo[w*32 +: 32] != 0) nonzero = nonzero + 1;
            for (w = 0; w < 16; w = w + 1) if (r_ro[w*32 +: 32] != 0) nonzero = nonzero + 1;
            for (w = 0; w < 96; w = w + 1) if (r_so[w*32 +: 32] != 0) nonzero = nonzero + 1;
            l_xo = r_xo; l_ro = r_ro; l_so = r_so;
        end
    endtask
    initial begin
        rng = 64'h9E3779B97F4A7C15 ^ {32'd0, SEED[31:0]} ^ ({32'd0, SEED[31:0]} << 32);
        // reset: inputs already random, outputs compared
        for (cyc = -6; cyc < 0; cyc = cyc + 1) begin
            @(negedge clk); drive_common; rq = 0; sv = 0; rowreads = 0; suans = 0; if (cyc == -1) rst_n = 1; check;
        end
        stalls = 0; moves = 0;
        // ---- main run: legal push / pop schedule ----
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            drive_common;
            // push: at most NPP - 3 beats issued and not yet popped (cnt <= issued-unpopped + 2 pops in flight < NPP)
            xv = 0;
            if ((pushes - pops) <= NPP - 4 && (rnd(0) % 3) == 0) begin xv = 1; ptime[pushes & 65535] = cyc; pushes = pushes + 1; end
            if ((pushes - pops) >= NPP - 3) deep = deep + 1;
            // pop: the pin is sampled on engine edges only (me_t = me_in one edge ago); a pop is legal once its
            // beat's push has reached cnt (push + 7 edges, pop + 2 engine edges: 8 clocks is safe)
            if (me_prev) begin
                pop = 0;
                if (pops < pushes && ptime[pops & 65535] + 8 <= cyc && (rnd(0) % 2) == 0) begin pop = 1; pops = pops + 1; end
            end else begin
                pop = rnd(0); if (pop) garbage = garbage + 1;
            end
            check;
            if (r_ovf) sched_err = sched_err + 1;
        end
        // ---- overflow run ----
        for (cyc = CYCLES; cyc < CYCLES + 160; cyc = cyc + 1) begin
            @(negedge clk);
            drive_common;
            if (OVFMODE == 0) begin xv = 1; pop = 0; end else begin xv = 0; pop = 1; end
            check;
            if (r_ovf) ovf_cmp = ovf_cmp + 1;
        end
        if (sched_err != 0) begin $display("FAIL qfd_vm_region_leaf BENCH schedule raised ovf in the main run (%0d)", sched_err); $fatal(1, "FAIL"); end
        if (pushes < CYCLES / 16 || pops < CYCLES / 16 || rowreads < CYCLES / 8 || suans < CYCLES / 8 || stalls < CYCLES / 8
            || moves < CYCLES / 2 || garbage < CYCLES / 32 || deep < CYCLES / 64 || xo_chg < pops / 2 || ro_chg < rowreads / 2
            || so_chg < suans / 2 || nonzero < 64 * CYCLES || ovf_cmp < 8 || ovf_cmp > 158) begin
            $display("FAIL qfd_vm_region_leaf VACUOUS pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d moves=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
                pushes, pops, rowreads, suans, stalls, moves, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
            $fatal(1, "FAIL");
        end
        if (errors != 0) begin
            $display("FAIL qfd_vm_region_leaf LEAF_MUT=%0d ROW_MUT=%0d SU_MUT=%0d errors=%0d of %0d (xo %0d ro %0d so %0d ovf %0d)", LEAF_MUT, ROW_MUT, SU_MUT, errors, checks, e_xo, e_ro, e_so, e_ovf);
            $fatal(1, "FAIL");
        end
        $display("PASS qfd_vm_region_leaf DEPTH=%0d LAW=%0d DEPTHS=%0d LAWS=%0d SEED=%0d OVFMODE=%0d exact %0d checks: pushes=%0d pops=%0d row_reads=%0d su_answers=%0d stalls=%0d pop_garbage=%0d deep=%0d xo_chg=%0d ro_chg=%0d so_chg=%0d nonzero_words=%0d ovf_cycles=%0d",
            DEPTH, LAW, DEPTHS, LAWS, SEED, OVFMODE, checks, pushes, pops, rowreads, suans, stalls, garbage, deep, xo_chg, ro_chg, so_chg, nonzero, ovf_cmp);
        $finish;
    end
endmodule
