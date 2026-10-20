`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE6 10-19 (Q.STA.SLICE.2, plan claude/qw-slice5-1019 @961b2dafd results/arch/qw_slice5_1019): the NEW leaves of
// the hardened one-level slice qfd_dv_slice2_{w,e}.  qfd_dv_slice2 #(SU_TLS 1, SU_LT 1, HD_W130 1, MU_NU 4,
// PRIVATE_CALR 1) is cut, register for register, into these leaves plus the closed / gating ones (8 stnrgc
// qfd_dv_redstn2_region, 8 lane heads, 24 SFU tiles, 32 xs_leaf, stream + tload).  The wires-only flat parents are
// GENERATED (tools/qwen_dv/gen_slice5_flat.py):
//   qfd_dv_s5_flat0  every leaf HARD 0 (and stnrgc PIN_IN 0 / BT_LAT 0, the rs / nb pin registers in qfd_dv_s5_spin):
//                    cycle-exact == qfd_dv_slice2 at offset 0 on every output (tb_qfd_dv_s5_flat0, lockstep).
//   qfd_dv_s5_flat   every leaf at its defaults = the HARDENED configuration (what the kits build; no #() overrides).
// HARD 1 (default, the hard master) only adds registers where the HARD 0 cut is combinational (a leaf output that is not
// flop-launched); every such edge is listed per leaf below and in results/arch/qw_slice6_1019/README.md (compiler
// NOTICE lanes/QW-GEN3.md).  Values / arithmetic / order unchanged.
// Every leaf lands rst_n in its own two registered stages (rs1 -> rst) = qfd_dv_slice2's regional synchroniser, so
// every register of the re-cut releases on the same edge as in qfd_dv_slice2.
// =====================================================================================================================

// ---------------------------------------------------------------------------------------------------------- reset land
module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule

// ---------------------------------------------------------------------------------------------------------- dn face
// The slice face toward W5 (master W face of qfd_dv_slice2_w, E face of _e): pin registers of the inputs arriving from
// the dn neighbour, the outbound-chain merge register ch_dn_o (pass word wins) and the status OR register ag_dn_o.
// HARD 1: the pass/own collision flag pc_bad leaves through a register (+1 edge, sticky status only).
module qfd_dv_s5_fdn #(parameter integer HARD = 1) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [115:0]   cmd_i,
    input  wire [452:0]   hr_i,
    input  wire [1087:0]  st_up_i,
    input  wire [47:0]    sc_up_i,
    input  wire [1037:0]  ch_dn_i,
    input  wire [8:0]     treq_i,
    output reg  [115:0]   cmd_q,
    output reg  [452:0]   hr_q,
    output reg  [1087:0]  sw_q,
    output reg  [47:0]    scu_q,
    output reg  [1037:0]  chd_q,
    output reg  [8:0]     treq_q,
    // outbound chain: pass word (up-face pin register) or the own word (ctl)
    input  wire [1094:0]  chu_q,
    input  wire [1094:0]  own_ch,
    output reg  [1094:0]  ch_dn_o,
    output wire           pc_bad,
    input  wire [9:0]     agu_q,
    input  wire [9:0]     ag_own,
    output reg  [9:0]     ag_dn_o
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    always @(posedge ck or negedge rst)
        if (!rst) begin cmd_q <= 116'd0; hr_q <= 453'd0; sw_q <= 1088'd0; scu_q <= 48'd0; chd_q <= 1038'd0; treq_q <= 9'd0; end
        else begin cmd_q <= cmd_i; hr_q <= hr_i; sw_q <= st_up_i; scu_q <= sc_up_i; chd_q <= ch_dn_i; treq_q <= treq_i; end
    wire p_ar = chu_q[1094], p_dd = chu_q[547];
    always @(posedge ck or negedge rst)
        if (!rst) begin ch_dn_o <= 1095'd0; ag_dn_o <= 10'd0; end
        else begin
            ch_dn_o <= {p_ar ? chu_q[1094:548] : own_ch[1094:548], p_dd ? chu_q[547:0] : own_ch[547:0]};
            ag_dn_o <= agu_q | ag_own;
        end
    wire pc = (p_ar && own_ch[1094]) || (p_dd && own_ch[547]);
    generate if (HARD != 0) begin : g_h
        reg pq;
        always @(posedge ck or negedge rst) if (!rst) pq <= 1'b0; else pq <= pc;
        assign pc_bad = pq;
    end else begin : g_s
        assign pc_bad = pc;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------- up face
// The slice face toward E5: pin registers of the inputs arriving from the up neighbour and the SETID command forward
// register cmd_o (SETID increments the id it forwards).
module qfd_dv_s5_fup #(parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [1087:0]  st_dn_i,
    input  wire [47:0]    sc_dn_i,
    input  wire [1094:0]  ch_up_i,
    input  wire [9:0]     ag_up_i,
    output reg  [1087:0]  se_q,
    output reg  [47:0]    scd_q,
    output reg  [1094:0]  chu_q,
    output reg  [9:0]     agu_q,
    input  wire [115:0]   cmd_q,
    output reg  [115:0]   cmd_o
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    always @(posedge ck or negedge rst)
        if (!rst) begin se_q <= 1088'd0; scd_q <= 48'd0; chu_q <= 1095'd0; agu_q <= 10'd0; cmd_o <= 116'd0; end
        else begin
            se_q <= st_dn_i; scd_q <= sc_dn_i; chu_q <= ch_up_i; agu_q <= ag_up_i;
            cmd_o <= setid ? {cmd_q[115:8], cmd_q[7:4] + ((MUT == 10) ? 4'd0 : 4'd1), cmd_q[3:0]} : cmd_q;
        end
endmodule

// ---------------------------------------------------------------------------------------------------------- spin
// HARD 0 only (qfd_dv_s5_flat0): the rs_s / rs_n / l9 pin registers of qfd_dv_slice2.  In the hardened slice the closed
// stnrgc regions take these ports straight into their own PIN_IN registers (the same edge), so this leaf is absent.
module qfd_dv_s5_spin (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [1027:0]  rs_s,
    input  wire [1027:0]  rs_n,
    input  wire [513:0]   l9_i,
    output reg  [1027:0]  rss_q,
    output reg  [1027:0]  rsn_q,
    output reg  [513:0]   nb_q,
    output wire           stn_rst_n       // the slice synchroniser's reset for the 8 station regions (flat0 only)
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    assign stn_rst_n = rst;
    always @(posedge ck or negedge rst)
        if (!rst) begin rss_q <= 1028'd0; rsn_q <= 1028'd0; nb_q <= 514'd0; end
        else begin rss_q <= rs_s; rsn_q <= rs_n; nb_q <= l9_i; end
endmodule

// ---------------------------------------------------------------------------------------------------------- ctl
// qfd_dv_s5_ctl: the slice glue of qfd_dv_slice2 -- SETID latch, command decode, station / port configuration, the VM
// write merge (16-el and 1-el sources), XC collective command, ARX arm + cross-die argmax gather, own AR / D2D word
// builder, LM-head running argmax (qfd_dv_amax_mu), status st / ag terms and the port fault.
// HARD 1 (+1 edge each, compiler record): the decoded command bundles (stn_cfg, sc_cfg, stm_cfg, su_cmd), the argmax
// candidate (am_*), the VM writes (w16_*, w1_*), the own chain word (own_ch) and the ag term leave through registers.
module qfd_dv_s5_ctl #(parameter integer HARD = 1, parameter integer MUT = 0, parameter integer MU_NU = 4) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [115:0]   cmd_q,
    input  wire [1037:0]  chd_q,
    // station (region 0 copies + every region's data slice)
    input  wire           r_v,
    input  wire [7:0]     r_idx,
    input  wire           r_last,
    input  wire [511:0]   r_d,
    input  wire           l9o_v,          // l9_o[512]
    input  wire           stn_fault,
    // SU lane write ports (lane relay outputs)
    input  wire [7:0]     vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire [7:0]     kv_we,
    input  wire [8*24-1:0] kv_waddr,
    input  wire [8*32-1:0] kv_wdata,
    input  wire           su_nr,          // su_go && !su_ready (suvm)
    input  wire           su_idle,
    input  wire           su_fault,
    input  wire [15:0]    su_prog,
    input  wire [15:0]    su_rows,
    input  wire           vm_fault,
    // reducer
    input  wire           red_we,
    input  wire [23:0]    red_addr,
    input  wire [31:0]    red_data,
    // scalar tree
    input  wire           sc_w1_we,
    input  wire [23:0]    sc_w1_addr,
    input  wire [31:0]    sc_w1_data,
    input  wire           tok_v,
    input  wire [23:0]    tok_idx,
    input  wire           tok_own,
    input  wire [31:0]    tok_val,
    input  wire [1:0]     tok_user,
    input  wire           sc_busy,
    input  wire           sc_fault,
    input  wire           stm_fault,
    input  wire           tld_fault,
    input  wire           hd_fault,
    input  wire           pc_bad,
    // decoded command bundles
    output wire [3:0]     sid,
    output wire [28:0]    stn_cfg,        // {v, mode 2, wsrc, nwords 8, sbase 9, kcm1 8}
    output wire [100:0]   sc_cfg,         // {v, root, rdir, nb 6, ss 24, fuse, rx 24, eps 32, k 5, amnb 6}
    output wire [30:0]    stm_cfg,        // {v, dir 2, tag 28}
    output wire [9:0]     su_cmd,         // {c_su, p_idx 9}
    output wire           am_v,
    output wire [23:0]    am_idx,
    output wire [31:0]    am_val,
    output wire [1:0]     am_u,
    // VM writes
    output wire           w16_we,
    output wire [23:0]    w16_addr,
    output wire [511:0]   w16_data,
    output wire           w1_we,
    output wire [23:0]    w1_addr,
    output wire [31:0]    w1_data,
    // outbound chain own word and status
    output wire [1094:0]  own_ch,
    output wire [9:0]     ag_own,
    output reg  [106:0]   st,
    output reg  [49:0]    cc_o
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire [517:0] ar_q = chd_q[1037:520];
    wire [519:0] dd_q = chd_q[519:0];
    // ------------------------------------------------------------------ SETID latch
    reg  [3:0] sid_q; reg sid_ok;
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    always @(posedge ck or negedge rst)
        if (!rst) begin sid_q <= 4'd0; sid_ok <= 1'b0; end
        else if (setid) begin sid_q <= cmd_q[7:4]; sid_ok <= 1'b1; end
    assign sid = sid_q;
    // ------------------------------------------------------------------ command decode
    reg        arx_arm, g_arm, g_tok_v, g_fault; reg [1:0] g_user; reg [2:0] g_cnt; reg [55:0] g_best; reg [23:0] g_tok_idx; reg [31:0] g_tok_val;
    wire       go = cmd_q[0] && sid_ok && (cmd_q[115:112] == sid_q || cmd_q[115:112] == 4'hF) && cmd_q[3:1] != 3'd7;
    wire [2:0] kind = cmd_q[3:1];
    wire c_su = go && kind == 3'd1, c_stn = go && kind == 3'd2, c_root = go && kind == 3'd3,
         c_prt = go && kind == 3'd4, c_stm = go && kind == 3'd5;
    reg [23:0] stn_dbase; reg [1:0] stn_dst;
    reg [23:0] ar_base, dd_base, em_base; reg [7:0] ar_k, em_k; reg ar_en, dd_en, em_en;
    always @(posedge ck or negedge rst)
        if (!rst) begin stn_dbase <= 24'd0; stn_dst <= 2'd0; ar_base <= 24'd0; dd_base <= 24'd0; em_base <= 24'd0;
                        ar_en <= 1'b0; dd_en <= 1'b0; em_en <= 1'b0; end
        else begin
            if (c_stn) begin stn_dst <= cmd_q[25:24]; stn_dbase <= cmd_q[49:26]; end
            if (c_prt) begin ar_base <= cmd_q[27:4]; dd_base <= cmd_q[51:28]; ar_en <= cmd_q[52]; dd_en <= cmd_q[53];
                             em_base <= cmd_q[77:54]; em_en <= cmd_q[78]; end
        end
    wire [28:0]  stn_cfg_c = {c_stn, cmd_q[5:4], cmd_q[6], cmd_q[14:7], cmd_q[23:15], (MUT == 15) ? cmd_q[58:51] : cmd_q[66:59]};
    wire [100:0] sc_cfg_c  = {c_root, cmd_q[4], cmd_q[103], cmd_q[10:5], cmd_q[34:11], cmd_q[35], cmd_q[59:36], cmd_q[91:60],
                              cmd_q[96:92], cmd_q[102:97]};
    wire [30:0]  stm_cfg_c = {c_stm, cmd_q[5:4], cmd_q[33:6]};
    wire [9:0]   su_cmd_c  = {c_su, cmd_q[12:4]};
    // ------------------------------------------------------------------ SU write windows (lane 0's window, as qfd_dv_slice2)
    wire [1:0] win = vm_waddr[23:22];
    wire       sw_any = |vm_we;
    wire [7:0] su_q_we  = (sw_any && win == 2'b10) ? vm_we : 8'd0;
    wire       su_rb    = sw_any && win == 2'b11;
    wire       win_bad  = sw_any && win == 2'b11 && vm_we != 8'd1;
    wire [23:0] r_addr = stn_dbase + {12'd0, r_idx, 4'd0};
    wire        red_vm = red_we && red_addr[23:22] == 2'b00;
    wire        red_bad = red_we && red_addr[23:22] != 2'b11 && red_addr[23:22] != 2'b00;
    // ------------------------------------------------------------------ LM-head running argmax
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    wire am_emit_empty, am_mu_fault, am_stn_pend;
    wire am_v_c; wire [23:0] am_idx_c; wire [31:0] am_val_c; wire [1:0] am_u_c;
    qfd_dv_amax_mu #(.NU(MU_NU), .MUT(0)) u_amax (.ck(ck), .rst(rst), .c_stn(c_stn), .stn_amax_bit(cmd_q[50]), .stn_user(cmd_q[52:51]), .stn_pend(am_stn_pend),
        .r_v(r_v), .r_addr(r_addr), .r_d(r_d), .c_am(go && kind == 3'd6), .am_clr(cmd_q[4]), .am_emit_cmd(cmd_q[5]),
        .am_user(cmd_q[9:8]), .am_v(am_v_c), .am_idx(am_idx_c), .am_val(am_val_c), .am_u(am_u_c), .emit_empty(am_emit_empty), .mu_fault(am_mu_fault));
    // ------------------------------------------------------------------ VM write merge (16-el and 1-el sources)
    wire ar_v = ar_q[517] && ar_en && !g_arm, dd_v = dd_q[519] && !dd_q[518] && dd_en, em_v = dd_q[519] && dd_q[518] && em_en;
    wire [23:0] em_wa = em_base + {12'd0, em_k, 4'd0};
    wire st_vm = r_v && stn_dst[0];
    wire [23:0] ar_wa = ar_base + {12'd0, ar_k, 4'd0};
    wire [23:0] dd_wa = dd_base + {14'd0, dd_q[517:512], 4'd0};
    wire        w16_we_c = st_vm || ar_v || dd_v || em_v;
    wire [23:0] w16_addr_c = st_vm ? r_addr : ar_v ? ar_wa : dd_v ? dd_wa : em_wa;
    wire [511:0] w16_data_c = st_vm ? r_d : ar_v ? ar_q[511:0] : dd_q[511:0];
    wire        w16_coll = (st_vm && ar_v) || (st_vm && (dd_v || em_v)) || (ar_v && (dd_v || em_v));
    wire        w1_we_c = sc_w1_we || red_vm || su_rb;
    wire [23:0] w1_addr_c = sc_w1_we ? sc_w1_addr : red_vm ? red_addr : {2'b00, vm_waddr[21:0]};
    wire [31:0] w1_data_c = sc_w1_we ? sc_w1_data : red_vm ? red_data : vm_wdata[31:0];
    wire        w1_coll = (sc_w1_we && red_vm) || (sc_w1_we && su_rb) || (red_vm && su_rb);
    always @(posedge ck or negedge rst)
        if (!rst) begin ar_k <= 8'd0; em_k <= 8'd0; end
        else if (c_prt) begin ar_k <= 8'd0; em_k <= 8'd0; end
        else begin if (ar_v) ar_k <= ar_k + 8'd1; if (em_v) em_k <= em_k + 8'd1; end
    // ------------------------------------------------------------------ XC (kind 0): collective command (sub 0 COLL)
    wire c_xc = go && kind == 3'd0;
    always @(posedge ck or negedge rst)
        if (!rst) cc_o <= 50'd0;
        else cc_o <= (c_xc && cmd_q[5:4] == 2'd0) ?
                     {1'b1, (MUT == 11) ? cmd_q[7] : cmd_q[6], cmd_q[22:7], cmd_q[54:23]} : 50'd0;
    // ------------------------------------------------------------------ ARX arm and the cross-die argmax gather
    wire       c_am = go && kind == 3'd6;
    wire       arx_v = tok_own && arx_arm;
    wire [546:0] arx_w = {1'b1, {8'd0, tok_idx}, 1'b1, 1'b1, 456'd0, tok_idx, tok_val};
    wire       g_v = g_arm && ar_q[517];
    wire [55:0] g_in = ar_q[55:0];
    wire       g_take = (g_cnt == 3'd0) || okey(g_in[31:0]) > okey(g_best[31:0]) ||
                        ((MUT == 12) && okey(g_in[31:0]) == okey(g_best[31:0]));
    always @(posedge ck or negedge rst)
        if (!rst) begin arx_arm <= 1'b0; g_arm <= 1'b0; g_tok_v <= 1'b0; g_fault <= 1'b0; g_cnt <= 3'd0; g_user <= 2'd0;
                        g_best <= 56'd0; g_tok_idx <= 24'd0; g_tok_val <= 32'd0; end
        else begin
            g_tok_v <= 1'b0;
            if (c_am && cmd_q[6]) arx_arm <= 1'b1; else if (arx_v) arx_arm <= 1'b0;
            if (c_am && cmd_q[7]) begin g_arm <= 1'b1; g_cnt <= 3'd0; if (MU_NU > 1) g_user <= cmd_q[9:8]; end
            else if (g_v) begin
                if (g_take) g_best <= g_in;
                g_cnt <= g_cnt + 3'd1;
                if (ar_q[516] || ar_q[515:513] != g_cnt) g_fault <= 1'b1;
                if (ar_q[512]) begin
                    g_arm <= 1'b0; g_tok_v <= 1'b1; g_tok_idx <= g_take ? g_in[55:32] : g_best[55:32];
                    g_tok_val <= g_take ? g_in[31:0] : g_best[31:0];
                end
            end
        end
    // ------------------------------------------------------------------ own AR / D2D words (merged at the dn face)
    wire        q_any = |su_q_we, kv_any = |kv_we;
    wire [1:0]  kv_kind = kv_waddr[23:22];
    reg  [8*24-1:0] q_loc, kv_loc;
    integer l;
    always @(*) for (l = 0; l < 8; l = l + 1) begin
        q_loc[24*l +: 24] = {2'b00, vm_waddr[24*l +: 22]};
        kv_loc[24*l +: 24] = {2'b00, kv_waddr[24*l +: 22]};
    end
    wire        own_ar = r_v && stn_dst[1];
    wire [546:0] own_arw = {1'b1, {8'd0, r_addr}, 1'b0, r_last, r_d};      // mode 0: all-reduce
    wire        own_dd = kv_any || q_any;
    wire [547:0] own_ddw = kv_any ? {1'b1, kv_kind, kv_we, kv_loc, kv_wdata, 89'd0}
                                  : {1'b1, 2'd0, su_q_we, q_loc, vm_wdata, 89'd0};
    wire [1094:0] own_ch_c = {own_ar ? own_arw : arx_v ? arx_w : 547'd0, own_dd ? own_ddw : 548'd0};
    wire own_bad = own_ar && arx_v;                                       // the pass collisions: dn face pc_bad
    wire dd_bad = own_bad || pc_bad || (kv_any && q_any) || (kv_any && (kv_kind == 2'd0 || kv_kind == 2'd3));
    // ------------------------------------------------------------------ status and faults
    reg port_fault; reg [2:0] ar_rank; reg ar_last;
    always @(posedge ck or negedge rst)
        if (!rst) begin port_fault <= 1'b0; ar_rank <= 3'd0; ar_last <= 1'b0; end
        else begin
            port_fault <= port_fault | w16_coll | w1_coll | win_bad | red_bad | dd_bad | (ar_v && ar_q[516]) |
                          (c_xc && cmd_q[5:4] != 2'd0) | am_emit_empty | am_mu_fault | su_nr |
                          g_fault | (c_am && cmd_q[7] && g_arm);
            if (ar_v) begin ar_rank <= ar_q[515:513]; ar_last <= ar_q[512]; end
        end
    reg tok_g;
    wire tsel = g_tok_v || (tok_g && !tok_v);
    reg [31:0] tok_own_val;
    always @(posedge ck or negedge rst) if (!rst) tok_own_val <= 32'd0; else if (tok_v) tok_own_val <= tok_own ? tok_val : 32'd0;
    reg [8:0] stn_left; reg stn_snd;
    wire stn_busy = stn_left != 9'd0;
    assign am_stn_pend = stn_busy && !stn_snd && !(stn_left == 9'd1 && r_v);
    always @(posedge ck or negedge rst)
        if (!rst) begin stn_left <= 9'd0; stn_snd <= 1'b0; end
        else if (c_stn) begin stn_left <= {1'b0, cmd_q[14:7]}; stn_snd <= cmd_q[5:4] == 2'd3; end
        else if (stn_busy && (stn_snd ? l9o_v : r_v)) stn_left <= stn_left - 9'd1;
    always @(posedge ck or negedge rst) if (!rst) tok_g <= 1'b0; else if (g_tok_v) tok_g <= 1'b1; else if (tok_v) tok_g <= 1'b0;
    wire any_fault = su_fault | vm_fault | stn_fault | sc_fault | stm_fault | port_fault | hd_fault | tld_fault;
    wire [1:0] st_ru = (MU_NU > 1 && (tok_v || g_tok_v)) ? (tsel ? g_user : tok_user) : ar_rank[1:0];
    always @(posedge ck or negedge rst)
        if (!rst) st <= 107'd0;
        else st <= {ar_v, tsel ? g_tok_val : tok_v ? (tok_own ? tok_val : 32'd0) : tok_own_val, 4'd0 /* sid */, any_fault, su_fault, vm_fault, stn_fault, sc_fault, stm_fault, port_fault,
                    su_idle, sc_busy, su_prog, su_rows, ar_rank[2], st_ru, ar_last, tok_v || g_tok_v,
                    tsel ? g_tok_idx : tok_idx} | (107'(sid_q) << 70);
    wire [9:0] ag_own_c = {stn_busy, any_fault, su_fault, vm_fault, stn_fault, sc_fault, stm_fault, port_fault, !su_idle, sc_busy};
    // ------------------------------------------------------------------ outputs (HARD 1: one register each)
    localparam integer OW = 29 + 101 + 31 + 10 + 1 + 24 + 32 + 2 + 1 + 24 + 512 + 1 + 24 + 32 + 1095 + 10;
    wire [OW-1:0] o_c = {stn_cfg_c, sc_cfg_c, stm_cfg_c, su_cmd_c, am_v_c, am_idx_c, am_val_c, am_u_c,
                         w16_we_c, w16_addr_c, w16_data_c, w1_we_c, w1_addr_c, w1_data_c, own_ch_c, ag_own_c};
    wire [OW-1:0] o_q;
    generate if (HARD != 0) begin : g_h
        // valid / strobe bits reset, payload not (qualified by the valid)
        reg [OW-1:0] oq;
        always @(posedge ck or negedge rst) if (!rst) oq <= {OW{1'b0}}; else oq <= o_c;
        assign o_q = oq;
    end else begin : g_s
        assign o_q = o_c;
    end endgenerate
    assign {stn_cfg, sc_cfg, stm_cfg, su_cmd, am_v, am_idx, am_val, am_u,
            w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data, own_ch, ag_own} = o_q;
    initial if (MUT < 0 || (MUT > 12 && MUT != 15)) $fatal(1, "qfd_dv_s5_ctl: MUT %0d undefined", MUT);
endmodule

// ---------------------------------------------------------------------------------------------------------- suvm
// qfd_dv_s5_suvm: the SU issue control of qfd_dv_su8_entries (SW 8, LT/LTD/LOFF/RTREE 1, RD 2) -- issue loop, the kept
// group relay gb / gv (relay stage 1 of the broadcast fields), stage 1 of every lane's live / offset relay, progress,
// idle, fault -- and qfd_dv_vm without the station's BTAB copy (qfd_dv_s5_btab, beside the station).  The VM answers,
// the program word and the issue control are those of qfd_dv_slice2 edge for edge (ML 1, the program word 2 edges after
// its request).  HARD 1: su_nr (= su_go && !ready, the port-fault term) leaves through a register (+1, sticky status).
module qfd_dv_s5_suvm #(parameter integer HARD = 1, parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [9:0]     su_cmd,         // {c_su, p_idx 9}
    // group relay (stage 1) -> the 8 lane relays
    output wire [499:0]   gb,             // GBW = NW + (NW + 1) + 5 AW + 6 + 8 + 9 + 64 + WR 16 = 500
    output wire [2:0]     gv,
    output wire [7:0]     lv1,            // live, relay stage 1 (per lane)
    output wire [8*96-1:0] pd1,           // {cura, curb, curc, curd} + lane offsets, relay stage 1 (per lane)
    // lane relay outputs (to the VM / the issue control)
    input  wire [7:0]     va_re, vb_re, vc_re, cr_re, vm_we, kv_we, l_retire, l_last, l_fault, l_wrom_re,
    input  wire [8*24-1:0] va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, l_wrom_addr,
    input  wire [8*32-1:0] vm_wdata,
    output wire [8*32-1:0] va_q, vb_q, vc_q,
    output wire [8*64-1:0] cr_q,
    // reducer state (qfd_dv_s5_red)
    input  wire           rd_v,
    input  wire           red_busy,
    input  wire           red_fault,
    // VM writes from ctl / tables from the stream (+ tload)
    input  wire           w16_we,
    input  wire [23:0]    w16_addr,
    input  wire [511:0]   w16_data,
    input  wire           w1_we,
    input  wire [23:0]    w1_addr,
    input  wire [31:0]    w1_data,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data,
    output wire           su_nr,
    output reg            su_idle,
    output reg            su_fault,
    output reg  [15:0]    su_prog,
    output reg  [15:0]    su_rows,
    output wire           vm_fault
);
    localparam integer SW = 8, LS = 3, NW = 18, AW = 24, WR = 16;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg rc;                                                   // su8 RTREE control / reducer reset copy
    always @(posedge ck or negedge rst) if (!rst) rc <= 1'b0; else rc <= 1'b1;
    wire rst_c = rc;
    wire c_su = su_cmd[9];
    wire [456:0] si;
    wire su_go;
    ot_hdc_delay #(.W(1), .D(2), .RESET(1)) u_sug (.clk(ck), .rst_n(rst), .d(c_su), .q(su_go));
    wire [NW-1:0] i_nout = si[18:1], i_nin = si[36:19];
    wire          i_asrc = si[37], i_bsrc = si[110], i_csrc = si[183];
    wire [AW-1:0] i_abase = si[61:38], i_aso = si[85:62], i_asi = si[109:86];
    wire [AW-1:0] i_bbase = si[134:111], i_bso = si[158:135], i_bsi = si[182:159];
    wire [AW-1:0] i_cbase = si[207:184], i_cso = si[231:208], i_csi = si[255:232];
    wire [1:0]    i_ma = si[257:256], i_mb = si[259:258];
    wire [2:0]    i_ad = si[262:260], i_sfu = si[265:263];
    wire          i_mc = si[266], i_md = si[267];
    wire [1:0]    i_dst = si[269:268];
    wire [AW-1:0] i_dbase = si[293:270], i_dso = si[317:294], i_dsi = si[341:318];
    wire [1:0]    i_red = si[343:342];
    wire          i_redsq = si[344];
    wire [AW-1:0] i_rbase = si[368:345], i_rso = si[392:369];
    wire [31:0]   i_imm1 = si[424:393], i_imm2 = si[456:425];
    // -- issue loop: vectors (qfd_dv_su8_entries) --------------------------------------------------------------
    reg              active;
    reg [2:0]        cls;
    reg [7:0]        inflight;
    reg [NW-1:0]     o, v, nout_r, nin_r, nvec_r;
    reg              v_last_r, o_last_r;
    reg [NW:0]       fin_th;
    reg [AW-1:0]     rowa, rowb, rowc, rowd, cura, curb, curc, curd, rrow;
    reg [AW-1:0]     aso, asi, bso, bsi, cso, csi, dso, dsi, rso;
    reg              asrc, bsrc, csrc, mc, md, redsq;
    reg [1:0]        ma, mb, dst, red;
    reg [2:0]        ad;
    reg [31:0]       imm1, imm2;
    wire             retire = l_retire[0];
    wire             ready = !active && ((i_sfu == cls) || (inflight == 0));
    wire   accept = su_go;
    wire   emit = active;
    wire [NW-1:0] nvec_in = (i_nin + (SW - 1)) >> LS;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) begin
            active <= 1'b0; cls <= 3'd0; inflight <= 0;
        end else begin
            inflight <= inflight + (emit ? 8'd1 : 8'd0) - (retire ? 8'd1 : 8'd0);
            if (accept) begin
                active <= 1'b1; cls <= i_sfu;
            end else if (active && v_last_r && o_last_r) begin
                active <= 1'b0;
            end
        end
    end
    always @(posedge ck) begin
        if (accept) begin
            o <= 0; v <= 0; nout_r <= i_nout; nin_r <= i_nin; nvec_r <= nvec_in;
            v_last_r <= (nvec_in == 1); o_last_r <= (i_nout == 1);
            fin_th <= {1'b0, nvec_in} - 19'd8;
            rowa <= i_abase; cura <= i_abase; rowb <= i_bbase; curb <= i_bbase;
            rowc <= i_cbase; curc <= i_cbase; rowd <= i_dbase; curd <= i_dbase; rrow <= i_rbase;
            aso <= i_aso; asi <= i_asi; bso <= i_bso; bsi <= i_bsi; cso <= i_cso; csi <= i_csi;
            dso <= i_dso; dsi <= i_dsi; rso <= i_rso;
            asrc <= i_asrc; bsrc <= i_bsrc; csrc <= i_csrc; mc <= i_mc; md <= i_md;
            ma <= i_ma; mb <= i_mb; ad <= i_ad; dst <= i_dst; red <= i_red; redsq <= i_redsq;
            imm1 <= i_imm1; imm2 <= i_imm2;
        end else if (active) begin
            if (!v_last_r) begin
                v <= v + 1'b1; v_last_r <= (v + 2 == nvec_r);
                cura <= cura + (asi << LS); curb <= curb + (bsi << LS);
                curc <= curc + (csi << LS); curd <= curd + (dsi << LS);
            end else begin
                v <= 0; v_last_r <= (nvec_r == 1);
                o <= o + 1'b1; o_last_r <= (o + 2 == nout_r);
                rowa <= rowa + aso; cura <= rowa + aso; rowb <= rowb + bso; curb <= rowb + bso;
                rowc <= rowc + cso; curc <= rowc + cso; rowd <= rowd + dso; curd <= rowd + dso;
                rrow <= rrow + rso;
            end
        end
    end
    // -- the broadcast fields' group relay (kept), relay stage 1 ------------------------------------------------
    wire [WR*16-1:0] wrom_q;
    reg rg;
    always @(posedge ck or negedge rst) if (!rst) rg <= 1'b0; else rg <= 1'b1;
    (* keep *) reg [499:0] gbr;
    (* keep *) reg [2:0]   gvr;
    always @(posedge ck or negedge rg) if (!rg) gvr <= 3'd0; else gvr <= {emit, accept, v_last_r};
    always @(posedge ck) gbr <= {v, fin_th, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                                 ma, mb, dst, red, ad, cls, i_sfu, imm1, imm2, wrom_q};
    assign gb = gbr;
    assign gv = gvr;
    // -- per lane: stage 1 of the live / offset relays (su8 u_lv / u_pd, RD 2) ---------------------------------
    // (the lane reset of su8 RTREE is one register from the slice reset = rst_c here: the same release edge)
`ifdef OT_S5_LOFF_MUT
    localparam integer LMUT = 1;      // bench mutant: the lane offset applied twice (must FAIL the lockstep)
