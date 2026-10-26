`timescale 1ns/1ps
// KV-PLAN 2026-10-17: lockstep check of the distributed es chain roots (qkd_kv_es_fan_root2 + two qkd_kv_es_fan_half)
// against the unchanged single root qkd_kv_es_fan_root (four qkd_kv_es_fan_stack): every stack chain word of the half roots equals the single
// root's word ONE edge later, every edge, for random writer / expected / token-start / boot traffic (MUT_H 1: caught).
module tb_qkd_kv_ctl_half_root;
    parameter integer MUT_H = 0;
    parameter integer N = 20000;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [4*288-1:0] es; reg [19:0] dpc, epc; reg [1:0] dst, gen, est, egen; reg [58:0] id, eid; reg [28:0] ea;
    reg [3:0] ev; reg ss; reg [17:0] tok; reg [15:0] ep; reg cw; reg [7:0] ca; reg [63:0] cd;
    wire [778:0] o0, o1, o2, o3; wire of, nf;
    wire [782:0] h; wire [778:0] sw, se, nw, ne;
    qkd_kv_es_fan_root u_old (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(id), .generation(gen),
        .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(eid), .expected_generation(egen),
        .expected_address(ea), .emb_start(ss), .emb_token(tok), .emb_epoch(ep), .cfg_we(cw), .cfg_addr(ca), .cfg_data(cd),
        .d0(o0), .d1(o1), .d2(o2), .d3(o3), .fault(of));
    qkd_kv_es_fan_root2 u_root (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(id), .generation(gen),
        .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(eid), .expected_generation(egen),
        .expected_address(ea), .emb_start(ss), .emb_token(tok), .emb_epoch(ep), .cfg_we(cw), .cfg_addr(ca), .cfg_data(cd),
        .h(h), .fault(nf));
    qkd_kv_es_fan_stack #(.MUT(MUT_H)) u_ws (.ck(ck), .rst_n(rst_n), .stack(2'd0), .h(h), .d(sw));
    qkd_kv_es_fan_stack #(.MUT(MUT_H)) u_wn (.ck(ck), .rst_n(rst_n), .stack(2'd1), .h(h), .d(nw));
    qkd_kv_es_fan_stack #(.MUT(MUT_H)) u_es (.ck(ck), .rst_n(rst_n), .stack(2'd2), .h(h), .d(se));
    qkd_kv_es_fan_stack #(.MUT(MUT_H)) u_en (.ck(ck), .rst_n(rst_n), .stack(2'd3), .h(h), .d(ne));
    reg [778:0] q0, q1, q2, q3; reg qf;
    always @(posedge ck) begin q0 <= o0; q1 <= o1; q2 <= o2; q3 <= o3; end
    integer t, bad, nv, k;
    function [63:0] r64; input integer x; begin r64 = {$random, $random}; end endfunction
    initial begin
        bad = 0; nv = 0;
        es = 0; dpc = 0; epc = 0; dst = 0; gen = 0; est = 0; egen = 0; id = 0; eid = 0; ea = 0; ev = 0; ss = 0; tok = 0;
        ep = 0; cw = 0; ca = 0; cd = 0;
        repeat (4) @(negedge ck);
        rst_n = 1;
        for (t = 0; t < N; t = t + 1) begin
            @(negedge ck);
            for (k = 0; k < 18; k = k + 1) es[64*k +: 64] = r64(0);
            // sparse writer events: valid bits mostly low, events >= 2 edges apart most of the time
            es[0] = ($random % 5 == 0); es[288] = ($random % 5 == 0); es[576] = ($random % 5 == 0); es[864] = ($random % 5 == 0);
            dpc = $random; epc = $random; dst = $random; est = $random; gen = $random; egen = $random;
            id = {$random, $random}; eid = {$random, $random}; ea = $random;
            ev = ($random % 4 == 0) ? $random : 4'd0;
            ss = ($random % 7 == 0); tok = $random; ep = $random;
            cw = ($random % 6 == 0); ca = $random; cd = r64(0);
            if ($random % 3 != 0) cd[63:18] = 0;          // mostly well-formed boot words (target 0)
            if ($random % 9 == 0) cd[63:62] = 2'd1;
            if (t > 2) begin
                if (sw !== q0 || nw !== q1 || se !== q2 || ne !== q3) begin
                    bad = bad + 1;
                    if (bad < 4) $display("MISMATCH t=%0d S %0d%0d N %0d%0d", t, sw === q0, se === q2, nw === q1, ne === q3);
                end
                if (q0[1:0] != 0 || q1[1:0] != 0 || q2[1:0] != 0 || q3[1:0] != 0) nv = nv + 1;
                if (nf !== of) begin bad = bad + 1; if (bad < 4) $display("FAULT MISMATCH t=%0d", t); end
            end
        end
        if (bad == 0) $display("PASS lockstep %0d edges (%0d with a chain write valid), MUT_H=%0d", N, nv, MUT_H);
        else $display("FAIL %0d mismatching edges, MUT_H=%0d", bad, MUT_H);
        $finish;
    end
endmodule
