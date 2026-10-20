`timescale 1ns/1ps
// S81-XG3 (10-19): cycle equivalence of ot_s81sl_rs (bit-sliced ring stop leaf) against ot_s81sl_rstop #(.RELAY(1)).
// Random protocol-shaped stimulus (valid probabilities per port, random kinds / hops / payloads, own and V fragment
// trains, control injects, xfin NX) on all inputs; every output compared every edge after both left reset.
// +sid=<0..15> +cycles=<n> +seed=<n> +dens=<0..255> (valid density).  Prints RS_EQUIV PASS|FAIL.
module tb_s81sl_rs_equiv (input wire clk);
    localparam integer W = 1104, V = 276;
    integer cyc = 0, mism = 0, sidp = 5, ncyc = 20000, seed = 1, dens = 40, nfa = 0, nown = 0, nasm = 0, nline = 0;
    reg rst_n = 1'b0;
    reg [3:0] sid; reg [W-1:0] ri_w, ri_e, ci_b; reg [V-1:0] vi; reg [4:0] xf_v, xf_s; reg [5*V-1:0] xf;
    reg [172:0] nx_eo, nx_wo; reg [2:0] ci_dir;
    wire [W-1:0] a_ro_e, a_ro_w, a_dl_e, a_dl_w, b_ro_e, b_ro_w, b_dl_e, b_dl_w;
    wire [V-1:0] a_vo, a_dl_vb, b_vo, b_dl_vb; wire [172:0] a_nxwi, a_nxei, b_nxwi, b_nxei;
    wire [2:0] a_gv, a_gf, b_gv, b_gf; wire [20:0] a_gi, b_gi; wire [3071:0] a_gd, b_gd;
    wire a_dlev, a_dlwv, a_dlvv, a_f, b_dlev, b_dlwv, b_dlvv, b_f;
    ot_s81sl_rstop #(.RELAY(1)) u_a (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(a_ro_e), .ro_w(a_ro_w),
        .vi(vi), .vo(a_vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(a_nxwi), .nx_ei(a_nxei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(a_gv), .g_fam(a_gf), .g_idx(a_gi), .g_d(a_gd), .dl_ev(a_dlev), .dl_e(a_dl_e), .dl_wv(a_dlwv), .dl_w(a_dl_w),
        .dl_vv(a_dlvv), .dl_vb(a_dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(a_f));
    ot_s81sl_rs u_b (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(b_ro_e), .ro_w(b_ro_w),
        .vi(vi), .vo(b_vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(b_nxwi), .nx_ei(b_nxei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(b_gv), .g_fam(b_gf), .g_idx(b_gi), .g_d(b_gd), .dl_ev(b_dlev), .dl_e(b_dl_e), .dl_wv(b_dlwv), .dl_w(b_dl_w),
        .dl_vv(b_dlvv), .dl_vb(b_dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(b_f));
    function automatic [W-1:0] rword(input integer n);
        integer k; begin for (k = 0; k < (n + 31) / 32; k = k + 1) rword[32 * k +: 32] = $urandom; end
    endfunction
    function automatic bit hit(input integer d); hit = ($urandom % 256) < d; endfunction
    integer own_k = 0, own_f = 0, v_f = 0, quiet = 0;
    initial begin
        void'($value$plusargs("sid=%d", sidp)); void'($value$plusargs("cycles=%d", ncyc));
        void'($value$plusargs("seed=%d", seed)); void'($value$plusargs("dens=%d", dens));
        void'($urandom(seed));
        sid = sidp[3:0]; ri_w = 0; ri_e = 0; ci_b = 0; vi = 0; xf_v = 0; xf_s = 0; xf = 0; nx_eo = 0; nx_wo = 0; ci_dir = 0;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc >= 20) begin
            // line beats {payload, idx [19:13], src [12:9], hops [8:4], kind [3:1], v}
            ri_w <= rword(W); ri_w[0] <= hit(dens); ri_w[3:1] <= $urandom % 4; ri_w[8:4] <= $urandom % 9;
            ri_e <= rword(W); ri_e[0] <= hit(dens); ri_e[3:1] <= $urandom % 4; ri_e[8:4] <= $urandom % 9;
            ci_b <= rword(W); ci_b[0] <= hit(dens / 2); ci_b[8:4] <= ($urandom % 2) ? 5'd0 : 5'($urandom % 8);
            ci_dir <= 3'($urandom);
            nx_eo <= {hit(dens / 2), 172'(rword(172))}; nx_wo <= {hit(dens / 2), 172'(rword(172))};
            // own fragment trains: one leaf, 4 fragments (start on the first), occasionally broken / doubled
            xf <= rword(5 * V); xf_v <= 0; xf_s <= 5'($urandom);
            if (own_f == 0 && hit(dens)) begin own_k = $urandom % 5; own_f = 4; end
            if (own_f > 0) begin
                xf_v[own_k] <= 1'b1; xf_s[own_k] <= own_f == 4; own_f = own_f - 1;
                if (hit(4)) xf_v[(own_k + 1) % 5] <= 1'b1;
            end
            xf[2:0] <= 3'd1;   // fragment 0 header kind field position (vq format) -- XQ
            // V beats: fragment trains (XQ / XB) or single NX / CTL beats
            vi <= rword(V); vi[0] <= 1'b0;
            if (v_f > 0) begin vi[0] <= 1'b1; v_f = v_f - 1; end
            else if (hit(dens)) begin vi[0] <= 1'b1; vi[3:1] <= $urandom % 4; if (vi[3:1] inside {3'd1, 3'd2}) v_f = 3; end
            quiet = (cyc / 3000) % 4 == 3;  // every 4th window: all-random headers (collisions / faults)
            if (quiet) begin ri_w[8:0] <= 9'($urandom); ri_e[8:0] <= 9'($urandom); vi[3:0] <= 4'($urandom); xf_v <= 5'($urandom); end
        end
        if (cyc > 12 && rst_n) begin
            if (a_ro_e !== b_ro_e || a_ro_w !== b_ro_w || a_vo !== b_vo || a_nxwi !== b_nxwi || a_nxei !== b_nxei ||
                a_gv !== b_gv || a_gf !== b_gf || a_gi !== b_gi || a_gd !== b_gd || a_dlev !== b_dlev || a_dl_e !== b_dl_e ||
                a_dlwv !== b_dlwv || a_dl_w !== b_dl_w || a_dlvv !== b_dlvv || a_dl_vb !== b_dl_vb || a_f !== b_f) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cyc=%0d ro_e=%0d ro_w=%0d vo=%0d nx=%0d%0d g=%0d%0d%0d%0d dl=%0d%0d%0d%0d%0d%0d f=%0d/%0d",
                    cyc, a_ro_e !== b_ro_e, a_ro_w !== b_ro_w, a_vo !== b_vo, a_nxwi !== b_nxwi, a_nxei !== b_nxei,
                    a_gv !== b_gv, a_gf !== b_gf, a_gi !== b_gi, a_gd !== b_gd, a_dlev !== b_dlev, a_dl_e !== b_dl_e,
                    a_dlwv !== b_dlwv, a_dl_w !== b_dl_w, a_dlvv !== b_dlvv, a_dl_vb !== b_dl_vb, a_f, b_f);
            end
            if (a_f && nfa == 0) nfa = cyc;
            if (a_gv[0]) nown = nown + 1;
            if (a_ro_e[0] | a_ro_w[0]) nline = nline + 1;
            if (u_a.asm_v) nasm = nasm + 1;
        end
        if (cyc == ncyc) begin
            $display("RS_EQUIV sid=%0d seed=%0d dens=%0d cycles=%0d mismatches=%0d first_fault=%0d gather0=%0d asm=%0d line_out=%0d",
                     sidp, seed, dens, ncyc, mism, nfa, nown, nasm, nline);
            if (mism == 0 && nown > 0 && nasm > 0 && nline > 0) $display("RS_EQUIV PASS"); else $display("RS_EQUIV FAIL");
            $finish;
        end
    end
endmodule
