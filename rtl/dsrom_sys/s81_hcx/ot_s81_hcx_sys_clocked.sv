`timescale 1ns/1ps
`default_nettype none
// Opt-in SYS clock partition. Original measured source0da modules are unchanged.
// Existing HCP operations/state are relocated, with no added logical pipeline edge.
// Native static scheduling, physical pin reach/clock phase and TT/FF/DRC remain OPEN.
// Scalar rs_take/rs_fault are inherited combinational occupancy/status surfaces;
// they are NOT qualified production scheduling or registered physical interfaces.
module ot_s81_hcx_hcp_sys_clocked #(
    parameter integer W    = 8,         // lanes per group (power of two >= 2); lanes = 8W (spec: W = 256)
    parameter integer TL   = 9,         // tail levels: runs per accumulation R <= 2^TL (spec: 4)
    parameter integer PMAX = 8,         // positions per command (power of two)
    parameter integer OMAX = 32,        // rows per position (power of two)
    parameter integer AW   = 16,        // bank word address width
    parameter integer CW   = 16,        // chunk-count width (nchunk = K/8)
    parameter integer ML   = 2,         // memory read latency
    parameter integer DF   = 32,        // raw-result FIFO depth (power of two)
    // el1011-hcvm-hc SYSTOLIC lanes (opt-in, default off; cycles change): SYS = 1 builds no lane groups and no bank
    // rotation.  The 8W lanes live outside in 8 bank stages (ot_hdc_v41x_hcp_stage, one per bank, chained): the task
    // descriptor leaves on sd_* (tap 0), stage k multiplies term k from its OWN bank and adds it to the partial chunk
    // sum of stage k - 1 (stage 0 adds to +0), so csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op; stage
    // 7's W chunk sums come back on sys_sum SYS_LAT cycles after tap 0 (the tree leaves at tap SYS_LAT + 1).
    parameter integer SYS  = 1,
    parameter integer SYS_LAT = 0,
    parameter integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1,
    parameter integer OXW  = (OMAX > 1) ? $clog2(OMAX) : 1
) (
    input  wire              clk,
    input wire clk_tree, clk_scalar,
    input  wire              rst_n,
    // command
    input  wire              cmd_valid,
    output reg               cmd_ready,
    input  wire [PW:0]       cmd_npos,          // 1 .. PMAX
    input  wire [OXW:0]      cmd_nout,          // 1 .. OMAX
    input  wire [CW-1:0]     cmd_nchunk,        // K / 8, >= 1
    input  wire              cmd_scale,
    input  wire [31:0]       cmd_nf,            // binary32 of K (the mean's divisor)
    input  wire [31:0]       cmd_eps,
    input  wire [AW-1:0]     cmd_wbase,
    input  wire [AW-1:0]     cmd_xbase,
    // weight banks (binary32) and x banks (BF16), bank k at [k*...]
    output reg  [7:0]        w_re,
    output reg  [8*AW-1:0]   w_addr,
    input  wire [8*W*32-1:0] w_data,
    output reg  [7:0]        x_re,
    output reg  [8*AW-1:0]   x_addr,
    input  wire [8*W*16-1:0] x_data,
    // results
    output reg               o_valid,
    input  wire              o_ready,
    output reg  [PW-1:0]     o_pos,
    output reg  [OXW-1:0]    o_idx,
    output reg  [31:0]       o_data,
    output reg               o_last,
    output reg               fault,
    output reg               idle,
    // SYS = 1: the descriptor to stage 0, the chunk sums and lane faults back from stage 7
    output wire              sd_v,
    output wire              sd_ss,
    output wire [$clog2(W):0] sd_nv,
    output wire [AW-1:0]     sd_wa,
    output wire [AW-1:0]     sd_xa,
    input  wire [W*32-1:0]   sys_sum,
    input  wire              sys_fault
);
    localparam integer LW  = $clog2(W);
    localparam integer NVW = LW + 1;
    localparam integer DFW = $clog2(DF);
    // descriptor fields
    localparam integer F_V   = 0;
    localparam integer F_SS  = 1;
    localparam integer F_LR  = 2;                 // last run
    localparam integer F_GRP = 3;                 // 3 bits
    localparam integer F_NV  = 6;                 // NVW bits
    localparam integer F_WA  = F_NV + NVW;
    localparam integer F_XA  = F_WA + AW;
    localparam integer F_POS = F_XA + AW;
    localparam integer F_IDX = F_POS + PW;
    localparam integer F_R   = F_IDX + OXW;       // TL low bits of the run index
    localparam integer F_LO  = F_R + TL;          // last output of the command
    localparam integer DW    = F_LO + 1;
    // pipeline taps (descriptor delay-line index of the task a stage holds)
    localparam integer T_OP   = 21 + ML + 3;                 // group operands of term 7
    localparam integer T_LEAF = SYS ? SYS_LAT + 1 : 31 + ML; // tree leaves
    localparam integer T_TAIL = T_LEAF + 3 * LW;             // tree output = tail level 0 input
    localparam integer NDL    = T_TAIL + 3 * TL + 1;

    genvar gk, gg, gl, gv;
    integer i;

    // ------------------------------------------------------------------ command / issue
    reg              busy, active;
    reg [PW:0]       npos_r;
    reg [OXW:0]      nout_r;
    reg [CW-1:0]     nrun_r, nlast_r;              // runs per accumulation; lanes of the last run
    reg              scale_r;
    reg [31:0]       nf_r, eps_r;
    reg [PW-1:0]     p;
    reg [OXW-1:0]    o;
    reg              ssph;
    reg [CW-1:0]     r;
    reg [AW-1:0]     wbase_r, wcur, xpos;
    reg [4:0]        ph24;                          // free-running cycle mod 24
    reg [DFW:0]      acc_cnt;                       // accumulations reserved, not yet popped
    wire             pop_raw;
    wire [CW-1:0]    nrun_c = (cmd_nchunk + W - 1) >> LW;
    wire             first_r = (r == 0);
    wire             last_r = (r == nrun_r - 1'b1);
    wire             credit = (acc_cnt < DF);
    wire             iss = active && (!first_r || credit);
    wire             last_o = ssph ? 1'b0 : ({1'b0, o} == nout_r - 1'b1);
    wire             last_p = ({1'b0, p} == npos_r - 1'b1);
    reg  [DW-1:0]    d0;
    wire             tl_over_c = (nrun_c > (1 << TL));
    localparam [NVW-1:0] WNV = W;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; active <= 1'b0; cmd_ready <= 1'b0; ph24 <= 5'd0; acc_cnt <= 0;
        end else begin
            ph24 <= (ph24 == 5'd23) ? 5'd0 : ph24 + 5'd1;
            cmd_ready <= !busy && !(cmd_valid && cmd_ready);
            acc_cnt <= acc_cnt + (iss && first_r) - pop_raw;
            if (cmd_valid && cmd_ready) begin
                busy <= 1'b1; active <= 1'b1;
            end else if (iss && last_r && last_o && last_p) begin
                active <= 1'b0;
            end
            if (o_valid && o_ready && o_last) busy <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (cmd_valid && cmd_ready) begin
            npos_r <= cmd_npos; nout_r <= cmd_nout; scale_r <= cmd_scale;
            nrun_r <= nrun_c; nlast_r <= ((cmd_nchunk - 1'b1) & (W - 1)) + 1'b1;
            nf_r <= cmd_nf; eps_r <= cmd_eps; wbase_r <= cmd_wbase;
            p <= 0; o <= 0; r <= 0; ssph <= cmd_scale; wcur <= cmd_wbase; xpos <= cmd_xbase;
        end else if (iss) begin
            if (!last_r) r <= r + 1'b1;
            else begin
                r <= 0;
                if (ssph) ssph <= 1'b0;
                else if (!last_o) o <= o + 1'b1;
                else begin
                    o <= 0; p <= p + 1'b1; ssph <= scale_r; wcur <= wbase_r; xpos <= xpos + nrun_r;
                end
            end
            if (!ssph && !(last_r && last_o)) wcur <= wcur + 1'b1;
        end
        // the task descriptor entering the delay line (a bubble still carries its group)
        d0 <= {DW{1'b0}};
        d0[F_V] <= iss;
        d0[F_SS] <= ssph;
        d0[F_LR] <= last_r;
        d0[F_GRP +: 3] <= ph24 / 3;
        d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;
        d0[F_WA +: AW] <= wcur;
        d0[F_XA +: AW] <= xpos + r;
        d0[F_POS +: PW] <= p;
        d0[F_IDX +: OXW] <= o;
        d0[F_R +: TL] <= r[TL-1:0];
        d0[F_LO] <= !ssph && last_o && last_p;
    end
    // delay line: dl[i] = d0 delayed i cycles (dl[0] = d0); the valid bit is reset
    reg  [NDL-1:0]        dlv;                      // valid bits (reset)
    reg  [(DW-1)*NDL-1:0] dld;                      // the other fields (no reset)
    wire [DW*(NDL+1)-1:0] dl;
    assign dl[DW-1:0] = d0;
    generate for (gv = 0; gv < NDL; gv = gv + 1) begin : g_dl
        assign dl[DW*(gv+1) +: DW] = {dld[(DW-1)*gv +: DW-1], dlv[gv]};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) dlv <= {NDL{1'b0}};
        else for (i = 0; i < NDL; i = i + 1) dlv[i] <= dl[DW*i + F_V];
    end
    always @(posedge clk)
        for (i = 0; i < NDL; i = i + 1) dld[(DW-1)*i +: DW-1] <= dl[DW*i + 1 +: DW-1];

    // ------------------------------------------------------------------ bank addresses (term k at tap 3k)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_re <= 8'd0; x_re <= 8'd0; end
        else for (i = 0; i < 8; i = i + 1) begin
            w_re[i] <= dl[DW*(3*i) + F_V] && !dl[DW*(3*i) + F_SS];
            x_re[i] <= dl[DW*(3*i) + F_V];
        end
    end
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1) begin
            w_addr[AW*i +: AW] <= dl[DW*(3*i) + F_WA +: AW];
            x_addr[AW*i +: AW] <= dl[DW*(3*i) + F_XA +: AW];
        end

    assign sd_v = d0[F_V]; assign sd_ss = d0[F_SS]; assign sd_nv = d0[F_NV +: NVW];
    assign sd_wa = d0[F_WA +: AW]; assign sd_xa = d0[F_XA +: AW];
    wire leaf_v, tree_fault, tree_vo;
    wire [31:0] root;
    wire lane_fault_any = sys_fault;
    // Move the EXISTING 1024-bit leaf + valid capture into the tree child.
    // The capture and every adder remain on the same logical edge as the SYS reference.
    ot_s81_hcx_sys_tree #(.W(W)) tree (
        .clk(clk_tree), .rst_n(rst_n), .capture_v(dl[DW*(T_LEAF-1) + F_V]),
        .sys_sum(sys_sum), .leaf_v(leaf_v), .root(root), .tree_vo(tree_vo), .tree_fault(tree_fault));
    wire [LW*3:0] tvv;
    ot_hdc_v41x_vline #(.D(3*LW)) u_tvv (.clk(clk), .rst_n(rst_n), .v(leaf_v), .vd(tvv));

    // ------------------------------------------------------------------ tail: pairwise tree over runs
    wire [32*(TL+1)-1:0] ev_val;
    wire [TL:0]          ev_v;
    wire [TL-1:0]        tail_fault;
    assign ev_val[31:0] = root;
    assign ev_v[0] = tvv[3*LW];
    generate for (gv = 0; gv < TL; gv = gv + 1) begin : g_tail
        localparam integer TAP = T_TAIL + 3 * gv;
        wire bitl  = dl[DW*TAP + F_R + gv];
        wire lastr = dl[DW*TAP + F_LR];
        wire go    = ev_v[gv] && (bitl || lastr);
        reg [31:0] slot;
        always @(posedge clk) if (ev_v[gv] && !bitl && !lastr) slot <= ev_val[32*gv +: 32];
        wire [1:0] e;
        ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(go),
                                  .a(bitl ? slot : 32'd0), .b(ev_val[32*gv +: 32]),
                                  .y(ev_val[32*(gv+1) +: 32]), .err(e), .valid_out(ev_v[gv+1]));
        assign tail_fault[gv] = ev_v[gv+1] && (|e);
    end endgenerate
    localparam integer T_RAW = T_TAIL + 3 * TL;
    wire raw_v   = ev_v[TL] && dl[DW*T_RAW + F_LR];
    wire raw_bad = ev_v[TL] && !dl[DW*T_RAW + F_LR];      // R > 2^TL

    // ------------------------------------------------------------------ raw-result FIFO
    localparam integer RQW = 1 + 1 + PW + OXW + 32;       // {last out, ss, pos, idx, value}
    reg  [RQW-1:0] rq [0:DF-1];
    reg  [DFW:0]   rq_wp, rq_rp;
    wire           rq_ne = (rq_wp != rq_rp);
    wire [RQW-1:0] rq_h = rq[rq_rp[DFW-1:0]];
    reg  [RQW-1:0] raw_w;
    reg            raw_wv;
    always @(posedge clk) begin
        raw_w <= {dl[DW*(T_RAW) + F_LO], dl[DW*(T_RAW) + F_SS], dl[DW*(T_RAW) + F_POS +: PW],
                  dl[DW*(T_RAW) + F_IDX +: OXW], ev_val[32*TL +: 32]};
        if (raw_wv) rq[rq_wp[DFW-1:0]] <= raw_w;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rq_wp <= 0; rq_rp <= 0; raw_wv <= 1'b0; end
        else begin
            raw_wv <= raw_v;
            if (raw_wv) rq_wp <= rq_wp + 1'b1;
            if (pop_raw) rq_rp <= rq_rp + 1'b1;
        end
    end
    wire          h_lo  = rq_h[RQW-1];
    wire          h_ss  = rq_h[RQW-2];
    wire [PW-1:0] h_pos = rq_h[32 + OXW +: PW];
    wire [OXW-1:0] h_idx = rq_h[32 +: OXW];
    wire [31:0]   h_val = rq_h[31:0];

    // The EXISTING scalar sequencer, operand flops and pipes live together.
    wire [PMAX-1:0] r_ok;
    wire [32*PMAX-1:0] rv_packed;
    wire [31:0] rv [0:PMAX-1];
    wire rs_take, rs_fault;
    for (genvar sr = 0; sr < PMAX; sr = sr + 1) begin : g_rv
        assign rv[sr] = rv_packed[32*sr +: 32];
    end
    ot_s81_hcx_sys_scalar #(.PMAX(PMAX), .PW(PW)) scalar (
        .clk(clk_scalar), .rst_n(rst_n), .cmd_start(cmd_valid && cmd_ready),
        .rq_ne(rq_ne), .h_ss(h_ss), .h_pos(h_pos), .h_val(h_val), .nf_r(nf_r), .eps_r(eps_r),
        .rs_take(rs_take), .r_ok_o(r_ok), .rv_o(rv_packed), .rs_fault(rs_fault));

    // ------------------------------------------------------------------ output: raw * r
    localparam integer OQ = 8;
    localparam integer OTW = 1 + PW + OXW;
    reg  [3:0]  oinf;                                 // products in flight
    reg  [3:0]  ocnt;
    wire        o_room = ({1'b0, oinf} + {1'b0, ocnt} + {4'd0, o_valid}) < OQ;
    wire        h_ok = !scale_r || r_ok[h_pos];
    wire        take_out = rq_ne && !h_ss && h_ok && o_room;
    assign pop_raw = rs_take || take_out;
    reg         ov_in;
    reg  [31:0] oa, ob;
    reg  [OTW-1:0] otag_in;
    wire [31:0] oy;
    wire [1:0]  oerr;
    wire        ovo;
    wire [OTW-1:0] otag;
    ot_hdc_fp32_mul_fast u_om (.clk(clk), .rst_n(rst_n), .valid_in(ov_in), .a(oa), .b(ob), .y(oy), .err(oerr),
                               .valid_out(ovo));
    ot_hdc_delay #(.W(OTW), .D(3)) u_otag (.clk(clk), .rst_n(rst_n), .d(otag_in), .q(otag));
    reg  [OTW+31:0] oq [0:OQ-1];
    reg  [3:0]      oq_wp, oq_rp;
    wire            oq_ne = (oq_wp != oq_rp);
    wire            o_load = oq_ne && (!o_valid || o_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_in <= 1'b0; oinf <= 4'd0; ocnt <= 4'd0; oq_wp <= 4'd0; oq_rp <= 4'd0; o_valid <= 1'b0;
        end else begin
            ov_in <= take_out;
            oinf <= oinf + {3'd0, take_out} - {3'd0, ovo};
            ocnt <= ocnt + {3'd0, ovo} - {3'd0, o_load};
            if (ovo) oq_wp <= (oq_wp == OQ - 1) ? 4'd0 : oq_wp + 4'd1;
            if (o_load) oq_rp <= (oq_rp == OQ - 1) ? 4'd0 : oq_rp + 4'd1;
            if (o_load) o_valid <= 1'b1;
            else if (o_ready) o_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (take_out) begin
            oa <= h_val; ob <= scale_r ? rv[h_pos] : 32'h3F800000; otag_in <= {h_lo, h_pos, h_idx};
        end
        if (ovo) oq[oq_wp] <= {otag, oy};
        if (o_load) {o_last, o_pos, o_idx, o_data} <= oq[oq_rp];
    end

    // ------------------------------------------------------------------ fault, idle
    reg lf_r, tf_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; idle <= 1'b1; lf_r <= 1'b0; tf_r <= 1'b0; end
        else begin
            lf_r <= lane_fault_any;
            tf_r <= tree_fault || (|tail_fault) || raw_bad || rs_fault || (ovo && (|oerr));
            if (cmd_valid && cmd_ready) fault <= tl_over_c;
            else if (lf_r || tf_r) fault <= 1'b1;
            idle <= !busy;
        end
    end
endmodule

module ot_s81_hcx_sys_tree #(parameter integer W = 32)(
    input wire clk, rst_n, capture_v,
    input wire [W*32-1:0] sys_sum,
    output reg leaf_v,
    output wire [31:0] root,
    output wire tree_vo, tree_fault
);
    reg [W*32-1:0] leaf;
    always @(posedge clk) leaf <= capture_v ? sys_sum : {(W*32){1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) leaf_v <= 1'b0; else leaf_v <= capture_v;
    ot_hdc_v41x_addtree #(.N(W)) u_tree (.clk(clk), .rst_n(rst_n), .v(leaf_v), .x(leaf),
        .y(root), .vo(tree_vo), .fault(tree_fault));
endmodule

module ot_s81_hcx_sys_scalar #(parameter integer PMAX = 2, PW = 1)(
    input wire clk, rst_n, cmd_start, rq_ne, h_ss,
    input wire [PW-1:0] h_pos,
    input wire [31:0] h_val, nf_r, eps_r,
    output wire rs_take, rs_fault,
    output wire [PMAX-1:0] r_ok_o,
    output wire [32*PMAX-1:0] rv_o
);
    // ------------------------------------------------------------------ scalar r unit
    reg  [31:0]     rv [0:PMAX-1];
    reg  [PMAX-1:0] r_ok;
    reg  [3:0]      st;
    reg             pend;
    reg  [1:0]      it;
    reg  [PW-1:0]   rs_pos;
    reg  [31:0]     rs_q, rs_h, rs_y, rs_a;
    localparam [3:0] S_IDLE = 4'd0, S_DIV = 4'd1, S_EPS = 4'd2, S_HALF = 4'd3, S_YY = 4'd4, S_HY = 4'd5,
                     S_SUB = 4'd6, S_MY = 4'd7;
    assign rs_take = rq_ne && h_ss && (st == S_IDLE);
    // units
    reg         dv, av, mv;
    reg  [31:0] da, db, aa, ab, ma, mb;
    wire [31:0] dy, ay, my;
    wire        dvo, avo, mvo, dfl;
    wire [1:0]  aerr, merr;
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(dv), .a(da), .b(db), .y(dy), .vo(dvo), .fault(dfl));
    ot_hdc_fp32_add_fast u_sa (.clk(clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay), .err(aerr),
                               .valid_out(avo));
    ot_hdc_fp32_mul_fast u_sm (.clk(clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my), .err(merr),
                               .valid_out(mvo));
    assign rs_fault = (dvo && dfl) || (avo && (|aerr)) || (mvo && (|merr));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pend <= 1'b0; dv <= 1'b0; av <= 1'b0; mv <= 1'b0; r_ok <= {PMAX{1'b0}};
        end else begin
            dv <= 1'b0; av <= 1'b0; mv <= 1'b0;
            if (cmd_start) r_ok <= {PMAX{1'b0}};
            case (st)
                S_IDLE: if (rs_take) begin st <= S_DIV; pend <= 1'b0; end
                S_DIV:  if (!pend) begin dv <= 1'b1; pend <= 1'b1; end
                        else if (dvo) begin pend <= 1'b0; st <= S_EPS; end
                S_EPS:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_HALF; end
                S_HALF: if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_YY; end
                S_YY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_HY; end
                S_HY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_SUB; end
                S_SUB:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_MY; end
                S_MY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin
                            pend <= 1'b0;
                            if (it == 2'd2) begin st <= S_IDLE; r_ok[rs_pos] <= 1'b1; end
                            else st <= S_YY;
                        end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == S_IDLE && rs_take) begin
            rs_pos <= h_pos; da <= h_val; db <= nf_r; it <= 2'd0;
        end
        if (st == S_DIV && pend && dvo) begin aa <= dy; ab <= eps_r; end
        if (st == S_EPS && pend && avo) begin
            ma <= ay; mb <= 32'h3F000000;                         // half = v * 0.5
            rs_y <= 32'h5F3759DF - {1'b0, ay[31:1]};              // y0 from v's bits
        end
        if (st == S_HALF && pend && mvo) begin rs_h <= my; ma <= rs_y; mb <= rs_y; end
        if (st == S_YY && pend && mvo) begin ma <= rs_h; mb <= my; end
        if (st == S_HY && pend && mvo) begin aa <= 32'h3FC00000; ab <= {~my[31], my[30:0]}; end
        if (st == S_SUB && pend && avo) begin ma <= rs_y; mb <= ay; end
        if (st == S_MY && pend && mvo) begin
            rs_y <= my; ma <= my; mb <= my; it <= it + 1'b1;
            if (it == 2'd2) rv[rs_pos] <= my;
        end
    end

    assign r_ok_o = r_ok;
    for (genvar si = 0; si < PMAX; si = si + 1) begin : g_export
        assign rv_o[32*si +: 32] = rv[si];
    end
endmodule

module ot_s81_hcx_sys_ctl_clocked #(
    parameter integer HLAYOUT = 1,
    parameter integer SYS_LAT = 86
) (
    input  wire          clk,
    input wire clk_tree, clk_scalar,
    input  wire          rst_n,
    input  wire          stage_begin,
    input  wire          stage_v,
    input  wire [6:0]    stage_word,
    input  wire          cmd_v,
    input  wire          cmd_ffn,
    input  wire [5:0]    cmd_layer,
    input  wire [31:0]   norm_eps,
    // descriptor to the two half chains (stage 0)
    output reg  [1:0]    d_v,
    output reg  [1:0]    d_ss,
    output reg  [9:0]    d_nv,
    output reg  [31:0]   d_wa,
    output reg  [31:0]   d_xa,
    // stage-7 chunk sums (lanes 0..31) and the 16 half-bank stage faults
    input  wire [1023:0] sys_sum,
    input  wire [15:0]   bf,
    output reg           o_v,
    output reg  [31:0]   o_d,
    output reg           fault
);
    reg  [6:0]  staged;
    wire        ready, hfault, last, idle;
    reg         stage_v_q, cmd_v_q, stage_begin_q;
    reg  [6:0]  stage_word_q;
    reg         cmd_ffn_q;
    reg  [5:0]  cmd_layer_q;
    reg  [31:0] norm_eps_q;
    wire        hv;
    wire [31:0] hd;
    wire [0:0]  pos;
    reg  [15:0] bf_q;
    reg         sys_fault;
    // Every input lands in a pin flop.  The flat leaf used stage_begin unregistered; its staging/command CHECK logic
    // (count + sticky fault only, never a cycle of the datapath) therefore runs here one cycle later on delayed
    // copies (begin_q = begin(t), v/word/cmd/ready/layer one cycle older), which is the flat check bit for bit.
    reg        stage_v_qq, cmd_v_qq, ready_q, idle_q;
    reg [6:0]  stage_word_qq;
    reg [5:0]  cmd_layer_qq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            stage_v_q <= 1'b0; cmd_v_q <= 1'b0; o_v <= 1'b0; stage_begin_q <= 1'b0; bf_q <= '0; sys_fault <= 1'b0;
            stage_v_qq <= 1'b0; cmd_v_qq <= 1'b0;
        end else begin
            stage_v_q <= stage_v; cmd_v_q <= cmd_v; o_v <= hv; stage_begin_q <= stage_begin;
            bf_q <= bf; sys_fault <= |bf_q;
            stage_v_qq <= stage_v_q; cmd_v_qq <= cmd_v_q;
        end
    always @(posedge clk) begin
        stage_word_q <= stage_word; cmd_ffn_q <= cmd_ffn; cmd_layer_q <= cmd_layer; norm_eps_q <= norm_eps; o_d <= hd;
        stage_word_qq <= stage_word_q; cmd_layer_qq <= cmd_layer_q; ready_q <= ready; idle_q <= idle;
    end
    wire       sd_v, sd_ss;
    wire [5:0] sd_nv;
    wire [15:0] sd_wa, sd_xa;
    ot_s81_hcx_hcp_sys_clocked #(.W(32), .TL(7), .PMAX(2), .OMAX(2), .AW(16), .CW(16), .ML(2), .SYS(1), .SYS_LAT(SYS_LAT)) hcp (
        .clk(clk), .clk_tree(clk_tree), .clk_scalar(clk_scalar), .rst_n(rst_n), .cmd_valid(cmd_v_q), .cmd_ready(ready), .cmd_npos(2'd1), .cmd_nout(2'd1),
        .cmd_nchunk(16'd2560), .cmd_scale(1'b1), .cmd_nf(32'h46a00000), .cmd_eps(norm_eps_q),
        .cmd_wbase(16'((2*cmd_layer_q+cmd_ffn_q)*80)), .cmd_xbase(16'd0),
        .w_re(), .w_addr(), .w_data(8192'd0), .x_re(), .x_addr(), .x_data(4096'd0),
        .o_valid(hv), .o_ready(1'b1), .o_pos(pos), .o_idx(), .o_data(hd), .o_last(last), .fault(hfault), .idle(idle),
        .sd_v(sd_v), .sd_ss(sd_ss), .sd_nv(sd_nv), .sd_wa(sd_wa), .sd_xa(sd_xa), .sys_sum(sys_sum),
        .sys_fault(sys_fault));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) d_v <= 2'b00; else d_v <= {2{sd_v}};
    always @(posedge clk) begin
        d_ss <= {2{sd_ss}};
        d_nv[4:0] <= (sd_nv > 6'd16) ? 5'd16 : sd_nv[4:0];
        d_nv[9:5] <= (sd_nv > 6'd16) ? 5'(sd_nv - 6'd16) : 5'd0;
        d_wa <= {2{sd_wa}};
        d_xa <= {2{sd_xa}};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin staged <= 0; fault <= 0; end
        else begin
            if (stage_begin_q) begin if (!idle_q) fault <= 1; staged <= 0; end
            if (stage_v_qq) begin
                if (stage_word_qq != (HLAYOUT ? 7'(20*staged[1:0]+staged[6:2]) : staged) || staged >= 80 || !idle_q) fault <= 1;
                staged <= staged + 1'b1;
            end
            // Availability is a check; it never moves the command's compiled cycle.
            if (cmd_v_qq && (!ready_q || staged != 80 || cmd_layer_qq > 42)) fault <= 1;
            if (hfault) fault <= 1;
        end
    end
endmodule
module ot_s81_hcx_projection_sys_clocked #(
    parameter IMAGE = "hcx_r0",
    parameter integer MUT_BANK = 0,
    parameter integer MUT_PAGE = 0,
    parameter integer HLAYOUT = 1
) (
    input wire clk_ctl, clk_tree, clk_scalar,
    input wire [15:0] clk_bank,
    input wire [31:0] clk_lane,
    input  wire          rst_n,
    input  wire          stage_begin,
    input  wire          stage_v,
    input  wire [6:0]    stage_word,
    input  wire [4095:0] stage_d,
    input  wire          cmd_v,
    input  wire          cmd_ffn,
    input  wire [5:0]    cmd_layer,
    input  wire [31:0]   norm_eps,
    output wire          o_v,
    output wire [31:0]   o_d,
    output wire          fault
);
    // descriptor chain per half: index k = into stage k (k = 0 from the controller)
    wire [8:0]  cv [0:1];
    wire [8:0]  css [0:1];
    wire [44:0] cnv [0:1];
    wire [143:0] cwa [0:1];
    wire [143:0] cxa [0:1];
    // partial sums: lsum[k][g] = output of lane leaf (k, g)
    wire [255:0] lsum [0:7][0:3];
    wire [15:0]  bf;
    wire [1023:0] sys_sum;
    wire [1:0]  dv, dss; wire [9:0] dnv; wire [31:0] dwa, dxa;
    ot_s81_hcx_sys_ctl_clocked #(.HLAYOUT(HLAYOUT)) ctl (
        .clk(clk_ctl), .clk_tree(clk_tree), .clk_scalar(clk_scalar), .rst_n(rst_n), .stage_begin(stage_begin), .stage_v(stage_v), .stage_word(stage_word),
        .cmd_v(cmd_v), .cmd_ffn(cmd_ffn), .cmd_layer(cmd_layer), .norm_eps(norm_eps),
        .d_v(dv), .d_ss(dss), .d_nv(dnv), .d_wa(dwa), .d_xa(dxa), .sys_sum(sys_sum), .bf(bf),
        .o_v(o_v), .o_d(o_d), .fault(fault));
    genvar k, h, j, i;
    generate
        for (h = 0; h < 2; h = h + 1) begin : g_hd
            assign cv[h][0] = dv[h]; assign css[h][0] = dss[h]; assign cnv[h][4:0] = dnv[5*h +: 5];
            assign cwa[h][15:0] = dwa[16*h +: 16]; assign cxa[h][15:0] = dxa[16*h +: 16];
        end
        for (k = 0; k < 8; k = k + 1) begin : g_stage
            for (h = 0; h < 2; h = h + 1) begin : g_half
                wire [1:0] gov; wire [15:0] lv, ss; wire [511:0] wd; wire [255:0] xd; wire [1:0] lf;
                wire [255:0] st_d;
                for (i = 0; i < 16; i = i + 1) begin : g_scatter
                    assign st_d[16*i +: 16] = stage_d[16*(8*(16*h+i)+k) +: 16];
                end
                ot_s81_hcx_hbank #(.IMAGE(IMAGE), .BANK(k), .HALF(h), .MUT_BANK(MUT_BANK), .MUT_PAGE(MUT_PAGE)) bank (
                    .clk(clk_bank[2*k+h]), .rst_n(rst_n),
                    .d_v(cv[h][k]), .d_ss(css[h][k]), .d_nv(cnv[h][5*k +: 5]), .d_wa(cwa[h][16*k +: 16]),
                    .d_xa(cxa[h][16*k +: 16]),
                    .o_v(cv[h][k+1]), .o_ss(css[h][k+1]), .o_nv(cnv[h][5*(k+1) +: 5]), .o_wa(cwa[h][16*(k+1) +: 16]),
                    .o_xa(cxa[h][16*(k+1) +: 16]),
                    .st_v(stage_v), .st_word(stage_word), .st_d(st_d),
                    .gov(gov), .lv(lv), .ss(ss), .wd(wd), .xd(xd), .lf(lf), .f_o(bf[2*k+h]));
                for (j = 0; j < 2; j = j + 1) begin : g_lane
                    localparam integer G = 2 * h + j;
                    wire [255:0] s_in;
                    if (k == 0) begin : g_s0
                        assign s_in = 256'd0;          // unused: fst = 1 (stage 0 adds to +0)
                    end else begin : g_sk
                        assign s_in = lsum[k-1][G];
                    end
                    ot_hdc_v41x_hcp_lanes lanes (
                        .clk(clk_lane[4*k+G]), .rst_n(rst_n), .fst(k == 0 ? 1'b1 : 1'b0), .gov_i(gov[j]),
                        .lv_i(lv[8*j +: 8]), .ss_i(ss[8*j +: 8]), .w_i(wd[256*j +: 256]), .x_i(xd[128*j +: 128]),
                        .s_i(s_in), .y(lsum[k][G]), .lf(lf[j]));
                end
            end
        end
        for (i = 0; i < 4; i = i + 1) begin : g_out
            assign sys_sum[256*i +: 256] = lsum[7][i];
        end
    endgenerate
endmodule
`default_nettype wire
