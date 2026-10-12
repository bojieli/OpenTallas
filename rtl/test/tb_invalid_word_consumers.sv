`timescale 1ns/1ps
// el1011-q-seq (2026-10-11): consumer-side proof for the ctlm_i AUD valid/data exactness rule.  ctlm_i's SRAM tag line
// differs from the flop ring only in words emitted while their valid is low: p_f_e2 (valid p_v_e2) and scale_addr (read
// under scale_re / scale_gre).  This bench drives each consumer twice with identical stimulus, except that copy B sees the
// word replaced by random junk whenever its valid is low, and requires every consumer output to match every cycle:
//   A: ot_qwen_me_spport_w12 (the port element: a_v_e2 / a_f_e2)       B: ot_qwen_rt_rom_bank (the die's scale ROM: re / addr)
// Port outputs: o_we / o_ov / fault every cycle; am on the cycles the tree-top accumulator samples it (tv = r_v && r_last, LPT+1 later); o_addr / o_mask / o_data per lane under o_we (the next valid/data hop).
// MUT = 1 scrambles also while the valid is high (1 in 8 cycles) -> must FAIL (the bench sees the words).
module tb_invalid_word_consumers;
    parameter integer NCYC = 20000, SEED = 1, MUT = 0;
    localparam integer W = 16, AW = 24, NW = 16, PQ = 4;
    localparam integer FW = 1+1+1+1+4+AW+AW+3*(NW+1);
    integer k, seed = SEED, cyc = 0, bad_a = 0, bad_b = 0, nva = 0, nvb = 0, nsa = 0, nsb = 0, i;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = !clk;
    // ---- A: port element ----
    reg  [PQ*W*32-1:0] lv_in = 0; reg a_v = 0; reg [FW-1:0] a_f = 0, a_fj = 0; reg [PQ*W*16-1:0] sq = 0;
    wire [FW-1:0] a_fb = (!a_v || (MUT != 0 && (cyc % 8) == 3)) ? a_fj : a_f;
    wire [PQ-1:0] we0, we1; wire [PQ*AW-1:0] ad0, ad1; wire [PQ*W-1:0] mk0, mk1; wire [PQ*W*32-1:0] da0, da1;
    wire ov0, ov1, f0, f1; wire [1+32+NW-1:0] am0, am1;
    ot_qwen_me_spport_w12 #(.W(W), .AW(AW), .NW(NW), .PQ(PQ)) u_a0 (.clk(clk), .rst_n(rst_n), .pt_id(16'd3), .lv_in(lv_in),
        .a_v_e2(a_v), .a_f_e2(a_f), .scale_q(sq), .o_we(we0), .o_addr(ad0), .o_mask(mk0), .o_data(da0), .o_ov(ov0), .am(am0), .fault(f0));
    ot_qwen_me_spport_w12 #(.W(W), .AW(AW), .NW(NW), .PQ(PQ)) u_a1 (.clk(clk), .rst_n(rst_n), .pt_id(16'd3), .lv_in(lv_in),
        .a_v_e2(a_v), .a_f_e2(a_fb), .scale_q(sq), .o_we(we1), .o_addr(ad1), .o_mask(mk1), .o_data(da1), .o_ov(ov1), .am(am1), .fault(f1));
    // the port element's outputs are themselves valid/data: o_addr / o_mask / o_data of lane l are written only under
    // o_we[l] (the vector-memory write), so they are compared per lane under o_we; o_we, o_ov, am and fault every cycle
    reg lane_bad; integer l, nlm = 0;
    always @(*) begin
        lane_bad = 1'b0;
        for (l = 0; l < PQ; l = l + 1)
            if (we0[l] && ((ad0[l*AW +: AW] !== ad1[l*AW +: AW]) || (mk0[l*W +: W] !== mk1[l*W +: W]) || (da0[l*W*32 +: W*32] !== da1[l*W*32 +: W*32])))
                lane_bad = 1'b1;
    end
    always @(posedge clk) if (rst_n && ({ad0, mk0, da0} !== {ad1, mk1, da1})) nlm = nlm + 1;   // differences on unwritten lanes
    // am is consumed by the tree-top accumulator only on the cycles its tv line marks (r_v && r_last of the element, LPT + 1
    // edges through the leaf register and the LPT argmax levels): compare am (all bits) on exactly those cycles
    localparam integer LPT = $clog2(PQ * W);
    reg [LPT:0] amq = 0; integer nam = 0;
    always @(posedge clk) amq <= {amq[LPT-1:0], u_a0.r_v && u_a0.r_last};
    always @(posedge clk) if (rst_n && amq[LPT]) nam = nam + 1;
    // ---- B: scale ROM bank ----
    reg re = 0; reg [AW-1:0] addr = 0, addrj = 0;
    wire [AW-1:0] addr_b = (!re || (MUT != 0 && (cyc % 8) == 5)) ? addrj : addr;
    wire [255:0] q0, q1; wire af0, af1;
    ot_qwen_rt_rom_bank #(.NB(2), .AW(AW), .DW(256)) u_b0 (.clk(clk), .rst_n(rst_n), .re(re), .addr(addr), .q(q0), .addr_fault(af0));
    ot_qwen_rt_rom_bank #(.NB(2), .AW(AW), .DW(256)) u_b1 (.clk(clk), .rst_n(rst_n), .re(re), .addr(addr_b), .q(q1), .addr_fault(af1));
    task stim;
        begin
            for (k = 0; k < PQ*W; k = k + 1) lv_in[k*32 +: 32] = $random(seed);
            for (k = 0; k < PQ*W/2; k = k + 1) sq[k*32 +: 32] = $random(seed);
            a_v = ($random(seed) & 3) == 0;
            for (k = 0; k < FW; k = k + 32) begin a_f[k +: 32] = $random(seed); a_fj[k +: 32] = $random(seed); end
            a_f[4 +: 4] = 4'($random(seed) % 6);                         // a split within the port's range
            re = ($random(seed) & 3) == 0;
            addr = {11'd0, 1'($random(seed) & 1), 12'($random(seed))};           // in range (NB 2) except rare faults
            if (($random(seed) & 63) == 0) addr[AW-1:12] = 12'd7;
            addrj = $random(seed);
        end
    endtask
    initial begin
        seed = SEED;
        repeat (4) @(posedge clk); rst_n = 1;
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge clk);
            stim;
            if ((i % 1000) == 999) rst_n = 0; else rst_n = 1;      // periodic resets
        end
        repeat (40) @(posedge clk);
        if (bad_a == 0 && bad_b == 0 && nsa > 0 && nsb > 0)
            $display("PASS invalid_word_consumers cycles=%0d port_valid=%0d port_scrambled=%0d rom_reads=%0d rom_scrambled=%0d unwritten_lane_diffs=%0d am_samples=%0d", cyc, nva, nsa, nvb, nsb, nlm, nam);
        else
            $display("FAIL invalid_word_consumers port_mismatch=%0d rom_mismatch=%0d (scrambled %0d / %0d)", bad_a, bad_b, nsa, nsb);
        $finish;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (a_v) nva = nva + 1; if (a_fb !== a_f) nsa = nsa + 1;
        if (re) nvb = nvb + 1; if (addr_b !== addr) nsb = nsb + 1;
        if (rst_n && (({we0, ov0, f0} !== {we1, ov1, f1}) || (amq[LPT] && (am0 !== am1)) || lane_bad)) begin
            bad_a = bad_a + 1; if (bad_a <= 3) $display("PORT MISMATCH cyc=%0d we=%b ad=%b mk=%b da=%b ov=%b am=%b f=%b", cyc, we0 !== we1, ad0 !== ad1, mk0 !== mk1, da0 !== da1, ov0 !== ov1, am0 !== am1, f0 !== f1); end
        if (rst_n && ({q0, af0} !== {q1, af1})) begin
            bad_b = bad_b + 1; if (bad_b <= 3) $display("ROM MISMATCH cyc=%0d", cyc); end
    end
endmodule
