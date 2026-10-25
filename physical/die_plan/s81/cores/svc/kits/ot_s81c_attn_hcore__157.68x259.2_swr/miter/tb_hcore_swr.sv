`timescale 1ns/1ps
// PATH-S81/HCORE 10-25: exact cycle-by-cycle miter of ot_s81c_attn_hcore built with -DOT_F12_SWAP_REP (replicated adder
// swap selects) against the unchanged EH physical source (8775dd9be: hcore 7a00f9ed, tile_s 780e8010; modules renamed
// *_ref), both with -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RSTE.  Same random pin stimulus to both; ov, oy, oflt compared on
// EVERY cycle (no valid masking).  Activity counters prove the datapath ran (ov count, distinct non-zero oy).
module tb;
    reg clk = 0, rst_n = 0;
    reg [7:0] gid;
    reg ld_v = 0, ld_mode = 0, ld_w2v = 0, iv = 0;
    reg [2:0] ld_bank = 0, ibank = 0;
    reg [7:0] ld_grp = 0;
    reg [511:0] ld_w = 0;
    reg [63:0] ld_wp = 0;
    reg [575:0] ib = 0;
    wire ov, ovr, of, ofr;
    wire [31:0] oy, oyr;
    ot_s81c_attn_hcore     dut (.clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
        .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(of));
    ot_s81c_attn_hcore_ref ref0 (.clk(clk), .rst_n(rst_n), .gid(gid), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
        .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ovr), .oy(oyr), .oflt(ofr));
    reg [63:0] st;
    function automatic [63:0] xs(input [63:0] x);
        reg [63:0] t; begin t = x ^ (x << 13); t = t ^ (t >> 7); xs = t ^ (t << 17); end
    endfunction
    integer cyc = 0, ncyc = 40000, seed = 1, mis = 0, n_ov = 0, n_nz = 0, n_chg = 0, n_flt = 0, k;
    reg [31:0] last_oy = 0;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 40000;
        st = 64'h2545f4914f6cdd1d ^ {32'd0, seed[31:0]} ^ ({32'd0, seed[31:0]} << 37);
        gid = 8'd1 + seed[2:0];
    end
    always #1 clk = ~clk;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1;
        st = xs(st);
        ld_v <= (st[3:0] < 4'd6);
        ld_mode <= st[4] & st[5] & st[6];
        ld_bank <= (st[9:7] > 3'd4) ? st[8:7] : st[9:7];      // banks 0..4 mostly (5..7 too, rarely)
        ld_grp <= st[10] ? gid : {4'd0, st[14:11]};
        ld_w2v <= st[15];
        iv <= st[16] | st[17];
        ibank <= (st[20:18] > 3'd4) ? {1'b0, st[19:18]} : st[20:18];
        for (k = 0; k < 8; k = k + 1) begin
            st = xs(st); ld_w[k*64 +: 64] <= st;
        end
        st = xs(st); ld_wp <= st;
        for (k = 0; k < 9; k = k + 1) begin
            st = xs(st); ib[k*64 +: 64] <= st;
        end
        for (k = 0; k < 32; k = k + 1) begin                 // sk_b lanes: pad (bit 17) and fault (bit 16) rare
            st = xs(st);
            ib[k*18 + 16] <= (st[2:0] == 3'd0) & st[3];
            ib[k*18 + 17] <= (st[6:4] == 3'd0);
        end
        if (ov) n_ov <= n_ov + 1;
        if (of) n_flt <= n_flt + 1;
        if (oy != 32'd0) n_nz <= n_nz + 1;
        if (oy != last_oy) n_chg <= n_chg + 1;
        last_oy <= oy;
        if ({ov, oy, of} !== {ovr, oyr, ofr}) begin
            if (mis < 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h/%h oflt %b/%b", cyc, ov, ovr, oy, oyr, of, ofr);
            mis <= mis + 1;
        end
        if (cyc == ncyc) begin
            $display("HCORE_SWR_MITER %s seed=%0d gid=%0d cycles=%0d mismatches=%0d ov=%0d oy_nonzero=%0d oy_changes=%0d oflt=%0d",
                     (mis == 0 && n_ov > 100 && n_chg > 100) ? "PASS" : "FAIL", seed, gid, ncyc, mis, n_ov, n_nz, n_chg, n_flt);
            $finish;
        end
    end
endmodule
