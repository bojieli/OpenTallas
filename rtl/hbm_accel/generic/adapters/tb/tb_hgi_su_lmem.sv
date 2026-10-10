`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// hgi-1010/d (2026-10-10): bench of the LANE-LOCAL SU local memory ot_hgi_su_lmem (one bank a lane, a few-way read
// network) against a behavioural reference per group.  Phases:
//   1 stage every staged group (A, B, C, D; A + C together = the c_pair copy) with 8-word writes, random alignment
//     and masks;
//   2 lane reads of the four port groups in every pattern the dense relayout produces: identity / rotated by a multiple
//     of M (contiguous vectors), pair-swapped (c_pair), half (BF16 pairs), lane 0 alone at any address (scalar ops),
//     with the bank row wrapping -> every rd_q exact, no cfault;
//   3 lane element writes into O (identity / rotated) and reducer writes into R -> read back by 8-word drain reads;
//   4 STREAM landing into GS one word an edge, read back by port A with a_str;
//   5 negatives after a reset: a used-port read outside the lane's candidates -> cfault; the same on an unused port ->
//     none; two lanes on one bank, different rows -> cfault; a gather read -> cfault; two lane writes on one bank,
//     different rows -> cfault.
// +define+MUT_XBAR: the network takes the neighbouring bank -> phase 2 must FAIL.  Prints HGI_SU_LMEM PASS / FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_su_lmem;
    localparam integer N = 16, M = 8, LWB = 14, AW = 24, NR = N / 8, LG1 = 13, LG2 = 13, LG3 = 12, LGO = 13, RWB = 6;
    localparam integer SLB = 12;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [3:0] use_p = 4'hF;
    reg [N-1:0] vi_re = 0; reg [N*AW-1:0] vi_addr = 0; wire [N*32-1:0] vi_q;
    reg [4*N-1:0] rd_re = 0; reg [4*N*AW-1:0] rd_addr = 0; reg [8*N-1:0] rd_src = 0; wire [4*N*32-1:0] rd_q;
    reg [N-1:0] vm_we = 0; reg [N*AW-1:0] vm_waddr = 0; reg [N*32-1:0] vm_wdata = 0;
    reg [NR-1:0] res_we = 0; reg [NR*AW-1:0] res_addr = 0; reg [NR*32-1:0] res_data = 0;
    reg sl_v = 0; reg [LWB-1:0] sl_addr = 0; reg [31:0] sl_data = 0; wire sl_pend; reg a_str = 0;
    reg sw_v = 0; reg [3:0] sw_g = 0; reg [LWB-1:0] sw_addr = 0; reg [7:0] sw_mask = 8'hFF; reg [255:0] sw_data = 0;
    reg sr_v = 0; reg [1:0] sr_g = 0; reg [LWB-1:0] sr_addr = 0; wire [255:0] sr_data;
    wire cfault;
`ifdef MUT_XBAR
    localparam integer MX = 1;
