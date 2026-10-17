`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_slice -- Q-DV distributed-vector slice of the Qwen3-8B TP8 ROM compute die (owner approval 2026-10-16 ~22:00;
// spec results/arch/qwen_dv_1016/SPEC.md on claude/qdv-1016, placement dv2r: the slice absorbs its quad's reduction
// station).  ONE master, hardened once, replicated 12x.  Contract: rtl/qwen_dv/README.md.
//
// Children (all real RTL; arithmetic is the existing qualified primitives, nothing re-invented):
//   u_stn  qfd_dv_redstn   matvec tree levels 7 / 8 / 9 + BF16 row scale (ot_hdc_fp32_add_lat / ot_hdc_fp32_mul_lat)
//   u_su   ot_hdc_vstream_static_entries #(SW 8)  -- the Qwen ROM die's SU core (lanes ot_hdc_vstream_lane: ot_hdc_qadd /
//          qmul, ot_hdc_exp_q / recip_q / rsqrt_q; reducer ot_hdc_vreduce = R-ARITH csum8), 8 lanes instead of 64
//   u_vm   qfd_dv_vm       VM slice / constants / BF16 table / SU program store on ot_sram_1r1w_* macros
//   u_sc   qfd_dv_scalar   scalar-tree face + global-sum root (pairwise top levels)
//   u_stm  qfd_dv_stream   neighbour stream relay, BF16 x packer, table-write tap
// Clocking / reset: ONE regional clock root `ck`; the regional reset `rst_n` is synchronised here (async assert,
// two-flop synchronous release) and drives every child.  Every input port lands in a pin register; every output
// port leaves a register.  Static schedule: no ready, no credit, no backpressure anywhere; faults only.
//
// SU write windows (element address bits [23:22]): 00 VM; 01 stream x packer (element = addr[21:0]); 10 D2D out
// (q / activations, element = addr[21:0]); 11 VM element addr[21:0] AND a scalar-tree broadcast (RB) of the value.
// Reducer windows: 00 VM; 11 scalar-tree block sum (PSUM, idx = addr[21:0]).  KV writes (SU dst KV, FP8-rounded in
// the lane): D2D out, kind = waddr[23:22] (1 K, 2 V).
// MUT: bench negative controls (1 root order, 2 BF16 truncation, 3 scale word +1, 4 CROM lo/hi swap, 5 B <- C).
// =====================================================================================================================
module qfd_dv_slice #(
    parameter integer MUT = 0
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,          // slice id strap
    input  wire [115:0]   cmd,          // from tt_ctlm
    input  wire [513:0]   cw0,          // cluster result word, left of the level-7 pair  {fault, valid, 16 x FP32}
    input  wire [513:0]   cw1,          // cluster result word, right of the level-7 pair
    input  wire [513:0]   nb9_i,        // neighbour level-8 word (L9 receiver)
    output wire [513:0]   nb9_o,        // own level-8 word (L9 sender)
    input  wire [1087:0]  sw_i,         // neighbour stream from the west (travelling east)
    output wire [1087:0]  so_e,
    input  wire [1087:0]  se_i,         // neighbour stream from the east (travelling west)
    output wire [1087:0]  so_w,
    input  wire [95:0]    sc_i,         // scalar tree
    output wire [95:0]    sc_o,
    output reg  [545:0]   ar_o,         // all-reduce chain out  {valid, tag 32, last, data 512}
    input  wire [517:0]   ar_i,         // all-reduce result     {valid, err, rank 3, last, data 512}
    output reg  [547:0]   dd_o,         // D2D out to native59   {valid, kind 2, mask 8, 8 x addr 24, 8 x FP32, 89 x 0}
    input  wire [519:0]   dd_i,         // D2D return            {valid, group, beat 6, data 512}
    output reg  [44:0]    st            // status to tt_ctlm
);
    // ------------------------------------------------------------------ regional reset (sync release)
    reg rs1, rst;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rst <= 1'b0; end
        else begin rs1 <= 1'b1; rst <= rs1; end
    // ------------------------------------------------------------------ pin registers
    reg [3:0]    sid_q;
    reg [115:0]  cmd_q;
    reg [513:0]  cw0_q, cw1_q, nb_q;
    reg [1087:0] sw_q, se_q;
    reg [95:0]   sc_q;
    reg [517:0]  ar_q;
    reg [519:0]  dd_q;
    always @(posedge ck or negedge rst)
        if (!rst) begin
            cmd_q <= 116'd0; cw0_q <= 514'd0; cw1_q <= 514'd0; nb_q <= 514'd0; sw_q <= 1088'd0; se_q <= 1088'd0;
            sc_q <= 96'd0; ar_q <= 518'd0; dd_q <= 520'd0;
        end else begin
            cmd_q <= cmd; cw0_q <= cw0; cw1_q <= cw1; nb_q <= nb9_i; sw_q <= sw_i; se_q <= se_i;
            sc_q <= sc_i; ar_q <= ar_i; dd_q <= dd_i;
        end
    always @(posedge ck) sid_q <= sid;
    // ------------------------------------------------------------------ command decode
    wire       go = cmd_q[0];
    wire [2:0] kind = cmd_q[3:1];
    wire c_su = go && kind == 3'd1, c_stn = go && kind == 3'd2, c_root = go && kind == 3'd3,
         c_prt = go && kind == 3'd4, c_stm = go && kind == 3'd5;
    reg [23:0] stn_dbase; reg [1:0] stn_dst;
    reg [23:0] ar_base, dd_base; reg [7:0] ar_k;
    always @(posedge ck or negedge rst)
        if (!rst) begin stn_dbase <= 24'd0; stn_dst <= 2'd0; ar_base <= 24'd0; dd_base <= 24'd0; end
        else begin
            if (c_stn) begin stn_dst <= cmd_q[25:24]; stn_dbase <= cmd_q[49:26]; end
            if (c_prt) begin ar_base <= cmd_q[27:4]; dd_base <= cmd_q[51:28]; end
        end
    // SU issue: the program word answers 2 edges after the command's pin register
    wire [456:0] si;
    wire         su_go;
    ot_hdc_delay #(.W(1), .D(2), .RESET(1)) u_sug (.clk(ck), .rst_n(rst), .d(c_su), .q(su_go));
    // ------------------------------------------------------------------ SU core (8 lanes)
    wire [7:0]    va_re, vb_re, vc_re, cr_re, vm_we, kv_we;
    wire [8*24-1:0] va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, kv_waddr;
    wire [8*32-1:0] va_q, vb_q, vc_q, vm_wdata, kv_wdata;
    wire [8*64-1:0] cr_q;
    wire          wrom_re, red_we, su_ready, su_idle, su_fault, su_active;
    wire [23:0]   wrom_addr, red_addr;
    wire [255:0]  wrom_q;
    wire [31:0]   red_data;
    wire [15:0]   su_prog, su_rows;
    wire [7:0]    su_infl;
    wire [7:0]    ck8 = {8{ck}};
    ot_hdc_vstream_static_entries #(.SW(8), .LV(4), .WR(16), .AW(24), .NW(18), .KV_FP8(1), .ML(1)) u_su (
        .ck_head(ck8), .ck_exp(ck8), .ck_rcp(ck8), .ck_rsq(ck8), .ck_lane(ck8), .ck_red({9{ck}}),
        .clk(ck), .rst_n(rst), .go(su_go), .ready(su_ready), .idle(su_idle),
        .i_nout(si[18:1]), .i_nin(si[36:19]),
        .i_asrc(si[37]), .i_abase(si[61:38]), .i_aso(si[85:62]), .i_asi(si[109:86]),
        .i_bsrc(si[110]), .i_bbase(si[134:111]), .i_bso(si[158:135]), .i_bsi(si[182:159]),
        .i_csrc(si[183]), .i_cbase(si[207:184]), .i_cso(si[231:208]), .i_csi(si[255:232]),
        .i_ma(si[257:256]), .i_mb(si[259:258]), .i_ad(si[262:260]), .i_sfu(si[265:263]),
        .i_mc(si[266]), .i_md(si[267]), .i_dst(si[269:268]),
        .i_dbase(si[293:270]), .i_dso(si[317:294]), .i_dsi(si[341:318]),
        .i_red(si[343:342]), .i_redsq(si[344]), .i_rbase(si[368:345]), .i_rso(si[392:369]),
        .i_imm1(si[424:393]), .i_imm2(si[456:425]),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .crom_re(cr_re), .crom_addr(cr_addr), .crom_q(cr_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data),
        .progress(su_prog), .progress_rows(su_rows), .fault(su_fault),
        .obs_active(su_active), .obs_inflight(su_infl));
    // ------------------------------------------------------------------ SU write windows
    wire [1:0] win = vm_waddr[23:22];
    wire       sw_any = |vm_we;
    reg  [8*24-1:0] vm_local;
    integer l;
    always @(*) for (l = 0; l < 8; l = l + 1) vm_local[24*l +: 24] = {2'b00, vm_waddr[24*l +: 22]};
    wire [7:0] su_vm_we = (sw_any && win == 2'b00) ? vm_we : 8'd0;
    wire [7:0] su_x_we  = (sw_any && win == 2'b01) ? vm_we : 8'd0;
    wire [7:0] su_q_we  = (sw_any && win == 2'b10) ? vm_we : 8'd0;
    wire       su_rb    = sw_any && win == 2'b11;
    wire       win_bad  = sw_any && win == 2'b11 && vm_we != 8'd1;          // a broadcast scalar is one lane
    // ------------------------------------------------------------------ station
    wire        bt_re, r_v, r_last, stn_fault;
    wire [8:0]  bt_word;
    wire [255:0] bt_q;
    wire [7:0]  r_idx;
    wire [511:0] r_d;
    qfd_dv_redstn #(.MUT(MUT)) u_stn (.ck(ck), .rst_n(rst),
        .cfg_v(c_stn), .cfg_mode(cmd_q[5:4]), .cfg_wsrc(cmd_q[6]), .cfg_nwords(cmd_q[14:7]), .cfg_sbase(cmd_q[23:15]),
        .cw0(cw0_q), .cw1(cw1_q), .nb_i(nb_q), .nb_o(nb9_o),
        .bt_re(bt_re), .bt_word(bt_word), .bt_q(bt_q),
        .r_v(r_v), .r_idx(r_idx), .r_last(r_last), .r_d(r_d), .fault(stn_fault));
    wire [23:0] r_addr = stn_dbase + {12'd0, r_idx, 4'd0};
    // ------------------------------------------------------------------ scalar tree
    wire        sc_w1_we, sc_busy, sc_fault;
    wire [23:0] sc_w1_addr;
    wire [31:0] sc_w1_data;
    wire        red_ps = red_we && red_addr[23:22] == 2'b11;
    wire        red_vm = red_we && red_addr[23:22] == 2'b00;
    wire        red_bad = red_we && red_addr[23:22] != 2'b11 && red_addr[23:22] != 2'b00;
    qfd_dv_scalar #(.MUT(MUT)) u_sc (.ck(ck), .rst_n(rst), .sid(sid_q),
        .cfg_v(c_root), .cfg_root(cmd_q[4]), .cfg_nb(cmd_q[10:5]), .cfg_ss(cmd_q[34:11]),
        .sc_i(sc_q), .sc_o(sc_o),
        .ps_v(red_ps), .ps_idx({2'b00, red_addr[21:0]}), .ps_val(red_data),
        .rb_v(su_rb), .rb_idx({2'b00, vm_waddr[21:0]}), .rb_val(vm_wdata[31:0]),
        .w1_we(sc_w1_we), .w1_addr(sc_w1_addr), .w1_data(sc_w1_data), .busy(sc_busy), .fault(sc_fault));
    // ------------------------------------------------------------------ stream
    wire        tw_we, stm_fault;
    wire [1:0]  tw_kind;
    wire [23:0] tw_addr;
    wire [1023:0] tw_data;
    qfd_dv_stream #(.MUT(MUT)) u_stm (.ck(ck), .rst_n(rst), .sid(sid_q),
        .cfg_v(c_stm), .cfg_dir(cmd_q[5:4]), .cfg_tag(cmd_q[33:6]),
        .sw_i(sw_q), .se_i(se_q), .so_e(so_e), .so_w(so_w),
        .xw_we(su_x_we), .xw_addr(vm_waddr), .xw_data(vm_wdata),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(stm_fault));
    // ------------------------------------------------------------------ VM write merge (16-el and 1-el sources)
    wire ar_v = ar_q[517], dd_v = dd_q[519];
    wire st_vm = r_v && stn_dst[0];
    wire [23:0] ar_wa = ar_base + {12'd0, ar_k, 4'd0};
    wire [23:0] dd_wa = dd_base + {13'd0, dd_q[518:512], 4'd0};
    wire        w16_we = st_vm || ar_v || dd_v;
    wire [23:0] w16_addr = st_vm ? r_addr : ar_v ? ar_wa : dd_wa;
    wire [511:0] w16_data = st_vm ? r_d : ar_v ? ar_q[511:0] : dd_q[511:0];
    wire        w16_coll = (st_vm && ar_v) || (st_vm && dd_v) || (ar_v && dd_v);
    // single elements: scalar face (RB tap, root total), reducer (window 00), own broadcast scalar (window 11)
    wire        w1_we = sc_w1_we || red_vm || su_rb;
    wire [23:0] w1_addr = sc_w1_we ? sc_w1_addr : red_vm ? red_addr : {2'b00, vm_waddr[21:0]};
    wire [31:0] w1_data = sc_w1_we ? sc_w1_data : red_vm ? red_data : vm_wdata[31:0];
    wire        w1_coll = (sc_w1_we && red_vm) || (sc_w1_we && su_rb) || (red_vm && su_rb);
    always @(posedge ck or negedge rst)
        if (!rst) ar_k <= 8'd0;
        else if (c_prt) ar_k <= 8'd0;
        else if (ar_v) ar_k <= ar_k + 8'd1;
    wire vm_fault;
    qfd_dv_vm #(.MUT(MUT)) u_vm (.ck(ck), .rst_n(rst),
        .a_re(va_re), .b_re(vb_re), .c_re(vc_re), .a_addr(va_addr), .b_addr(vb_addr), .c_addr(vc_addr),
        .a_q(va_q), .b_q(vb_q), .c_q(vc_q),
        .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
        .bs_re(wrom_re), .bs_addr(wrom_addr), .bs_q(wrom_q),
        .bt_re(bt_re), .bt_word(bt_word), .bt_q(bt_q),
        .p_re(c_su), .p_idx(cmd_q[12:4]), .p_q(si),
        .su_we(su_vm_we), .su_waddr(vm_waddr), .su_wdata(vm_wdata),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(vm_fault));
    // ------------------------------------------------------------------ AR out (station results routed to the AR)
    always @(posedge ck or negedge rst)
        if (!rst) ar_o <= 546'd0;
        else ar_o <= {r_v && stn_dst[1], {8'd0, r_addr}, r_last, r_d};
    // ------------------------------------------------------------------ D2D out: q / activation rows, K / V rows
    wire        q_any = |su_q_we, kv_any = |kv_we;
    wire [1:0]  kv_kind = kv_waddr[23:22];
    reg  [8*24-1:0] q_loc, kv_loc;
    always @(*) for (l = 0; l < 8; l = l + 1) begin
        q_loc[24*l +: 24] = {2'b00, vm_waddr[24*l +: 22]};
        kv_loc[24*l +: 24] = {2'b00, kv_waddr[24*l +: 22]};
    end
    always @(posedge ck or negedge rst)
        if (!rst) dd_o <= 548'd0;
        else if (kv_any) dd_o <= {1'b1, kv_kind, kv_we, kv_loc, kv_wdata, 89'd0};
        else if (q_any) dd_o <= {1'b1, 2'd0, su_q_we, q_loc, vm_wdata, 89'd0};
        else dd_o <= 548'd0;
    wire dd_bad = (kv_any && q_any) || (kv_any && (kv_kind == 2'd0 || kv_kind == 2'd3));
    // ------------------------------------------------------------------ status and faults
    reg port_fault; reg [2:0] ar_rank; reg ar_last;
    always @(posedge ck or negedge rst)
        if (!rst) begin port_fault <= 1'b0; ar_rank <= 3'd0; ar_last <= 1'b0; end
        else begin
            port_fault <= port_fault | w16_coll | w1_coll | win_bad | red_bad | dd_bad | (ar_v && ar_q[516]) |
                          (go && (kind == 3'd0 || kind > 3'd5)) | (su_go && !su_ready);
            if (ar_v) begin ar_rank <= ar_q[515:513]; ar_last <= ar_q[512]; end
        end
    wire any_fault = su_fault | vm_fault | stn_fault | sc_fault | stm_fault | port_fault;
    always @(posedge ck or negedge rst)
        if (!rst) st <= 45'd0;
        else st <= {any_fault, su_fault, vm_fault, stn_fault, sc_fault, stm_fault, port_fault,
                    su_idle, sc_busy, su_prog, su_rows, ar_rank, ar_last};
    initial if (MUT < 0 || MUT > 5) $fatal(1, "qfd_dv_slice: MUT %0d undefined", MUT);
endmodule
