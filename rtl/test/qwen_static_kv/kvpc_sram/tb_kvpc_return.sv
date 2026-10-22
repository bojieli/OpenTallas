`timescale 1ps/1fs
// KV-PC 2026-10-19: lockstep REF qkd_static_kv_return_slots_mc_nc (flop ring) vs DUT qkd_kvpc_s_return (native banks).
// Two clocks: HBM 1024 ps (pll_hbm and the four storage roots), core 834 ps (+0.3 ps: no coincident edges).  Legal
// traffic: the HBM side puts a sector (compiled_hbm_put with controller_co[0]) while fewer than DEPTH are unconsumed
// (consumption seen >= 4 HBM edges ago); the core side issues expected_put for the oldest put >= 4 core edges after
// it, with the sector's {epoch, layer, sector} as meta.  Fault phases inject wrong meta (fault_core) and a put whose
// controller_co[0] disagrees (fault_hbm); the ring capacity is always respected (an overrun / early slot reads a slot
// under write, whose data is undefined in both designs).
// Every output compared at every edge of both clocks.  +define+KVPC_MUT=N: DUT MUT (1 bank permutation, 2 no
// prefetch: must FAIL).
`ifndef KVPC_MUT
`define KVPC_MUT 0
`endif
module tb_kvpc_return;
    localparam integer DEPTH = 8;
    reg hck = 0, ck = 0;
    always #512 hck = ~hck;
    initial begin #0.3; forever #417 ck = ~ck; end
    reg hrst = 0, rsi = 0;
    reg [281:0] co;
    reg [15:0] ep;
    reg put;
    reg eput;
    reg [9:0] esec;
    reg [15:0] eep;
    reg [5:0] ely;
    wire r_av, d_av, r_fh, d_fh, r_fc, d_fc, r_ih, d_ih, r_ic, d_ic;
    wire [9:0] r_as, d_as;
    wire [15:0] r_ae, d_ae;
    wire [5:0] r_al, d_al;
    wire [255:0] r_ad, d_ad;
    qkd_static_kv_return_slots_mc_nc #(.DEPTH(DEPTH)) u_ref (.pll_hbm(hck), .hrst(hrst), .ck(ck), .rsi(rsi),
        .pll_hbm_data({4{hck}}), .controller_co(co), .controller_epoch(ep), .compiled_hbm_put(put),
        .expected_put(eput), .expected_sector(esec), .expected_epoch(eep), .expected_layer(ely),
        .actual_valid(r_av), .actual_sector(r_as), .actual_epoch(r_ae), .actual_layer(r_al), .actual_data(r_ad),
        .fault_hbm(r_fh), .fault_core(r_fc), .idle_hbm(r_ih), .idle_core(r_ic));
    qkd_kvpc_s_return #(.DEPTH(DEPTH), .MUT(`KVPC_MUT)) u_dut (.pll_hbm(hck), .hrst(hrst), .ck(ck), .rsi(rsi),
        .pll_hbm_data({4{hck}}), .controller_co(co), .controller_epoch(ep), .compiled_hbm_put(put),
        .expected_put(eput), .expected_sector(esec), .expected_epoch(eep), .expected_layer(ely),
        .actual_valid(d_av), .actual_sector(d_as), .actual_epoch(d_ae), .actual_layer(d_al), .actual_data(d_ad),
        .fault_hbm(d_fh), .fault_core(d_fc), .idle_hbm(d_ih), .idle_core(d_ic));
    integer bad, chk, acts, seed, edges, t, np, nc, ncs, phase;
    reg [31:0] qm [0:4095];          // meta of put n
    time qt [0:4095];                // time of put n
    time ct [0:4095];                // time of consume n
    task compare(input [8*3-1:0] ph); begin
        chk = chk + 1;
        if ({r_av, r_as, r_ae, r_al, r_ad, r_fh, r_fc, r_ih, r_ic} !== {d_av, d_as, d_ae, d_al, d_ad, d_fh, d_fc, d_ih, d_ic}) begin
            bad = bad + 1;
            if (bad < 10) $display("MISMATCH %s t=%0t av %b/%b sec %h/%h data %h/%h fh %b/%b fc %b/%b ih %b/%b ic %b/%b", ph,
                $time, r_av, d_av, r_as, d_as, r_ad[31:0], d_ad[31:0], r_fh, d_fh, r_fc, d_fc, r_ih, d_ih, r_ic, d_ic);
        end
        if (r_av) acts = acts + 1;
    end endtask
    reg pfh = 0, pfc = 0;
    always @(negedge hck) begin
        if (hrst && r_fh && !pfh) $display("INFO first fault_hbm t=%0t phase=%0d np=%0d nc=%0d ncs=%0d", $time, phase, np, nc, ncs);
        if (rsi && r_fc && !pfc) $display("INFO first fault_core t=%0t phase=%0d np=%0d nc=%0d", $time, phase, np, nc);
        pfh = r_fh; pfc = r_fc;
    end
    always @(posedge ck) if (rsi && u_ref.slot && $test$plusargs("debug") && $time < 40000)
        $display("DBG t=%0t ra=%0d rp=%0d pub2=%b ov=%b rd_meta=%h meta=%h wp=%0d pub=%b", $time, u_ref.ra, u_ref.rp,
                 u_ref.pub_sync2, u_ref.observed_valid, u_ref.read_data[287:256], u_ref.meta, u_ref.wp, u_ref.published);
    always @(negedge hck) if (hrst) compare("hck");
    always @(negedge ck) if (rsi) compare("ck ");
    // HBM side writer (traffic starts 4 edges after both resets released: the ring's hr / rs_* captures)
    reg [31:0] m;
    integer live_h = 0, live_c = 0;
    always @(negedge hck) live_h <= (hrst && rsi) ? live_h + 1 : 0;
    always @(negedge ck) live_c <= (hrst && rsi) ? live_c + 1 : 0;
    always @(negedge hck) begin
        put <= 1'b0; co[0] <= 1'b0;
        co[281:1] <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        ep <= $urandom;
        while (ncs < nc && $time >= ct[ncs] + 4 * 1024) ncs = ncs + 1;
        if (live_h > 4 && live_c > 4 && np < 4096 && (np - ncs) < DEPTH && ($urandom % 100) < (phase == 1 ? 25 : 70)) begin
            m = $urandom;
            ep <= m[31:16];
            co[17:12] <= m[15:10]; co[11:9] <= m[9:7]; co[7:1] <= m[6:0];
            qm[np] = m; qt[np] = $time;
            np = np + 1;
            put <= 1'b1; co[0] <= (phase == 3 && ($urandom % 30) == 0) ? 1'b0 : 1'b1;   // fault: observed != put
        end
    end
    // core side reader
    always @(negedge ck) begin
        eput <= 1'b0; esec <= $urandom; eep <= $urandom; ely <= $urandom;
        if (live_h > 4 && live_c > 4 && nc < np && $time >= qt[nc] + 4 * 834 && ($urandom % 100) < (phase == 1 ? 90 : 40)) begin
            {eep, ely, esec} <= (phase == 2 && ($urandom % 20) == 0) ? ~qm[nc] : qm[nc];       // fault: wrong meta
            ct[nc] = $time;
            nc = nc + 1;
            eput <= 1'b1;
        end
    end
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("edges=%d", edges)) edges = 12000;
        t = $urandom(seed);
        bad = 0; chk = 0; acts = 0; np = 0; nc = 0; ncs = 0; phase = 0;
        co = 0; ep = 0; put = 0; eput = 0; esec = 0; eep = 0; ely = 0;
        repeat (8) @(negedge hck);
        hrst = 1; rsi = 1;
        for (t = 0; t < edges; t = t + 1) begin
            @(negedge hck);
            phase = (t / 1500) % 4;
            if (t == edges / 2) begin           // reset both domains (ring state and faults restart; storage keeps data)
                hrst = 0; rsi = 0;
                repeat (6) @(negedge hck);
                np = 0; nc = 0; ncs = 0;
                hrst = 1; rsi = 1;
            end
        end
        if (bad == 0 && acts > 1000)
            $display("KVPC_RETURN PASS edges=%0d checks=%0d consumed=%0d errors=0 mut=%0d", edges, chk, acts, `KVPC_MUT);
        else
            $display("KVPC_RETURN FAIL edges=%0d checks=%0d errors=%0d consumed=%0d mut=%0d", edges, chk, bad, acts, `KVPC_MUT);
        $finish;
    end
endmodule
