`timescale 1ns/1ps
// KDIE4-LP 10-22: lockstep random equivalence of the native-safe rope core against the 015489b01 core
// (qkd_d2d_cal_seq_ovl_rope_bc_core_old = that commit's core over the shared ot_qwen_d2d_ovl_seq).  Same pins, same
// list ROM images, random reset / reload / halt / epoch / boot-write traffic with quiet stretches long enough for the
// players to run whole frames; every output and every fault-cause register compared on every edge.
module tb_kv_dcal_ovl_rope_eq;
    parameter ROM_DIR = "rtl/qwen_sys/d2d_static_20261015/ovl_release_rope";
    parameter integer MUT = 0;
    parameter integer HMUT = 0;
    `include "ovl_release_rope/ovl_wrapper_params.svh"
    `include "ovl_release_rope/ovl_release_img.svh"
    reg ck = 0; always #0.4167 ck = ~ck;
    reg rst_n = 0, reload = 0, epoch_go = 0, halt = 0, bt = 0, br = 0; reg [5:0] ba = 0; reg [31:0] bd = 0;
    wire [10:0] ta0, ra0, ta1, ra1; wire [71:0] tq0, rq0, tq1, rq1;
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_tx.viamap.hex"}),.INSTANCE("o_tx")) u_t0 (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ta0}),.rd_out(tq0));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_rx.viamap.hex"}),.INSTANCE("o_rx")) u_r0 (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ra0}),.rd_out(rq0));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_tx.viamap.hex"}),.INSTANCE("n_tx")) u_t1 (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ta1}),.rd_out(tq1));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_rx.viamap.hex"}),.INSTANCE("n_rx")) u_r1 (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ra1}),.rd_out(rq1));
    wire [63:0] o0, o1;
    `define OT_EQ_CORE(M, I, TA, RA, TQ, RQ, O) \
        M #(.FIRST_OFS(ROPE_OVL_FIRST_OFS), .ADM_OFS(ROPE_OVL_ADM_OFS), .ADM_LEN(ROPE_OVL_ADM_LEN), .MUT(MUT), \
            .MUT_HALT_REWIND(HMUT)) I ( \
            .ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt), \
            .bcfg_tx_we(bt),.bcfg_rx_we(br),.bcfg_addr(ba),.bcfg_data(bd), \
            .cfg_tx_we(O[0]),.cfg_rx_we(O[1]),.cfg_addr(O[7:2]),.cfg_data(O[39:8]), \
            .cal_start(O[40]),.cal_seg(O[41]),.cal_start_rx(O[42]),.cal_seg_rx(O[43]), \
            .cal_user_tx(O[45:44]),.cal_user_rx(O[47:46]),.cal_ready(O[48]),.adm_done(O[49]), \
            .running(O[50]),.fault(O[51]),.tx_rom_addr(TA),.tx_rom_q(TQ[31:0]),.rx_rom_addr(RA),.rx_rom_q(RQ[31:0]));
    `OT_EQ_CORE(qkd_d2d_cal_seq_ovl_rope_bc_core_old, u_old, ta0, ra0, tq0, rq0, o0)
    `OT_EQ_CORE(qkd_d2d_cal_seq_ovl_rope_bc_core, u_new, ta1, ra1, tq1, rq1, o1)
    assign o0[63:52] = {ta0[7:0], u_old.f_col, u_old.f_run, u_old.f_stale, u_old.f_early};
    assign o1[63:52] = {ta1[7:0], u_new.f_col, u_new.f_run, u_new.f_stale, u_new.f_early};
    integer cyc = 0, bad = 0, seed = 1, ncyc = 400000, starts = 0, adms = 0, cfgw = 0, faults = 0;
    always @(negedge ck) begin
        cyc <= cyc + 1;
        if (o0 !== o1 || ta0 !== ta1 || ra0 !== ra1) begin
            if (bad < 5) $display("KDCALEQ_MISMATCH cyc%0d old %h new %h ta %h/%h ra %h/%h", cyc, o0, o1, ta0, ta1, ra0, ra1);
            bad = bad + 1;
        end
        if (o0[40] | o0[42]) starts = starts + 1;
        if (o0[49]) adms = adms + 1;
        if (o0[0] | o0[1]) cfgw = cfgw + 1;
        if (o0[51]) faults = faults + 1;
    end
    // stimulus: phases of 0..3 = quiet run / boot writes / disturbances / reset
    integer r, ph, k;
    initial begin
        void'($value$plusargs("SEED=%d", seed));
        void'($value$plusargs("NCYC=%d", ncyc));
        r = $urandom(seed);
        repeat (3) @(negedge ck); rst_n = 1;
        while (cyc < ncyc) begin
            ph = $urandom % 20;
            if (ph >= 16) begin                     // clean boot as the die: reset, table + bases, epoch, long run
                #0.2 rst_n = 0; @(negedge ck); #0.1 rst_n = 1;
                repeat (80 + $urandom % 20) @(negedge ck);
                for (k = 0; k < 32; k = k + 1) begin
                    @(negedge ck); bt = 1; br = 0; ba = 6'(k); bd = OVL_K_TX_IMG[32*k +: 32];
                    @(negedge ck); bt = 0; br = 1; ba = 6'(k); bd = OVL_K_RX_IMG[32*k +: 32];
                end
                @(negedge ck); bt = 1; br = 0; ba = 6'd32; bd = 32'd16;
                @(negedge ck); bt = 0; br = 1; ba = 6'd32; bd = 32'd16;
                @(negedge ck); bt = 0; br = 0;
                repeat (5 + $urandom % 10) @(negedge ck);
                epoch_go = 1; @(negedge ck); epoch_go = 0;
                repeat (20000 + $urandom % 60000) @(negedge ck);
                if ($urandom % 2) begin halt = 1; repeat (1 + $urandom % 8) @(negedge ck); halt = 0; end
                if ($urandom % 3 == 0) begin @(negedge ck); reload = 1; @(negedge ck); reload = 0; end
            end else if (ph < 6) begin                       // quiet: one epoch, then let the lists run
                @(negedge ck); epoch_go = 1; @(negedge ck); epoch_go = $urandom % 2; @(negedge ck); epoch_go = 0;
                repeat (500 + $urandom % 6000) @(negedge ck);
            end else if (ph < 10) begin             // boot writes (tables, bases good / stale)
                for (k = 0; k < 4 + $urandom % 70; k = k + 1) begin
                    @(negedge ck); bt = $urandom % 2; br = ($urandom % 3 == 0) ? bt : !bt;
                    ba = ($urandom % 4 == 0) ? 6'd32 : 6'($urandom % 64);
                    bd = ($urandom % 2) ? 32'd16 : $urandom;
                end
                @(negedge ck); bt = 0; br = 0;
            end else if (ph < 15) begin             // random control disturbances
                for (k = 0; k < 20 + $urandom % 400; k = k + 1) begin
                    @(negedge ck);
                    reload = ($urandom % 50 == 0); halt = ($urandom % 30 == 0); epoch_go = ($urandom % 40 == 0);
                    if ($urandom % 60 == 0) begin bt = 1; br = $urandom % 2; ba = 6'($urandom); bd = $urandom; end
                    else begin bt = 0; br = 0; end
                end
                @(negedge ck); reload = 0; halt = 0; epoch_go = 0; bt = 0; br = 0;
            end else begin                          // asynchronous reset pulse (mid-cycle)
                #0.2 rst_n = 0; repeat (1 + $urandom % 3) @(negedge ck); #0.1 rst_n = 1;
            end
        end
        $display("KDCALEQ_%s seed%0d cyc%0d mismatches%0d starts%0d adm%0d cfgw%0d faultcyc%0d", bad ? "FAIL" : "PASS",
                 seed, cyc, bad, starts, adms, cfgw, faults);
        if (bad) $fatal(1);
        $finish;
    end
endmodule
