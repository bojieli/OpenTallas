`timescale 1ns/1ps
`default_nettype none
// L2H-IDX e86s 2026-10-19: lockstep bench of the SAFE e86 control replication (CREP 1) against the e86 form.
//   REF = ot_hgi_coll_tkm_tile_rg #(EW 86, PT 64, PRE 1, CREP 0)  (the e86 tile: one control flop per row group)
//   DUT = ot_hgi_coll_tkm_tile_rg #(EW 86, PT 64, PRE 1, CREP 1)  (per-slice kept one-hot select copies, <= 29 loads)
// Both see the same random stimulus (sorted 4-element blocks with valid bits, clr / conv pulses, tau probes, up_in);
// every output (ovf_v, ovf_b, up_out, tau_o, busy) is compared at every edge.  The bench also counts activity so a
// silent pass is impossible (ovf_v, up_out changes and nonzero tau_o hits must all occur).
//   MUT 0: DUT CMUT 0 -> must PASS (cycle identity, every output every edge, ovf_b compared every edge too).
//   MUT 1: DUT CMUT 1 (position 13 slice 1 holds where it should shift on conv) -> must FAIL.
//   RT 1 (STEWARD-HBMd/E86 10-23): DUT = FAN32 2 + RT 1 (retimed stage-C compare, one added input edge).  The REF sees
//   clr / conv / ins_v / ins_b / tid / tau one edge late (a bench register), up_in undelayed (the conveyor samples it at
//   the shift edge in both), so every output is still compared at every edge.  MUT 5 / 6 = DUT CMUT 5 / 6 (RT select
//   mutants) -> must FAIL.
module tb_hgi_coll_tkm_tile_rg_crep;
    parameter integer MUT = 0;
    parameter integer FAN32 = 0;
    parameter integer SEAM = 0;
    parameter integer RT = 0;
    // CHAIN 1 (STEWARD-HBMd/E86 10-23, used with RT 1): REF and DUT are each a TWO-TILE chain as tkm_static wires it
    // (tile 1 takes tile 0's ovf as its insertion, tile 0's up_in is tile 1's up_out, tile 1's up_in is 0), so the array
    // stays globally sorted.  Random up_in blocks (CHAIN 0) unsort X after a conv; the insertion legs then stop being
    // one-hot and the tile ORs several values -- an input the chain never produces, on which RT's registered compare
    // (compare of each leg, ORed) and a compare of the ORed value legitimately differ.  conv waits 14 idle edges (chain drained).
    parameter integer CHAIN = 0;
    parameter integer NCYC = 4000;
    parameter integer SEED = 17;
    localparam integer EW = 86, PT = 64, TW = 6, LW = 7;
    localparam real T = 10.0, SKEW = 3.0;
    reg clk = 1'b0;
    always #(T/2) clk = ~clk;
    reg [TW-1:0] tid = 6'd5, tau_t;
    reg [LW-1:0] tau_l;
    reg clr, conv, ins_v;
    reg [4*EW-1:0] ins_b, up_in;
    wire ro_v, do_v, rbusy, dbusy;
    wire r1_v, d1_v; wire [4*EW-1:0] r1_b, d1_b, r1_up, d1_up, rui, dui;
    wire [4*EW-1:0] ro_b, do_b, rup, dup;
    wire [EW-2:0] rtau, dtau;
    reg [TW-1:0] d_tid = 6'd5, d_tau_t = '0; reg [LW-1:0] d_tau_l = '0; reg d_clr = 1'b1, d_conv = 1'b0, d_ins_v = 1'b0;
    reg [4*EW-1:0] d_ins_b = '0;
    always @(posedge clk) begin d_tid <= tid; d_tau_t <= tau_t; d_tau_l <= tau_l; d_clr <= clr; d_conv <= conv; d_ins_v <= ins_v; d_ins_b <= ins_b; end
    wire [TW-1:0] r_tid = RT ? d_tid : tid, r_tau_t = RT ? d_tau_t : tau_t; wire [LW-1:0] r_tau_l = RT ? d_tau_l : tau_l;
    wire r_clr = RT ? d_clr : clr, r_conv = RT ? d_conv : conv, r_ins_v = RT ? d_ins_v : ins_v;
    wire [4*EW-1:0] r_ins_b = RT ? d_ins_b : ins_b;
    ot_hgi_coll_tkm_tile_rg #(.EW(EW), .PT(PT), .TW(TW), .LW(LW), .PRE(1), .CREP(0)) u_ref (.clk(clk), .clk_r0(clk), .clk_r1(clk),
        .clk_r2(clk), .clk_r3(clk), .tid(r_tid), .clr(r_clr), .conv(r_conv),
        .tau_t(r_tau_t), .tau_l(r_tau_l), .ins_v(r_ins_v), .ins_b(r_ins_b), .ovf_v(ro_v), .ovf_b(ro_b), .up_in(rui), .up_out(rup),
        .tau_o(rtau), .busy(rbusy));
    ot_hgi_coll_tkm_tile_rg #(.EW(EW), .PT(PT), .TW(TW), .LW(LW), .PRE(1), .CREP(1), .CMUT(MUT), .FAN32(FAN32), .SEAM(SEAM), .RT(RT)) u_dut (.clk(clk), .clk_r0(clk), .clk_r1(clk), .clk_r2(clk),
        .clk_r3(clk), .tid(tid), .clr(clr), .conv(conv), .tau_t(tau_t), .tau_l(tau_l), .ins_v(ins_v), .ins_b(ins_b),
        .ovf_v(do_v), .ovf_b(do_b), .up_in(dui), .up_out(dup), .tau_o(dtau), .busy(dbusy));
    generate if (CHAIN != 0) begin : g_chain
        wire [EW-2:0] t1r, t1d; wire b1r, b1d;
        ot_hgi_coll_tkm_tile_rg #(.EW(EW), .PT(PT), .TW(TW), .LW(LW), .PRE(1), .CREP(0)) u_ref1 (.clk(clk), .clk_r0(clk), .clk_r1(clk),
            .clk_r2(clk), .clk_r3(clk), .tid(6'd6), .clr(r_clr), .conv(r_conv), .tau_t(r_tau_t), .tau_l(r_tau_l), .ins_v(ro_v),
            .ins_b(ro_b), .ovf_v(r1_v), .ovf_b(r1_b), .up_in({4*EW{1'b0}}), .up_out(r1_up), .tau_o(t1r), .busy(b1r));
        ot_hgi_coll_tkm_tile_rg #(.EW(EW), .PT(PT), .TW(TW), .LW(LW), .PRE(1), .CREP(1), .FAN32(FAN32), .SEAM(SEAM), .RT(RT)) u_dut1 (.clk(clk),
            .clk_r0(clk), .clk_r1(clk), .clk_r2(clk), .clk_r3(clk), .tid(6'd6), .clr(clr), .conv(conv), .tau_t(tau_t), .tau_l(tau_l),
            .ins_v(do_v), .ins_b(do_b), .ovf_v(d1_v), .ovf_b(d1_b), .up_in({4*EW{1'b0}}), .up_out(d1_up), .tau_o(t1d), .busy(b1d));
        assign rui = r1_up; assign dui = d1_up;
    end else begin : g_single
        assign rui = up_in; assign dui = up_in; assign r1_v = 1'b0; assign d1_v = 1'b0; assign r1_b = '0; assign d1_b = '0;
        assign r1_up = '0; assign d1_up = '0;
    end endgenerate
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
            if (gap >= ((CHAIN != 0) ? 14 : 3) && ($unsigned($random(seed)) % 23) == 0) begin conv = 1'b1; ins_v = 1'b0; gap = 0; end
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
            $display("TKM_RG_CREP MUT%0d VACUOUS ovf%0d up%0d tau%0d ins%0d", MUT, n_ovf, n_up, n_tau, n_ins); err = err + 1;
        end
        $display("TKM_RG_CREP MUT%0d cycles%0d ins%0d ovf%0d up%0d tau%0d errors%0d %s", MUT, NCYC, n_ins, n_ovf, n_up,
                 n_tau, err, (err == 0) ? "PASS" : "FAIL");
        $finish;
    end
    // compare just before the next rising edge (all roots have settled, including the skewed mutant root)
    always @(posedge clk) begin
        #(T/2 - 0.5);
        if (ro_v) n_ovf = n_ovf + 1;
        if (rup != last_up) begin n_up = n_up + 1; last_up = rup; end
        if (rtau != '0) n_tau = n_tau + 1;
        if ({ro_v, rbusy, rtau, rup, ro_b, r1_v, r1_up} !== {do_v, dbusy, dtau, dup, do_b, d1_v, d1_up} || (r1_v && r1_b !== d1_b)) begin
            if (err < 5) $display("MISMATCH t=%0t ovf %b/%b busy %b/%b tau %h/%h up_eq %b ovfb_eq %b", $time, ro_v, do_v,
                                  rbusy, dbusy, rtau, dtau, rup === dup, ro_b === do_b);
            err = err + 1;
        end
    end
endmodule
`default_nettype wire
