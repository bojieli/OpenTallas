`timescale 1ns/1ps
// PL-SVC (10-18): lockstep of the original slice (dsdv_svc_rs_c) against its wires-only refactor (the lp.py input):
//   ENTRY 0: dsdv_svc_rs        vs dsdv_svc_rs_f        ENTRY 1: dsdv_svc_rs_entry vs dsdv_svc_rs_entry_f
// Same random inputs every cycle, every output compared every cycle after reset.  The refactor's up face is split
// (up_d = up bits {[13], [11:0]}, up_f = {[15], [14], [12]} a face): the bench feeds both from one random up word and
// reassembles the refactor's up_d_o / up_f_o into the original layout before comparing.
// FEQ_MUT 1 (negative control): the refactor's sid strap is one slice off (sid ^ 1) -> must FAIL.
module tb_dsdv_svc_rs_feq;
    parameter integer SID = 9;
    parameter integer CYC = 3000;
    parameter integer FEQ_MUT = 0;
    parameter integer ENTRY = 0;
    reg ck = 1'b0; always #0.5 ck = ~ck;
    reg rst = 1'b0;
    wire [3:0] sid = SID[3:0];
    wire [3:0] sid_f = (FEQ_MUT == 1) ? (SID[3:0] ^ 4'd1) : SID[3:0];
    reg [4*805-1:0] dn_i; reg [4*16-1:0] up_i; reg [4*514-1:0] ri; reg [3:0] gi_v, si_v; reg [4*2132-1:0] gi_d;
    reg [4*1076-1:0] si_d; reg [1:0] rk, wd, rv, hs; reg [2*256-1:0] r_data; reg [2*17-1:0] r_tag; reg [2*4-1:0] r_beat;
    reg [32:0] j; reg [514:0] q; reg [291:0] hw;
    wire [4*805-1:0] dn_o_a, dn_o_b; wire [4*16-1:0] up_o_a, up_o_b; wire [4*514-1:0] ro_a, ro_b;
    wire [3:0] go_v_a, go_v_b, so_v_a, so_v_b; wire [4*2132-1:0] go_d_a, go_d_b; wire [4*1076-1:0] so_d_a, so_d_b;
    wire [2*341-1:0] rq_a, rq_b; wire w_v_a, w_v_b; wire [13:0] w_a_a, w_a_b; wire [15:0] w_m_a, w_m_b;
    wire [511:0] w_d_a, w_d_b; wire [11:0] w_st_a, w_st_b;
    wire [1:0] jd_a, jd_b, st_a, st_b; wire [8:0] hc_a, hc_b; wire f_a, f_b, pv_v_a, pv_v_b; wire [512:0] pv_d_a, pv_d_b;
    wire [4*13-1:0] up_d_i, up_d_o; wire [4*3-1:0] up_f_i, up_f_o;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_up
        assign up_d_i[13*g +: 13] = {up_i[16*g + 13], up_i[16*g +: 12]};
        assign up_f_i[3*g +: 3] = {up_i[16*g + 15], up_i[16*g + 14], up_i[16*g + 12]};
        assign up_o_b[16*g +: 16] = {up_f_o[3*g + 2], up_f_o[3*g + 1], up_d_o[13*g + 12], up_f_o[3*g], up_d_o[13*g +: 12]};
    end endgenerate
    generate if (ENTRY) begin : g_e
        dsdv_svc_rs_entry u_a (.ck(ck), .rst(rst), .sid(sid), .j(j), .jd(jd_a), .q(q), .hw(hw), .hc(hc_a), .fault(f_a),
            .st_rg(st_a), .dn_i(dn_i), .dn_o(dn_o_a), .up_i(up_i), .up_o(up_o_a), .ri(ri), .ro(ro_a),
            .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v_a), .go_d(go_d_a), .si_v(si_v), .si_d(si_d), .so_v(so_v_a), .so_d(so_d_a),
            .rq(rq_a), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),
            .pv_v(pv_v_a), .pv_d(pv_d_a), .w_v(w_v_a), .w_a(w_a_a), .w_m(w_m_a), .w_d(w_d_a), .w_st(w_st_a));
        dsdv_svc_rs_entry_f u_b (.ck(ck), .rst(rst), .sid(sid_f), .j(j), .jd(jd_b), .q(q), .hw(hw), .hc(hc_b), .fault(f_b),
            .st_rg(st_b), .dn_i(dn_i), .dn_o(dn_o_b), .up_d_i(up_d_i), .up_d_o(up_d_o), .up_f_i(up_f_i), .up_f_o(up_f_o),
            .ri(ri), .ro(ro_b),
            .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v_b), .go_d(go_d_b), .si_v(si_v), .si_d(si_d), .so_v(so_v_b), .so_d(so_d_b),
            .rq(rq_b), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),
            .pv_v(pv_v_b), .pv_d(pv_d_b), .w_v(w_v_b), .w_a(w_a_b), .w_m(w_m_b), .w_d(w_d_b), .w_st(w_st_b));
    end else begin : g_n
        dsdv_svc_rs u_a (.ck(ck), .rst(rst), .sid(sid), .dn_i(dn_i), .dn_o(dn_o_a), .up_i(up_i), .up_o(up_o_a), .ri(ri), .ro(ro_a),
            .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v_a), .go_d(go_d_a), .si_v(si_v), .si_d(si_d), .so_v(so_v_a), .so_d(so_d_a),
            .rq(rq_a), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),
            .w_v(w_v_a), .w_a(w_a_a), .w_m(w_m_a), .w_d(w_d_a), .w_st(w_st_a));
        dsdv_svc_rs_f u_b (.ck(ck), .rst(rst), .sid(sid_f), .dn_i(dn_i), .dn_o(dn_o_b), .up_d_i(up_d_i), .up_d_o(up_d_o),
            .up_f_i(up_f_i), .up_f_o(up_f_o), .ri(ri), .ro(ro_b),
            .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v_b), .go_d(go_d_b), .si_v(si_v), .si_d(si_d), .so_v(so_v_b), .so_d(so_d_b),
            .rq(rq_b), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),
            .w_v(w_v_b), .w_a(w_a_b), .w_m(w_m_b), .w_d(w_d_b), .w_st(w_st_b));
        assign {jd_a, jd_b, st_a, st_b, hc_a, hc_b, f_a, f_b, pv_v_a, pv_v_b, pv_d_a, pv_d_b} = '0;
    end endgenerate
    wire [4*805+64+4*514+8+4*2132+4*1076+682+1+14+16+512+12+2+2+9+1+1+513-1:0] oa = {dn_o_a, up_o_a, ro_a, go_v_a,
        so_v_a, go_d_a, so_d_a, rq_a, w_v_a, w_a_a, w_m_a, w_d_a, w_st_a, jd_a, st_a, hc_a, f_a, pv_v_a, pv_d_a};
    wire [$bits(oa)-1:0] ob = {dn_o_b, up_o_b, ro_b, go_v_b, so_v_b, go_d_b, so_d_b, rq_b, w_v_b, w_a_b, w_m_b, w_d_b, w_st_b,
        jd_b, st_b, hc_b, f_b, pv_v_b, pv_d_b};
    task automatic rnd(output logic [8191:0] x); for (int k = 0; k < 256; k++) x[32*k +: 32] = $urandom; endtask
    logic [8191:0] t0, t1, t2; logic [16383:0] tt;
    integer cyc, bad, nc, nv, ne;
    initial begin
        bad = 0; nc = 0; nv = 0; ne = 0;
        for (cyc = 0; cyc < CYC; cyc++) begin
            @(negedge ck);
            if (cyc == 16) rst = 1'b1;
            rnd(t0); rnd(t1); rnd(t2);
            tt = {t0, t1}; dn_i = tt[4*805-1:0]; up_i = t2[63:0]; ri = tt[16383 -: 4*514];
            gi_v = t2[67:64]; si_v = t2[71:68]; rk = t2[73:72]; wd = t2[75:74]; rv = t2[77:76]; hs = t2[79:78];
            j = t2[112:80]; hw = t2[404:113]; q = t2[919:405];
            rnd(t0); rnd(t1); tt = {t0, t1}; gi_d = tt[4*2132-1:0]; rnd(t2); si_d = t2[4*1076-1:0];
            rnd(t0); r_data = t0[511:0]; r_tag = t0[545:512]; r_beat = t0[553:546];
            if (cyc > 24) begin
                nc++;
                if (oa !== ob) begin bad++; if (bad <= 5) $display("FEQ_MISMATCH cycle=%0d", cyc); end
                if (w_v_a || |go_v_a || |so_v_a || ro_a[0] || |rq_a[0] || dn_o_a[0]) nv++;
                if (pv_v_a || |hc_a || |jd_a) ne++;
            end
        end
        if (bad == 0) $display("FEQ PASS ENTRY=%0d SID=%0d FEQ_MUT=%0d compared=%0d active=%0d entry_active=%0d", ENTRY, SID,
                               FEQ_MUT, nc, nv, ne);
        else $display("FEQ FAIL ENTRY=%0d SID=%0d FEQ_MUT=%0d mismatches=%0d of %0d", ENTRY, SID, FEQ_MUT, bad, nc);
        $finish;
    end
endmodule