`else
    localparam integer LMUT = 0;
`endif
    genvar gl;
    generate for (gl = 0; gl < SW; gl = gl + 1) begin : g_lane
        wire live = ({1'b0, v} << LS) + gl < {1'b0, nin_r};
        wire [AW-1:0] tcura = cura + gl * asi + LMUT * gl * asi, tcurb = curb + gl * bsi;
        wire [AW-1:0] tcurc = curc + gl * csi, tcurd = curd + gl * dsi;
        ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_lv (.clk(ck), .rst_n(rst_c), .d(live), .q(lv1[gl]));
        ot_hdc_delay #(.W(4*AW), .D(1)) u_pd (.clk(ck), .rst_n(rst_c), .d({tcura, tcurb, tcurc, tcurd}), .q(pd1[96*gl +: 96]));
    end endgenerate
    // -- progress / idle / fault (qfd_dv_su8_entries) ----------------------------------------------------------
    reg [15:0] n_emit, n_retire, first_mark;
    wire [15:0] done_n = n_retire - first_mark;
    reg [15:0] r_emit, r_retire, r_mark;
    wire [15:0] rdone_n = r_retire - r_mark;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) begin
            n_emit <= 0; n_retire <= 0; first_mark <= 0; su_prog <= 0;
            r_emit <= 0; r_retire <= 0; r_mark <= 0; su_rows <= 0;
        end else begin
            n_emit <= n_emit + (emit ? 16'd1 : 16'd0);
            n_retire <= n_retire + (retire ? 16'd1 : 16'd0);
            r_emit <= r_emit + ((emit && v_last_r) ? 16'd1 : 16'd0);
            r_retire <= r_retire + ((retire && l_last[0]) ? 16'd1 : 16'd0);
            if (accept) begin
                first_mark <= n_emit; su_prog <= 0;
                r_mark <= r_emit; su_rows <= 0;
            end else begin
                su_prog <= done_n[15] ? 16'd0 : done_n;
                su_rows <= rdone_n[15] ? 16'd0 : rdone_n;
            end
        end
    end
    wire idle_c = !active && inflight == 0 && !(|vm_we) && !(|kv_we) && !rd_v && !red_busy;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) su_idle <= 1'b1;
        else su_idle <= idle_c && !(accept);
    end
    reg fault_q;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) begin fault_q <= 1'b0; su_fault <= 1'b0; end
        else begin
            fault_q <= fault_q || (su_go && !ready) || (|l_fault) || red_fault;
            su_fault <= fault_q;
        end
    end
    wire nr_c = su_go && !ready;
    generate if (HARD != 0) begin : g_h
        reg nq;
        always @(posedge ck or negedge rst) if (!rst) nq <= 1'b0; else nq <= nr_c;
        assign su_nr = nq;
    end else begin : g_s
        assign su_nr = nr_c;
    end endgenerate
    // -- VM: the SU writes of window 00, the lane-0 weight-ROM read ---------------------------------------------
    wire [7:0] su_vm_we = (|vm_we && vm_waddr[23:22] == 2'b00) ? vm_we : 8'd0;
    qfd_dv_s5_vm #(.MUT(MUT)) u_vm (.ck(ck), .rst_n(rst),
        .a_re(va_re), .b_re(vb_re), .c_re(vc_re), .a_addr(va_addr), .b_addr(vb_addr), .c_addr(vc_addr),
        .a_q(va_q), .b_q(vb_q), .c_q(vc_q),
        .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
        .bs_re(l_wrom_re[0]), .bs_addr(l_wrom_addr[0 +: AW]), .bs_q(wrom_q),
        .p_re(c_su), .p_idx(su_cmd[8:0]), .p_q(si),
        .su_we(su_vm_we), .su_waddr(vm_waddr), .su_wdata(vm_wdata),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(vm_fault));
