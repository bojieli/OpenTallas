`timescale 1ns/1ps
`default_nettype none
// HBM-C lane 2026-10-17: lockstep bench of the TKM e86 row-group tile against the generic tile.
//   REF = ot_hgi_coll_tkm_tile #(EW 86, PT 64, CDUP 1)  (the fab3f5eba tile the K2048 TP192 gate passed)
//   DUT = ot_hgi_coll_tkm_tile_rg #(EW 86, PT 64)       (1bf775c44: live-node compares, clk + clk_r0..r3 roots)
// Both see the same random stimulus (sorted 4-element blocks with valid bits, clr / conv pulses, tau probes, up_in);
// every output (ovf_v, ovf_b, up_out, tau_o, busy) is compared at every edge.  The bench also counts activity so a
// silent pass is impossible (ovf_v, up_out changes and nonzero tau_o hits must all occur).
//   MUT 0: all five roots are one clock -> must PASS (cycle identity).
//   MUT 1: clk_r2 skewed late by SKEW ns (a mis-bound / unbalanced regional root) -> must FAIL (the row-group seams
//          really cross roots; the bench sees a root that is not edge-aligned).
module tb_hgi_coll_tkm_tile_rg_lockstep;
    parameter integer MUT = 0;
    parameter integer NCYC = 4000;
    parameter integer SEED = 17;
    localparam integer EW = 86, PT = 64, TW = 6, LW = 7;
    localparam real T = 10.0, SKEW = 3.0;
    reg clk = 1'b0;
    always #(T/2) clk = ~clk;
    wire clk_r2;
    generate if (MUT == 1) begin : g_skew assign #(SKEW) clk_r2 = clk; end else begin : g_ok assign clk_r2 = clk; end endgenerate
    reg [TW-1:0] tid = 6'd5, tau_t;
    reg [LW-1:0] tau_l;
    reg clr, conv, ins_v;
    reg [4*EW-1:0] ins_b, up_in;
    wire ro_v, do_v, rbusy, dbusy;
    wire [4*EW-1:0] ro_b, do_b, rup, dup;
    wire [EW-2:0] rtau, dtau;
    ot_hgi_coll_tkm_tile #(.EW(EW), .PT(PT), .TW(TW), .LW(LW), .CDUP(1)) u_ref (.clk(clk), .tid(tid), .clr(clr), .conv(conv),
        .tau_t(tau_t), .tau_l(tau_l), .ins_v(ins_v), .ins_b(ins_b), .ovf_v(ro_v), .ovf_b(ro_b), .up_in(up_in), .up_out(rup),
        .tau_o(rtau), .busy(rbusy));
    ot_hgi_coll_tkm_tile_rg #(.EW(EW), .PT(PT), .TW(TW), .LW(LW)) u_dut (.clk(clk), .clk_r0(clk), .clk_r1(clk), .clk_r2(clk_r2),
        .clk_r3(clk), .tid(tid), .clr(clr), .conv(conv), .tau_t(tau_t), .tau_l(tau_l), .ins_v(ins_v), .ins_b(ins_b),
        .ovf_v(do_v), .ovf_b(do_b), .up_in(up_in), .up_out(dup), .tau_o(dtau), .busy(dbusy));
    integer seed = SEED, cyc, err = 0, n_ovf = 0, n_up = 0, n_tau = 0, n_ins = 0, gap = 0;
    reg [4*EW-1:0] last_up = '0;
    // one valid element: {valid, 85-bit key}; a block = 4 elements in descending key order (as the TKM merge feeds it)
    function automatic [EW-1:0] elem(input integer s);
        reg [EW-2:0] k; integer i;
        begin for (i = 0; i < EW - 1; i = i + 32) k[i +: 32] = $random(seed); elem = {1'b1, k}; end
    endfunction
    task automatic mk_block(output reg [4*EW-1:0] b);
        reg [EW-1:0] e [0:3]; reg [EW-1:0] t_; integer i, j, nv;
        begin
            nv = 1 + ($unsigned($random(seed)) % 4);
            for (i = 0; i < 4; i = i + 1) e[i] = (i < nv) ? elem(0) : '0;
            for (i = 0; i < 4; i = i + 1) for (j = 0; j < 3 - i; j = j + 1)
                if (e[j][EW-2:0] < e[j+1][EW-2:0]) begin t_ = e[j]; e[j] = e[j+1]; e[j+1] = t_; end
            b = {e[3], e[2], e[1], e[0]};
        end
    endtask
    initial begin
        clr = 1'b1; conv = 1'b0; ins_v = 1'b0; ins_b = '0; up_in = '0; tau_t = 6'd5; tau_l = '0;
        repeat (4) @(posedge clk);
        @(negedge clk) clr = 1'b0;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            clr = ($unsigned($random(seed)) % 997) == 0;
            // conveying never overlaps an entering block (the tile's legality): a conv pulse only after 3 idle edges
            if (gap >= 3 && ($unsigned($random(seed)) % 23) == 0) begin conv = 1'b1; ins_v = 1'b0; gap = 0; end
            else begin
                conv = 1'b0;
                ins_v = (gap >= 3 || ins_v) ? (($unsigned($random(seed)) % 4) != 0) : 1'b0;
                gap = ins_v ? 0 : gap + 1;
            end
            mk_block(ins_b); mk_block(up_in);
            if (ins_v) n_ins = n_ins + 1;
            tau_t = ($unsigned($random(seed)) % 2) ? 6'd5 : 6'($random(seed));
            tau_l = 7'($unsigned($random(seed)) % PT);
        end
        repeat (8) @(negedge clk);
        if (n_ovf == 0 || n_up == 0 || n_tau == 0) begin
            $display("TKM_RG_LOCKSTEP MUT%0d VACUOUS ovf%0d up%0d tau%0d ins%0d", MUT, n_ovf, n_up, n_tau, n_ins); err = err + 1;
        end
        $display("TKM_RG_LOCKSTEP MUT%0d cycles%0d ins%0d ovf%0d up%0d tau%0d errors%0d %s", MUT, NCYC, n_ins, n_ovf, n_up,
                 n_tau, err, (err == 0) ? "PASS" : "FAIL");
        $finish;
    end
    // compare just before the next rising edge (all roots have settled, including the skewed mutant root)
    always @(posedge clk) begin
        #(T/2 - 0.5);
        if (ro_v) n_ovf = n_ovf + 1;
        if (rup != last_up) begin n_up = n_up + 1; last_up = rup; end
        if (rtau != '0) n_tau = n_tau + 1;
        if ({ro_v, rbusy, rtau, rup} !== {do_v, dbusy, dtau, dup} || (ro_v && ro_b !== do_b)) begin
            if (err < 5) $display("MISMATCH t=%0t ovf %b/%b busy %b/%b tau %h/%h up_eq %b ovfb_eq %b", $time, ro_v, do_v,
                                  rbusy, dbusy, rtau, dtau, rup === dup, ro_b === do_b);
            err = err + 1;
        end
    end
endmodule
`default_nettype wire
