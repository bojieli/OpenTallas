`timescale 1ns/1ps
// el1014-qwen-kvsys-elements: hub-level equivalence of the die-leaf hub (ot_qwen_nearhbm_attn_hub_d = qkd_ahub_core + the
// 13 hard tiles + die relay stages) against the hardened-tile hub ot_qwen_nearhbm_attn_hub_t (QKH_RECIP_LEAF form).
// Both get the SAME randomised layer traffic (per group: per-stack max partials, Z block sums, Z done, 32 P beats a stack,
// random stalls, groups / stacks interleaved); every mo word {g, hh, data} and every out beat {g, beat, data} must match
// in order, no fault on either side, and both must finish.  Prints the first-output and last-output latency difference.
//   +LAYERS=n (default 6)  +SEED=s   define TB_MUT: a one-bit flip on the core's pl_rz copy (the bench must FAIL).
module tb_qkd_ahub_d_eq;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg          start;
    reg [3:0]    si_valid;  reg [7:0] si_type;  reg [3:0] si_g;  reg [7:0] si_hh;  reg [15:0] si_k;  reg [3:0] si_any;
    reg [127:0]  si_data;
    reg [3:0]    pi_valid;  reg [3:0] pi_g;  reg [23:0] pi_beat;  reg [2047:0] pi_data;
    wire         mo_v_t, mo_g_t, out_v_t, out_g_t, flt_t, mo_v_d, mo_g_d, out_v_d, out_g_d, flt_d;
    wire [1:0]   mo_hh_t, mo_hh_d;  wire [31:0] mo_d_t, mo_d_d;  wire [5:0] ob_t, ob_d;  wire [511:0] od_t, od_d;
    wire [7:0]   ev_t, ev_d;
    ot_qwen_nearhbm_attn_hub_t u_t (.clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type),
        .si_g(si_g), .si_hh(si_hh), .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g),
        .pi_beat(pi_beat), .pi_data(pi_data), .mo_valid(mo_v_t), .mo_g(mo_g_t), .mo_hh(mo_hh_t), .mo_data(mo_d_t),
        .out_valid(out_v_t), .out_g(out_g_t), .out_beat(ob_t), .out_data(od_t), .fault(flt_t), .ev(ev_t));
`ifndef R_ZW
`define R_ZW 0
`endif
`ifndef R_ZR
`define R_ZR 0
`endif
`ifndef R_RA
`define R_RA 0
`endif
`ifndef R_SR
`define R_SR 1
`endif
`ifndef R_PV
`define R_PV 0
`endif
`ifndef R_Y
`define R_Y 0
`endif
`ifndef R_RX
`define R_RX 1
`endif
`ifndef R_PI
`define R_PI 0
`endif
`ifndef R_SI
`define R_SI 0
`endif
    ot_qwen_nearhbm_attn_hub_d #(.ZW_RLY(`R_ZW), .ZR_RLY(`R_ZR), .RA_RLY(`R_RA), .SR_RLY(`R_SR), .PV_RLY(`R_PV),
        .Y_RLY(`R_Y), .RX_RLY(`R_RX), .RY_RLY(`R_RX), .PI_RLY(`R_PI), .SI_RLY(`R_SI)) u_d (.clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid),
        .si_type(si_type), .si_g(si_g), .si_hh(si_hh), .si_k(si_k), .si_any(si_any), .si_data(si_data),
        .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat), .pi_data(pi_data), .mo_valid(mo_v_d), .mo_g(mo_g_d),
        .mo_hh(mo_hh_d), .mo_data(mo_d_d), .out_valid(out_v_d), .out_g(out_g_d), .out_beat(ob_d), .out_data(od_d),
        .fault(flt_d), .ev(ev_d));
`ifdef TB_MUT
    initial begin
        #1; force u_d.u_die.u_core.pl_rz[3] = 1'b1;
    end
`endif
    // ---- output logs -----------------------------------------------------------------------------------------------
    reg [34:0]  mq_t [0:4095];  reg [34:0]  mq_d [0:4095];
    reg [518:0] oq_t [0:4095];  reg [518:0] oq_d [0:4095];
    integer nm_t = 0, nm_d = 0, no_t = 0, no_d = 0, cyc = 0;
    integer first_t = -1, first_d = -1, last_t = 0, last_d = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (mo_v_t) begin mq_t[nm_t] <= {mo_g_t, mo_hh_t, mo_d_t}; nm_t <= nm_t + 1; end
        if (mo_v_d) begin mq_d[nm_d] <= {mo_g_d, mo_hh_d, mo_d_d}; nm_d <= nm_d + 1; end
        if (out_v_t) begin oq_t[no_t] <= {out_g_t, ob_t, od_t}; no_t <= no_t + 1; if (first_t < 0) first_t = cyc; last_t = cyc; end
        if (out_v_d) begin oq_d[no_d] <= {out_g_d, ob_d, od_d}; no_d <= no_d + 1; if (first_d < 0) first_d = cyc; last_d = cyc; end
    end
    // ---- stimulus --------------------------------------------------------------------------------------------------
    integer seed, layers, L, sd, n, i, guard, err;
    // per stack: a queue of S words {type, g, hh, k, data, any} and of P beats {g, beat}
    reg [47:0] sq [0:3][0:299];
    integer    sn [0:3], sp [0:3];
    integer    pbn [0:3];
    function [31:0] rf(input integer dummy);
        reg [31:0] r;
        begin r = $random(seed); rf = {r[31], 1'b0, (r[29:23] == 7'h7f) ? 7'h3f : r[29:23], r[22:0]}; end   // finite
    endfunction
    task build_queues;
        integer s, g, hh, k, m;
        reg [47:0] w;
        begin
            for (s = 0; s < 4; s = s + 1) begin
                m = 0;
                for (g = 0; g < 2; g = g + 1) begin
                    for (hh = 0; hh < 4; hh = hh + 1) begin       // type 0: max partial {g, s, hh}
                        w = 48'd0; w[47:46] = 2'd0; w[45] = g; w[44:43] = hh; w[38] = ($random(seed) % 8 != 0);
                        sq[s][m] = w; m = m + 1;
                    end
                    for (hh = 0; hh < 4; hh = hh + 1) for (k = 0; k < 16; k = k + 1) begin   // type 1: Z block sum
                        w = 48'd0; w[47:46] = 2'd1; w[45] = g; w[44:43] = hh; w[42:39] = k;
                        sq[s][m] = w; m = m + 1;
                    end
                    w = 48'd0; w[47:46] = 2'd2; w[45] = g; sq[s][m] = w; m = m + 1;            // type 2: Z done
                end
                sn[s] = m; sp[s] = 0; pbn[s] = 0;
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("LAYERS=%d", layers)) layers = 6;
        start = 0; si_valid = 0; si_type = 0; si_g = 0; si_hh = 0; si_k = 0; si_any = 0; si_data = 0;
        pi_valid = 0; pi_g = 0; pi_beat = 0; pi_data = 0; err = 0;
        repeat (20) @(posedge clk);
        rst_n = 1;
        repeat (20) @(posedge clk);
        for (L = 0; L < layers; L = L + 1) begin
            build_queues;
            @(negedge clk) start = 1; @(negedge clk) start = 0;
            repeat (4) @(negedge clk);
            guard = 0;
            while ((sp[0] < sn[0] || sp[1] < sn[1] || sp[2] < sn[2] || sp[3] < sn[3] ||
                    pbn[0] < 64 || pbn[1] < 64 || pbn[2] < 64 || pbn[3] < 64) && guard < 20000) begin
                @(negedge clk);
                guard = guard + 1;
                si_valid = 0; pi_valid = 0;
                for (sd = 0; sd < 4; sd = sd + 1) begin
                    if (sp[sd] < sn[sd] && ($random(seed) % 4 != 0)) begin
                        si_valid[sd] = 1'b1;
                        si_type[2*sd +: 2] = sq[sd][sp[sd]][47:46];
                        si_g[sd] = sq[sd][sp[sd]][45];
                        si_hh[2*sd +: 2] = sq[sd][sp[sd]][44:43];
                        si_k[4*sd +: 4] = sq[sd][sp[sd]][42:39];
                        si_any[sd] = sq[sd][sp[sd]][38];
                        si_data[32*sd +: 32] = rf(0);
                        sp[sd] = sp[sd] + 1;
                    end else begin
                        si_type[2*sd +: 2] = $random(seed); si_data[32*sd +: 32] = $random(seed);   // idle garbage
                    end
                    // P beats: group 0 beats 0..31 then group 1, in order, random stalls
                    if (pbn[sd] < 64 && ($random(seed) % 3 != 0)) begin
                        pi_valid[sd] = 1'b1;
                        pi_g[sd] = pbn[sd] / 32;
                        pi_beat[6*sd +: 6] = pbn[sd] % 32;
                        for (i = 0; i < 16; i = i + 1) pi_data[512*sd + 32*i +: 32] = rf(0);
                        pbn[sd] = pbn[sd] + 1;
                    end
                end
            end
            @(negedge clk) si_valid = 0; pi_valid = 0;
            // wait for both hubs to drain this layer (64 out beats a layer)
            guard = 0;
            while ((no_t < 64 * (L + 1) || no_d < 64 * (L + 1)) && guard < 20000) begin @(negedge clk); guard = guard + 1; end
            if (guard >= 20000) begin $display("TIMEOUT layer %0d: out t %0d d %0d", L, no_t, no_d); err = err + 1; end
            repeat (30) @(negedge clk);
        end
        // compare
        if (nm_t != nm_d) begin $display("MISMATCH mo count t %0d d %0d", nm_t, nm_d); err = err + 1; end
        if (no_t != no_d) begin $display("MISMATCH out count t %0d d %0d", no_t, no_d); err = err + 1; end
        for (n = 0; n < nm_t && n < nm_d; n = n + 1)
            if (mq_t[n] !== mq_d[n]) begin if (err < 10) $display("MISMATCH mo %0d t %h d %h", n, mq_t[n], mq_d[n]); err = err + 1; end
        for (n = 0; n < no_t && n < no_d; n = n + 1)
            if (oq_t[n] !== oq_d[n]) begin if (err < 10) $display("MISMATCH out %0d g/beat t %h d %h", n, oq_t[n][518:512], oq_d[n][518:512]); err = err + 1; end
        if (flt_t || flt_d) begin $display("FAULT t %b d %b", flt_t, flt_d); err = err + 1; end
        if (nm_t != 8 * layers || no_t != 64 * layers) begin $display("REF COUNT mo %0d out %0d (want %0d / %0d)", nm_t, no_t, 8*layers, 64*layers); err = err + 1; end
        $display("AHUB_D_EQ layers %0d mo %0d out %0d first_out t %0d d %0d (+%0d) last_out t %0d d %0d (+%0d) errors %0d",
                 layers, nm_t, no_t, first_t, first_d, first_d - first_t, last_t, last_d, last_d - last_t, err);
        if (err == 0) $display("PASS ahub_d == hub_t"); else $display("FAIL ahub_d != hub_t");
        $finish;
    end
endmodule
