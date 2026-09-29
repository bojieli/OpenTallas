`timescale 1ns/1ps
// Exhaustive check of the local partition's K steering against the monolithic arbiter's: every value of the
// 17 sector-address bits [18:2] that reach pc_of (with random bits above, AW = 30) is presented to both; the
// monolithic arbiter steers combinationally, the local partition two edges later; the PC each request reaches
// (and its payload) must match, for the local and the pipelined local partitions.  Both run with every PHY ready and no B traffic.
module tb_chip_v41x_karb_local_hash;
    localparam integer NPC = 32, AW = 30, TAGW = 16, N = 1 << 17;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, k_v = 0;
    reg [AW-1:0] k_addr = 0;
    reg [TAGW-1:0] k_tag = 0;
    wire [NPC-1:0] hm_v, hl_v; wire [NPC*AW-1:0] hm_addr, hl_addr; wire [NPC*(TAGW+1)-1:0] hm_tag, hl_tag;
    wire km_rdy, kl_rdy, kp_rdy;
    wire [NPC-1:0] hp_v, v5, v6, v7, v8, v9; wire [NPC*AW-1:0] hp_addr; wire [NPC*(TAGW+1)-1:0] hp_tag;
    wire [NPC*4-1:0] lp2, lp3; wire [NPC*256-1:0] wp2, wp3; wire [NPC*32-1:0] sp1; wire [NPC*TAGW-1:0] tp;
    wire [TAGW-1:0] ktp; wire [3:0] kbp; wire [255:0] kdp; wire xp2, xp3; wire [31:0] d3, d4, d5;
    wire [NPC-1:0] u0, u1, u2, u3, u4, u5, u6, u7, u8, u9;
    wire [NPC*4-1:0] l0, l1, l2, l3; wire [NPC*256-1:0] w0, w1, w2, w3; wire [NPC*32-1:0] s0, s1;
    wire [NPC*TAGW-1:0] t0, t1; wire [TAGW-1:0] kt0, kt1; wire [3:0] kb0, kb1; wire [255:0] kd0, kd1;
    wire x0, x1, x2, x3; wire [31:0] c0, c1, c2, c3, c4, c5;
    ot_chip_v41x_hbm_karb #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) m (
        .clk(clk), .rst_n(rst_n), .b_v({NPC{1'b0}}), .b_rdy(u0), .b_addr({NPC*AW{1'b0}}), .b_len({NPC*4{1'b0}}), .b_tag({NPC*TAGW{1'b0}}), .b_we({NPC{1'b0}}),
        .b_wdata({NPC*256{1'b0}}), .b_wstrb({NPC*32{1'b0}}), .b_wr_done(u1), .b_rsp_v(u2), .b_rsp_rdy({NPC{1'b1}}), .b_rsp_tag(t0), .b_rsp_beat(l0),
        .b_rsp_data(w0), .k_v(k_v), .k_rdy(km_rdy), .k_addr(k_addr), .k_len(4'd1), .k_tag(k_tag), .k_we(1'b0),
        .k_wdata(256'd0), .k_wstrb(32'd0), .k_wr_done(x0), .k_rsp_v(x1), .k_rsp_rdy(1'b1), .k_rsp_tag(kt0),
        .k_rsp_beat(kb0), .k_rsp_data(kd0), .h_v(hm_v), .h_rdy({NPC{1'b1}}), .h_addr(hm_addr), .h_len(l1), .h_tag(hm_tag),
        .h_we(u3), .h_wdata(w1), .h_wstrb(s0), .h_wr_done({NPC{1'b0}}), .r_v({NPC{1'b0}}), .r_rdy(u4), .r_tag({NPC*(TAGW+1){1'b0}}), .r_beat({NPC*4{1'b0}}),
        .r_data({NPC*256{1'b0}}), .k_grants(c0), .b_grants(c1), .contended(c2));
    ot_chip_v41x_hbm_karb_local #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) l (
        .clk(clk), .rst_n(rst_n), .b_v({NPC{1'b0}}), .b_rdy(u5), .b_addr({NPC*AW{1'b0}}), .b_len({NPC*4{1'b0}}), .b_tag({NPC*TAGW{1'b0}}), .b_we({NPC{1'b0}}),
        .b_wdata({NPC*256{1'b0}}), .b_wstrb({NPC*32{1'b0}}), .b_wr_done(u6), .b_rsp_v(u7), .b_rsp_rdy({NPC{1'b1}}), .b_rsp_tag(t1), .b_rsp_beat(l2),
        .b_rsp_data(w2), .k_v(k_v), .k_rdy(kl_rdy), .k_addr(k_addr), .k_len(4'd1), .k_tag(k_tag), .k_we(1'b0),
        .k_wdata(256'd0), .k_wstrb(32'd0), .k_wr_done(x2), .k_rsp_v(x3), .k_rsp_rdy(1'b1), .k_rsp_tag(kt1),
        .k_rsp_beat(kb1), .k_rsp_data(kd1), .h_v(hl_v), .h_rdy({NPC{1'b1}}), .h_addr(hl_addr), .h_len(l3), .h_tag(hl_tag),
        .h_we(u8), .h_wdata(w3), .h_wstrb(s1), .h_wr_done({NPC{1'b0}}), .r_v({NPC{1'b0}}), .r_rdy(u9), .r_tag({NPC*(TAGW+1){1'b0}}), .r_beat({NPC*4{1'b0}}),
        .r_data({NPC*256{1'b0}}), .k_grants(c3), .b_grants(c4), .contended(c5));
    ot_chip_v41x_hbm_karb_pipe #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) pp (
        .clk(clk), .rst_n(rst_n), .b_v({NPC{1'b0}}), .b_rdy(v5), .b_addr({NPC*AW{1'b0}}), .b_len({NPC*4{1'b0}}), .b_tag({NPC*TAGW{1'b0}}), .b_we({NPC{1'b0}}),
        .b_wdata({NPC*256{1'b0}}), .b_wstrb({NPC*32{1'b0}}), .b_wr_done(v6), .b_rsp_v(v7), .b_rsp_rdy({NPC{1'b1}}), .b_rsp_tag(tp), .b_rsp_beat(lp2),
        .b_rsp_data(wp2), .k_v(k_v), .k_rdy(kp_rdy), .k_addr(k_addr), .k_len(4'd1), .k_tag(k_tag), .k_we(1'b0),
        .k_wdata(256'd0), .k_wstrb(32'd0), .k_wr_done(xp2), .k_rsp_v(xp3), .k_rsp_rdy(1'b1), .k_rsp_tag(ktp),
        .k_rsp_beat(kbp), .k_rsp_data(kdp), .h_v(hp_v), .h_rdy({NPC{1'b1}}), .h_addr(hp_addr), .h_len(lp3), .h_tag(hp_tag),
        .h_we(v8), .h_wdata(wp3), .h_wstrb(sp1), .h_wr_done({NPC{1'b0}}), .r_v({NPC{1'b0}}), .r_rdy(v9), .r_tag({NPC*(TAGW+1){1'b0}}), .r_beat({NPC*4{1'b0}}),
        .r_data({NPC*256{1'b0}}), .k_grants(d3), .b_grants(d4), .contended(d5));
    reg [4:0] want [0:N-1];
    reg [AW-1:0] sent [0:N-1];
    function automatic [TAGW-1:0] sent_tag(input [16:0] i); sent_tag = i[15:0]; endfunction
    integer i, p, got = 0, bad = 0, multi = 0, stall = 0, pgot = 0;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            k_v = 1; k_tag = i[15:0]; k_addr = {$urandom} << 19 | (i << 2) | ($urandom & 3);
            #0.1;
            if ($countones(hm_v) != 1 || !km_rdy) bad = bad + 1;
            for (p = 0; p < NPC; p = p + 1) if (hm_v[p]) want[i] = p;
            sent[i] = k_addr;
            if (!kl_rdy || !kp_rdy) stall = stall + 1;
        end
        @(negedge clk); k_v = 0;
        repeat (200) @(posedge clk);
        $display("KARB_HASH n=%0d got=%0d pipe_got=%0d bad=%0d multi=%0d ingress_stalls=%0d", N, got, pgot, bad, multi, stall);
        if (got == N && pgot == N && bad == 0 && multi == 0 && stall == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
    // the monolithic arbiter answers within the cycle, so the local ingress sees one request per cycle
    always @(posedge clk) if (rst_n) begin
        if ($countones(hl_v) > 1) multi = multi + 1;
        for (p = 0; p < NPC; p = p + 1) if (hl_v[p]) begin
            if (hl_tag[p*(TAGW+1) + TAGW] !== 1'b1 || want[got] !== p || hl_addr[p*AW +: AW] !== sent[got]) bad = bad + 1;
            got = got + 1;
        end
        if ($countones(hp_v) > 1) multi = multi + 1;
        for (p = 0; p < NPC; p = p + 1) if (hp_v[p]) begin
            if (hp_tag[p*(TAGW+1) + TAGW] !== 1'b1 || want[hp_addr[p*AW + 2 +: 17]] !== p ||
                hp_addr[p*AW +: AW] !== sent[hp_addr[p*AW + 2 +: 17]] ||
                hp_tag[p*(TAGW+1) +: TAGW] !== sent_tag(hp_addr[p*AW + 2 +: 17])) bad = bad + 1;
            pgot = pgot + 1;
        end
    end
endmodule
