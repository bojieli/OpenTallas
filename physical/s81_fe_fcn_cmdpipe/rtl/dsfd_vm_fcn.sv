(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

module dsfd_vm_fob #(parameter integer STALE = 0, parameter integer WEV = 1, parameter integer MV = 0,
                     parameter integer DF = 1, parameter integer DX = 0) (
    input  wire clk, input wire rn,
    input  wire i_v, input wire i_we, input wire [13:0] i_row, input wire [15:0] i_m, input wire [511:0] i_d,
    output wire [4*(15 + WEV + 4*MV + 128*DF)-1:0] s_o, output wire [((DX > 0) ? DX : 1)-1:0] x_o, output wire [31:0] k_o
);
    localparam integer SW = 15 + WEV + 4*MV + 128*DF;
    reg b_v, b_we; reg [13:0] b_row; reg [15:0] b_m; reg [511:0] b_d;
    always @(posedge clk) begin
        if (!rn) b_v <= 1'b0; else b_v <= i_v;
        b_we <= i_we; b_row <= i_row; b_m <= i_m; b_d <= i_d;
    end
    wire c_v, c_we; wire [13:0] c_row; wire [15:0] c_m; wire [511:0] c_d;
    generate if (STALE != 0) begin : g_st
        reg s_v6, s_we6; reg [13:0] s_row6; reg [15:0] s_m6; reg [511:0] s_d6;
        always @(posedge clk) begin
            if (!rn) s_v6 <= 1'b0; else s_v6 <= b_v;
            s_we6 <= b_we; s_row6 <= b_row; s_m6 <= b_m; s_d6 <= b_d;
        end
        assign c_v = s_v6; assign c_we = s_we6; assign c_row = s_row6; assign c_m = s_m6; assign c_d = s_d6;
    end else begin : g_ns
        assign c_v = b_v; assign c_we = b_we; assign c_row = b_row; assign c_m = b_m; assign c_d = b_d;
    end endgenerate
    genvar gs;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        wire [SW-1:0] w;
        assign w[SW-1] = rn ? c_v : 1'b0;
        if (WEV != 0) begin : g_we assign w[SW-2] = c_we; end
        assign w[4*MV + 128*DF +: 14] = c_row;
        if (MV != 0) begin : g_m assign w[128*DF +: 4] = c_m[4*gs +: 4]; end
        if (DF != 0) begin : g_d assign w[127:0] = c_d[128*gs +: 128]; end
        dsfd_vm_be_kreg #(.W(SW), .ID(600 + gs)) u_s0 (.clk(clk), .d(w), .q(s_o[SW*gs +: SW]));
    end
    if (DX > 0) begin : g_x
        dsfd_vm_be_kreg #(.W(DX), .ID(604)) u_x0 (.clk(clk), .d(c_d[DX-1:0]), .q(x_o));
    end else begin : g_nx
        assign x_o = 1'b0;
    end endgenerate
    (* keep = 1 *) reg k_v; (* keep = 1 *) reg k_we; (* keep = 1 *) reg [13:0] k_row; (* keep = 1 *) reg [15:0] k_m;
    always @(posedge clk) begin
        if (!rn) k_v <= 1'b0; else k_v <= b_v;
        k_we <= b_we; k_row <= b_row; k_m <= b_m;
    end
    assign k_o = {k_v, k_we, k_row, k_m};
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_vm_fcn (
    input  wire [0:0]    ck, input wire [0:0] rst, input wire [0:0] cks, input wire [0:0] rss,
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    input  wire [63:0]   f_cq, input wire [0:0] f_p2c,
    output reg  [0:0]    c_wv, output reg [9:0] c_wd, input wire [0:0] c_wr,
    output reg  [3:0]    t_rdy,
    input  wire [703:0]  k_i,
    input  wire [15:0]   clf_i, input wire so_i, input wire ovr_i, input wire sflt_i, input wire err_i,
    output wire [359:0]  s_o,            
    output wire [111:0]  x_o,            
    output reg  [9:0]    arm_v, output reg [139:0] arm_base,
    output reg  [3:0]    rf_o,
    output reg  [15:0]   fe_flt,
    output reg  [7:0]    rn_o
);
    localparam integer NP = 28, RA = 14, NSLOT = 4, P2D = 40, CQD = 4, KD = 1, DVR = 1, XRT = 1;
    wire clk = ck[0];
    wire rn0, rns;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn0));
    (* keep = 1 *) reg [1:0] rr_c;
    (* keep = 1 *) reg [7:0] rn_k;
    always @(posedge clk) begin rr_c <= {rr_c[0], rn0}; rn_k <= {8{rn0}}; end
    always @* rn_o = rn_k;
    wire rn = rr_c[1];
    ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns));
    reg [63:0] cq_p;
    always @(posedge clk) cq_p <= f_cq;
    wire cap_src_flt = cq_p[3];
    reg a_p2c;
    always @(posedge clk) if (!rn) a_p2c <= 1'b0; else a_p2c <= f_p2c[0];
    wire ad_v, ad_r; wire [83:0] ad_d; wire ad_flt_c, ad_on; wire ad_flt;
    generate if (XRT != 0) begin : g_afs
        reg ad_flt_q; (* async_reg = "true" *) reg [1:0] ad_flt_s;
        always @(posedge cks[0]) ad_flt_q <= ad_flt_c;
        always @(posedge clk) ad_flt_s <= {ad_flt_s[0], ad_flt_q};
        assign ad_flt = ad_flt_s[1];
    end else begin : g_nafs
        assign ad_flt = ad_flt_c;
    end endgenerate
    reg ed_v; reg [7:0] ed_t;
    reg cv_p; reg [83:0] cd_p;
    always @(posedge cks[0]) begin if (!rns) cv_p <= 1'b0; else cv_p <= cv[0]; cd_p <= cd; end
    wire ad_dv; wire [7:0] ad_dt;
    generate if (DVR != 0) begin : g_dvr
        reg dv_q; reg [7:0] dt_q;
        always @(posedge cks[0]) begin if (!rns) dv_q <= 1'b0; else dv_q <= ad_dv; dt_q <= ad_dt; end
        assign dv[0] = dv_q; assign dt = dt_q;
    end else begin : g_ndvr
        assign dv[0] = ad_dv; assign dt = ad_dt;
    end endgenerate
    ot_s81_engine_adapter #(.QD(8), .XRT(XRT)) u_ad (
        .c_clk(cks[0]), .c_rst_n(rss[0]), .c_cmd_v(cv_p), .c_cmd_d(cd_p), .c_done_v(ad_dv), .c_done_tag(ad_dt),
        .fault(ad_flt_c), .online(ad_on),
        .e_clk(clk), .e_rst_n(rst[0]), .e_cmd_v(ad_v), .e_cmd_d(ad_d), .e_cmd_ready(ad_r), .e_inputs_present(1'b1),
        .e_done_v(ed_v), .e_done_tag(ed_t));
    wire [2:0] vop = ad_d[30:28];        
    wire [23:0] arg = ad_d[30:7];
    wire [7:0] ctag = {ad_d[83], ad_d[6:0]};
    reg imm_v; reg [7:0] imm_t;          
    reg [$clog2(CQD+1)-1:0] cq_n;
    wire [2:0] xp_c = arg[20:18];         
    wire x_go = arg[17];
    reg [4:0] x_act;
    wire imm_op = vop == 3'd1 || vop == 3'd2 || vop == 3'd4 || vop == 3'd6 || (vop == 3'd7 && !x_go);
    assign ad_r = !(imm_op && imm_v) && !(vop == 3'd5 && cq_n == CQD) && !(vop == 3'd7 && x_go && xp_c < 3'd5 && x_act[xp_c]);
    wire acc = ad_v && ad_r;
    wire is_armb = acc && vop == 3'd1, is_armr = acc && vop == 3'd2, is_arm = acc && vop == 3'd3;
    wire is_pid = acc && vop == 3'd4, is_prd = acc && vop == 3'd5;
    wire [1:0] arm_s = arg[20:19];
    wire is_larm = acc && vop == 3'd6, is_xmap = acc && vop == 3'd7 && !x_go, is_xgo = acc && vop == 3'd7 && x_go;
    wire is_bad = acc && (vop == 3'd0 || (vop == 3'd7 && xp_c > 3'd4));
    reg [89:0] id_r;                     
    always @(posedge clk) if (!rn) id_r <= 90'd0; else if (is_pid && arg[20:18] <= 3'd4) id_r[18*arg[20:18] +: 18] <= arg[17:0];
    localparam integer QW = 113, QB = (CQD > 1) ? $clog2(CQD) : 1;
    reg [QW-1:0] cq [0:CQD-1];
    reg [QB-1:0] cq_h, cq_t;
    wire [QW-1:0] cq_in = {id_r[73:0], arg[20:7], arg[6:0], id_r[82:74], id_r[83], ctag};
    reg r_act; reg [13:0] r_base; reg [6:0] r_w, r_nw; reg [73:0] r_id; reg [8:0] r_ex; reg r_sh; reg [7:0] r_tag;
    reg [$clog2(P2D+1):0] cr;
    wire r_iss = r_act && cr != 0;
    wire r_last = r_iss && r_w == r_nw;
    wire cq_pop = (!r_act || r_last) && cq_n != 0;
    wire cq_push = is_prd;
    always @(posedge clk) begin
        if (!rn) begin cq_h <= 0; cq_t <= 0; cq_n <= 0; r_act <= 1'b0; cr <= P2D; end
        else begin
            if (cq_push) begin cq[cq_t] <= cq_in; cq_t <= (cq_t == CQD - 1) ? 0 : cq_t + 1'b1; end
            if (cq_pop) cq_h <= (cq_h == CQD - 1) ? 0 : cq_h + 1'b1;
            cq_n <= cq_n + cq_push - cq_pop;
            if (cq_pop) begin
                r_act <= 1'b1; {r_id, r_base, r_nw, r_ex, r_sh, r_tag} <= cq[cq_h]; r_w <= 7'd0;
            end else if (r_last) r_act <= 1'b0;
            if (r_iss && !r_last) r_w <= r_w + 7'd1;
            cr <= cr - r_iss + a_p2c;
        end
    end
    reg [3:0] x_bus [0:4]; reg [12:0] x_n [0:4], x_c [0:4]; reg [13:0] x_b [0:4]; reg [7:0] x_tag [0:4];
    reg [4:0] x_dp;                        
    wire [4:0] x_iss = x_act;
    wire [4:0] x_last;
    genvar gx;
    generate for (gx = 0; gx < 5; gx = gx + 1) begin : g_xl
        assign x_last[gx] = x_act[gx] && x_c[gx] == x_n[gx];
    end endgenerate
    always @(posedge clk) begin : p_l507 integer xi;
        if (!rn) x_act <= 5'd0;
        else for (xi = 0; xi < 5; xi = xi + 1) begin
            if (is_xmap && xp_c == xi[2:0]) begin x_bus[xi] <= arg[16:13]; x_n[xi] <= arg[12:0]; end
            if (is_xgo && xp_c == xi[2:0]) begin x_act[xi] <= 1'b1; x_b[xi] <= arg[13:0]; x_c[xi] <= 13'd0; x_tag[xi] <= ctag; end
            else if (x_last[xi]) x_act[xi] <= 1'b0;
            else if (x_act[xi]) x_c[xi] <= x_c[xi] + 13'd1;
        end
    end
    wire [13:0] x_row0 = x_b[0] + {1'b0, x_c[0]}, x_row1 = x_b[1] + {1'b0, x_c[1]}, x_row2 = x_b[2] + {1'b0, x_c[2]},
                x_row3 = x_b[3] + {1'b0, x_c[3]}, x_row4 = x_b[4] + {1'b0, x_c[4]};
    wire [3:0] larm_g = arg[20:17];
    (* keep = 1 *) reg [9:0] arm_vk; (* keep = 1 *) reg [139:0] arm_bk;
    always @* begin arm_v = arm_vk; arm_base = arm_bk; end
    always @(posedge clk) begin : p_la integer l;
        for (l = 0; l < 10; l = l + 1) begin
            arm_bk[14*l +: 14] <= arg[13:0];
            if (!rn) arm_vk[l] <= 1'b0;
            else arm_vk[l] <= is_larm && larm_g == ((l < 2) ? 4'd0 : (l < 6) ? 4'd4 : (l == 6) ? 4'd5 : (l == 7) ? 4'd6 : 4'd7);
        end
    end
    wire [6*60-1:0] fs; wire [6*32-1:0] ko;
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(4)) u_b2 (.clk(clk), .rn(rn), .i_v(x_iss[2]), .i_we(1'b0), .i_row(x_row2), .i_m(16'hffff),
        .i_d({508'd0, x_bus[2]}), .s_o(fs[0*60 +: 60]), .x_o(x_o[3:0]), .k_o(ko[0*32 +: 32]));
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(92)) u_b5 (.clk(clk), .rn(rn), .i_v(r_iss), .i_we(1'b0), .i_row(r_base + {7'd0, r_w}), .i_m(16'hffff),
        .i_d({420'd0, r_id, r_ex, r_sh, r_last, r_w}), .s_o(fs[1*60 +: 60]), .x_o(x_o[95:4]), .k_o(ko[1*32 +: 32]));
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(4)) u_b6 (.clk(clk), .rn(rn), .i_v(x_iss[0]), .i_we(1'b0), .i_row(x_row0), .i_m(16'hffff),
        .i_d({508'd0, x_bus[0]}), .s_o(fs[2*60 +: 60]), .x_o(x_o[99:96]), .k_o(ko[2*32 +: 32]));
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(4)) u_b7 (.clk(clk), .rn(rn), .i_v(x_iss[1]), .i_we(1'b0), .i_row(x_row1), .i_m(16'hffff),
        .i_d({508'd0, x_bus[1]}), .s_o(fs[3*60 +: 60]), .x_o(x_o[103:100]), .k_o(ko[3*32 +: 32]));
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(4)) u_b8 (.clk(clk), .rn(rn), .i_v(x_iss[3]), .i_we(1'b0), .i_row(x_row3), .i_m(16'hffff),
        .i_d({508'd0, x_bus[3]}), .s_o(fs[4*60 +: 60]), .x_o(x_o[107:104]), .k_o(ko[4*32 +: 32]));
    dsfd_vm_fob #(.WEV(0), .DF(0), .DX(4)) u_b9 (.clk(clk), .rn(rn), .i_v(x_iss[4]), .i_we(1'b0), .i_row(x_row4), .i_m(16'hffff),
        .i_d({508'd0, x_bus[4]}), .s_o(fs[5*60 +: 60]), .x_o(x_o[111:108]), .k_o(ko[5*32 +: 32]));
    genvar gj, gs, gp;
    generate for (gj = 0; gj < 6; gj = gj + 1) begin : g_o
        for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
            assign s_o[(6*gs + gj)*15 +: 15] = fs[60*gj + 15*gs +: 15];
        end
    end endgenerate
    localparam integer KP = 3 - 2;
    wire [191:0] ko_d;
    generate if (KP > 0) begin : g_kp
        reg [191:0] ko_q [0:KP-1]; integer qi;
        always @(posedge clk) begin
            if (!rn) for (qi = 0; qi < KP; qi = qi + 1) ko_q[qi] <= 192'd0;
            else begin ko_q[0] <= ko; for (qi = 1; qi < KP; qi = qi + 1) ko_q[qi] <= ko_q[qi-1]; end
        end
        assign ko_d = ko_q[KP-1];
    end else begin : g_nkp
        assign ko_d = ko;
    end endgenerate
    wire [NP-1:0] b_v, b_we; wire [NP*RA-1:0] b_row; wire [NP*16-1:0] b_m;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_k
        localparam integer OWN = (gp == 2) ? 0 : (gp >= 5 && gp <= 9) ? gp - 4 : -1;
        localparam integer EXT = (gp < 2) ? gp : (gp < 5) ? gp - 1 : gp - 6;
        wire [31:0] kw;
        if (OWN >= 0) begin : g_i assign kw = ko_d[32*OWN +: 32]; end
        else begin : g_e assign kw = k_i[32*EXT +: 32]; end
        assign b_v[gp] = kw[31]; assign b_we[gp] = kw[30]; assign b_row[RA*gp +: RA] = kw[29:16]; assign b_m[16*gp +: 16] = kw[15:0];
    end endgenerate
    reg p0_armb, p0_armr, p0_arm; reg [23:0] p0_arg; reg [7:0] p0_tag; reg [9:0] p0_user;
    always @(posedge clk) begin
        if (!rn) begin p0_armb <= 1'b0; p0_armr <= 1'b0; p0_arm <= 1'b0; end
        else begin p0_armb <= is_armb; p0_armr <= is_armr; p0_arm <= is_arm; end
        p0_arg <= arg; p0_tag <= ctag; p0_user <= ad_d[82:73];
    end
    wire p_armb, p_armr, p_arm; wire [23:0] p_arg; wire [7:0] p_tag; wire [9:0] p_user;
    generate if (KP > 0) begin : g_pa
        reg [2:0] pa_c [0:KP-1]; reg [41:0] pa_q [0:KP-1]; integer qj;
        always @(posedge clk) begin
            if (!rn) for (qj = 0; qj < KP; qj = qj + 1) pa_c[qj] <= 3'd0;
            else begin pa_c[0] <= {p0_armb, p0_armr, p0_arm}; for (qj = 1; qj < KP; qj = qj + 1) pa_c[qj] <= pa_c[qj-1]; end
            pa_q[0] <= {p0_arg, p0_tag, p0_user}; for (qj = 1; qj < KP; qj = qj + 1) pa_q[qj] <= pa_q[qj-1];
        end
        assign {p_armb, p_armr, p_arm} = pa_c[KP-1]; assign {p_arg, p_tag, p_user} = pa_q[KP-1];
    end else begin : g_npa
        assign {p_armb, p_armr, p_arm} = {p0_armb, p0_armr, p0_arm}; assign {p_arg, p_tag, p_user} = {p0_arg, p0_tag, p0_user};
    end endgenerate
    reg [NSLOT-1:0] sl_arm, sl_dp, sl_rp, sl_ntf;
    reg [13:0] sl_base [0:NSLOT-1]; reg [14:0] sl_n [0:NSLOT-1]; reg [18:0] sl_need [0:NSLOT-1], sl_cnt [0:NSLOT-1];
    reg [9:0] sl_user [0:NSLOT-1]; reg [7:0] sl_tag [0:NSLOT-1];
    reg [13:0] st_base [0:NSLOT-1]; reg [14:0] st_n [0:NSLOT-1]; reg [NSLOT-1:0] st_ntf;    
    reg [NSLOT*NP-1:0] k_w, k_r;         
    reg [NP*5-1:0] k_pc;                 
    reg [NP-1:0] k_v, k_we;
    reg [NSLOT-1:0] k_ok;
    reg [NP-1:0] kq_v [0:KD-1], kq_we [0:KD-1]; reg [NP*RA-1:0] kq_row [0:KD-1]; reg [NP*16-1:0] kq_m [0:KD-1];
    reg [KD-1:0] kq_armb, kq_armr, kq_arm; reg [23:0] kq_arg [0:KD-1]; reg [7:0] kq_tag [0:KD-1]; reg [9:0] kq_user [0:KD-1];
    always @(posedge clk) begin : p_kq integer i;
        if (!rn) begin
            for (i = 0; i < KD; i = i + 1) kq_v[i] <= {NP{1'b0}};
            kq_armb <= {KD{1'b0}}; kq_armr <= {KD{1'b0}}; kq_arm <= {KD{1'b0}};
        end else begin
            kq_v[0] <= b_v; for (i = 1; i < KD; i = i + 1) kq_v[i] <= kq_v[i-1];
            kq_armb <= {kq_armb, p_armb}; kq_armr <= {kq_armr, p_armr}; kq_arm <= {kq_arm, p_arm};
        end
        kq_we[0] <= b_we; kq_row[0] <= b_row; kq_m[0] <= b_m; kq_arg[0] <= p_arg; kq_tag[0] <= p_tag; kq_user[0] <= p_user;
        for (i = 1; i < KD; i = i + 1) begin
            kq_we[i] <= kq_we[i-1]; kq_row[i] <= kq_row[i-1]; kq_m[i] <= kq_m[i-1];
            kq_arg[i] <= kq_arg[i-1]; kq_tag[i] <= kq_tag[i-1]; kq_user[i] <= kq_user[i-1];
        end
    end
    wire [NP-1:0] kb_v = kq_v[KD-1], kb_we = kq_we[KD-1]; wire [NP*RA-1:0] kb_row = kq_row[KD-1]; wire [NP*16-1:0] kb_m = kq_m[KD-1];
    wire k_armb = kq_armb[KD-1], k_armr = kq_armr[KD-1], k_arm = kq_arm[KD-1];
    wire [23:0] k_arg = kq_arg[KD-1]; wire [7:0] k_tag = kq_tag[KD-1]; wire [9:0] k_user = kq_user[KD-1];
    wire [1:0] k_s = k_arg[20:19];
    integer kk, b;
    reg [4:0] pc;
    reg [15:0] wm;
    always @(posedge clk) begin : p_l672 integer kk, q, b;
        for (q = 0; q < NP; q = q + 1) begin
            wm = kb_m[q*16 +: 16];
            pc = 5'd0; for (b = 0; b < 16; b = b + 1) pc = pc + {4'd0, wm[b]};
            k_pc[5*q +: 5] <= pc;
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                k_w[kk*NP + q] <= kb_v[q] && kb_we[q] && kb_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, kb_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
                k_r[kk*NP + q] <= kb_v[q] && !kb_we[q] && kb_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, kb_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
            end
        end
        if (!rn) k_v <= {NP{1'b0}}; else k_v <= kb_v;
        k_ok <= ~(k_arm ? ({{(NSLOT-1){1'b0}}, 1'b1} << k_s) : {NSLOT{1'b0}});
    end
    reg [7:0] k2_g [0:NSLOT*4-1]; reg [NSLOT-1:0] k2_hr;
    reg k2_arm; reg [1:0] k2_s; reg [18:0] k2_need; reg [7:0] k2_tag; reg [9:0] k2_user; reg k2_ntf;
    always @(posedge clk) begin : p_k2 integer kk, g, q; reg [7:0] a; reg h;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            h = 1'b0;
            for (g = 0; g < 4; g = g + 1) begin
                a = 8'd0;
                for (q = 7 * g; q < 7 * g + 7; q = q + 1) if (k_w[kk*NP + q]) a = a + {3'd0, k_pc[5*q +: 5]};
                k2_g[kk*4 + g] <= k_ok[kk] ? a : 8'd0;
            end
            for (q = 0; q < NP; q = q + 1) if (k_r[kk*NP + q]) h = 1'b1;
            k2_hr[kk] <= h && k_ok[kk];
        end
        if (!rn) k2_arm <= 1'b0; else k2_arm <= k_arm;
        k2_s <= k_s; k2_need <= k_arg[18:0]; k2_tag <= k_tag; k2_user <= k_user; k2_ntf <= st_ntf[k_s];
    end
    reg [9:0] inc [0:NSLOT-1];
    reg [NSLOT-1:0] hit_r, cmpl;
    always @* begin : p_l691 integer kk;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            inc[kk] = ({2'd0, k2_g[kk*4]} + {2'd0, k2_g[kk*4 + 1]}) + ({2'd0, k2_g[kk*4 + 2]} + {2'd0, k2_g[kk*4 + 3]});
            hit_r[kk] = k2_hr[kk];
            cmpl[kk] = sl_arm[kk] && sl_cnt[kk] + inc[kk] >= sl_need[kk];
        end
    end
    reg [7:0] pd_q [0:CQD]; reg [$clog2(CQD+2)-1:0] pd_h, pd_t, pd_n;
    reg early, ovf_cr, rearm, ovf_pd;
    reg [NSLOT-1:0] dsel, rsel;
    always @* begin : p_l709 integer kk;
        dsel = {NSLOT{1'b0}}; rsel = {NSLOT{1'b0}};
        for (kk = NSLOT - 1; kk >= 0; kk = kk - 1) begin
            if (sl_dp[kk]) dsel = {{(NSLOT-1){1'b0}}, 1'b1} << kk;
            if (sl_rp[kk]) rsel = {{(NSLOT-1){1'b0}}, 1'b1} << kk;
        end
    end
    wire d_slot = |sl_dp;                       
    wire d_p2 = !d_slot && pd_n != 0;
    wire d_x = !d_slot && !d_p2 && x_dp != 5'd0;
    reg [2:0] xsel; integer xq;
    always @* begin xsel = 3'd0; for (xq = 4; xq >= 0; xq = xq - 1) if (x_dp[xq]) xsel = xq[2:0]; end
    wire d_imm = !d_slot && !d_p2 && !d_x && imm_v;
    wire c_w_go = !c_wv[0] || c_wr[0];
    reg [7:0] dsel_tag; reg [9:0] rsel_user;
    always @* begin : p_l724 integer kk;
        dsel_tag = 8'd0; rsel_user = 10'd0;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            if (dsel[kk]) dsel_tag = dsel_tag | sl_tag[kk];
            if (rsel[kk]) rsel_user = rsel_user | sl_user[kk];
        end
    end
    always @(posedge clk) begin : p_l731 integer kk;
        if (!rn) begin
            sl_arm <= 0; sl_dp <= 0; sl_rp <= 0; sl_ntf <= 0; ed_v <= 1'b0; c_wv <= 1'b0; t_rdy <= 0; imm_v <= 1'b0; x_dp <= 5'd0;
            pd_h <= 0; pd_t <= 0; pd_n <= 0;
            early <= 1'b0; ovf_cr <= 1'b0; rearm <= 1'b0; ovf_pd <= 1'b0;
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin sl_base[kk] <= 14'd0; sl_n[kk] <= 15'd0; end
        end else begin
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                if (sl_arm[kk]) sl_cnt[kk] <= sl_cnt[kk] + {9'd0, inc[kk]};
                if (hit_r[kk] && sl_arm[kk] && !cmpl[kk]) early <= 1'b1;
                if (cmpl[kk]) begin sl_arm[kk] <= 1'b0; t_rdy[kk] <= 1'b1; end
            end
            if (k_armb) begin st_base[k_s] <= k_arg[13:0]; st_ntf[k_s] <= k_arg[18]; end
            if (k_armr) st_n[k_s] <= k_arg[14:0];
            if (k_arm) begin sl_base[k_s] <= st_base[k_s]; sl_n[k_s] <= st_n[k_s]; end    
            if (k2_arm) begin                                                             
                if (sl_arm[k2_s] || sl_dp[k2_s] || sl_rp[k2_s]) rearm <= 1'b1;
                sl_arm[k2_s] <= 1'b1; t_rdy[k2_s] <= 1'b0; sl_ntf[k2_s] <= k2_ntf; sl_user[k2_s] <= k2_user;
                sl_need[k2_s] <= k2_need; sl_cnt[k2_s] <= 19'd0; sl_tag[k2_s] <= k2_tag;
            end
            ed_v <= d_slot || d_p2 || d_x || d_imm;
            ed_t <= d_slot ? dsel_tag : d_p2 ? pd_q[pd_h] : d_x ? x_tag[xsel] : imm_t;
            x_dp <= (x_dp & ~(d_x ? (5'd1 << xsel) : 5'd0)) | x_last;
            sl_dp <= (sl_dp & ~(d_slot ? dsel : {NSLOT{1'b0}})) | cmpl;
            if (d_imm) imm_v <= 1'b0;
            if (acc && imm_op) begin imm_v <= 1'b1; imm_t <= ctag; end
            if (r_last) begin pd_q[pd_t] <= r_tag; pd_t <= (pd_t == CQD) ? 0 : pd_t + 1'b1; end
            if (d_p2) pd_h <= (pd_h == CQD) ? 0 : pd_h + 1'b1;
            pd_n <= pd_n + r_last - d_p2;
            if (r_last && pd_n == CQD + 1) ovf_pd <= 1'b1;
            if (c_w_go) begin
                c_wv <= |sl_rp; c_wd <= rsel_user;
                sl_rp <= (sl_rp & ~rsel) | (cmpl & sl_ntf);
            end else sl_rp <= sl_rp | (cmpl & sl_ntf);
            if (cr > P2D) ovf_cr <= 1'b1;
        end
    end
    reg [15:0] clf_q; reg so_q, ovr_q, sflt_q, err_q;
    always @(posedge clk) begin clf_q <= clf_i; so_q <= so_i; ovr_q <= ovr_i; sflt_q <= sflt_i; err_q <= err_i; end
    wire [3:0] clf = clf_q[3:0] | clf_q[7:4] | clf_q[11:8] | clf_q[15:12];
    (* keep = 1 *) reg [3:0] rf_k;
    always @* rf_o = rf_k;
    always @(posedge clk) begin
        if (!rn) fe_flt <= 16'd0;
        else fe_flt <= fe_flt | {so_q, ovr_q, ad_flt, cap_src_flt, clf, is_bad, ovf_pd, rearm, sflt_q, ovf_cr, 1'b0, err_q, early};
        rf_k <= {4{|fe_flt}};
    end
endmodule

module ot_s81_engine_adapter #(parameter integer QD=8, MUT=0, XRT=0)(
 input wire c_clk,c_rst_n,input wire c_cmd_v,input wire[83:0] c_cmd_d,
 output reg c_done_v,output reg[7:0] c_done_tag,output wire fault,output wire online,
 input wire e_clk,e_rst_n,output wire e_cmd_v,output wire[83:0] e_cmd_d,
 input wire e_cmd_ready,input wire e_inputs_present,
 input wire e_done_v,input wire[7:0] e_done_tag
);
 localparam integer CW=$clog2(QD+1);
 wire arst_n=c_rst_n&&e_rst_n;
 wire c_run,e_run,c_run0,e_run0;
 wire c_rcmd,c_rdone,e_rcmd,e_rdone;    
 ot_reset_sync u_cr(.clk(c_clk),.async_rst_n(arst_n),.sync_rst_n(c_run0));
 ot_reset_sync u_er(.clk(e_clk),.async_rst_n(arst_n),.sync_rst_n(e_run0));
 generate if(XRT!=0) begin:g_xrt
  (* keep=1 *) reg[2:0] c_rt; (* keep=1 *) reg[2:0] e_rt;
  always @(posedge c_clk or negedge c_run0) if(!c_run0) c_rt<=3'b000; else c_rt<=3'b111;
  always @(posedge e_clk or negedge e_run0) if(!e_run0) e_rt<=3'b000; else e_rt<=3'b111;
  assign c_run=c_rt[0]; assign c_rcmd=c_rt[1]; assign c_rdone=c_rt[2];
  assign e_run=e_rt[0]; assign e_rcmd=e_rt[1]; assign e_rdone=e_rt[2];
 end else begin:g_nxrt
  assign c_run=c_run0; assign c_rcmd=c_run0; assign c_rdone=c_run0;
  assign e_run=e_run0; assign e_rcmd=e_run0; assign e_rdone=e_run0;
 end endgenerate
 reg[255:0] cpending,epending;reg[CW-1:0] cused,eused;
 reg cf,ef;
 (* async_reg="true" *) reg ef_c1,ef_c2,eonline_c1,eonline_c2;
 assign online=c_run&&eonline_c2;
 assign fault=cf||ef_c2;
 wire[7:0] ctag={c_cmd_d[83],c_cmd_d[6:0]};
 wire cv,cr;wire[83:0] cd;wire cmd_accept,cmd_fault;
 wire dv,dr;wire[7:0] dt;wire done_accept,done_fault;
 reg dq_v; reg[7:0] dq_t;
 always @(posedge c_clk or negedge c_run) if(!c_run) dq_v<=1'b0; else dq_v<=dv;
 always @(posedge c_clk) dq_t<=dt;
 wire return_ok=dq_v&&cpending[dq_t]&&(cused!=0);
 wire admit=c_cmd_v&&cmd_accept&&!cpending[ctag]&&((cused<QD)||return_ok);
 wire[83:0] payload=(MUT==1)?(c_cmd_d^(84'd1<<73)):c_cmd_d;
 ot_s81_pulse_cdc #(.W(84),.QD(QD),.XR(XRT)
 ,.INPUT_PIPE(1)
 ) u_cmd(
 .s_clk(c_clk),.s_rst_n(c_rcmd),.i_v(admit),.i_d(payload),.i_accept(cmd_accept),.fault(cmd_fault),
 .d_clk(e_clk),.d_rst_n(e_rcmd),.o_v(cv),.o_r(cr),.o_d(cd)
 );
 reg rv; reg[83:0] rq;
 wire[7:0] etag={rq[83],rq[6:0]};
 assign e_cmd_d=rq;
 assign e_cmd_v=rv&&e_inputs_present&&!epending[etag]&&(eused<QD);
 wire take=e_cmd_v&&e_cmd_ready;
 assign cr=!rv||take;
 always @(posedge e_clk or negedge e_run) if(!e_run) rv<=1'b0; else if(cr) rv<=cv;
 always @(posedge e_clk) if(cr&&cv) rq<=cd;
 wire complete=e_done_v&&epending[e_done_tag]&&(eused!=0)&&done_accept;
 wire[7:0] completion=(MUT==2)?(e_done_tag^8'h80):e_done_tag;
 ot_s81_pulse_cdc #(.W(8),.QD(QD),.XR(XRT)) u_done(
 .s_clk(e_clk),.s_rst_n(e_rdone),.i_v(complete),.i_d(completion),.i_accept(done_accept),.fault(done_fault),
 .d_clk(c_clk),.d_rst_n(c_rdone),.o_v(dv),.o_r(dr),.o_d(dt)
 );
 assign dr=1'b1;
 always @(posedge c_clk or negedge c_run) begin
  if(!c_run) begin cpending<=0;cused<=0;cf<=0;c_done_v<=0;c_done_tag<=0;ef_c1<=0;ef_c2<=0;eonline_c1<=0;eonline_c2<=0;end
  else begin
   ef_c1<=ef;ef_c2<=ef_c1;eonline_c1<=e_run;eonline_c2<=eonline_c1;
   c_done_v<=return_ok;
   if(return_ok) begin c_done_tag<=dq_t;cpending[dq_t]<=0;end
   if(admit) cpending[ctag]<=1;
   case({admit,return_ok}) 2'b10:cused<=cused+1'b1;2'b01:cused<=cused-1'b1;default:cused<=cused;endcase
   if((c_cmd_v&&!admit)||(dq_v&&!return_ok)||cmd_fault) cf<=1;
  end
 end
 always @(posedge e_clk or negedge e_run) begin
  if(!e_run) begin epending<=0;eused<=0;ef<=0;end
  else begin
   if(complete) epending[e_done_tag]<=0;
   if(take) epending[etag]<=1;
   case({take,complete}) 2'b10:eused<=eused+1'b1;2'b01:eused<=eused-1'b1;default:eused<=eused;endcase
   if((e_done_v&&!complete)||(rv&&epending[etag])||done_fault) ef<=1;
  end
 end
endmodule

module ot_s81_pulse_cdc #(parameter integer W=84, QD=8, XR=0
 , parameter integer INPUT_PIPE=0
)(
 input wire s_clk,s_rst_n, input wire i_v,input wire[W-1:0] i_d,
 output wire i_accept,output reg fault,
 input wire d_clk,d_rst_n,output wire o_v,input wire o_r,output wire[W-1:0] o_d
);
 localparam integer AW=$clog2(QD);
 reg[W-1:0] q[0:QD-1]; reg[AW-1:0] wp,rp;reg[AW:0] count;
 wire fready;wire pop=(count!=0)&&fready;
 wire push=i_v&&i_accept;
 wire queue_push;wire[W-1:0] queue_data;
 generate if(INPUT_PIPE!=0) begin:g_input_pipe
  reg pending;reg[W-1:0] data_q;
  assign i_accept=((count+pending)<QD)||pop;
  always @(posedge s_clk or negedge s_rst_n)
   if(!s_rst_n) pending<=1'b0;else pending<=push;
  always @(posedge s_clk) data_q<=i_d;
  assign queue_push=pending;
  assign queue_data=data_q;
 end else begin:g_no_input_pipe
  assign i_accept=(count<QD)||pop;
  assign queue_push=push;assign queue_data=i_d;
 end endgenerate
 wire unused_over,unused_under;
 ot_async_fifo #(.WIDTH(W),.DEPTH(QD),.EXT_RST(XR)) u_fifo(
 .wr_clk(s_clk),.wr_rst_n(s_rst_n),.wr_valid(count!=0),.wr_ready(fready),.wr_data(q[rp]),.wr_overflow(unused_over),
 .rd_clk(d_clk),.rd_rst_n(d_rst_n),.rd_valid(o_v),.rd_ready(o_r),.rd_data(o_d),.rd_underflow(unused_under)
 );
 always @(posedge s_clk or negedge s_rst_n) begin
  if(!s_rst_n) begin wp<=0;rp<=0;count<=0;fault<=0;end
  else begin
   if(i_v&&!i_accept) fault<=1;
   if(queue_push) begin q[wp]<=queue_data;wp<=wp+1'b1;end
   if(pop) rp<=rp+1'b1;
   case({queue_push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
  end
 end
endmodule

module ot_async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 4,
    parameter integer EXT_RST = 0
) (
    input  wire             wr_clk,
    input  wire             wr_rst_n,
    input  wire             wr_valid,
    output wire             wr_ready,
    input  wire [WIDTH-1:0] wr_data,
    output reg              wr_overflow,
    input  wire             rd_clk,
    input  wire             rd_rst_n,
    output wire             rd_valid,
    input  wire             rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output reg              rd_underflow
);
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0)
            $error("ot_async_fifo DEPTH must be a power of two >= 4");
    end
    localparam integer ADDR_W = $clog2(DEPTH);
    localparam integer PTR_W = ADDR_W + 1;
    wire fifo_async_rst_n = wr_rst_n && rd_rst_n;
    wire wr_domain_rst_n;
    wire rd_domain_rst_n;
    generate if (EXT_RST != 0) begin : g_xr
        assign wr_domain_rst_n = wr_rst_n;
        assign rd_domain_rst_n = rd_rst_n;
    end else begin : g_ir
        ot_reset_sync wr_reset_conditioner (
            .clk(wr_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(wr_domain_rst_n));
        ot_reset_sync rd_reset_conditioner (
            .clk(rd_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(rd_domain_rst_n));
    end endgenerate
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [PTR_W-1:0] wr_bin, wr_gray;
    reg [PTR_W-1:0] rd_bin, rd_gray;
    (* async_reg = "true" *) reg [PTR_W-1:0] rd_gray_w1, rd_gray_w2;
    (* async_reg = "true" *) reg [PTR_W-1:0] wr_gray_r1, wr_gray_r2;
    reg wr_online, rd_online;
    (* async_reg = "true" *) reg rd_online_w1, rd_online_w2;
    (* async_reg = "true" *) reg wr_online_r1, wr_online_r2;
    reg wr_full, rd_empty;
    wire wr_fire = wr_valid && wr_ready;
    wire rd_fire = rd_valid && rd_ready;
    wire [PTR_W-1:0] wr_increment = {{(PTR_W-1){1'b0}},wr_fire};
    wire [PTR_W-1:0] wr_bin_next = wr_bin + wr_increment;
    wire [PTR_W-1:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
    wire [PTR_W-1:0] rd_increment = {{(PTR_W-1){1'b0}},rd_fire};
    wire [PTR_W-1:0] rd_bin_next = rd_bin + rd_increment;
    wire [PTR_W-1:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;
    wire wr_full_next;
    wire rd_empty_next;
    assign wr_full_next = (wr_gray_next ==
                           {~rd_gray_w2[PTR_W-1:PTR_W-2],
                            rd_gray_w2[PTR_W-3:0]});
    assign rd_empty_next = (rd_gray_next == wr_gray_r2);
    assign wr_ready = wr_domain_rst_n && rd_online_w2 && !wr_full;
    assign rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty;
    assign rd_data = mem[rd_bin[ADDR_W-1:0]];
    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n) begin
            rd_gray_w1 <= {PTR_W{1'b0}};
            rd_gray_w2 <= {PTR_W{1'b0}};
            rd_online_w1 <= 1'b0;
            rd_online_w2 <= 1'b0;
            wr_online <= 1'b0;
            wr_bin <= {PTR_W{1'b0}};
            wr_gray <= {PTR_W{1'b0}};
            wr_full <= 1'b0;
            wr_overflow <= 1'b0;
        end else begin
            wr_online <= 1'b1;
            rd_online_w1 <= rd_online;
            rd_online_w2 <= rd_online_w1;
            rd_gray_w1 <= rd_gray;
            rd_gray_w2 <= rd_gray_w1;
            if (wr_fire)
                mem[wr_bin[ADDR_W-1:0]] <= wr_data;
            wr_bin <= wr_bin_next;
            wr_gray <= wr_gray_next;
            wr_full <= wr_full_next;
        end
    end
    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n) begin
            wr_gray_r1 <= {PTR_W{1'b0}};
            wr_gray_r2 <= {PTR_W{1'b0}};
            wr_online_r1 <= 1'b0;
            wr_online_r2 <= 1'b0;
            rd_online <= 1'b0;
            rd_bin <= {PTR_W{1'b0}};
            rd_gray <= {PTR_W{1'b0}};
            rd_empty <= 1'b1;
            rd_underflow <= 1'b0;
        end else begin
            rd_online <= 1'b1;
            wr_online_r1 <= wr_online;
            wr_online_r2 <= wr_online_r1;
            wr_gray_r1 <= wr_gray;
            wr_gray_r2 <= wr_gray_r1;
            rd_bin <= rd_bin_next;
            rd_gray <= rd_gray_next;
            rd_empty <= rd_empty_next;
        end
    end
endmodule

module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;
    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end
    assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
endmodule

module ot_dsrom_mtp_rstsync (input wire clk, input wire rst_n_async, output wire rst_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n_async) if (!rst_n_async) s <= 2'b00; else s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule
