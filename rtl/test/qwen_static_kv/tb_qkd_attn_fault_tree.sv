`timescale 1ns/1ps
// RTL-BUILD-KV/FAULT 2026-10-18 (lanes/RTL-BUILD-KV.md P7): the static KV die's attention service-unit fault tree, as
// kv_static_die.py (OT_KV_AFAULT, default with OT_KV_STATIC_DIE + PVFIN + FANFOLD) wires it, with the REAL node RTL:
//   per stack st, strip slot s = 0..7 (landing group g = ORDER[s]): af node qkd_kv_cfault_node R 3 fault_in =
//   {up = node(s-1), vport_<st>_<g/2>.f (forked to both groups of the pair), ectl kiss kf of engine g}; slot 0 R 2
//   {vport f, kf}; slot 7 -> kvs_attn c[st]; qkd_attn_fault_root: d = {pvfin ff, pvw_1 pf, pvw_0 pf, ahub hf, astk af
//   EN, ES, WN, WS}, c = the 4 chain ends; unit_fault = {E chains, W chains, d}.
// Every die bus is a registered relay line of a fixed, arbitrary depth (depth(): 0..3 stages per bus id, incl. the
// vport fork branch), so the bench proves the composition exact for any priced relay depths.  The checker compares
// unit_fault EVERY cycle against the reference: lane k = OR over its leaf paths p of src_p(t - L_p), L_p = relay
// stages + registered nodes on p (kv_static_die.afault_latency is the same formula on the die's priced stages).
// Phases: (1) exhaustive single faults: each of the 56 sources pulsed ONE cycle alone (the output pulse must arrive
// exactly L later, one cycle wide, on its own lane only); (2) ALL 1,540 source pairs, second pulse 0..3 cycles after
// the first; (3) 20,000 random cycles (sparse multi-source); (4) sticky: a held random set stays visible.
// MUT: 1 node WS slot 3 drops its K input (qkd_kv_cfault_node MUT 1); 2 root d skips its pin register (root MUT 2);
// 3 root drops chain WS (root MUT 1); 4 root swaps the PV pair lanes (root MUT 3); 5 slot 5 of WN takes its up input
// from slot 3 (slot 4 bypassed: wiring); 6 node ES slot 6 has 2 register stages (latency +1).  Every MUT must FAIL.
module tb_afd #(parameter integer D = 0) (input wire ck, input wire i, output wire o);
    generate if (D == 0) begin : g0
        assign o = i;
    end else if (D == 1) begin : g1
        reg r = 0;
        always @(posedge ck) r <= i;
        assign o = r;
    end else begin : gd
        reg [D-1:0] r = 0;
        always @(posedge ck) r <= {r[D-2:0], i};
        assign o = r[D-1];
    end endgenerate
endmodule

module tb_qkd_attn_fault_tree #(parameter integer MUT = 0);
    localparam integer NS = 56;                 // 32 kf + 16 vf + 8 direct
    localparam [31:0] ORDER = {4'd7, 4'd6, 4'd3, 4'd2, 4'd1, 4'd0, 4'd5, 4'd4};   // slot s -> group ORDER[4s +: 4]
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0;
    reg [NS-1:0] src = 0;
    wire [9:0] uf;
    // ---- bus relay depths (any fixed value; the die prices them) ----
    function automatic integer depth(input integer kind, input integer a, input integer b);
        depth = (kind * 5 + a * 3 + b * 7 + ((a * b) % 3)) % 4;
    endfunction
    // kind: 0 K leaf (st, g), 1 V trunk (st, k), 2 V fork (st, k), 3 chain hop (st, s), 4 chain end (st, 0), 5 direct (j, 0)
    function automatic integer ord(input integer s); ord = ORDER[4*s +: 4]; endfunction
    function automatic integer slot_of(input integer g);
        integer s; begin slot_of = 0; for (s = 0; s < 8; s = s + 1) if (ord(s) == g) slot_of = s; end
    endfunction
    // node register stages (MUT 6: ES slot 6 = 2)
    function automatic integer nst(input integer st, input integer s); nst = (MUT == 6 && st == 2 && s == 6) ? 2 : 1; endfunction
    // DESIGN edges from node (st, s) output to unit_fault (every node 1 stage; the reference never sees MUT 6)
    function automatic integer down(input integer st, input integer s);
        integer j; begin
            down = depth(4, st, 0) + 1;
            for (j = 7; j > s; j = j - 1) down = down + depth(3, st, j) + 1;
        end
    endfunction
    wire [3:0] cend;
    genvar st, s;
    generate for (st = 0; st < 4; st = st + 1) begin : gs
        wire [7:0] no;                              // node outputs by slot
        for (s = 0; s < 8; s = s + 1) begin : gn
            localparam integer G = ORDER[4*s +: 4];
            localparam integer K = G / 2;
            wire kf_r, vf_r, up;
            tb_afd #(depth(0, st, G)) u_k (ck, src[8*st + G], kf_r);
            if (G % 2 == 0) begin : vt tb_afd #(depth(1, st, K)) u_v (ck, src[32 + 4*st + K], vf_r); end
            else begin : vfk tb_afd #(depth(2, st, K)) u_v (ck, src[32 + 4*st + K], vf_r); end
            if (s == 0) begin : h
                qkd_kv_cfault_node #(.R(2), .STAGES(nst(st, s)), .MUT(0)) u (.ck(ck), .rst_n(rst_n), .fault_in({vf_r, kf_r}),
                                                                         .fault(no[s]));
            end else begin : l
                localparam integer SRC = (MUT == 5 && st == 1 && s == 5) ? 3 : s - 1;
                tb_afd #(depth(3, st, s)) u_c (ck, no[SRC], up);
                qkd_kv_cfault_node #(.R(3), .STAGES(nst(st, s)), .MUT((MUT == 1 && st == 0 && s == 3) ? 1 : 0)) u (
                    .ck(ck), .rst_n(rst_n), .fault_in({up, vf_r, kf_r}), .fault(no[s]));
            end
        end
        tb_afd #(depth(4, st, 0)) u_e (ck, no[7], cend[st]);
    end endgenerate
    wire [7:0] dr;
    genvar j;
    generate for (j = 0; j < 8; j = j + 1) begin : gd
        tb_afd #(depth(5, j, 0)) u_d (ck, src[48 + j], dr[j]);
    end endgenerate
    qkd_attn_fault_root #(.ND(8), .NC(4), .MUT((MUT == 2) ? 2 : (MUT == 3) ? 1 : (MUT == 4) ? 3 : 0)) u_root (
        .ck(ck), .rst_n(rst_n), .d(dr), .c(cend), .unit_fault(uf));
    // ---- reference: leaf paths (source, lane, latency) as kv_static_die.afault_latency ----
    localparam integer NP = 32 + 32 + 8;        // K paths, V paths (2 per vport), direct
    integer p_src[0:NP-1], p_lane[0:NP-1], p_lat[0:NP-1];
    integer i, k, g, j_;
    initial begin
        for (i = 0; i < 4; i = i + 1)
            for (g = 0; g < 8; g = g + 1) begin
                p_src[8*i + g] = 8*i + g; p_lane[8*i + g] = 8 + i / 2;
                p_lat[8*i + g] = depth(0, i, g) + 1 + down(i, slot_of(g));      // 1 = node edge (STAGES 1 at the leaf node)
            end
        for (i = 0; i < 4; i = i + 1)
            for (k = 0; k < 4; k = k + 1) begin
                p_src[32 + 8*i + 2*k] = 32 + 4*i + k; p_lane[32 + 8*i + 2*k] = 8 + i / 2;
                p_lat[32 + 8*i + 2*k] = depth(1, i, k) + 1 + down(i, slot_of(2*k));
                p_src[32 + 8*i + 2*k + 1] = 32 + 4*i + k; p_lane[32 + 8*i + 2*k + 1] = 8 + i / 2;
                p_lat[32 + 8*i + 2*k + 1] = depth(2, i, k) + 1 + down(i, slot_of(2*k + 1));
            end
        for (j_ = 0; j_ < 8; j_ = j_ + 1) begin p_src[64 + j_] = 48 + j_; p_lane[64 + j_] = j_; p_lat[64 + j_] = depth(5, j_, 0) + 1; end
    end
    localparam integer H = 128;
    reg [NS-1:0] hist [0:H-1];
    integer cyc = 0, errors = 0, checking = 0, maxlat = 0, checks = 0;
    reg [9:0] ref_;
    integer q;
    // at every negative edge: hist[cyc] = the sources of THIS cycle; unit_fault (registered outputs) must equal, per lane,
    // the OR over its paths p of the sources of cycle cyc - L_p
    always @(negedge ck) begin
        hist[cyc % H] = src;
        if (checking) begin
            ref_ = 0;
            for (q = 0; q < NP; q = q + 1) ref_[p_lane[q]] = ref_[p_lane[q]] | hist[(cyc - p_lat[q] + H) % H][p_src[q]];
            checks = checks + 1;
            if (uf !== ref_) begin
                if (errors < 10) $display("BAD cycle %0d: unit_fault %b expected %b", cyc, uf, ref_);
                errors = errors + 1;
            end
        end
        cyc = cyc + 1;
    end
    task tick; begin @(posedge ck); #1; end endtask
    task drain; begin src = 0; repeat (maxlat + 4) tick(); end endtask
    integer a, b, t, seen;
    initial begin
        #2;
        for (i = 0; i < NP; i = i + 1) if (p_lat[i] > maxlat) maxlat = p_lat[i];
        repeat (3) tick(); rst_n = 1; repeat (H) tick();          // relays flushed with 0, history filled with 0
        checking = 1;
        // (1) exhaustive single faults
        for (a = 0; a < NS; a = a + 1) begin src = 0; src[a] = 1; tick(); drain(); end
        $display("phase 1: %0d single faults, max path latency %0d edges", NS, maxlat);
        // (2) every pair
        for (a = 0; a < NS; a = a + 1)
            for (b = a + 1; b < NS; b = b + 1) begin
                t = (a * 7 + b) % 4;                     // the second fault t cycles after the first
                src = 0; src[a] = 1; if (t == 0) src[b] = 1;
                tick(); src = 0;
                if (t != 0) begin repeat (t - 1) tick(); src[b] = 1; tick(); end
                drain();
            end
        $display("phase 2: %0d pairs", NS * (NS - 1) / 2);
        // (3) random
        for (t = 0; t < 20000; t = t + 1) begin
            for (a = 0; a < NS; a = a + 1) src[a] = ($urandom % 64) == 0;
            tick();
        end
        drain();
        $display("phase 3: 20000 random cycles");
        // (4) sticky
        for (t = 0; t < 8; t = t + 1) begin
            for (a = 0; a < NS; a = a + 1) src[a] = ($urandom % 16) == 0;
            repeat (maxlat + 40) tick();
            drain();
        end
        $display("phase 4: 8 held fault sets");
        checking = 0;
        if (errors) begin $display("FAIL attn_fault_tree mut%0d errors%0d checks%0d", MUT, errors, checks); $fatal(1); end
        $display("PASS attn_fault_tree mut%0d: %0d exact cycle checks, 56 sources, 10 lanes, max latency %0d", MUT, checks, maxlat);
        $finish;
    end
    initial begin #50000000; $display("FAIL attn_fault_tree timeout"); $fatal(1); end
endmodule
