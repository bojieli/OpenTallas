`timescale 1ns/1ps
// S81-SVC-5 (11-08) R5 lock-step bench: the 16 real dsdv_svc_rs slices (tb_svc_lower wiring, protect-lib builds) driven
// ONLY by a lower_svc.py bench image, at H = `TBH (16 = the H16 slice, one job; 8 = the R5 H8 slice built -DOT_SVC_H8,
// two head passes on one landing).  The bench DUMPS every observable output stream with its cycle; the checker
// (tools/s81_dv/layer_prog/svc/check_lockstep.py) decodes them per head / row / dim and compares
//   (a) against the image golden (sc.hex scores, pv.hex P.V, oexp.hex SO o rows) and the compiled cycles (image.json);
//   (b) the H8x2 run against the H16x1 run on the SAME fixture: the ordered per-head output streams must be equal
//       (latency shift allowed: streams are compared in order, not cycle-aligned).
// Dump lines (IMG/ls_dump_s<seed>.txt):
//   RT  cyc row_hex lane_hex          root score beat at the fold (rt_dd[RS_FOLD], LW = TBH*132+20 bits)
//   SE  slice cyc data_hex            SE operand row (512 b)
//   W   slice cyc st a m data_hex     SM / SO target write (w_*)
//   PV  slice cyc x_hex data_hex      entry P.V / SO gather word (pv_x 48 b, pv_d 513 b)
//   JD  entry cyc jd                  jd pulse (bit0 done, bit1 fault)
//   FLT slice cyc code                slice fault code change
`ifndef RS_OBS
`define RS_OBS
`endif
`ifndef TBH
`define TBH 16
`endif
module tb_svc_lockstep;
    parameter integer ST = 0;
    parameter integer MAXCYC = 30000;
`include "dsdv_svc_rs_roles.svh"
    localparam integer H = `TBH, NHBM = 8192, QMAX = 8192;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst = 0;
    reg [31:0] meta [0:31];
    reg [31:0] qcyc [0:QMAX-1];
    reg [511:0] qwd [0:QMAX-1];
    reg [63:0] hkey [0:NHBM-1];
    reg [255:0] hdat [0:NHBM-1];
    reg [255:0] hbm [longint];
    reg [1023:0] dir;
    integer seed = 1, lat = 40, fd = 0;
    integer NQ, JW, JE, NH, i;
    reg [32:0] JWORD;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("lat=%d", lat)) ;
        $readmemh({dir, "/meta.hex"}, meta);
        NQ = meta[0]; JW = meta[2]; JE = meta[3]; JWORD = {meta[5][0], meta[4]}; NH = meta[6];
        if (meta[11] != ST) begin $display("image ST %0d != bench ST %0d", meta[11], ST); $finish; end
        $readmemh({dir, "/qcyc.hex"}, qcyc, 0, NQ - 1);
        $readmemh({dir, "/qwd.hex"}, qwd, 0, NQ - 1);
        $readmemh({dir, "/hkey.hex"}, hkey, 0, NH - 1);
        $readmemh({dir, "/hdat.hex"}, hdat, 0, NH - 1);
        for (i = 0; i < NH; i = i + 1) hbm[hkey[i]] = hdat[i];
        void'($urandom(seed));
        fd = $fopen($sformatf("%0s/ls_dump_h%0d_s%0d.txt", dir, H, seed), "w");
        $display("LS_IMG dir=%0s H=%0d nq=%0d jW=%0d jE=%0d hbm=%0d seed=%0d", dir, H, NQ, JW, JE, NH, seed);
    end

    localparam integer W = H * 132 + 20, SW = 1076, DW = 805, UW = 16, OBW = H * 132 + 567;
    wire [3:0] gi_v [0:15], go_v [0:15], si_v [0:15], so_v [0:15];
    wire [4*W-1:0] gi_d [0:15], go_d [0:15]; wire [4*SW-1:0] si_d [0:15], so_d [0:15];
    wire [4*DW-1:0] dn_i [0:15], dn_o [0:15]; wire [4*UW-1:0] up_i [0:15], up_o [0:15];
    wire [2*341-1:0] rq [0:15]; reg [1:0] rk [0:15], wd [0:15], rv [0:15];
    reg [2*256-1:0] r_data [0:15]; reg [2*17-1:0] r_tag [0:15]; reg [2*4-1:0] r_beat [0:15];
    wire [15:0] pv_v, w_v; wire [512:0] pv_d [0:15]; wire [47:0] pv_x [0:15]; wire [13:0] w_a [0:15]; wire [15:0] w_m [0:15];
    wire [511:0] w_d [0:15]; wire [11:0] w_st [0:15];
    reg [32:0] jcmd [0:1]; reg q_v = 0; reg [511:0] q_d = 0;
    wire [1:0] jdx [0:1]; wire [8:0] hcx [0:1]; wire [1:0] rfx; wire [1:0] stx [0:1];
    wire [4*514-1:0] ri [0:15], ro [0:15];
    reg [1:0] hsv [0:15];
    initial begin jcmd[0] = 0; jcmd[1] = 0; for (int k = 0; k < 16; k++) hsv[k] = 2'b01; end
    wire [OBW-1:0] obs [0:15];
    function automatic integer nb(input integer sd, input integer fc);
        integer r, c;
        r = sd % 2; c = sd / 2;
        case (fc)
            0: nb = (r == 0) ? 2*c + 1 : -1;
            1: nb = (c < 7) ? 2*(c+1) + r : -1;
            2: nb = (r == 1) ? 2*c : -1;
            default: nb = (c > 0) ? 2*(c-1) + r : -1;
        endcase
    endfunction
    genvar gs, gf;
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_s
        for (gf = 0; gf < 4; gf = gf + 1) begin : g_f
            localparam integer NBS = nb(gs, gf), OF = (gf + 2) % 4;
            if (NBS >= 0) begin : g_c
                assign gi_v[gs][gf] = go_v[NBS][OF]; assign gi_d[gs][W*gf +: W] = go_d[NBS][W*OF +: W];
                assign si_v[gs][gf] = so_v[NBS][OF]; assign si_d[gs][SW*gf +: SW] = so_d[NBS][SW*OF +: SW];
                assign dn_i[gs][DW*gf +: DW] = dn_o[NBS][DW*OF +: DW]; assign up_i[gs][UW*gf +: UW] = up_o[NBS][UW*OF +: UW];
                assign ri[gs][514*gf +: 514] = ro[NBS][514*OF +: 514];
            end else begin : g_e
                assign gi_v[gs][gf] = 1'b0; assign gi_d[gs][W*gf +: W] = '0;
                assign si_v[gs][gf] = 1'b0; assign si_d[gs][SW*gf +: SW] = '0;
                assign dn_i[gs][DW*gf +: DW] = '0; assign up_i[gs][UW*gf +: UW] = '0;
                assign ri[gs][514*gf +: 514] = '0;
            end
        end
        if (gs == RS_ENTRY_W || gs == RS_ENTRY_E) begin : g_r
            localparam integer HX = (gs == RS_ENTRY_E) ? 1 : 0;
            dsdv_svc_rs_entry_pl u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .j(jcmd[HX]), .jd(jdx[HX]), .q({2'b00, q_d, q_v}), .hw(292'd0), .hc(hcx[HX]), .fault(rfx[HX]), .st_rg(stx[HX]),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]), .pv_v(pv_v[gs]), .pv_d(pv_d[gs]), .pv_x(pv_x[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
        end else begin : g_n
            dsdv_svc_rs_pl u (.ck(ck), .rst(rst), .sid(4'(gs)),
                .dn_i(dn_i[gs]), .dn_o(dn_o[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .ri(ri[gs]), .ro(ro[gs]),
                .gi_v(gi_v[gs]), .gi_d(gi_d[gs]), .go_v(go_v[gs]), .go_d(go_d[gs]),
                .si_v(si_v[gs]), .si_d(si_d[gs]), .so_v(so_v[gs]), .so_d(so_d[gs]),
                .rq(rq[gs]), .rk(rk[gs]), .wd(wd[gs]), .rv(rv[gs]), .r_data(r_data[gs]), .r_tag(r_tag[gs]),
                .r_beat(r_beat[gs]), .hs(hsv[gs]),
                .w_v(w_v[gs]), .w_a(w_a[gs]), .w_m(w_m[gs]), .w_d(w_d[gs]), .w_st(w_st[gs]), .obs(obs[gs]));
            assign pv_v[gs] = 1'b0; assign pv_d[gs] = '0; assign pv_x[gs] = '0;
        end
    end endgenerate
    // obs = {rt_v, rt_d[W], se_v, se_d[512], a_fc[32], lf}
    wire [15:0] sflt; wire [31:0] afc [0:15];
    wire [15:0] se_v; wire [511:0] se_d [0:15]; wire [15:0] rt_vv; wire [W-1:0] rt_dd [0:15];
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_p
        assign sflt[gs] = obs[gs][0]; assign afc[gs] = obs[gs][32:1];
        assign se_d[gs] = obs[gs][544:33]; assign se_v[gs] = obs[gs][545];
        assign rt_dd[gs] = obs[gs][546 + W - 1:546]; assign rt_vv[gs] = obs[gs][546 + W];
    end endgenerate

    // ---------------- HBM: 32 PCs (tb_svc_lower model, unchanged) ----------------
    localparam integer PQ = 64;
    integer pq_t [0:31][0:PQ-1]; reg [340:0] pq_w [0:31][0:PQ-1]; integer pq_h [0:31], pq_n [0:31], pq_b [0:31];
    integer cred_err = 0, cyc = 0, hbm_wr = 0, hbm_rd = 0;
    initial for (i = 0; i < 32; i = i + 1) begin pq_h[i] = 0; pq_n[i] = 0; pq_b[i] = 0; end
    always @(posedge ck) begin
        reg [340:0] w341; reg [255:0] old; longint key; integer pc, sd, pp, jj;
        for (sd = 0; sd < 16; sd = sd + 1) begin rk[sd] <= 0; wd[sd] <= 0; rv[sd] <= 0; end
        for (pc = 0; pc < 32; pc = pc + 1) begin
            sd = pc / 2; pp = pc % 2;
            if (rq[sd][341*pp]) begin
                pq_t[pc][(pq_h[pc] + pq_n[pc]) % PQ] = cyc + lat + ($urandom % 16);
                pq_w[pc][(pq_h[pc] + pq_n[pc]) % PQ] = rq[sd][341*pp +: 341];
                pq_n[pc] = pq_n[pc] + 1;
                if (pq_n[pc] > 8) cred_err = cred_err + 1;
            end
            if (pq_n[pc] > 0 && pq_t[pc][pq_h[pc]] <= cyc) begin
                w341 = pq_w[pc][pq_h[pc]];
                key = (longint'(pc) << 32) | longint'(w341[31:2] + (w341[1] ? 0 : pq_b[pc]));
                if (w341[1]) begin
                    old = hbm.exists(key) ? hbm[key] : 256'd0;
                    for (jj = 0; jj < 32; jj = jj + 1) if (w341[53 + jj]) old[8*jj +: 8] = w341[85 + 8*jj +: 8];
                    hbm[key] = old; wd[sd][pp] <= 1'b1; rk[sd][pp] <= 1'b1; hbm_wr = hbm_wr + 1;
                    pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1;
                end else begin
                    rv[sd][pp] <= 1'b1; r_tag[sd][17*pp +: 17] <= w341[52:36]; r_beat[sd][4*pp +: 4] <= 4'(pq_b[pc]);
                    r_data[sd][256*pp +: 256] <= hbm.exists(key) ? hbm[key] : 256'd0;
                    if (pq_b[pc] + 1 == w341[35:32]) begin
                        pq_b[pc] = 0; pq_h[pc] = (pq_h[pc] + 1) % PQ; pq_n[pc] = pq_n[pc] - 1; rk[sd][pp] <= 1'b1; hbm_rd = hbm_rd + 1;
                    end else pq_b[pc] = pq_b[pc] + 1;
                end
            end
        end
    end

    // ---------------- drive + dump ----------------
    reg [31:0] last_afc [0:15];
    initial for (int k = 0; k < 16; k++) last_afc[k] = 0;
    integer qi = 0, late_q = 0, n_done [0:1], done_c [0:1], n_rt = 0, n_pv = 0, n_w = 0, n_se = 0;
    initial begin n_done[0] = 0; n_done[1] = 0; done_c[0] = -1; done_c[1] = -1; end
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst <= 1;
        jcmd[0] <= (cyc == JW) ? JWORD : 33'd0;
        jcmd[1] <= (cyc == JE) ? JWORD : 33'd0;
        q_v <= 0;
        if (qi < NQ && cyc == qcyc[qi]) begin q_v <= 1; q_d <= qwd[qi]; qi = qi + 1; end
        else if (qi < NQ && cyc > qcyc[qi]) late_q = late_q + 1;
        for (int k = 0; k < 2; k++) if (jdx[k] != 2'b00) begin
            $fdisplay(fd, "JD %0d %0d %0d", k, cyc, jdx[k]);
            if (jdx[k][0]) begin n_done[k] = n_done[k] + 1; done_c[k] = cyc; end
        end
        if (rt_vv[RS_FOLD]) begin $fdisplay(fd, "RT %0d %0h", cyc, rt_dd[RS_FOLD]); n_rt = n_rt + 1; end
        for (int s = 0; s < 16; s++) begin
            if (se_v[s]) begin $fdisplay(fd, "SE %0d %0d %0128h", s, cyc, se_d[s]); n_se = n_se + 1; end
            if (w_v[s]) begin $fdisplay(fd, "W %0d %0d %03h %04h %04h %0128h", s, cyc, w_st[s], w_a[s], w_m[s], w_d[s]); n_w = n_w + 1; end
            if (pv_v[s]) begin $fdisplay(fd, "PV %0d %0d %012h %0129h", s, cyc, pv_x[s], pv_d[s]); n_pv = n_pv + 1; end
            if (afc[s] != last_afc[s]) begin
                $fdisplay(fd, "FLT %0d %0d %08h", s, cyc, afc[s]);
                last_afc[s] <= afc[s];
            end
        end
        if ((n_done[0] > 0 && n_done[1] > 0 && cyc > done_c[0] + 400 && cyc > done_c[1] + 400) || cyc >= MAXCYC) begin
            reg [15:0] fl; fl = 0;
            for (int s = 0; s < 16; s++) fl[s] = sflt[s];
            $display("LS_END H=%0d cycles=%0d q_sent=%0d/%0d late_q=%0d n_done=%0d/%0d done_W=%0d done_E=%0d rt=%0d se=%0d w=%0d pv=%0d jd_fault=%0d root_fault=%0d slice_faults=%04x cred_err=%0d hbm_wr=%0d hbm_rd=%0d timeout=%0d",
                H, cyc, qi, NQ, late_q, n_done[0], n_done[1], done_c[0], done_c[1], n_rt, n_se, n_w, n_pv,
                jdx[0][1] | jdx[1][1], rfx != 0, fl, cred_err, hbm_wr, hbm_rd, cyc >= MAXCYC);
            $fdisplay(fd, "END %0d qi %0d nq %0d late %0d slice_faults %04x rfx %0d cred %0d", cyc, qi, NQ, late_q, fl, rfx, cred_err);
            $fclose(fd);
            $finish;
        end
    end
endmodule
