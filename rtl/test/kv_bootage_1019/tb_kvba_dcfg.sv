`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19: bench of qkd_kv_die_cfg_a (AGES=1) against the closed qkd_kv_die_cfg (CAP=1).
//   1  the closed image (32 ECTL + NRST reset + capability + seal) into the reference, the same words + 19 age words before
//      the seal into the successor: ECTL / reset / capability / sealed / fault outputs identical after both seals; every age
//      output reads 0 until the seal and exactly its word after it (attention {D_RL, D_QK, F_DLY, PV_LEAD}, pairs, 16 V ports)
//   2  negative: non-zero padding in an age word, an age word out of order, a write after the seal -> fault, never sealed
// Prints "KVBA_DCFG PASS mut=.. checks=N" or "KVBA_DCFG FAIL ...".
module tb_kvba_dcfg;
    parameter integer MUT = 0, NRST = 43, SEED = 1;
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    localparam integer A0 = 32 + NRST + 1;
    reg ck = 0, por_n = 0;
    always #1 ck = ~ck;
    reg awe = 0, bwe = 0; reg [7:0] aad = 0, bad_ = 0; reg [63:0] ad = 0, bd = 0;
    wire [159:0] a_ea, a_eb, a_ec, b_ea, b_eb, b_ec; wire [NRST*8-1:0] a_rd, b_rd; wire a_cap, b_cap, a_s, b_s, a_f, b_f;
    wire [31:0] b_at; wire [15:0] b_pv; wire [255:0] b_vp;
    qkd_kv_die_cfg #(.NRST(NRST), .CAP(1), .MUT(0)) u_ref (.ck(ck), .por_n(por_n), .cfg_we(awe), .cfg_addr(aad), .cfg_data(ad),
        .ectl_a_cfg(a_ea), .ectl_b_cfg(a_eb), .ectl_c_cfg(a_ec), .rst_dly(a_rd), .fused_program_capability(a_cap), .sealed(a_s), .fault(a_f));
    qkd_kv_die_cfg_a #(.NRST(NRST), .CAP(1), .AGES(1), .MUT(MUT)) u_dut (.ck(ck), .por_n(por_n), .cfg_we(bwe), .cfg_addr(bad_),
        .cfg_data(bd), .ectl_a_cfg(b_ea), .ectl_b_cfg(b_eb), .ectl_c_cfg(b_ec), .rst_dly(b_rd), .fused_program_capability(b_cap),
        .age_attn(b_at), .age_pv(b_pv), .age_vport(b_vp), .sealed(b_s), .fault(b_f));
    reg [63:0] img [0:A0 + 19];
    reg [31:0] w_at; reg [15:0] w_pv; reg [255:0] w_vp;
    integer i, seed, checks = 0, errs = 0, neg_ok = 0, n;
    task wr_b(input [7:0] a, input [63:0] d); begin bwe = 1; bad_ = a; bd = d; @(negedge ck); bwe = 0; end endtask
    task wr_a(input [7:0] a, input [63:0] d); begin awe = 1; aad = a; ad = d; @(negedge ck); awe = 0; end endtask
    task err(input [8*48-1:0] msg); begin errs = errs + 1; if (errs < 8) $display("ERROR %0s", msg); end endtask
    task por; begin por_n = 0; repeat (4) @(negedge ck); por_n = 1; repeat (4) @(negedge ck); end endtask
    initial begin
        seed = SEED;
        for (i = 0; i < 32; i = i + 1) img[i] = {49'd0, 15'($random(seed))};
        for (i = 0; i < NRST; i = i + 1) img[32 + i] = {56'd0, 8'($random(seed))};
        img[32 + NRST] = 64'd1;
        w_at = $random(seed); w_pv = $random(seed);
        for (i = 0; i < 16; i = i + 1) w_vp[16*i +: 16] = $random(seed);
        // ---- 1: positive
        por;
        for (i = 0; i < A0; i = i + 1) wr_a(8'(i), img[i]);
        wr_a(8'(A0), SEAL);
        for (i = 0; i < A0; i = i + 1) wr_b(8'(i), img[i]);
        wr_b(8'(A0), {32'd0, w_at});
        for (i = 0; i < 2; i = i + 1) wr_b(8'(A0 + 1 + i), {56'd0, w_pv[8*i +: 8]});
        for (i = 0; i < 16; i = i + 1) begin
            wr_b(8'(A0 + 3 + i), {48'd0, w_vp[16*i +: 16]});
            checks = checks + 1;
            if ({b_at, b_pv, b_vp} !== 0) err("age outputs visible before the seal");
        end
        wr_b(8'(A0 + 19), SEAL);
        repeat (4) @(negedge ck);
        checks = checks + 1;
        if ({a_ea, a_eb, a_ec, a_rd, a_cap, a_s, a_f} !== {b_ea, b_eb, b_ec, b_rd, b_cap, b_s, b_f}) err("closed outputs differ");
        if (!b_s || b_f) err("successor not sealed / faulted");
        if (b_at !== w_at || b_pv !== w_pv || b_vp !== w_vp) err("age outputs != image words");
        // ---- 2: negatives (each: fault, never sealed)
        for (n = 0; n < 3; n = n + 1) begin
            por;
            for (i = 0; i < A0; i = i + 1) wr_b(8'(i), img[i]);
            if (n == 0) wr_b(8'(A0), {31'd1, 1'b0, w_at});                     // attention word padding bit 32
            else if (n == 1) wr_b(8'(A0 + 1), {56'd0, w_pv[7:0]});             // pair word before the attention word
            else begin
                wr_b(8'(A0), {32'd0, w_at});
                for (i = 0; i < 2; i = i + 1) wr_b(8'(A0 + 1 + i), {56'd0, w_pv[8*i +: 8]});
                for (i = 0; i < 16; i = i + 1) wr_b(8'(A0 + 3 + i), {48'd0, w_vp[16*i +: 16]});
                wr_b(8'(A0 + 19), SEAL);
                wr_b(8'(A0 + 3), 64'd5);                                       // write after the seal
            end
            repeat (3) @(negedge ck);
            checks = checks + 1;
            if (b_f && (n == 2 || !b_s)) neg_ok = neg_ok + 1; else $display("NEG %0d not caught (fault %b sealed %b)", n, b_f, b_s);
        end
        if (errs == 0 && neg_ok == 3)
            $display("KVBA_DCFG PASS mut=%0d checks=%0d", MUT, checks);
        else
            $display("KVBA_DCFG FAIL mut=%0d checks=%0d errors=%0d negatives=%0d/3", MUT, checks, errs, neg_ok);
        $finish;
    end
endmodule
