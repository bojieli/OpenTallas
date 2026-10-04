`timescale 1ns/1ps
// Lockstep bench (Verilator --binary): the hardened per-tile landing merge
// (rtl/hdc/kv/ot_qwen_kv_land_merge.sv) against the per-tile arbitration of
// ot_qwen_rt_kv_stream4_service written the service's way (sequential walk in rotating port order
// with the accumulated quarter set), on random requests: grants, write address, data and mask
// must agree every cycle.  Requests use the real lane-quarter shapes (K: two quarters {0,1} or
// {2,3}; V: one quarter; tail K beats may carry an empty mask) and few distinct slice words so
// that claims, combines and refusals all occur.  Prints LAND_MERGE_LOCKSTEP PASS/FAIL.
module tb_qwen_kv_land_merge;
    localparam integer NSRC = 12, PW = 7, LW = 7, DW = 512, N = 200000;
    reg clk = 0, rst_n = 0;
    reg [PW-1:0] rr;
    reg [NSRC-1:0] s_v; reg [NSRC*PW-1:0] s_port; reg [NSRC*LW-1:0] s_loc; reg [NSRC*4-1:0] s_q4;
    reg [NSRC*DW-1:0] s_data, s_mask;
    reg tok_v; reg [LW-1:0] tok_loc; reg [DW-1:0] tok_data, tok_mask;
    wire [NSRC-1:0] s_grant; wire kvw_ce; wire [LW-1:0] kvw_addr; wire [DW-1:0] kvw_data, kvw_mask;
    ot_qwen_kv_land_merge #(.NSRC(NSRC)) dut (.clk(clk), .rst_n(rst_n), .rr(rr), .s_v(s_v), .s_port(s_port), .s_loc(s_loc),
        .s_q4(s_q4), .s_data(s_data), .s_mask(s_mask), .s_grant(s_grant), .tok_v(tok_v), .tok_loc(tok_loc),
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
    reg e_ce; reg [LW-1:0] e_loc; reg [DW-1:0] e_data, e_mask;
    initial begin
        bad = 0; grants = 0; combines = 0; refusals = 0;
        #1 rst_n = 1;
        for (t = 0; t < N; t = t + 1) begin
            rr = PW'($urandom);
            ports_used = 0;
            for (i = 0; i < NSRC; i = i + 1) begin
                integer pt, sh; reg [3:0] q;
                do pt = $urandom % 128; while (ports_used[pt]);
                ports_used[pt] = 1;
                s_port[i*PW +: PW] = PW'(pt);
                s_v[i] = ($urandom % 3) != 0;
                s_loc[i*LW +: LW] = LW'($urandom % 3);
                case ($urandom % 3)
                    0: q = 4'b0011; 1: q = 4'b1100; default: q = 4'b0001 << ($urandom % 4);
                endcase
                if (($urandom % 16) == 0) q = 4'b0000;                     // tail K beat with PL = 0
                s_q4[i*4 +: 4] = q;
                for (sh = 0; sh < 4; sh = sh + 1) begin
                    s_mask[i*DW + sh*128 +: 128] = q[sh] ? {4{$urandom}} : 128'd0;
                    s_data[i*DW + sh*128 +: 128] = {4{$urandom}} & s_mask[i*DW + sh*128 +: 128];
                end
            end
            tok_v = ($urandom % 8) == 0; tok_loc = LW'($urandom); tok_data = {16{$urandom}}; tok_mask = {16{$urandom}};
            #1;
            ref_walk();
            if (s_grant !== r_grant) begin bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d grant %h ref %h", t, s_grant, r_grant); end
            grants = grants + $countones(s_grant);
            if ($countones(s_grant) > 1) combines = combines + 1;
            refusals = refusals + $countones(s_v & ~s_grant);
            e_ce = r_ce; e_loc = r_loc; e_data = r_data; e_mask = r_mask;
            clk = 1; #1; clk = 0;
            if (kvw_ce !== e_ce || (e_ce && (kvw_addr !== e_loc || kvw_data !== e_data || kvw_mask !== e_mask))) begin
                bad = bad + 1; if (bad < 5) $display("MISMATCH t=%0d write", t);
            end
        end
        $display("%s cycles=%0d grants=%0d multi_grant_cycles=%0d refusals=%0d mismatches=%0d",
                 bad == 0 ? "LAND_MERGE_LOCKSTEP PASS" : "LAND_MERGE_LOCKSTEP FAIL", N, grants, combines, refusals, bad);
        $finish;
    end
endmodule
