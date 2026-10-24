module ot_codex_gq_land_keep #(parameter integer MUT = 0)(
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire          ld_fire,
    input  wire [52:0]   ld_desc,
    input  wire          ld_ev_v,
    input  wire [9:0]    ld_ev_k,
    input  wire [1:0]    ld_p_v,
    input  wire [511:0]  ld_p_d,
    input  wire [1:0]    pa_v, pb_v,
    input  wire [3:0]    pa_src, pb_src,
    input  wire [5:0]    pa_tag, pb_tag,
    input  wire [511:0]  pa_d, pb_d,
    output wire [1123:0] vm_kq_lo, vm_kq_hi,      // banks 0-3 / 4-7 on separate faces
    output reg           fault
);
    reg [2247:0] vm_kq; assign vm_kq_lo = face_clone_vm_kq[1123:0]; assign vm_kq_hi = face_clone_vm_kq[2247:1124];
    localparam integer NL = 36;      // le[j] = the entry of issue stage j + 1
    localparam integer S_KQ = 31;    // publish kq register @31+2h (entry at stage 30+2h = le[29+2h]); self-land kq @26
    wire [0:0] rl;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rn = rl[0];
    reg [1:0] q_id; always @(posedge clk) q_id <= qid;
    function automatic [1:0] nextq(input [1:0] q); case (q) 2'd0: nextq = 2'd1; 2'd1: nextq = 2'd3; 2'd3: nextq = 2'd2; default: nextq = 2'd0; endcase endfunction
    function automatic [1:0] prevq(input [1:0] q); case (q) 2'd0: prevq = 2'd2; 2'd1: prevq = 2'd0; 2'd3: prevq = 2'd1; default: prevq = 2'd3; endcase endfunction
    function automatic [1:0] srcq(input [1:0] q, input integer d, input integer h);
        reg [1:0] s; s = q;
        for (integer j = 0; j < h; j = j + 1) begin
            if (d == 0 || (MUT == 1 && h == 1)) s = prevq(s); else s = nextq(s);
        end
        srcq = s;
    endfunction
    // pin registers
    reg f_q; reg [52:0] d_q; reg [1:0] pl_v; reg [511:0] pl_d;
    reg [NL-1:0] le_v; reg [9:0] le_k [0:NL-1];
    always @(posedge clk or negedge rn)
        if (!rn) begin f_q <= 1'b0; pl_v <= 2'd0; le_v <= '0; end
        else begin f_q <= ld_fire; pl_v <= ld_p_v; le_v <= {le_v[NL-2:0], ld_ev_v}; end
    always @(posedge clk) begin
        d_q <= ld_desc; pl_d <= ld_p_d; le_k[0] <= ld_ev_k;
        for (integer j = 1; j < NL; j = j + 1) le_k[j] <= le_k[j-1];
    end
    // descriptor (held for the gather; gathers never overlap: the issue leaf faults a fire while busy)
    reg g_r2, g_self, g_qbg; reg [9:0] g_f; reg [7:0] g_bs; reg [15:0] g_dst, g_str;
    always @(posedge clk) if (f_q) {g_r2, g_self, g_qbg, g_f, g_bs, g_dst, g_str} <= d_q;
    function automatic [10:0] flit_i(input [9:0] k, input integer r); flit_i = g_r2 ? {k, 1'(r)} : (r == 0 ? {1'b0, k} : 11'h7ff); endfunction
    function automatic fv(input [9:0] k, input integer r);
        reg [10:0] i; i = flit_i(k, r); fv = (r == 0 || g_r2) && i < {1'b0, g_f};
    endfunction
    function automatic [15:0] sec_add(input [15:0] s, input [12:0] a); sec_add = {s[15:13], s[12:0] + a}; endfunction
    // ------------------------------------------------------------------ publish capture (@30+2h) and VM landing (@31+2h)
    reg [1:0] pav_q, pbv_q; reg [3:0] pas_q, pbs_q; reg [5:0] pat_q, pbt_q; reg [511:0] pad_q, pbd_q;
    always @(posedge clk or negedge rn) if (!rn) begin pav_q <= 2'd0; pbv_q <= 2'd0; end else begin pav_q <= pa_v; pbv_q <= pb_v; end
    always @(posedge clk) begin pas_q <= pa_src; pbs_q <= pb_src; pat_q <= pa_tag; pbt_q <= pb_tag; pad_q <= pa_d; pbd_q <= pb_d; end
    // Landing address pre-stage (HBM-COLLQ3 10-18: the CTS gate measured -323.9 ps on q_id -> sector add -> bank
    // decode -> 8-way bank mux -> vm_kq; 17 levels). Everything that is a function of the descriptor, q_id and the
    // entry's k is computed one edge EARLY from le[j-1] (the shift register holds the same entry there one edge before)
    // and registered per lane: enable, bank one-hot, sector, source quadrant, d. The landing edge keeps only the
    // capture compare, the bank-collision OR and an AND-OR bank select. vm_kq timing is unchanged (same edge).
    // Sector bases g_dst + g_str * q are registered from the held descriptor (gathers never overlap; the first use is
    // >= 23 edges after the descriptor fires).
    reg [15:0] base_q [0:3];
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) base_q[q] <= sec_add(g_dst, 13'(g_str * q));
    // lanes 0..5 = publish (h - 1) * 2 + r, lanes 6..7 = self-land r
    reg [7:0] ln_en; reg [7:0] ln_bk [0:7]; reg [15:0] ln_s [0:7]; reg [1:0] ln_sq [0:5]; reg [5:0] ln_d;
    always @(posedge clk or negedge rn)
        if (!rn) ln_en <= 8'd0;
        else begin : nb_pre
            reg [9:0] k; reg [10:0] i; reg [1:0] sq; reg [15:0] s;
            for (integer h = 1; h <= 3; h = h + 1)
                for (integer r = 0; r < 2; r = r + 1) begin
                    k = le_k[S_KQ + 2*h - 3]; i = flit_i(k, r); sq = srcq(q_id, k[0], h);
                    s = {base_q[sq][15:13], base_q[sq][12:0] + 13'(i) + ((MUT == 3) ? 13'd1 : 13'd0)};
                    ln_en[(h-1)*2 + r] <= le_v[S_KQ + 2*h - 3] && fv(k, r);
                    ln_bk[(h-1)*2 + r] <= 8'd1 << s[2:0]; ln_s[(h-1)*2 + r] <= s;
                    ln_sq[(h-1)*2 + r] <= sq; ln_d[(h-1)*2 + r] <= k[0];
                end
            for (integer r = 0; r < 2; r = r + 1) begin
                k = le_k[23]; i = flit_i(k, r);
                s = {base_q[q_id][15:13], base_q[q_id][12:0] + 13'(i)};
                ln_en[6 + r] <= g_self && MUT != 4 && le_v[23] && fv(k, r);
                ln_bk[6 + r] <= 8'd1 << s[2:0]; ln_s[6 + r] <= s;
            end
        end
    reg [2247:0] kq_n; reg kq_bad, pub_bad;
    always @* begin : nb_11
        reg [3:0] lane_exp; reg [7:0] act; reg [7:0] seen; reg [255:0] gd [0:7];
        reg v; reg [1:0] gs; reg [2:0] gt; reg [9:0] kk; integer l;
        kq_n = '0; kq_bad = 1'b0; pub_bad = 1'b0; lane_exp = 4'd0; seen = 8'd0; act = 8'd0; v = 1'b0; gs = 2'd0; gt = 3'd0;
        for (integer m = 0; m < 8; m = m + 1) gd[m] = '0;
        for (integer h = 1; h <= 3; h = h + 1)
            for (integer r = 0; r < 2; r = r + 1) begin
                l = (h-1)*2 + r;
                kk = le_k[S_KQ + 2*h - 2];
                act[l] = ln_en[l];
                if (ln_en[l]) begin
                    lane_exp[r*2 + ln_d[l]] = 1'b1;
                    v = r ? pbv_q[ln_d[l]] : pav_q[ln_d[l]];
                    gs = r ? (ln_d[l] ? pbs_q[3:2] : pbs_q[1:0]) : (ln_d[l] ? pas_q[3:2] : pas_q[1:0]);
                    gt = r ? (ln_d[l] ? pbt_q[5:3] : pbt_q[2:0]) : (ln_d[l] ? pat_q[5:3] : pat_q[2:0]);
                    if (!v || gs != ln_sq[l] || gt != kk[2:0]) pub_bad = 1'b1;
                end
                gd[l] = r ? (ln_d[l] ? pbd_q[511:256] : pbd_q[255:0]) : (ln_d[l] ? pad_q[511:256] : pad_q[255:0]);
            end
        if ({pbv_q, pav_q} & ~lane_exp) pub_bad = 1'b1;        // unexpected publish
        for (integer r = 0; r < 2; r = r + 1) begin act[6 + r] = ln_en[6 + r] && pl_v[r]; gd[6 + r] = pl_d[r*256 +: 256]; end
        // two writes to one bank in one edge: fault; the last lane (original order) wins the bank
        for (integer m = 0; m < 8; m = m + 1) if (act[m]) begin
            if (seen & ln_bk[m]) kq_bad = 1'b1;
            seen = seen | ln_bk[m];
        end
        for (integer b = 0; b < 8; b = b + 1)
            for (integer m = 0; m < 8; m = m + 1)
                if (act[m] && ln_bk[m][b]) kq_n[b*281 +: 281] = {1'b1, ln_s[m], gd[m], 8'hff};
    end
    // the publish lanes are evaluated with the entry one stage past the capture (le[S_KQ+2h-2] = issue stage 30+2h, the
    // entry whose publish was captured on the previous edge); both register into kq.
    // sticky fault flop beside the landing logic, then a FACE register at the E fault pin (NATIVE-SWEEP 10-18: the
    // routed view hcoll_gq_land_1018-r1-b7918441e launched fault at O-R 228.0 > 220 ps from the interior flop). +1 edge
    // on the fault report only (sticky, off the token path; no data / VM edge moves). MUT 6 (bench): the face register
    // never forwards.
    reg flt_r;
    always @(posedge clk or negedge rn)
        if (!rn) begin vm_kq <= '0; flt_r <= 1'b0; fault <= 1'b0; end
        else begin vm_kq <= kq_n; if (kq_bad || pub_bad) flt_r <= 1'b1; fault <= flt_r && MUT != 6; end

    (* keep = 1 *) wire [11:0] keep_unused_ld_desc;
    (* keep = 1, keep_hierarchy = 1 *) ot_hbm_face_input_sink #(.W(12)) u_bin_unused_ld_desc (.clk(clk), .d({ld_desc[50], ld_desc[39], ld_desc[38], ld_desc[37], ld_desc[36], ld_desc[35], ld_desc[34], ld_desc[33], ld_desc[32], ld_desc[15], ld_desc[14], ld_desc[13]}), .q(keep_unused_ld_desc));

    wire [2247:0] face_clone_vm_kq;
    generate for (genvar cp=0;cp<2248;cp=cp+1) begin:g_face_clone_vm_kq
        (* keep = 1, keep_hierarchy = 1 *) ot_hbm_face_state_bit u_bout_copy (.clk(clk),.rst_n(rn),.d(kq_n[cp]),.q(face_clone_vm_kq[cp]));
    end endgenerate
endmodule
