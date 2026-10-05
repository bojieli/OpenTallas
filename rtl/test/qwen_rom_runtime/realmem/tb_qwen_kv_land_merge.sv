`timescale 1ns/1ps
// Lockstep bench (Verilator --binary): the hardened per-tile landing merge
// (rtl/hdc/kv/ot_qwen_kv_land_merge.sv) against the per-tile arbitration of
// ot_qwen_rt_kv_stream4_service written the service's way (sequential walk in rotating port order
// with the accumulated quarter set), on random requests: grants, write address, data and mask
// must agree every cycle.  Requests are the service's beat shapes (K: 256 bits at quarter 0 or 2,
// tail-masked in the open tile; V half: 128 bits at one quarter; the tail mask may be empty) and few distinct slice words so
// that claims, combines and refusals all occur.  Prints LAND_MERGE_LOCKSTEP PASS/FAIL.
module tb_qwen_kv_land_merge;
    localparam integer NSRC = 12, PW = 7, LW = 7, DW = 512, N = 200000;
    reg clk = 0, rst_n = 0;
    reg [PW-1:0] rr, rr_n;
    reg [NSRC-1:0] s_v; reg [NSRC*PW-1:0] s_port; reg [NSRC*LW-1:0] s_loc; reg [NSRC*4-1:0] s_q4;
    reg [NSRC*DW-1:0] s_data, s_mask;
    reg [NSRC-1:0] s_isk, s_ktail; reg [NSRC*2-1:0] s_sel; reg [NSRC*256-1:0] s_beat; reg [127:0] tail_lm;
    reg tok_v; reg [LW-1:0] tok_loc; reg [DW-1:0] tok_data, tok_mask;
    wire [NSRC-1:0] s_grant; wire kvw_ce; wire [LW-1:0] kvw_addr; wire [DW-1:0] kvw_data, kvw_mask;
    ot_qwen_kv_land_merge #(.NSRC(NSRC)) dut (.clk(clk), .rst_n(rst_n), .rr_n(rr_n), .s_v(s_v), .s_port(s_port), .s_loc(s_loc),
        .s_isk(s_isk), .s_ktail(s_ktail), .s_sel(s_sel), .s_beat(s_beat), .tail_lm(tail_lm), .s_grant(s_grant), .tok_v(tok_v), .tok_loc(tok_loc),
        .tok_data(tok_data), .tok_mask(tok_mask), .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
    // reference: the service's walk
    reg [NSRC-1:0] r_grant; reg r_ce; reg [LW-1:0] r_loc; reg [DW-1:0] r_data, r_mask;
    task automatic ref_walk();
        integer o, i; reg claimed; reg [3:0] seen; reg [LW-1:0] cl;
        claimed = 0; seen = 0; cl = 0; r_grant = 0; r_data = 0; r_mask = 0;
        r_ce = tok_v || (|s_v);
        if (tok_v) begin r_loc = tok_loc; r_data = tok_data; r_mask = tok_mask; end
        else begin
            for (o = 0; o < 128; o = o + 1)
                for (i = 0; i < NSRC; i = i + 1)
                    if (s_v[i] && s_port[i*PW +: PW] == PW'(rr + o)) begin
                        if (!claimed) begin
                            claimed = 1; cl = s_loc[i*LW +: LW]; seen = s_q4[i*4 +: 4]; r_grant[i] = 1;
                            r_data = s_data[i*DW +: DW]; r_mask = s_mask[i*DW +: DW];
                        end else if (s_loc[i*LW +: LW] == cl) begin
                            if ((seen & s_q4[i*4 +: 4]) == 0) begin
                                r_grant[i] = 1; r_data = r_data | s_data[i*DW +: DW]; r_mask = r_mask | s_mask[i*DW +: DW];
                            end
                            seen = seen | s_q4[i*4 +: 4];
                        end
                    end
            r_loc = cl;
        end
    endtask
    integer t, i, bad, grants, combines, refusals;
    reg [127:0] ports_used;
    reg e_ce, p_ce; reg [LW-1:0] e_loc, p_loc; reg [DW-1:0] e_data, e_mask, p_data, p_mask;
    initial begin
        bad = 0; grants = 0; combines = 0; refusals = 0;
        #1 rst_n = 1;
        // the tile's source ports are straps: fixed for the run
        ports_used = 0;
        for (i = 0; i < NSRC; i = i + 1) begin
            integer pt;
            do pt = $urandom % 128; while (ports_used[pt]);
            ports_used[pt] = 1; s_port[i*PW +: PW] = PW'(pt);
        end
        rr = PW'($urandom); rr_n = rr; s_v = 0; tok_v = 0;
        #1 clk = 1; #1 clk = 0;                                  // the order of cycle 0
        p_ce = 0;
        for (t = 0; t < N; t = t + 1) begin
            // the open tile's mask changes only at a layer start (no landed beats in that cycle)
            if (t % 64 == 0) tail_lm = (($urandom % 4) == 0) ? 128'd0 : ((128'd1 << (8 * ($urandom % 16))) - 128'd1);
            for (i = 0; i < NSRC; i = i + 1) begin
                reg [3:0] q;
                s_v[i] = ($urandom % 3) != 0;
                s_loc[i*LW +: LW] = LW'($urandom % 3);
                // the service's beat shapes: K (two quarters at sel 0/2, tail-masked), V half (one quarter)
                s_beat[i*256 +: 256] = {8{$urandom}};
                s_isk[i] = $urandom % 2; s_ktail[i] = s_isk[i] && ($urandom % 4) == 0;
                s_sel[i*2 +: 2] = s_isk[i] ? 2'(2 * ($urandom % 2)) : 2'($urandom % 4);
                begin
                    reg [127:0] lm; reg [1:0] sl; sl = s_sel[i*2 +: 2];
                    lm = s_ktail[i] ? tail_lm : {128{1'b1}};
                    if (s_isk[i]) begin
                        s_data[i*DW +: DW] = {256'd0, s_beat[i*256 +: 256]} << (128 * sl);
                        s_mask[i*DW +: DW] = {256'd0, lm, lm} << (128 * sl);
                    end else begin
                        s_data[i*DW +: DW] = {384'd0, s_beat[i*256 +: 128]} << (128 * sl);
                        s_mask[i*DW +: DW] = {384'd0, {128{1'b1}}} << (128 * sl);
                    end
                    q = {|s_mask[i*DW+384 +: 128], |s_mask[i*DW+256 +: 128], |s_mask[i*DW+128 +: 128], |s_mask[i*DW +: 128]};
                    s_q4[i*4 +: 4] = q;
                end
            end
            if (t % 64 == 0) s_v = 0;
            tok_v = ($urandom % 8) == 0; tok_loc = LW'($urandom); tok_data = {16{$urandom}}; tok_mask = {16{$urandom}};
            rr_n = ($urandom % 2) ? PW'(rr + 1) : PW'($urandom);   // the service's rr counts; random also
            #1;
            ref_walk();
            if (s_grant !== r_grant) begin bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d grant %h ref %h", t, s_grant, r_grant); end
            grants = grants + $countones(s_grant);
            if ($countones(s_grant) > 1) combines = combines + 1;
            refusals = refusals + $countones(s_v & ~s_grant);
            e_ce = p_ce; e_loc = p_loc; e_data = p_data; e_mask = p_mask;       // the write is two edges late
            p_ce = r_ce; p_loc = r_loc; p_data = r_data; p_mask = r_mask;
            clk = 1; #1; clk = 0;
            rr = rr_n;
            if (t > 0 && (kvw_ce !== e_ce || (e_ce && (kvw_addr !== e_loc || kvw_data !== e_data || kvw_mask !== e_mask)))) begin
                bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d write", t);
            end
        end
        $display("%s cycles=%0d grants=%0d multi_grant_cycles=%0d refusals=%0d mismatches=%0d",
                 bad == 0 ? "LAND_MERGE_LOCKSTEP PASS" : "LAND_MERGE_LOCKSTEP FAIL", N, grants, combines, refusals, bad);
        if (bad != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
    end
endmodule