endmodule

// ---------------------------------------------------------------------------------------------------------- lrly
// qfd_dv_s5_lrly: ONE lane's relay stages (qfd_dv_su8_entries LTD lane: broadcast fields RD - 1, live / offsets RD
// (stage 1 in suvm), memory answers RD - 1, read requests RD - 1, results RD) and the qfd_dv_su_lane glue (IREG / OREG
// pin flops, its reset register).  Placed at the path midpoint between suvm and its lane cell; one master x 8, no
// parameters in the slice.  The lane head (closed lane_h) and its 3 SFU tiles are its neighbours (r_su).
module qfd_dv_s5_lrly #(parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    // from suvm
    input  wire [499:0]   gb,
    input  wire [2:0]     gv,
    input  wire           lv1,
    input  wire [95:0]    pd1,
    input  wire [31:0]    va_q, vb_q, vc_q,
    input  wire [63:0]    cr_q,
    // to the lane head (its input pins) and the head's reset
    output wire           h_rst_n,
    output wire           c_emit0, c_live, c_ilast, c_accept,
    output wire [17:0]    c_i,
    output wire [18:0]    c_fin_th,
    output wire [23:0]    c_cura, c_curb, c_curc, c_curd, c_rrow, c_asi, c_bsi, c_csi, c_dsi,
    output wire           c_asrc, c_bsrc, c_csrc, c_mc, c_md, c_redsq,
    output wire [1:0]     c_ma, c_mb, c_dst, c_red,
    output wire [2:0]     c_ad, c_cls, c_isfu,
    output wire [31:0]    c_imm1, c_imm2,
    output wire [31:0]    c_va, c_vb, c_vc,
    output wire [255:0]   c_wrom,
    output wire [63:0]    c_crom,
    // from the lane head (its output pins)
    input  wire           h_va_re, h_vb_re, h_vc_re, h_wrom_re, h_crom_re, h_vm_we, h_kv_we, h_l_ov, h_l_redsq, h_l_last,
                          h_retire, h_l_fault,
    input  wire [23:0]    h_va_addr, h_vb_addr, h_vc_addr, h_wrom_addr, h_crom_addr, h_vm_waddr, h_kv_waddr, h_l_raddr,
    input  wire [31:0]    h_vm_wdata, h_kv_wdata, h_l_out,
    input  wire [1:0]     h_l_red,
    // results / requests (to suvm, ctl, red, stream)
    output wire           va_re, vb_re, vc_re, wrom_re, crom_re, vm_we, kv_we, l_ov, l_last, retire, l_fault, l_redsq,
    output wire [23:0]    va_addr, vb_addr, vc_addr, wrom_addr, crom_addr, vm_waddr, kv_waddr, l_raddr,
    output wire [31:0]    vm_wdata, kv_wdata, l_out,
    output wire [1:0]     l_red
);
    localparam integer WR = 16, AW = 24, NW = 18, RD = 2, GBW = 500;
    wire rst;
    qfd_dv_s5_rst2 u_rlz (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg rl;                                       // su8 RTREE lane reset register
    always @(posedge ck or negedge rst) if (!rst) rl <= 1'b0; else rl <= 1'b1;
    wire rst_l = rl;
    // ---- su8 LTD inbound relays (AC 1: the answers one stage, the broadcast wrom row none)
    wire [GBW-1:0] b_q;
    wire [2:0]     bv_q;
    wire           lv_q;
    wire [95:0]    pd_q;
    wire [159:0]   pa_q;
    ot_hdc_delay #(.W(GBW - WR*16), .D(RD - 1)) u_bd (.clk(ck), .rst_n(rst_l), .d(gb[GBW-1:WR*16]), .q(b_q[GBW-1:WR*16]));
    assign b_q[WR*16-1:0] = gb[WR*16-1:0];
    ot_hdc_delay #(.W(3), .D(RD - 1), .RESET(1)) u_bv (.clk(ck), .rst_n(rst_l), .d(gv), .q(bv_q));
    ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_lv (.clk(ck), .rst_n(rst_l), .d(lv1), .q(lv_q));
    ot_hdc_delay #(.W(96), .D(1)) u_pd (.clk(ck), .rst_n(rst_l), .d(pd1), .q(pd_q));
`ifdef OT_S5_LRLY_MUT
    localparam integer AD = 0;    // bench mutant: the memory answers skip their relay stage (one edge early: must FAIL)
`else
    localparam integer AD = 1;
`endif
    ot_hdc_delay #(.W(160), .D(AD)) u_pa (.clk(ck), .rst_n(rst_l), .d({va_q, vb_q, vc_q, cr_q}), .q(pa_q));
    wire [NW-1:0] t_i; wire [NW:0] t_fin; wire [AW-1:0] t_rrow, t_asi, t_bsi, t_csi, t_dsi;
    wire t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq; wire [1:0] t_ma, t_mb, t_dst, t_red;
    wire [2:0] t_ad, t_cls, t_isfu; wire [31:0] t_imm1, t_imm2; wire [WR*16-1:0] t_wrom;
    assign {t_i, t_fin, t_rrow, t_asi, t_bsi, t_csi, t_dsi, t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq,
            t_ma, t_mb, t_dst, t_red, t_ad, t_cls, t_isfu, t_imm1, t_imm2, t_wrom} = b_q;
    // ---- qfd_dv_su_lane glue: reset register, IREG (valid bits reset, data none), OREG
    reg rsr;
    always @(posedge ck or negedge rst_l) if (!rst_l) rsr <= 1'b0; else rsr <= 1'b1;
    wire rs = rsr;
    assign h_rst_n = rs;
    localparam integer IVB = 4;
    localparam integer IDB = NW + (NW + 1) + 9*AW + 6 + 8 + 3 + 64 + 3 + 3 + 3*32 + WR*16 + 64;
    wire [IVB-1:0] pv = {bv_q[2], lv_q, bv_q[0], bv_q[1]};
    wire [IDB-1:0] pdw = {t_i, t_fin, pd_q[95 -: AW], pd_q[71 -: AW], pd_q[47 -: AW], pd_q[23 -: AW], t_rrow, t_asi, t_bsi,
                          t_csi, t_dsi, t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq, t_ma, t_mb, t_dst, t_red, t_ad, t_imm1,
                          t_imm2, t_cls, t_isfu, pa_q[159 -: 32], pa_q[127 -: 32], pa_q[95 -: 32], t_wrom, pa_q[63:0]};
    (* keep *) reg [IVB-1:0] ivr;
    (* keep *) reg [IDB-1:0] idr;
    always @(posedge ck or negedge rs) if (!rs) ivr <= {IVB{1'b0}}; else ivr <= pv;
    always @(posedge ck) idr <= pdw;
    assign {c_emit0, c_live, c_ilast, c_accept} = ivr;
    assign {c_i, c_fin_th, c_cura, c_curb, c_curc, c_curd, c_rrow, c_asi, c_bsi, c_csi, c_dsi, c_asrc, c_bsrc, c_csrc, c_mc,
            c_md, c_redsq, c_ma, c_mb, c_dst, c_red, c_ad, c_imm1, c_imm2, c_cls, c_isfu, c_va, c_vb, c_vc, c_wrom,
            c_crom} = idr;
    localparam integer OVB = 12;
    localparam integer ODB = 8*AW + 3*32 + 2;
    wire [OVB-1:0] hv = {h_va_re, h_vb_re, h_vc_re, h_wrom_re, h_crom_re, h_vm_we, h_kv_we, h_l_ov, h_l_redsq, h_l_last,
                         h_retire, h_l_fault};
    wire [ODB-1:0] hd = {h_va_addr, h_vb_addr, h_vc_addr, h_wrom_addr, h_crom_addr, h_vm_waddr, h_kv_waddr, h_l_raddr,
                         h_vm_wdata, h_kv_wdata, h_l_out, h_l_red};
    (* keep *) reg [OVB-1:0] ovr;
    (* keep *) reg [ODB-1:0] odr;
    always @(posedge ck or negedge rs) if (!rs) ovr <= {OVB{1'b0}}; else ovr <= hv;
    always @(posedge ck) odr <= hd;
    wire t_va_re, t_vb_re, t_vc_re, t_wrom_re, t_crom_re, t_vm_we, t_kv_we, t_l_ov, t_l_redsq, t_l_last, t_retire, t_l_fault;
    wire [AW-1:0] t_va_addr, t_vb_addr, t_vc_addr, t_wrom_addr, t_crom_addr, t_vm_waddr, t_kv_waddr, t_l_raddr;
    wire [31:0] t_vm_wdata, t_kv_wdata, t_l_out; wire [1:0] t_l_red;
    assign {t_va_re, t_vb_re, t_vc_re, t_wrom_re, t_crom_re, t_vm_we, t_kv_we, t_l_ov, t_l_redsq, t_l_last, t_retire, t_l_fault} = ovr;
    assign {t_va_addr, t_vb_addr, t_vc_addr, t_wrom_addr, t_crom_addr, t_vm_waddr, t_kv_waddr, t_l_raddr, t_vm_wdata,
            t_kv_wdata, t_l_out, t_l_red} = odr;
    // ---- su8 LTD outbound relays (AQ 1: the five read requests one stage, the rest RD)
    localparam integer OVW = 11;
    localparam integer ODW = 7*AW + 2*32 + 32 + 2 + 1 + AW;
    wire [OVW-1:0] o_v = {t_va_re, t_vb_re, t_vc_re, t_wrom_re, t_crom_re, t_vm_we, t_kv_we, t_l_ov, t_l_last, t_retire, t_l_fault};
    wire [ODW-1:0] o_d = {t_va_addr, t_vb_addr, t_vc_addr, t_wrom_addr, t_crom_addr, t_vm_waddr, t_vm_wdata, t_kv_waddr,
                          t_kv_wdata, t_l_out, t_l_red, t_l_redsq, t_l_raddr};
    wire [OVW-1:0] o_vq;
    wire [ODW-1:0] o_dq;
    ot_hdc_delay #(.W(5), .D(RD - 1), .RESET(1)) u_ovr (.clk(ck), .rst_n(rst_l), .d(o_v[10:6]), .q(o_vq[10:6]));
    ot_hdc_delay #(.W(OVW - 5), .D(RD), .RESET(1)) u_ov (.clk(ck), .rst_n(rst_l), .d(o_v[5:0]), .q(o_vq[5:0]));
    ot_hdc_delay #(.W(5*AW), .D(RD - 1)) u_odr (.clk(ck), .rst_n(rst_l), .d(o_d[ODW-1 -: 5*AW]), .q(o_dq[ODW-1 -: 5*AW]));
    ot_hdc_delay #(.W(ODW - 5*AW), .D(RD)) u_od (.clk(ck), .rst_n(rst_l), .d(o_d[ODW-5*AW-1:0]), .q(o_dq[ODW-5*AW-1:0]));
    assign {va_re, vb_re, vc_re, wrom_re, crom_re, vm_we, kv_we, l_ov, l_last, retire, l_fault} = o_vq;
    assign {va_addr, vb_addr, vc_addr, wrom_addr, crom_addr, vm_waddr, vm_wdata, kv_waddr, kv_wdata, l_out, l_red, l_redsq,
            l_raddr} = o_dq;
endmodule

// ---------------------------------------------------------------------------------------------------------- red
// qfd_dv_s5_red: the SU reducer of qfd_dv_su8_entries (input registers rd_* + ot_hdc_vreduce SW 8 LV 4, R-ARITH).
module qfd_dv_s5_red (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [7:0]     l_ov,
    input  wire [8*32-1:0] l_out,
    input  wire [1:0]     l_red0,
    input  wire           l_redsq0,
    input  wire           l_last0,
    input  wire [23:0]    l_raddr0,
    output wire           red_we,
    output wire [23:0]    red_addr,
    output wire [31:0]    red_data,
    output reg            rd_v,
    output wire           busy,
    output wire           fault
);
    localparam integer SW = 8, AW = 24;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg rc;
    always @(posedge ck or negedge rst) if (!rst) rc <= 1'b0; else rc <= 1'b1;
    wire rst_c = rc;
    reg              rd_mx, rd_sq, rd_last;
    reg [AW-1:0]     rd_addr;
    reg [SW*32-1:0]  rd_x;
    integer li;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) rd_v <= 1'b0;
        else rd_v <= l_ov[0] && l_red0 != 2'd0;
    end
    always @(posedge ck) begin
`ifdef OT_S5_RED_MUT
        rd_mx <= (l_red0 == 2'd1); rd_sq <= l_redsq0; rd_last <= l_last0; rd_addr <= l_raddr0;   // bench mutant: SUM taken as MAX (must FAIL)
`else
        rd_mx <= (l_red0 == 2'd2); rd_sq <= l_redsq0; rd_last <= l_last0; rd_addr <= l_raddr0;
`endif
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= l_ov[li] ? l_out[32*li +: 32] : (l_red0 == 2'd2) ? l_out[31:0] : 32'd0;
    end
    ot_hdc_vreduce #(.SW(SW), .LV(4), .AW(AW)) u_red (.clk(ck), .rst_n(rst_c), .v_in(rd_v), .mx_in(rd_mx),
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(busy), .fault(fault));
endmodule

// ---------------------------------------------------------------------------------------------------------- sc
// qfd_dv_s5_sc: the slice scalar face qfd_dv_scalar2 (MU_NU 4) with its two local taps decoded here: the reducer's
// PSUM window (red_addr[23:22] = 11) and the SU broadcast scalar (lane write window 11, lane 0).
module qfd_dv_s5_sc #(parameter integer MUT = 0, parameter integer MU_NU = 4) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [100:0]   sc_cfg,
    input  wire [47:0]    dn_i,
    output wire [47:0]    dn_o,
    input  wire [47:0]    up_i,
    output wire [47:0]    up_o,
    input  wire           red_we,
    input  wire [23:0]    red_addr,
    input  wire [31:0]    red_data,
    input  wire [7:0]     vm_we,
    input  wire [1:0]     vm_win0,         // lane 0 vm_waddr[23:22]
    input  wire [31:0]    vm_wdata0,
    input  wire           am_v,
    input  wire [23:0]    am_idx,
    input  wire [31:0]    am_val,
    input  wire [1:0]     am_u,
    output wire           w1_we,
    output wire [23:0]    w1_addr,
    output wire [31:0]    w1_data,
    output wire           tok_v,
    output wire [23:0]    tok_idx,
    output wire           tok_own,
    output wire [31:0]    tok_val,
    output wire [1:0]     tok_user,
    output wire           busy,
    output wire           fault
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire red_ps = red_we && red_addr[23:22] == 2'b11;
`ifdef OT_S5_SC_MUT
    wire su_rb = (|vm_we) && vm_win0 == 2'b10;     // bench mutant: the broadcast scalar tap reads window 10 (must FAIL)
`else
    wire su_rb = (|vm_we) && vm_win0 == 2'b11;
`endif
    wire c_root = sc_cfg[100];
    qfd_dv_scalar2 #(.MUT(MUT), .MU_NU(MU_NU), .MU_MUT(0)) u_sc (.ck(ck), .rst_n(rst),
        .cfg_v(c_root), .cfg_root(sc_cfg[99]), .cfg_rdir(sc_cfg[98]), .cfg_nb(sc_cfg[97:92]), .cfg_ss(sc_cfg[91:68]),
        .cfg_fuse(sc_cfg[67]), .cfg_rx(sc_cfg[66:43]), .cfg_eps(sc_cfg[42:11]), .cfg_k(sc_cfg[10:6]), .cfg_amnb(sc_cfg[5:0]),
        .dn_i(dn_i), .dn_o(dn_o), .up_i(up_i), .up_o(up_o),
        .ps_v(red_ps), .ps_idx({2'b00, red_addr[21:0]}), .ps_val(red_data),
        .rb_v(su_rb), .rb_val(vm_wdata0),
        .am_v(am_v), .am_idx(am_idx), .am_val(am_val), .am_u(am_u),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .tok_v(tok_v), .tok_idx(tok_idx),
        .tok_own(tok_own), .tok_val(tok_val), .tok_user(tok_user),
        .busy(busy), .fault(fault));
endmodule

// ---------------------------------------------------------------------------------------------------------- stm
// qfd_dv_s5_stm: LABELLED STAND-IN for the stream tile (QW-STREAM2 qfd_dv_stream_t2 / t2c gating) + the tload tile
// (QW-TLOAD2 qfd_dv_slice_tload_ns3 / ns3b): qfd_dv_stream + qfd_dv_slice_tload as in qfd_dv_slice2 (PRIVATE_CALR 1)
// with the SU x-window decode (lane write window 01).  HARD 1: the joined table write tw_* leaves through a register
// (+1 edge on every table write; static exclusive window, f16_calr_edges).
module qfd_dv_s5_stm #(parameter integer HARD = 1, parameter integer MUT = 0, parameter integer TSLICE = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire [30:0]    stm_cfg,
    input  wire [1087:0]  sw_i,
    input  wire [1087:0]  se_i,
    output wire [1087:0]  so_e,
    output wire [1087:0]  so_w,
    input  wire [7:0]     vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire [8:0]     treq_i,
    output wire           tw_we,
    output wire [1:0]     tw_kind,
    output wire [23:0]    tw_addr,
    output wire [1023:0]  tw_data,
    output wire           xt_v,
    output wire [23:0]    xt_a,
    output wire [1023:0]  xt_d,
    output wire           xt_bad,
    output wire           stm_fault,
    output wire           tld_fault
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire [7:0] su_x_we = (|vm_we && vm_waddr[23:22] == 2'b01) ? vm_we : 8'd0;
    wire        stm_tw_we;
    wire [1:0]  stm_tw_kind;
    wire [23:0] stm_tw_addr;
    wire [1023:0] stm_tw_data;
    qfd_dv_stream #(.MUT(MUT)) u_stm (.ck(ck), .rst_n(rst), .sid(sid),
        .cfg_v(stm_cfg[30]), .cfg_dir(stm_cfg[29:28]), .cfg_tag(stm_cfg[27:0]),
        .sw_i(sw_i), .se_i(se_i), .so_e(so_e), .so_w(so_w),
        .xw_we(su_x_we), .xw_addr(vm_waddr), .xw_data(vm_wdata),
        .tw_we(stm_tw_we), .tw_kind(stm_tw_kind), .tw_addr(stm_tw_addr), .tw_data(stm_tw_data),
        .xt_v(xt_v), .xt_a(xt_a), .xt_d(xt_d), .xt_bad(xt_bad), .fault(stm_fault));
    wire        j_we;
    wire [1:0]  j_kind;
    wire [23:0] j_addr;
    wire [1023:0] j_data;
    qfd_dv_slice_tload #(.SLICE(TSLICE)) u_tld (.ck(ck), .rst_n(rst), .treq(treq_i),
        .s_we(stm_tw_we), .s_kind(stm_tw_kind), .s_addr(stm_tw_addr), .s_data(stm_tw_data),
        .tw_we(j_we), .tw_kind(j_kind), .tw_addr(j_addr), .tw_data(j_data), .busy(), .done(), .fault(tld_fault));
    generate if (HARD != 0) begin : g_h
        reg twv; reg [1:0] twk; reg [23:0] twa; reg [1023:0] twd;
        always @(posedge ck or negedge rst) if (!rst) twv <= 1'b0; else twv <= j_we;
        always @(posedge ck) begin twk <= j_kind; twa <= j_addr; twd <= j_data; end
        assign tw_we = twv; assign tw_kind = twk; assign tw_addr = twa; assign tw_data = twd;
    end else begin : g_s
        assign tw_we = j_we; assign tw_kind = j_kind; assign tw_addr = j_addr; assign tw_data = j_data;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------- btab
// qfd_dv_s5_btab: the station's copy of the VM BF16 table (qfd_dv_vm BTAB copy 0: 4 banks x 128 x 256, written 4 words
// an edge by a table write of kind 2), placed beside station region 0 (which issues bt_re / bt_word), so the closed
// stnrgc BT_LAT 1 round trip (bt pin register) holds with no landing in the loop.  Answers 2 edges after bt_re, as
// qfd_dv_vm.  The SU's copy (copy 1, the weight-ROM operand port) stays in qfd_dv_s5_vm.  Write faults are counted by
// the VM (same tw_* stream), so this leaf has none of its own.
module qfd_dv_s5_btab (
    input  wire           ck,
    input  wire           bt_re,
    input  wire [8:0]     bt_word,
    output wire [255:0]   bt_q,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data
);
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [4*256-1:0] bt_rd;
    genvar bk;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(bt_re && bt_word[1:0] == bk[1:0]), .r_addr_in(bt_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
            .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] t1_bank, t2_bank;
    reg [1023:0] btcap;
    always @(posedge ck) begin t1_bank <= bt_word[1:0]; btcap <= bt_rd; t2_bank <= t1_bank; end
`ifdef OT_S5_BTAB_MUT
    assign bt_q = btcap[256*(t2_bank ^ 2'd1) +: 256];   // bench mutant: the answer from the neighbour bank (must FAIL)
`else
    assign bt_q = btcap[256*t2_bank +: 256];
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------- tap
// qfd_dv_s5_tap: the heads' fill tap ot_qfd_xs_tap (STATIC_SCHEDULE 1, NATIVE_AFFINE 1) with the stream x beat expanded
// to the 64-lane {bf16, 16'h0} write, the hr arm / ib gating, the 32 x-leaf read-fault join, and the four columns'
// die column ids 4 sid + c (HARD 1: registered, +1 edge on a value static after SETID).
module qfd_dv_s5_tap #(parameter integer HARD = 1, parameter integer TAP_MUT = 0, parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire [452:0]   hr_q,
    input  wire           xt_v,
    input  wire [23:0]    xt_a,
    input  wire [1023:0]  xt_d,
    input  wire           xt_bad,
    input  wire [31:0]    lq_bad,
    output wire [1566:0]  hw,
    output wire [4*6-1:0] cid,
    output wire           tap_fault
);
    localparam integer AW = 24, NW = 18, XCW = 12;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg  [64*32-1:0] xt_f;
    integer l;
    always @(*) for (l = 0; l < 64; l = l + 1) xt_f[32*l +: 32] = {xt_d[16*l +: 16] ^ ((MUT == 9) ? 16'd1 : 16'd0), 16'h0000};
    wire hv = hr_q[0];
    wire [71:0]  xpf = {hr_q[72:2], hr_q[1] & hv};
    wire [379:0] gi  = {hr_q[451:73], hr_q[452] & hv};
    wire [1566:0] he_unused;
    ot_qfd_xs_tap #(.AW(AW), .NW(NW), .XCW(XCW), .STATIC_SCHEDULE(1), .NATIVE_AFFINE(1), .MUT(TAP_MUT)) u_tap (
        .clk(ck), .rst_n(rst),
        .xpf_v(xpf[0]), .xpf_xbase(xpf[1 +: AW]), .xpf_xcs(xpf[1+AW +: XCW]), .xpf_xks(xpf[1+AW+XCW +: XCW]),
        .xpf_split(xpf[1+AW+2*XCW +: 4]), .xpf_k(xpf[1+AW+2*XCW+4 +: NW]), .xpf_round(xpf[1+AW+2*XCW+4+NW]),
        .sw_v(xt_v), .sw_a(xt_a), .sw_m({64{1'b1}}), .sw_d(xt_f),
        .aw_v(1'b0), .aw_a({AW{1'b0}}), .aw_m(16'd0), .aw_d(512'd0),
        .gi(gi), .hw(hw), .he(he_unused), .fw_i(|lq_bad), .fe_i(xt_bad), .fault(tap_fault));
    wire [23:0] cid_c = {4'(sid) * 6'd4 + 6'd3, 4'(sid) * 6'd4 + 6'd2, 4'(sid) * 6'd4 + 6'd1, 4'(sid) * 6'd4};
    generate if (HARD != 0) begin : g_h
        reg [23:0] cq;
        always @(posedge ck) cq <= cid_c;
        assign cid = cq;
    end else begin : g_s
        assign cid = cid_c;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------- xhead
// qfd_dv_s5_xhead: one column head ot_qfd_xhead (NH 8, NATIVE_AFFINE 1, w130 leaves: LEAF_READ_PIN_PIPE 1, FILL_LEAD 5,
// DX 14) with its strap tile-id registers (from the die column id cid = 4 sid + c) and the corridor station retag.
// One master x 4 (the column is the cid input, no parameter).
module qfd_dv_s5_xhead #(parameter integer HEAD_MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [5:0]     cid,
    input  wire           fault_i,
    input  wire [1566:0]  a_d,
    output wire [515:0]   n_d,
    output wire [515:0]   s_d,
    output wire [1:0]     lw_v, lw_ep, lc_v, lc_ep,
    output wire [11:0]    lw_off,
    output wire [127:0]   lw_m,
    output wire [2047:0]  lw_d,
    output wire [143:0]   lw_ctl,
    output wire [7:0]     lr_v, lr_t, lr_ep,
    output wire [223:0]   lr_p,
    input  wire [511:0]   lq,
    input  wire [7:0]     lq_v,
    input  wire [7:0]     lq_bad,
    output wire           l_rst_n,        // the column's landed reset -> its 8 x leaves
    output wire           fault
);
    localparam integer AW = 24, NW = 18, XCW = 12, NH = 8, NCOLD = 48;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer CW  = 1 + IBW + 128 + 8;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    assign l_rst_n = rst;
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = (NCOLD >= 4) ? 4 : NCOLD; br = (2 * NH >= 4) ? 4 : 2 * NH;
            lbc = (bc >= 4) ? 2 : (bc >= 2) ? 1 : 0; lbr = (br >= 4) ? 2 : (br >= 2) ? 1 : 0;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
            end
            tid = bc * br * blk + z;
        end
    endfunction
    reg [16*2*NH-1:0] tids;
    integer ri;
    always @(posedge ck)
        for (ri = 0; ri < 2 * NH; ri = ri + 1)
            tids[ri * 16 +: 16] <= 16'(tid(int'(cid), ri));
    function automatic [7:0] retag(input [7:0] t, input integer side_s);
        reg [2:0] a, b;
        begin
            a = t[2:0]; b = t[6:4];
            if (side_s ? !a[2] : a[2]) a = a ^ 3'd3;
            if (side_s ? !b[2] : b[2]) b = b ^ 3'd3;
            retag = {t[7], b, t[3], a};
        end
    endfunction
    wire [CW-1:0] n_raw, s_raw;
`ifdef OT_S5_XH_MUT
    assign n_d = {retag(n_raw[1 + IBW + 128 +: 8], 1), n_raw[0 +: 1 + IBW + 128]};   // bench mutant: N retag as S (must FAIL)
`else
    assign n_d = {retag(n_raw[1 + IBW + 128 +: 8], 0), n_raw[0 +: 1 + IBW + 128]};
`endif
    assign s_d = {retag(s_raw[1 + IBW + 128 +: 8], 1), s_raw[0 +: 1 + IBW + 128]};
    ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .NH(NH), .NATIVE_AFFINE(1), .MUT(HEAD_MUT),
        .LEAF_READ_PIN_PIPE(1), .FILL_LEAD(5), .DX(14)) u_head (
        .ck(ck), .rst_n(rst), .tids(tids), .fault_i(fault_i),
        .a_d(a_d), .a_r(), .b_d(), .b_r(1'b1),
        .n_d(n_raw), .n_r(1'b1), .s_d(s_raw), .s_r(1'b1),
        .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
        .lc_v(lc_v), .lc_ep(lc_ep), .lr_v(lr_v), .lr_t(lr_t), .lr_ep(lr_ep), .lr_p(lr_p),
        .lq(lq), .lq_v(lq_v), .lq_bad(lq_bad), .fault(fault));
endmodule