`else
    localparam integer MX = 0;
`endif
    ot_hgi_su_lmem #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(1), .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB),
        .SLB(SLB), .MUT_XBAR(MX)) dut (
        .clk(clk), .rst_n(rst_n), .use_p(use_p), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re),
        .rd_addr(rd_addr), .rd_src(rd_src), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sl_pend(sl_pend), .a_str(a_str), .sw_v(sw_v), .sw_g(sw_g), .sw_addr(sw_addr), .sw_mask(sw_mask),
        .sw_data(sw_data), .sr_v(sr_v), .sr_g(sr_g), .sr_addr(sr_addr), .sr_data(sr_data), .cfault(cfault));
    reg [31:0] ref0 [0:(1<<LWB)-1]; reg [31:0] ref1 [0:(1<<LG1)-1]; reg [31:0] ref2 [0:(1<<LG2)-1];
    reg [31:0] ref3 [0:(1<<LG3)-1]; reg [31:0] refo [0:(1<<LGO)-1]; reg [31:0] refr [0:(1<<RWB)-1];
    reg [31:0] refs [0:(1<<SLB)-1];
    function automatic integer gsize(input integer g);
        gsize = (g == 0) ? (1 << LWB) : (g == 1) ? (1 << LG1) : (g == 2) ? (1 << LG2) : (1 << LG3);
    endfunction
    function automatic [31:0] rget(input integer g, input integer a);
        case (g) 0: rget = ref0[a]; 1: rget = ref1[a]; 2: rget = ref2[a]; 3: rget = ref3[a]; 4: rget = refo[a];
                 5: rget = refr[a]; default: rget = refs[a]; endcase
    endfunction
    task automatic rput(input integer g, input integer a, input [31:0] v);
        case (g) 0: ref0[a] = v; 1: ref1[a] = v; 2: ref2[a] = v; 3: ref3[a] = v; 4: refo[a] = v; 5: refr[a] = v;
                 default: refs[a] = v; endcase
    endtask
    integer errors = 0, reads = 0, g, s, l, k, t, base, a, pat, rot;
    reg [31:0] v;
    // one cycle of lane reads on every port group in pattern pat; check the next edge
    task automatic lane_cycle(input integer pt, input integer gstream);
        integer gg, ll, ad, rr0;
        begin
            for (gg = 0; gg < 4; gg = gg + 1) begin
                if (gstream && gg != 0) continue;
                base = N * ($urandom % (((gstream ? (1 << SLB) : gsize(gg)) / N) - 4));
                rot = M * ($urandom % (N / M));
                for (ll = 0; ll < N; ll = ll + 1) begin
                    case (pt)
                        0: ad = base + rot + ll;                     // contiguous vector, rotated by a multiple of M
                        1: ad = (base + rot + ll) ^ 1;               // c_pair partner
                        2: ad = base + (M / 2) * ($urandom % 2) + (ll >> 1);   // BF16 pairs
                        default: ad = (ll == 0) ? $urandom % (gstream ? (1 << SLB) : gsize(gg)) : 0;   // scalar lane 0
                    endcase
                    rd_addr[(4*ll + gg)*AW +: AW] = ad;
                    rd_re[4*ll + gg] = (pt != 3) || (ll == 0);
                end
            end
            @(posedge clk); #0.1;
            for (gg = 0; gg < 4; gg = gg + 1) begin
                if (gstream && gg != 0) continue;
                for (ll = 0; ll < N; ll = ll + 1) if (rd_re[4*ll + gg]) begin
                    reads = reads + 1;
                    rr0 = gstream ? rget(6, rd_addr[(4*ll)*AW +: AW] % (1 << SLB)) : rget(gg, rd_addr[(4*ll + gg)*AW +: AW]);
                    if (rd_q[(4*ll + gg)*32 +: 32] !== rr0) begin
                        if (errors < 10) $display("ERR read p%0d g%0d lane %0d addr %0d got %h exp %h", pt, gg, ll,
                            rd_addr[(4*ll + gg)*AW +: AW], rd_q[(4*ll + gg)*32 +: 32], rr0);
                        errors = errors + 1;
                    end
                end
            end
            rd_re = 0;
        end
    endtask
    task automatic sr_check(input integer gg, input integer ad);
        integer jj;
        begin
            sr_v = 1; sr_g = (gg == 4) ? 2'd1 : 2'd2; sr_addr = ad; @(posedge clk); #0.1; sr_v = 0;
            for (jj = 0; jj < 8; jj = jj + 1)
                if (sr_data[32*jj +: 32] !== rget(gg, (ad + jj) % ((gg == 4) ? (1 << LGO) : (1 << RWB)))) begin
                    if (errors < 10) $display("ERR sr g%0d addr %0d w%0d got %h exp %h", gg, ad, jj, sr_data[32*jj +: 32],
                                              rget(gg, ad + jj));
                    errors = errors + 1;
                end
        end
    endtask
    initial begin
        repeat (4) @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
        // ---- phase 1: stage A..D (G0 + G2 together for the first part: the c_pair copy)
        for (g = 0; g < 4; g = g + 1)
            for (s = 0; s < gsize(g) / 8; s = s + 1) begin
                for (k = 0; k < 8; k = k + 1) begin v = $urandom; sw_data[32*k +: 32] = v; rput(g, s*8 + k, v);
                    if (g == 0 && s*8 + k < gsize(2)) rput(2, s*8 + k, v); end
                sw_v = 1; sw_addr = s * 8; sw_mask = 8'hFF; sw_g = (g == 0) ? 4'b0101 : (4'b0001 << g);
                @(posedge clk); #0.1;
            end
        for (t = 0; t < 64; t = t + 1) begin                  // unaligned masked writes
            g = t % 4; a = $urandom % (gsize(g) - 16); sw_v = 1; sw_g = 4'b0001 << g; sw_addr = a; sw_mask = $urandom;
            for (k = 0; k < 8; k = k + 1) begin v = $urandom; sw_data[32*k +: 32] = v; if (sw_mask[k]) rput(g, a + k, v); end
            @(posedge clk); #0.1;
        end
        sw_v = 0; sw_mask = 8'hFF; @(posedge clk); #0.1;
        // ---- phase 2: lane reads, every pattern
        for (t = 0; t < 400; t = t + 1) lane_cycle(t % 4, 0);
        if (cfault) begin $display("ERR cfault on legal patterns"); errors = errors + 1; end
        // ---- phase 3: element writes into O (contiguous, rotated) and reducer writes into R
        for (t = 0; t < 60; t = t + 1) begin
            base = N * ($urandom % ((1 << LGO) / N - 2)); rot = M * ($urandom % (N / M)); vm_we = {N{1'b1}};
            for (l = 0; l < N; l = l + 1) begin v = $urandom; vm_waddr[l*AW +: AW] = base + rot + l; vm_wdata[32*l +: 32] = v;
                rput(4, base + rot + l, v); end
            a = $urandom % ((1 << RWB) - 8); res_we = {NR{1'b1}};
            for (l = 0; l < NR; l = l + 1) begin v = $urandom; res_addr[l*AW +: AW] = a + l; res_data[32*l +: 32] = v;
                rput(5, a + l, v); end
            @(posedge clk); #0.1; vm_we = 0; res_we = 0;
            sr_check(4, base + rot + ($urandom % 9)); sr_check(4, base + rot + 8); sr_check(5, a);
        end
        // ---- phase 4: STREAM landing (GS) one word an edge, read back by port A with a_str
        for (t = 0; t < (1 << SLB); t = t + 1) begin
            sl_v = 1; sl_addr = ((1 << LWB) - (1 << SLB)) + t; v = $urandom; sl_data = v; refs[t] = v;
            @(posedge clk); #0.1;
        end
        sl_v = 0; a_str = 1; @(posedge clk); #0.1;
        for (t = 0; t < 100; t = t + 1) lane_cycle((t % 2) ? 3 : 0, 1);
        a_str = 0;
        if (cfault) begin $display("ERR cfault after legal traffic"); errors = errors + 1; end
        $display("summary: %0d lane reads exact, phases 1-4", reads);
        // ---- phase 5: negatives
        begin : neg
            integer f1, f2, f3, f4, f5;
            rst_n = 0; @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
            use_p = 4'b0010; rd_re = 0; rd_re[4*3 + 1] = 1; rd_addr[(4*3 + 1)*AW +: AW] = 6;      // lane 3 -> bank 6 (not a candidate)
            @(posedge clk); #0.1 rd_re = 0; repeat (3) @(posedge clk); #0.1 f1 = cfault;
            rst_n = 0; @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
            use_p = 4'b0001; rd_re[4*3 + 1] = 1; @(posedge clk); #0.1 rd_re = 0; repeat (3) @(posedge clk); #0.1 f2 = cfault;
            rst_n = 0; @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
            use_p = 4'b0001; rd_re[4*0] = 1; rd_re[4*1] = 1; rd_addr[0 +: AW] = 9; rd_addr[(4*1)*AW +: AW] = N + 9; // lane 0 bank 9 row 0, lane 1 bank 9 row 1
            @(posedge clk); #0.1 rd_re = 0; repeat (3) @(posedge clk); #0.1 f3 = cfault;
            rst_n = 0; @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
            vi_re = 1; @(posedge clk); #0.1 vi_re = 0; repeat (3) @(posedge clk); #0.1 f4 = cfault;
            rst_n = 0; @(posedge clk); #0.1 rst_n = 1; @(posedge clk); #0.1;
            vm_we = 2'b11; vm_waddr[0 +: AW] = 1; vm_waddr[AW +: AW] = N + 1;                    // lane 1 -> bank 1, another row
            @(posedge clk); #0.1 vm_we = 0; repeat (3) @(posedge clk); #0.1 f5 = cfault;
            $display("negatives: outside candidates %0d (exp 1), unused port %0d (exp 0), bank row clash %0d (exp 1), gather %0d (exp 1), write clash %0d (exp 1)",
                     f1, f2, f3, f4, f5);
            if (f1 !== 1 || f2 !== 0 || f3 !== 1 || f4 !== 1 || f5 !== 1) errors = errors + 1;
        end
        if (errors == 0) $display("HGI_SU_LMEM PASS"); else $display("HGI_SU_LMEM FAIL (%0d errors)", errors);
        $finish;
    end
endmodule
