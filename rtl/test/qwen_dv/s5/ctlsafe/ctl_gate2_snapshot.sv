// Exact source extraction1f858dec1 for reproducible structural construction.
module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule
module qfd_dv_s5_rrly (input wire ck, input wire arst_n, output reg q);
    always @(posedge ck or negedge arst_n) if (!arst_n) q <= 1'b0; else q <= 1'b1;
endmodule
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
    // ---- HARD 1: every input lands in ONE pin register (no reset: the drivers are reset, so the register holds
    //      their reset value one edge later); HARD 0: wires (flat0 == qfd_dv_slice2 at offset 0)
    wire [115:0] cmd_q_r;
    wire [1037:0] chd_q_r;
    wire  r_v_r;
    wire [7:0] r_idx_r;
    wire  r_last_r;
    wire [511:0] r_d_r;
    wire  l9o_v_r;
    wire  stn_fault_r;
    wire [7:0] vm_we_r;
    wire [8*24-1:0] vm_waddr_r;
    wire [8*32-1:0] vm_wdata_r;
    wire [7:0] kv_we_r;
    wire [8*24-1:0] kv_waddr_r;
    wire [8*32-1:0] kv_wdata_r;
    wire  su_nr_r;
    wire  su_idle_r;
    wire  su_fault_r;
    wire [15:0] su_prog_r;
    wire [15:0] su_rows_r;
    wire  vm_fault_r;
    wire  red_we_r;
    wire [23:0] red_addr_r;
    wire [31:0] red_data_r;
    wire  sc_w1_we_r;
    wire [23:0] sc_w1_addr_r;
    wire [31:0] sc_w1_data_r;
    wire  tok_v_r;
    wire [23:0] tok_idx_r;
    wire  tok_own_r;
    wire [31:0] tok_val_r;
    wire [1:0] tok_user_r;
    wire  sc_busy_r;
    wire  sc_fault_r;
    wire  stm_fault_r;
    wire  tld_fault_r;
    wire  hd_fault_r;
    wire  pc_bad_r;
    generate if (HARD != 0) begin : g_pin
        (* keep *) reg [115:0] q_cmd_q; always @(posedge ck) q_cmd_q <= cmd_q; assign cmd_q_r = q_cmd_q;
        (* keep *) reg [1037:0] q_chd_q; always @(posedge ck) q_chd_q <= chd_q; assign chd_q_r = q_chd_q;
        (* keep *) reg  q_r_v; always @(posedge ck) q_r_v <= r_v; assign r_v_r = q_r_v;
        (* keep *) reg [7:0] q_r_idx; always @(posedge ck) q_r_idx <= r_idx; assign r_idx_r = q_r_idx;
        (* keep *) reg  q_r_last; always @(posedge ck) q_r_last <= r_last; assign r_last_r = q_r_last;
        (* keep *) reg [511:0] q_r_d; always @(posedge ck) q_r_d <= r_d; assign r_d_r = q_r_d;
        (* keep *) reg  q_l9o_v; always @(posedge ck) q_l9o_v <= l9o_v; assign l9o_v_r = q_l9o_v;
        (* keep *) reg  q_stn_fault; always @(posedge ck) q_stn_fault <= stn_fault; assign stn_fault_r = q_stn_fault;
        (* keep *) reg [7:0] q_vm_we; always @(posedge ck) q_vm_we <= vm_we; assign vm_we_r = q_vm_we;
        (* keep *) reg [8*24-1:0] q_vm_waddr; always @(posedge ck) q_vm_waddr <= vm_waddr; assign vm_waddr_r = q_vm_waddr;
        (* keep *) reg [8*32-1:0] q_vm_wdata; always @(posedge ck) q_vm_wdata <= vm_wdata; assign vm_wdata_r = q_vm_wdata;
        (* keep *) reg [7:0] q_kv_we; always @(posedge ck) q_kv_we <= kv_we; assign kv_we_r = q_kv_we;
        (* keep *) reg [8*24-1:0] q_kv_waddr; always @(posedge ck) q_kv_waddr <= kv_waddr; assign kv_waddr_r = q_kv_waddr;
        (* keep *) reg [8*32-1:0] q_kv_wdata; always @(posedge ck) q_kv_wdata <= kv_wdata; assign kv_wdata_r = q_kv_wdata;
        (* keep *) reg  q_su_nr; always @(posedge ck) q_su_nr <= su_nr; assign su_nr_r = q_su_nr;
        (* keep *) reg  q_su_idle; always @(posedge ck) q_su_idle <= su_idle; assign su_idle_r = q_su_idle;
        (* keep *) reg  q_su_fault; always @(posedge ck) q_su_fault <= su_fault; assign su_fault_r = q_su_fault;
        (* keep *) reg [15:0] q_su_prog; always @(posedge ck) q_su_prog <= su_prog; assign su_prog_r = q_su_prog;
        (* keep *) reg [15:0] q_su_rows; always @(posedge ck) q_su_rows <= su_rows; assign su_rows_r = q_su_rows;
        (* keep *) reg  q_vm_fault; always @(posedge ck) q_vm_fault <= vm_fault; assign vm_fault_r = q_vm_fault;
        (* keep *) reg  q_red_we; always @(posedge ck) q_red_we <= red_we; assign red_we_r = q_red_we;
        (* keep *) reg [23:0] q_red_addr; always @(posedge ck) q_red_addr <= red_addr; assign red_addr_r = q_red_addr;
        (* keep *) reg [31:0] q_red_data; always @(posedge ck) q_red_data <= red_data; assign red_data_r = q_red_data;
        (* keep *) reg  q_sc_w1_we; always @(posedge ck) q_sc_w1_we <= sc_w1_we; assign sc_w1_we_r = q_sc_w1_we;
        (* keep *) reg [23:0] q_sc_w1_addr; always @(posedge ck) q_sc_w1_addr <= sc_w1_addr; assign sc_w1_addr_r = q_sc_w1_addr;
        (* keep *) reg [31:0] q_sc_w1_data; always @(posedge ck) q_sc_w1_data <= sc_w1_data; assign sc_w1_data_r = q_sc_w1_data;
        (* keep *) reg  q_tok_v; always @(posedge ck) q_tok_v <= tok_v; assign tok_v_r = q_tok_v;
        (* keep *) reg [23:0] q_tok_idx; always @(posedge ck) q_tok_idx <= tok_idx; assign tok_idx_r = q_tok_idx;
        (* keep *) reg  q_tok_own; always @(posedge ck) q_tok_own <= tok_own; assign tok_own_r = q_tok_own;
        (* keep *) reg [31:0] q_tok_val; always @(posedge ck) q_tok_val <= tok_val; assign tok_val_r = q_tok_val;
        (* keep *) reg [1:0] q_tok_user; always @(posedge ck) q_tok_user <= tok_user; assign tok_user_r = q_tok_user;
        (* keep *) reg  q_sc_busy; always @(posedge ck) q_sc_busy <= sc_busy; assign sc_busy_r = q_sc_busy;
        (* keep *) reg  q_sc_fault; always @(posedge ck) q_sc_fault <= sc_fault; assign sc_fault_r = q_sc_fault;
        (* keep *) reg  q_stm_fault; always @(posedge ck) q_stm_fault <= stm_fault; assign stm_fault_r = q_stm_fault;
        (* keep *) reg  q_tld_fault; always @(posedge ck) q_tld_fault <= tld_fault; assign tld_fault_r = q_tld_fault;
        (* keep *) reg  q_hd_fault; always @(posedge ck) q_hd_fault <= hd_fault; assign hd_fault_r = q_hd_fault;
        (* keep *) reg  q_pc_bad; always @(posedge ck) q_pc_bad <= pc_bad; assign pc_bad_r = q_pc_bad;
    end else begin : g_iw
        assign cmd_q_r = cmd_q;
        assign chd_q_r = chd_q;
        assign r_v_r = r_v;
        assign r_idx_r = r_idx;
        assign r_last_r = r_last;
        assign r_d_r = r_d;
        assign l9o_v_r = l9o_v;
        assign stn_fault_r = stn_fault;
        assign vm_we_r = vm_we;
        assign vm_waddr_r = vm_waddr;
        assign vm_wdata_r = vm_wdata;
        assign kv_we_r = kv_we;
        assign kv_waddr_r = kv_waddr;
        assign kv_wdata_r = kv_wdata;
        assign su_nr_r = su_nr;
        assign su_idle_r = su_idle;
        assign su_fault_r = su_fault;
        assign su_prog_r = su_prog;
        assign su_rows_r = su_rows;
        assign vm_fault_r = vm_fault;
        assign red_we_r = red_we;
        assign red_addr_r = red_addr;
        assign red_data_r = red_data;
        assign sc_w1_we_r = sc_w1_we;
        assign sc_w1_addr_r = sc_w1_addr;
        assign sc_w1_data_r = sc_w1_data;
        assign tok_v_r = tok_v;
        assign tok_idx_r = tok_idx;
        assign tok_own_r = tok_own;
        assign tok_val_r = tok_val;
        assign tok_user_r = tok_user;
        assign sc_busy_r = sc_busy;
        assign sc_fault_r = sc_fault;
        assign stm_fault_r = stm_fault;
        assign tld_fault_r = tld_fault;
        assign hd_fault_r = hd_fault;
        assign pc_bad_r = pc_bad;
    end endgenerate
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    // HARD 1: the landed reset feeds 5 kept relay registers (<= ~170 sinks each; amax_mu's tree on its own relay);
    // every register of the leaf releases on the same (+1) edge.  HARD 0: wires.
    wire rst_c, rst_g, rst_s, rst_v, rst_a;
    generate if (HARD != 0) begin : g_rr
        qfd_dv_s5_rrly u_rc (.ck(ck), .arst_n(rst), .q(rst_c));
        qfd_dv_s5_rrly u_rg (.ck(ck), .arst_n(rst), .q(rst_g));
        qfd_dv_s5_rrly u_rs (.ck(ck), .arst_n(rst), .q(rst_s));
        qfd_dv_s5_rrly u_rv (.ck(ck), .arst_n(rst), .q(rst_v));
        qfd_dv_s5_rrly u_ra (.ck(ck), .arst_n(rst), .q(rst_a));
    end else begin : g_rw
        assign rst_c = rst, rst_g = rst, rst_s = rst, rst_v = rst, rst_a = rst;
    end endgenerate
    wire [517:0] ar_q = chd_q_r[1037:520];
    wire [519:0] dd_q = chd_q_r[519:0];
    // ------------------------------------------------------------------ SETID latch
    reg  [3:0] sid_q; reg sid_ok;
    wire setid = cmd_q_r[0] && cmd_q_r[3:1] == 3'd7;
    always @(posedge ck or negedge rst_c)
        if (!rst_c) begin sid_q <= 4'd0; sid_ok <= 1'b0; end
        else if (setid) begin sid_q <= cmd_q_r[7:4]; sid_ok <= 1'b1; end
    assign sid = sid_q;
    // ------------------------------------------------------------------ command decode
    reg        arx_arm, g_arm, g_tok_v, g_fault; reg [1:0] g_user; reg [2:0] g_cnt; reg [55:0] g_best; reg [23:0] g_tok_idx; reg [31:0] g_tok_val;
    wire       go = cmd_q_r[0] && sid_ok && (cmd_q_r[115:112] == sid_q || cmd_q_r[115:112] == 4'hF) && cmd_q_r[3:1] != 3'd7;
    wire [2:0] kind = cmd_q_r[3:1];
    wire c_su = go && kind == 3'd1, c_stn = go && kind == 3'd2, c_root = go && kind == 3'd3,
         c_prt = go && kind == 3'd4, c_stm = go && kind == 3'd5;
    reg [23:0] stn_dbase; reg [1:0] stn_dst;
    reg [23:0] ar_base, dd_base, em_base; reg [7:0] ar_k, em_k; reg ar_en, dd_en, em_en;
    always @(posedge ck or negedge rst_c)
        if (!rst_c) begin stn_dbase <= 24'd0; stn_dst <= 2'd0; ar_base <= 24'd0; dd_base <= 24'd0; em_base <= 24'd0;
                        ar_en <= 1'b0; dd_en <= 1'b0; em_en <= 1'b0; end
        else begin
            if (c_stn) begin stn_dst <= cmd_q_r[25:24]; stn_dbase <= cmd_q_r[49:26]; end
            if (c_prt) begin ar_base <= cmd_q_r[27:4]; dd_base <= cmd_q_r[51:28]; ar_en <= cmd_q_r[52]; dd_en <= cmd_q_r[53];
                             em_base <= cmd_q_r[77:54]; em_en <= cmd_q_r[78]; end
        end
    wire [28:0]  stn_cfg_c = {c_stn, cmd_q_r[5:4], cmd_q_r[6], cmd_q_r[14:7], cmd_q_r[23:15], (MUT == 15) ? cmd_q_r[58:51] : cmd_q_r[66:59]};
    wire [100:0] sc_cfg_c  = {c_root, cmd_q_r[4], cmd_q_r[103], cmd_q_r[10:5], cmd_q_r[34:11], cmd_q_r[35], cmd_q_r[59:36], cmd_q_r[91:60],
                              cmd_q_r[96:92], cmd_q_r[102:97]};
    wire [30:0]  stm_cfg_c = {c_stm, cmd_q_r[5:4], cmd_q_r[33:6]};
    wire [9:0]   su_cmd_c  = {c_su, cmd_q_r[12:4]};
    // ------------------------------------------------------------------ SU write windows (lane 0's window, as qfd_dv_slice2)
    wire [1:0] win = vm_waddr_r[23:22];
    wire       sw_any = |vm_we_r;
    wire [7:0] su_q_we  = (sw_any && win == 2'b10) ? vm_we_r : 8'd0;
    wire       su_rb    = sw_any && win == 2'b11;
    wire       win_bad  = sw_any && win == 2'b11 && vm_we_r != 8'd1;
    wire [23:0] r_addr = stn_dbase + {12'd0, r_idx_r, 4'd0};
    wire        red_vm = red_we_r && red_addr_r[23:22] == 2'b00;
    wire        red_bad = red_we_r && red_addr_r[23:22] != 2'b11 && red_addr_r[23:22] != 2'b00;
    // ------------------------------------------------------------------ LM-head running argmax
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    wire am_emit_empty, am_mu_fault, am_stn_pend;
    wire am_v_c; wire [23:0] am_idx_c; wire [31:0] am_val_c; wire [1:0] am_u_c;
    qfd_dv_amax_mu #(.NU(MU_NU), .MUT(0)) u_amax (.ck(ck), .rst(rst_a), .c_stn(c_stn), .stn_amax_bit(cmd_q_r[50]), .stn_user(cmd_q_r[52:51]), .stn_pend(am_stn_pend),
        .r_v(r_v_r), .r_addr(r_addr), .r_d(r_d_r), .c_am(go && kind == 3'd6), .am_clr(cmd_q_r[4]), .am_emit_cmd(cmd_q_r[5]),
        .am_user(cmd_q_r[9:8]), .am_v(am_v_c), .am_idx(am_idx_c), .am_val(am_val_c), .am_u(am_u_c), .emit_empty(am_emit_empty), .mu_fault(am_mu_fault));
    // ------------------------------------------------------------------ VM write merge (16-el and 1-el sources)
    wire ar_v = ar_q[517] && ar_en && !g_arm, dd_v = dd_q[519] && !dd_q[518] && dd_en, em_v = dd_q[519] && dd_q[518] && em_en;
    wire [23:0] em_wa = em_base + {12'd0, em_k, 4'd0};
    wire st_vm = r_v_r && stn_dst[0];
    wire [23:0] ar_wa = ar_base + {12'd0, ar_k, 4'd0};
    wire [23:0] dd_wa = dd_base + {14'd0, dd_q[517:512], 4'd0};
    wire        w16_we_c = st_vm || ar_v || dd_v || em_v;
    wire [23:0] w16_addr_c = st_vm ? r_addr : ar_v ? ar_wa : dd_v ? dd_wa : em_wa;
    wire [511:0] w16_data_c;                // per 32-bit group g: kept select copies (<= ~70 mux loads per select)
    wire        w16_coll = (st_vm && ar_v) || (st_vm && (dd_v || em_v)) || (ar_v && (dd_v || em_v));
    wire        w1_we_c = sc_w1_we_r || red_vm || su_rb;
    wire [23:0] w1_addr_c = sc_w1_we_r ? sc_w1_addr_r : red_vm ? red_addr_r : {2'b00, vm_waddr_r[21:0]};
    wire [31:0] w1_data_c = sc_w1_we_r ? sc_w1_data_r : red_vm ? red_data_r : vm_wdata_r[31:0];
    wire        w1_coll = (sc_w1_we_r && red_vm) || (sc_w1_we_r && su_rb) || (red_vm && su_rb);
    always @(posedge ck or negedge rst_c)
        if (!rst_c) begin ar_k <= 8'd0; em_k <= 8'd0; end
        else if (c_prt) begin ar_k <= 8'd0; em_k <= 8'd0; end
        else begin if (ar_v) ar_k <= ar_k + 8'd1; if (em_v) em_k <= em_k + 8'd1; end
    // ------------------------------------------------------------------ XC (kind 0): collective command (sub 0 COLL)
    wire c_xc = go && kind == 3'd0;
    always @(posedge ck or negedge rst_s)
        if (!rst_s) cc_o <= 50'd0;
        else cc_o <= (c_xc && cmd_q_r[5:4] == 2'd0) ?
                     {1'b1, (MUT == 11) ? cmd_q_r[7] : cmd_q_r[6], cmd_q_r[22:7], cmd_q_r[54:23]} : 50'd0;
    // ------------------------------------------------------------------ ARX arm and the cross-die argmax gather
    wire       c_am = go && kind == 3'd6;
    wire       arx_v = tok_own_r && arx_arm;
    wire [546:0] arx_w = {1'b1, {8'd0, tok_idx_r}, 1'b1, 1'b1, 456'd0, tok_idx_r, tok_val_r};
    wire       g_v = g_arm && ar_q[517];
    wire [55:0] g_in = ar_q[55:0];
    wire       g_take = (g_cnt == 3'd0) || okey(g_in[31:0]) > okey(g_best[31:0]) ||
                        ((MUT == 12) && okey(g_in[31:0]) == okey(g_best[31:0]));
    always @(posedge ck or negedge rst_g)
        if (!rst_g) begin arx_arm <= 1'b0; g_arm <= 1'b0; g_tok_v <= 1'b0; g_fault <= 1'b0; g_cnt <= 3'd0; g_user <= 2'd0;
                        g_best <= 56'd0; g_tok_idx <= 24'd0; g_tok_val <= 32'd0; end
        else begin
            g_tok_v <= 1'b0;
            if (c_am && cmd_q_r[6]) arx_arm <= 1'b1; else if (arx_v) arx_arm <= 1'b0;
            if (c_am && cmd_q_r[7]) begin g_arm <= 1'b1; g_cnt <= 3'd0; if (MU_NU > 1) g_user <= cmd_q_r[9:8]; end
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
    wire        q_any = |su_q_we, kv_any = |kv_we_r;
    wire [1:0]  kv_kind = kv_waddr_r[23:22];
    reg  [8*24-1:0] q_loc, kv_loc;
    integer l;
    always @(*) for (l = 0; l < 8; l = l + 1) begin
        q_loc[24*l +: 24] = {2'b00, vm_waddr_r[24*l +: 22]};
        kv_loc[24*l +: 24] = {2'b00, kv_waddr_r[24*l +: 22]};
    end
    wire        own_ar = r_v_r && stn_dst[1];
    wire [546:0] own_arw = {1'b1, {8'd0, r_addr}, 1'b0, r_last_r, r_d_r};      // mode 0: all-reduce
    wire        own_dd = kv_any || q_any;
    wire [547:0] own_ddw = kv_any ? {1'b1, kv_kind, kv_we_r, kv_loc, kv_wdata_r, 89'd0}
                                  : {1'b1, 2'd0, su_q_we, q_loc, vm_wdata_r, 89'd0};
    wire [1094:0] own_ch_c;
    // ---- wide-mux selects: 16 kept copies (HARD 1; HARD 0 = the single signals).  Input copies are registered from the
    //      same ports on the same edge as the pin registers; state copies are written exactly as their originals.
    localparam integer NG = 16;
    wire [NG-1:0] rvk, arvk, tokk, sd0k, sd1k, arenk, garmk, arxk;
    wire [8*8-1:0] kvwek, vmwek;          // per lane l: a kept copy of kv_we / vm_we
    wire [8*2-1:0] wink;                  // per lane l: a kept copy of lane 0's window vm_waddr[23:22]
    wire garm_n = (c_am && cmd_q_r[7]) ? 1'b1 : (g_v && ar_q[512]) ? 1'b0 : g_arm;
    wire arx_n  = (c_am && cmd_q_r[6]) ? 1'b1 : arx_v ? 1'b0 : arx_arm;
    genvar gk;
    generate if (HARD != 0) begin : g_kc
        for (gk = 0; gk < NG; gk = gk + 1) begin : g_c
            (* keep *) reg rv, arv, tk, s0, s1, ae, ga, ax;
            always @(posedge ck) begin rv <= r_v; arv <= chd_q[1037]; tk <= tok_own; end
            always @(posedge ck or negedge rst_v)
                if (!rst_v) begin s0 <= 1'b0; s1 <= 1'b0; ae <= 1'b0; ga <= 1'b0; ax <= 1'b0; end
                else begin
                    if (c_stn) begin s0 <= cmd_q_r[24]; s1 <= cmd_q_r[25]; end
                    if (c_prt) ae <= cmd_q_r[52];
                    ga <= garm_n; ax <= arx_n;
                end
            assign rvk[gk] = rv, arvk[gk] = arv, tokk[gk] = tk, sd0k[gk] = s0, sd1k[gk] = s1, arenk[gk] = ae,
                   garmk[gk] = ga, arxk[gk] = ax;
        end
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_l
            (* keep *) reg [7:0] kw, vw; (* keep *) reg [1:0] wn;
            always @(posedge ck) begin kw <= kv_we; vw <= vm_we; wn <= vm_waddr[23:22]; end
            assign kvwek[8*gk +: 8] = kw, vmwek[8*gk +: 8] = vw, wink[2*gk +: 2] = wn;
        end
    end else begin : g_kw
        assign rvk = {NG{r_v_r}}, arvk = {NG{chd_q_r[1037]}}, tokk = {NG{tok_own_r}}, sd0k = {NG{stn_dst[0]}},
               sd1k = {NG{stn_dst[1]}}, arenk = {NG{ar_en}}, garmk = {NG{g_arm}}, arxk = {NG{arx_arm}};
        assign kvwek = {8{kv_we_r}}, vmwek = {8{vm_we_r}}, wink = {8{vm_waddr_r[23:22]}};
    end endgenerate
    generate for (gk = 0; gk < NG; gk = gk + 1) begin : g_w16
        wire stg = rvk[gk] && sd0k[gk], arg = arvk[gk] && arenk[gk] && !garmk[gk];
        wire oag = rvk[gk] && sd1k[gk], axg = tokk[gk] && arxk[gk];
        assign w16_data_c[32*gk +: 32] = stg ? r_d_r[32*gk +: 32] : arg ? ar_q[32*gk +: 32] : dd_q[32*gk +: 32];
        assign own_ch_c[548 + 32*gk +: 32] = oag ? own_arw[32*gk +: 32] : axg ? arx_w[32*gk +: 32] : 32'd0;
    end endgenerate
    assign own_ch_c[1094:1060] = own_ar ? own_arw[546:512] : arx_v ? arx_w[546:512] : 35'd0;
    // own D2D word: header (11 b) on the single selects, lane l's {loc 24, data 32} on its kept copies
    assign own_ch_c[547:537] = own_dd ? own_ddw[547:537] : 11'd0;
    assign own_ch_c[88:0] = 89'd0;
    generate for (gk = 0; gk < 8; gk = gk + 1) begin : g_dd
        wire kva = |kvwek[8*gk +: 8];
        wire qa  = (|vmwek[8*gk +: 8]) && wink[2*gk +: 2] == 2'b10;
        wire od  = kva || qa;
        assign own_ch_c[345 + 24*gk +: 24] = od ? (kva ? kv_loc[24*gk +: 24] : q_loc[24*gk +: 24]) : 24'd0;
        assign own_ch_c[89 + 32*gk +: 32]  = od ? (kva ? kv_wdata_r[32*gk +: 32] : vm_wdata_r[32*gk +: 32]) : 32'd0;
    end endgenerate
    wire own_bad = own_ar && arx_v;                                       // the pass collisions: dn face pc_bad_r
    wire dd_bad = own_bad || pc_bad_r || (kv_any && q_any) || (kv_any && (kv_kind == 2'd0 || kv_kind == 2'd3));
    // ------------------------------------------------------------------ status and faults
    reg port_fault; reg [2:0] ar_rank; reg ar_last;
    always @(posedge ck or negedge rst_g)
        if (!rst_g) begin port_fault <= 1'b0; ar_rank <= 3'd0; ar_last <= 1'b0; end
        else begin
            port_fault <= port_fault | w16_coll | w1_coll | win_bad | red_bad | dd_bad | (ar_v && ar_q[516]) |
                          (c_xc && cmd_q_r[5:4] != 2'd0) | am_emit_empty | am_mu_fault | su_nr_r |
                          g_fault | (c_am && cmd_q_r[7] && g_arm);
            if (ar_v) begin ar_rank <= ar_q[515:513]; ar_last <= ar_q[512]; end
        end
    reg tok_g;
    wire tsel = g_tok_v || (tok_g && !tok_v_r);
    reg [31:0] tok_own_val;
    always @(posedge ck or negedge rst_c) if (!rst_c) tok_own_val <= 32'd0; else if (tok_v_r) tok_own_val <= tok_own_r ? tok_val_r : 32'd0;
    reg [8:0] stn_left; reg stn_snd;
    wire stn_busy = stn_left != 9'd0;
    assign am_stn_pend = stn_busy && !stn_snd && !(stn_left == 9'd1 && r_v_r);
    always @(posedge ck or negedge rst_c)
        if (!rst_c) begin stn_left <= 9'd0; stn_snd <= 1'b0; end
        else if (c_stn) begin stn_left <= {1'b0, cmd_q_r[14:7]}; stn_snd <= cmd_q_r[5:4] == 2'd3; end
        else if (stn_busy && (stn_snd ? l9o_v_r : r_v_r)) stn_left <= stn_left - 9'd1;
    always @(posedge ck or negedge rst_c) if (!rst_c) tok_g <= 1'b0; else if (g_tok_v) tok_g <= 1'b1; else if (tok_v_r) tok_g <= 1'b0;
    wire any_fault = su_fault_r | vm_fault_r | stn_fault_r | sc_fault_r | stm_fault_r | port_fault | hd_fault_r | tld_fault_r;
    wire [1:0] st_ru = (MU_NU > 1 && (tok_v_r || g_tok_v)) ? (tsel ? g_user : tok_user_r) : ar_rank[1:0];
    always @(posedge ck or negedge rst_s)
        if (!rst_s) st <= 107'd0;
        else st <= {ar_v, tsel ? g_tok_val : tok_v_r ? (tok_own_r ? tok_val_r : 32'd0) : tok_own_val, 4'd0 /* sid */, any_fault, su_fault_r, vm_fault_r, stn_fault_r, sc_fault_r, stm_fault_r, port_fault,
                    su_idle_r, sc_busy_r, su_prog_r, su_rows_r, ar_rank[2], st_ru, ar_last, tok_v_r || g_tok_v,
                    tsel ? g_tok_idx : tok_idx_r} | (107'(sid_q) << 70);
    wire [9:0] ag_own_c = {stn_busy, any_fault, su_fault_r, vm_fault_r, stn_fault_r, sc_fault_r, stm_fault_r, port_fault, !su_idle_r, sc_busy_r};
    // ------------------------------------------------------------------ outputs (HARD 1: one register each)
    localparam integer OW = 29 + 101 + 31 + 10 + 1 + 24 + 32 + 2 + 1 + 24 + 512 + 1 + 24 + 32 + 1095 + 10;
    wire [OW-1:0] o_c = {stn_cfg_c, sc_cfg_c, stm_cfg_c, su_cmd_c, am_v_c, am_idx_c, am_val_c, am_u_c,
                         w16_we_c, w16_addr_c, w16_data_c, w1_we_c, w1_addr_c, w1_data_c, own_ch_c, ag_own_c};
    wire [OW-1:0] o_q;
    generate if (HARD != 0) begin : g_h
        // valid / strobe bits reset (VB: stn_cfg v, sc_cfg v, stm_cfg v, c_su, am_v, w16_we, w1_we, own AR v, own D2D v,
        // ag_own), payload not (it follows o_c every edge, qualified by its valid): the async-reset net stays ~20 sinks
        localparam integer P_STN = OW - 1, P_SC = OW - 30, P_STM = OW - 131, P_SU = OW - 162, P_AM = OW - 172,
                           P_W16 = OW - 231, P_W1 = OW - 768, P_AR = 1094 + 10, P_DD = 547 + 10;
        reg [OW-1:0] oq;
        always @(posedge ck) oq <= o_c;
        reg [19:0] vq;
        wire [19:0] vc = {o_c[P_STN], o_c[P_SC], o_c[P_STM], o_c[P_SU], o_c[P_AM], o_c[P_W16], o_c[P_W1], o_c[P_AR], o_c[P_DD],
                          1'b0, o_c[9:0]};
        always @(posedge ck or negedge rst_v) if (!rst_v) vq <= 20'd0; else vq <= vc;
        reg [OW-1:0] om;
        always @(*) begin
            om = oq;
            {om[P_STN], om[P_SC], om[P_STM], om[P_SU], om[P_AM], om[P_W16], om[P_W1], om[P_AR], om[P_DD]} = vq[19:11];
            om[9:0] = vq[9:0];
        end
        assign o_q = om;
    end else begin : g_s
        assign o_q = o_c;
    end endgenerate
    assign {stn_cfg, sc_cfg, stm_cfg, su_cmd, am_v, am_idx, am_val, am_u,
            w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data, own_ch, ag_own} = o_q;
    initial if (MUT < 0 || (MUT > 12 && MUT != 15)) $fatal(1, "qfd_dv_s5_ctl: MUT %0d undefined", MUT);
endmodule
