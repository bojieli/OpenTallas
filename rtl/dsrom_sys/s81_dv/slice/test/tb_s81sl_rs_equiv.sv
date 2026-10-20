`timescale 1ns/1ps
// S81-XG4 (10-20): cycle equivalence of ot_s81sl_rs (native-bounded ring stop leaf) against CURRENT MAIN ot_s81sl_rstop
// (incl. S81-SMWIRE CI_XB) followed by a one-edge testbench relay on every relayed output (line E / W, V, control
// deliveries, xfin NX ports, gather port g_*; fault is not relayed).  Every output is compared every edge.
//   +sid=<0..15> +cycles=<n> +seed=<n> +dens=<0..255>
//   +legal=1      protocol-legal traffic: one source class per 256-cycle window (line / own / V / ci incl. XB / NX),
//                 so neither model may fault; requires fault == 0 throughout plus nonzero coverage of every class
//   +rstat=<cyc>  in-flight reset: rst_n low at <cyc> for 8 edges with traffic still in flight; inputs idle for 40
//                 edges, compare suspended for 30; both models must agree again afterwards (state fully reset)
// Prints RS_EQUIV PASS|FAIL.
module tb_s81sl_rs_equiv (input wire clk);
    localparam integer W = 1104, V = 276;
    integer cyc = 0, mism = 0, sidp = 5, ncyc = 20000, seed = 1, dens = 40, nfa = 0, nown = 0, nasm = 0, nline = 0;
    integer legal = 0, rstat = 0, ncxo = 0, nvt = 0, nnx = 0, ndl = 0, nfwd = 0;
    reg rst_n = 1'b0;
    reg [3:0] sid; reg [W-1:0] ri_w, ri_e, ci_b; reg [V-1:0] vi; reg [4:0] xf_v, xf_s; reg [5*V-1:0] xf;
    reg [172:0] nx_eo, nx_wo; reg [2:0] ci_dir;
    wire [W-1:0] a_ro_e0, a_ro_w0, a_dl_e0, a_dl_w0, b_ro_e, b_ro_w, b_dl_e, b_dl_w;
    wire [V-1:0] a_vo0, a_dl_vb0, b_vo, b_dl_vb; wire [172:0] a_nxwi0, a_nxei0, b_nxwi, b_nxei;
    wire [2:0] a_gv0, a_gf0, b_gv, b_gf; wire [20:0] a_gi0, b_gi; wire [3071:0] a_gd0, b_gd;
    wire a_dlev0, a_dlwv0, a_dlvv0, a_f, b_dlev, b_dlwv, b_dlvv, b_f;
    ot_s81sl_rstop u_a (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(a_ro_e0), .ro_w(a_ro_w0),
        .vi(vi), .vo(a_vo0), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(a_nxwi0), .nx_ei(a_nxei0), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(a_gv0), .g_fam(a_gf0), .g_idx(a_gi0), .g_d(a_gd0), .dl_ev(a_dlev0), .dl_e(a_dl_e0), .dl_wv(a_dlwv0),
        .dl_w(a_dl_w0), .dl_vv(a_dlvv0), .dl_vb(a_dl_vb0), .ci_dir(ci_dir), .ci_b(ci_b), .fault(a_f));
    // testbench relay = the RELAY = 1 contract of the leaf
    reg [W-1:0] a_ro_e, a_ro_w, a_dl_e, a_dl_w; reg [V-1:0] a_vo, a_dl_vb; reg [172:0] a_nxwi, a_nxei;
    reg [2:0] a_gv, a_gf; reg [20:0] a_gi; reg [3071:0] a_gd; reg a_dlev, a_dlwv, a_dlvv;
    always @(posedge clk) begin
        a_ro_e <= a_ro_e0; a_ro_w <= a_ro_w0; a_dl_e <= a_dl_e0; a_dl_w <= a_dl_w0; a_vo <= a_vo0; a_dl_vb <= a_dl_vb0;
        a_nxwi <= a_nxwi0; a_nxei <= a_nxei0; a_gv <= a_gv0; a_gf <= a_gf0; a_gi <= a_gi0; a_gd <= a_gd0;
        a_dlev <= a_dlev0; a_dlwv <= a_dlwv0; a_dlvv <= a_dlvv0;
    end
    ot_s81sl_rs u_b (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(b_ro_e), .ro_w(b_ro_w),
        .vi(vi), .vo(b_vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(b_nxwi), .nx_ei(b_nxei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(b_gv), .g_fam(b_gf), .g_idx(b_gi), .g_d(b_gd), .dl_ev(b_dlev), .dl_e(b_dl_e), .dl_wv(b_dlwv), .dl_w(b_dl_w),
        .dl_vv(b_dlvv), .dl_vb(b_dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(b_f));
    function automatic [1407:0] rword(input integer n);
        integer k; begin rword = 1408'd0; for (k = 0; k < (n + 31) / 32; k = k + 1) rword[32 * k +: 32] = $urandom; end
    endfunction
    function automatic bit hit(input integer d); hit = ($urandom % 256) < d; endfunction
    integer vk = 0, own_k = 0, own_f = 0, v_f = 0, quiet = 0, cls = 0, wpos = 0, ci_gap = 0, idle = 0, cmp_off = 0;
    initial begin
        void'($value$plusargs("sid=%d", sidp)); void'($value$plusargs("cycles=%d", ncyc));
        void'($value$plusargs("seed=%d", seed)); void'($value$plusargs("dens=%d", dens));
        void'($value$plusargs("legal=%d", legal)); void'($value$plusargs("rstat=%d", rstat));
        void'($urandom(seed));
        sid = sidp[3:0]; ri_w = 0; ri_e = 0; ci_b = 0; vi = 0; xf_v = 0; xf_s = 0; xf = 0; nx_eo = 0; nx_wo = 0; ci_dir = 0;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rstat > 0 && cyc == rstat) rst_n <= 1'b0;
        if (rstat > 0 && cyc == rstat + 8) rst_n <= 1'b1;
        idle = rstat > 0 && cyc >= rstat && cyc < rstat + 40;
        cmp_off = rstat > 0 && cyc >= rstat && cyc < rstat + 30;
        cls = (cyc / 256) % 5; wpos = cyc % 256;
        if (cyc >= 20 && !idle) begin
            // line beats {payload, idx [19:13], src [12:9], hops [8:4], kind [3:1], v}
            ri_w <= rword(W); ri_w[0] <= hit(dens); ri_w[3:1] <= $urandom % 4; ri_w[8:4] <= $urandom % 9;
            ri_e <= rword(W); ri_e[0] <= hit(dens); ri_e[3:1] <= $urandom % 4; ri_e[8:4] <= $urandom % 9;
            ci_b <= rword(W); ci_b[0] <= hit(dens / 2); ci_b[3:1] <= $urandom % 4;
            ci_b[8:4] <= ($urandom % 2) ? 5'd0 : 5'($urandom % 8);
            ci_dir <= 3'($urandom);
            nx_eo <= {hit(dens / 2), 172'(rword(172))}; nx_wo <= {hit(dens / 2), 172'(rword(172))};
            xf <= rword(5 * V); xf_v <= 0; xf_s <= 5'($urandom);
            if (own_f == 0 && hit(dens)) begin own_k = $urandom % 5; own_f = 4; end
            if (own_f > 0) begin
                xf_v[own_k] <= 1'b1; xf_s[own_k] <= own_f == 4; own_f = own_f - 1;
                if (!legal && hit(4)) xf_v[(own_k + 1) % 5] <= 1'b1;
            end
            xf[2:0] <= 3'd1;
            vi <= rword(V); vi[0] <= 1'b0;
            if (v_f > 0) begin vi[0] <= 1'b1; v_f = v_f - 1; end
            else if (hit(dens)) begin vk = $urandom % 4; vi[0] <= 1'b1; vi[3:1] <= vk[2:0]; if (vk == 1 || vk == 2) v_f = 3; end
            if (!legal) begin
                quiet = (cyc / 3000) % 4 == 3;  // every 4th window: all-random headers (collisions / faults)
                if (quiet) begin ri_w[8:0] <= 9'($urandom); ri_e[8:0] <= 9'($urandom); vi[3:0] <= 4'($urandom); xf_v <= 5'($urandom); end
            end else begin
                // one source class per window, last 24 edges of a window idle (trains drain)
                if (cls != 0 || wpos >= 232) begin ri_w[0] <= 1'b0; ri_e[0] <= 1'b0; end
                if (cls != 1 || wpos >= 232) begin xf_v <= 5'd0; own_f = 0; end
                if (cls != 2 || wpos >= 232) begin vi[0] <= 1'b0; v_f = 0; end
                if (cls != 3 || wpos >= 232 || ci_gap > 0) ci_b[0] <= 1'b0;
                else begin ci_b[0] <= 1'b1; ci_b[3:1] <= ($urandom % 2) ? 3'd2 : 3'($urandom % 4); ci_gap = 5; end
                if (ci_gap > 0) ci_gap = ci_gap - 1;
                if (cls != 4 || wpos >= 232) begin nx_eo[172] <= 1'b0; nx_wo[172] <= 1'b0; end
            end
        end else if (idle) begin
            ri_w[0] <= 1'b0; ri_e[0] <= 1'b0; ci_b[0] <= 1'b0; nx_eo[172] <= 1'b0; nx_wo[172] <= 1'b0; xf_v <= 5'd0;
            vi[0] <= 1'b0; own_f = 0; v_f = 0;
        end
        if (cyc > 12 && rst_n && !cmp_off) begin
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
            if (u_a.cxo) ncxo = ncxo + 1;
            if (u_a.vt_on) nvt = nvt + 1;
            if (a_nxwi[172] | a_nxei[172]) nnx = nnx + 1;
            if (a_dlev | a_dlwv | a_dlvv) ndl = ndl + 1;
            if (u_a.fe | u_a.fw) nfwd = nfwd + 1;
        end
        if (cyc == ncyc) begin
            $display("RS_EQUIV sid=%0d seed=%0d dens=%0d legal=%0d rstat=%0d cycles=%0d mismatches=%0d first_fault=%0d gather0=%0d asm=%0d line_out=%0d fwd=%0d cixb_own=%0d vtrain=%0d nx=%0d dl=%0d",
                     sidp, seed, dens, legal, rstat, ncyc, mism, nfa, nown, nasm, nline, nfwd, ncxo, nvt, nnx, ndl);
            if (mism == 0 && nown > 0 && nasm > 0 && nline > 0 && nfwd > 0 && ncxo > 0 && nvt > 0 && nnx > 0 && ndl > 0 &&
                (!legal || nfa == 0))
                $display("RS_EQUIV PASS");
            else $display("RS_EQUIV FAIL");
            $finish;
        end
    end
endmodule
