`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_hdc_v41_fh_head_top: the registered TOP of the quadrant-structured fused head (redesign pass 2026-10-06), i.e.
// ot_hdc_v41_fh_macro_ctx MARGIN=1 HARD_LANE=1 (CAPTURE, ALAT 7, RETURN_EXTRA 5, PROTECT_SPLIT 1, RETIRE, VM_ENDPOINT,
// VM_GUARD) minus the four group datapaths that live in ot_hdc_v41_fh_quad. It keeps the tag / valid lines, the
// fused-add address generation and return-valid line, the centre copies of the group broadcast trees (u_rvm, u_selm,
// u_iwgm), the index-write state machine, the SRAM request decode with its ADDR_PIPE stage-1 registers (the per-lane
// group write_ok; mask/data stage-1 registers in the quadrants), the five-deep fault retirement, the checked endpoint
// (FPIPE: registered fault aggregation) and the argmax level-1 consumers. Every quadrant-facing output is a flop;
// every quadrant output arrives from a flop. Cycle-identical composition: ot_hdc_v41_fh_head_q.
// ---------------------------------------------------------------------------------------------------------------
module ot_hdc_v41_fh_head_top #(
    parameter integer W = 16, G = 4, IL = 8, AW = 24, NW = 16, ALAT = 7, RETURN_EXTRA = 5,
    parameter integer FPIPE = 1,
    parameter integer SAFE = 0,          // retirement SAFE + registered stand-in fold (with FPIPE=2)
    parameter integer HQ = 0,            // half-quadrant views: q_group_fault carries 2 bits per group (ORed here)
    // LRET (default 0; needs HQ): the lanes retire their packet slices (ot_hdc_v41_fh_hquad LRET) and the checked
    // endpoint is its own view: the retirement packet here is the narrow control part (we, tag, valids), the lane
    // veto leaves one register early (q_lane_veto), leaf/data/mask/address and the argmax stand-in live outside.
    parameter integer LRET = 0,
    // OREG (2026-10-07, default 0; needs LRET and SAFE): o_we and commit_warm launched from registers at the output
    // pins, computed one stage early from the retirement registers' next-edge values: cycle-identical (0 cycles),
    // removes the retirement logic between the last register and the pins (ctl r6 output hold/setup window).
    parameter integer OREG = 0,
    parameter integer ROWS = 505,
    parameter [AW-1:0] LG_BASE_WORD = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire commit_busy,commit_ack_v,
    input wire native_cold_n,native_request_ready,native_reply_capture,native_reply_v,
    input wire [31:0] native_ordinal,
    input wire [46:0] native_request_owner,
    input wire [1266:0] native_checked_reply,
    output wire native_request_checked_v,native_reply_checked_v,
    output wire [3:0] native_permission_capture,
    output wire [2830:0] native_captured_request,
    output wire [1266:0] native_captured_reply,
    input wire [7:0] commit_ack_id,
    input wire [23:0] commit_ack_word,
    input wire [15:0] commit_ack_mask,
    output wire commit_warm,commit_debt,
    output wire [7:0] commit_id,
    input  wire              s3_v_in,
    input  wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] a_tag_p_in,
    input wire [G-1:0] wr_en,
    input wire [G*AW-1:0] wr_addr,
    output wire [G-1:0]      ra_re,
    output wire [G*AW-1:0]   ra_addr,
    input  wire              go_fus,
    input  wire [AW-1:0]     i_iaddr,
    input  wire [4:0]        busy_in,
    input  wire [G-1:0]      o_we1_in,
    input  wire              tv_in,
    input  wire              ov1_in,
    output wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] r_tag,
    output wire               r_v,
    output wire [(1+32+NW)*G*W-1:0] leaf,
    output wire  [G-1:0]      o_we,
    output wire  [G*AW-1:0]   o_addr,
    output wire  [G*W-1:0]    o_mask,
    output wire  [G*W*32-1:0] o_data,
    output wire              fault,
    output wire [0:0] argmax_level1,
    // quadrant interface (to: flops here; from: flops in the quadrants)
    output reg  [G-1:0]      q_rok,
    output reg  [G*9-1:0]    q_rrow,
    output reg  [G-1:0]      q_wok,
    output reg  [G*9-1:0]    q_wrow,
    output wire [G-1:0]      q_rv_mid,
    output wire [G-1:0]      q_fsel_m,
    output wire [G-1:0]      q_iwg_m,
    output wire [AW-1:0]     q_iw_e,
    input  wire [(1+32+NW)*G*W-1:0] q_leaf,
    input  wire [G*W*32-1:0] q_o_data,
    input  wire [G*W-1:0]    q_o_mask,
    input  wire [G*AW-1:0]   q_o_addr,
    input  wire [G*W-1:0]    q_poison,
    input  wire [(HQ?2:1)*G-1:0] q_group_fault,
    // LRET: external endpoint results and the early lane veto
    input  wire ep_ack_v, ep_fault, ep_guard_busy, ep_request_checked_v, ep_reply_checked_v,
    input  wire [7:0] ep_ack_id,
    input  wire [23:0] ep_ack_word,
    input  wire [15:0] ep_ack_mask,
    output wire [G*W-1:0] q_lane_veto
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer OD = 6 * LG;
    localparam integer LV = $clog2(G * W);
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 2 + AW + AW + 3 * (NW + 1) + 2 + AW + 3 + AW + 1;
    localparam integer CAPTURE = 1;
    localparam integer DF = 2 + RETURN_EXTRA + CAPTURE + ALAT;
    // ======================= ot_hdc_v41_fh_ctx (MARGIN=1, CAPTURE=1, RETIRE=1) control ===========================
    reg [TW-1:0]     a_tag_p;
    reg [4:0]        busy_q;
    reg              s3_v;
    reg [G-1:0]      o_we1;
    reg [LV:0]       tv;
    reg              ov1, ov;
    reg [TW-1:0]     r_tag_q;
    reg              r_v_q;
    reg [G-1:0]      o_we_q;
    reg              warm_emit;
    always @(posedge clk) a_tag_p <= a_tag_p_in;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy_q <= 0; s3_v <= 0; o_we1 <= 0; tv <= 0; ov1 <= 0; ov <= 0; end
        else begin
            busy_q <= busy_in; s3_v <= s3_v_in; o_we1 <= o_we1_in; tv <= {tv[LV-1:0], tv_in}; ov1 <= ov1_in;
            ov <= ov1;
        end
    end
    wire [10+OD:0] vline;
    ot_hdc_vline #(.D(10 + OD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    reg  [TW-1:0] a_tag;
    always @(posedge clk) a_tag <= a_tag_p;
    wire          t_v = vline[10 + OD];
    wire          u_fus = a_tag[0];
    wire          t_v_p = vline[10 + OD - 1];
    wire          p_last, p_oen, p_amax, p_wsrc, p_mmode, p_fus;
    wire [1:0]    p_split, p_hg;
    wire [AW-1:0] p_ogs, p_oa, p_ots, p_ops;
    wire [2:0]    p_m;
    wire [NW:0]   p_nb, p_lb, p_nout;
    assign {p_last, p_oen, p_amax, p_wsrc, p_mmode, p_split, p_oa, p_ots, p_nb, p_lb, p_nout, p_hg, p_ogs, p_m,
            p_ops, p_fus} = a_tag_p;
    wire [LG:0]   p_tq = (G >> p_hg) - 1;
    wire [LG:0]   p_ports = G >> p_split;
    wire [TW-1:0] f_tag_p;
    ot_hdc_delay #(.W(TW), .D(DF - 1)) u_ftag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(f_tag_p));
    wire [DF:0] fline;
    ot_hdc_vline #(.D(DF)) u_fv (.clk(clk), .rst_n(rst_n), .v(t_v && u_fus), .vd(fline));
    always @(posedge clk) r_tag_q <= fline[DF - 1] ? f_tag_p : a_tag_p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_v_q <= 1'b0;
        else r_v_q <= fline[DF - 1] || (t_v_p && !p_fus);
    end
    // ---- ot_hdc_v41_fh_add: address generation, return valid (TREE centre copies) ----------------------------
    localparam integer MPI = 0;
    integer rq;
    reg [G-1:0]    re0, ra_re_q;
    reg [G*AW-1:0] ta, tb, tc, ra_addr_q;
    assign ra_re = ra_re_q; assign ra_addr = ra_addr_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin re0 <= 0; ra_re_q <= 0; end
        else begin
            for (rq = 0; rq < G; rq = rq + 1)
                re0[rq] <= t_v_p && p_fus && p_last && (rq < p_ports) && (MPI < p_m);
            ra_re_q <= re0;
        end
    end
    localparam [AW-1:0] MPI_W = MPI;
    wire [AW-1:0] ots3, ogs3, mops, ta_n;
    ot_hdc_ksadd_k #(.W(AW)) u_o3 (.a(p_ots), .b(p_ots << 1), .cin(1'b0), .s(ots3), .cout());
    ot_hdc_ksadd_k #(.W(AW)) u_g3 (.a(p_ogs), .b(p_ogs << 1), .cin(1'b0), .s(ogs3), .cout());
    assign mops = MPI_W * p_ops;
    ot_hdc_ksadd_k #(.W(AW)) u_ta (.a(p_oa), .b(mops), .cin(1'b0), .s(ta_n), .cout());
    function automatic [AW-1:0] kx(input [1:0] k, input [AW-1:0] x, input [AW-1:0] x3);
        kx = (k == 2'd0) ? {AW{1'b0}} : (k == 2'd1) ? x : (k == 2'd2) ? (x << 1) : x3;
    endfunction
    genvar ga;
    generate for (ga = 0; ga < G; ga = ga + 1) begin : g_ra
        wire [AW-1:0] sa = ta[ga*AW +: AW], sb = tb[ga*AW +: AW], sc = tc[ga*AW +: AW];
        wire [AW-1:0] cs_s = sa ^ sb ^ sc;
        wire [AW-1:0] cs_c = ((sa & sb) | (sa & sc) | (sb & sc)) << 1;
        wire [AW-1:0] sum;
        ot_hdc_ksadd_k #(.W(AW)) u_sum (.a(cs_s), .b(cs_c), .cin(1'b0), .s(sum), .cout());
        always @(posedge clk) begin
            ta[ga*AW +: AW] <= ta_n;
            tb[ga*AW +: AW] <= kx(2'(ga & p_tq), p_ots, ots3);
            tc[ga*AW +: AW] <= kx(2'(ga >> (LG - p_hg)), p_ogs, ogs3);
            ra_addr_q[ga*AW +: AW] <= sum;
        end
    end endgenerate
    reg hv0, hv1, ah_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hv0 <= 1'b0; hv1 <= 1'b0; ah_v <= 1'b0; end
        else begin hv0 <= t_v_p && p_fus && p_last; hv1 <= hv0; ah_v <= hv1; end
    end
    wire rv_pre;
    ot_hdc_delay #(.W(1), .D(RETURN_EXTRA - 2)) u_return_valid (.clk(clk), .rst_n(rst_n), .d(ah_v), .q(rv_pre));
    // ---- index-write state (ctx, RETIRE, IW_EXTRA = 1) ---------------------------------------------------------
    wire retire_busy, retire_warm_ack;
    reg iw_pend, iw_issued, iw_go, iw_go2, iw_go3;
    reg [AW-1:0] iaddr_r;
    wire iw_write_go = iw_go3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iw_go2 <= 0; iw_go3 <= 0; end else begin iw_go2 <= iw_go; iw_go3 <= iw_go2; end
    wire drained_nx = !retire_busy && !(|busy_q) && !s3_v && !(|vline) && !(|tv[LV-1:0]) && !ov1 && !ov && !(|fline);
    wire iw_go_n = iw_pend && !iw_go && !iw_go2 && !iw_go3 && drained_nx && !iw_issued;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iw_pend <= 1'b0; iw_issued <= 0; warm_emit <= 0; iaddr_r <= 0; iw_go <= 1'b0; end
        else begin
            iw_go <= iw_go_n; warm_emit <= iw_write_go;
            if (go_fus && !iw_pend && !retire_busy) begin
                iw_pend <= 1'b1; iw_issued <= 0; iaddr_r <= i_iaddr;
            end else if (iw_write_go) iw_issued <= 1;
            else if (retire_warm_ack) begin iw_pend <= 0; iw_issued <= 0; end
        end
    end
    assign q_iw_e = iaddr_r + MPI;
    genvar gq;
    generate for (gq = 0; gq < G; gq = gq + 1) begin : g_centre
        ot_hdc_v41_fh_kreg u_rvm (.clk(clk), .rst_n(rst_n), .d(rv_pre), .q(q_rv_mid[gq]));
        ot_hdc_v41_fh_kreg u_selm (.clk(clk), .rst_n(rst_n), .d(fline[DF-3]), .q(q_fsel_m[gq]));
        ot_hdc_v41_fh_kreg u_iwgm (.clk(clk), .rst_n(rst_n), .d(iw_go_n), .q(q_iwg_m[gq]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we_q <= 0;
        else if (iw_write_go) o_we_q <= {{(G-1){1'b0}}, 1'b1};
        else o_we_q <= o_we1;
    end
    // ======================= ot_hdc_v41_fh_sram_return_hardened request decode + ADDR_PIPE stage 1 ==============
    wire [G-1:0] read_ok, write_ok;
    wire [G*9-1:0] read_row, write_row;
    reg [G-1:0] address_fault;
    generate for (ga = 0; ga < G; ga = ga + 1) begin : g_address
        wire [AW-1:0] ra = ra_addr[ga*AW+:AW] - LG_BASE_WORD;
        wire [AW-1:0] wa = wr_addr[ga*AW+:AW] - LG_BASE_WORD;
        assign read_ok[ga] = ra_re[ga] && ra_addr[ga*AW+:AW] >= LG_BASE_WORD && ra[LG-1:0] == ga && (ra >> LG) < ROWS;
        assign write_ok[ga] = wr_en[ga] && wr_addr[ga*AW+:AW] >= LG_BASE_WORD && wa[LG-1:0] == ga && (wa >> LG) < ROWS;
        assign read_row[ga*9+:9] = 9'(ra >> LG);
        assign write_row[ga*9+:9] = 9'(wa >> LG);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) address_fault[ga] <= 0;
            else if ((ra_re[ga] && !read_ok[ga]) || (wr_en[ga] && !write_ok[ga])) address_fault[ga] <= 1;
    end endgenerate
    // (the write mask / data stage-1 registers sit at the quadrant pins: wr_mask / wr_data feed through)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_rok <= 0; q_wok <= 0; end
        else begin q_rok <= read_ok; q_wok <= write_ok; end
    always @(posedge clk) begin q_rrow <= read_row; q_wrow <= write_row; end
    // ======================= ot_hdc_v41_fh_macro_ctx: endpoint, retirement, consumers ============================
    wire native_ack_v, native_fault, native_bounds_fault, native_guard_busy;
    wire [7:0] native_ack_id;
    wire [23:0] native_ack_word;
    wire [15:0] native_ack_mask;
    wire [2830:0] native_request_check_full;
    wire [1266:0] native_reply_check_full;
    generate if(!LRET) begin : g_ep_in
    ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1),.CHECK_PIPE(1),.MARGIN(1),.FPIPE(FPIPE)) u_native (
        .fast_clk(clk),.cold_n(native_cold_n),
        .request_accept((|o_we)&&native_request_ready),.request_warm(commit_warm),
        .checked_reply_capture(native_reply_capture),.published_reply_v(native_reply_v),
        .native_ordinal(native_ordinal),.request_owner(native_request_owner),.request_id(commit_id),
        .head_we(o_we),.head_addr(o_addr),.head_mask(o_mask),.head_data(o_data),
        .checked_reply(native_checked_reply),.bounds_fault(native_bounds_fault),.endpoint_fault(native_fault),
        .captured_request(native_captured_request),.captured_request_check(native_request_check_full),
        .captured_reply(native_captured_reply),.captured_reply_check(native_reply_check_full),
        .request_checked_v(native_request_checked_v),.reply_checked_v(native_reply_checked_v),.guard_busy(native_guard_busy),
        .head_ack_v(native_ack_v),.head_ack_id(native_ack_id),.head_ack_word(native_ack_word),.head_ack_mask(native_ack_mask));
    end else begin : g_ep_out
        assign native_ack_v=ep_ack_v; assign native_ack_id=ep_ack_id; assign native_ack_word=ep_ack_word;
        assign native_ack_mask=ep_ack_mask; assign native_fault=ep_fault; assign native_guard_busy=ep_guard_busy;
        assign native_request_checked_v=ep_request_checked_v; assign native_reply_checked_v=ep_reply_checked_v;
        assign native_captured_request=0; assign native_captured_reply=0; assign native_bounds_fault=0;
    end endgenerate
    (* keep=1,dont_touch=1 *) reg request_v,request_check,reply_v,reply_check;
    assign native_permission_capture={reply_check,reply_v,request_check,request_v};
    always @(posedge clk) begin
        if(!native_cold_n) begin
            request_v<=0;request_check<=1;reply_v<=0;reply_check<=1;
        end else begin
            request_v<=native_request_checked_v;request_check<=~native_request_checked_v;
            reply_v<=native_reply_checked_v;reply_check<=~native_reply_checked_v;
        end
    end
    wire [G-1:0] group_fault_g;
    genvar gg;
    for(gg=0;gg<G;gg=gg+1) begin : g_gf
        assign group_fault_g[gg]=HQ?(q_group_fault[2*gg]|q_group_fault[2*gg+1]):q_group_fault[gg];
    end
    localparam integer PW=LRET?(G+TW+4):5512;
    wire parent_fault, rv, rw, retired_warm_payload, retired_ov, retired_leaf_v;
    wire child_leaf_v = tv[0], child_ov = ov;
    wire [PW-1:0] packet;
    wire [63:0] veto_pre;
    assign q_lane_veto = veto_pre;
    wire [PW-1:0] retired;
    wire [63:0] veto;
    wire [3:0] write_veto,retired_we,write_veto_nx;
    wire rv_nx, rw_nx;
    wire [PW-1:0] retired_nx;
    wire [3135:0] retired_leaf;
    wire [TW-1:0] raw_tag_out;
    wire raw_v_out;
    ot_hdc_v41_fh_retire_parent #(.ENABLE(1),.PAYLOAD_BITS(PW),.MARGIN(1),.SAFE(SAFE)) u_parent (
        .clk(clk),.rst_n(rst_n),.packet_v(r_v_q||child_ov||(|o_we_q)||warm_emit||child_leaf_v),
        .warm(warm_emit),.packet(packet),.warm_word(q_o_addr[23:0]),.warm_mask(q_o_mask[15:0]),
        .poison(q_poison),.address_fault(address_fault),.arithmetic_fault(native_fault),.group_fault(group_fault_g),
        .sink_busy(commit_busy||native_guard_busy),.ack_v(native_ack_v),.ack_id(native_ack_id),
        .ack_word(native_ack_word),.ack_mask(native_ack_mask),
        .retired_v(rv),.retired_warm(rw),.retired_packet(retired),.retired_id(commit_id),
        .lane_veto(veto),.lane_veto_pre(veto_pre),.write_veto(write_veto),.busy(retire_busy),.warm_ack(retire_warm_ack),
        .fault(parent_fault),.warm_debt(commit_debt),
        .retired_v_nx(rv_nx),.retired_warm_nx(rw_nx),.retired_packet_nx(retired_nx),.write_veto_nx(write_veto_nx));
    generate if(LRET) begin : g_narrow
        assign packet={o_we_q,r_tag_q,r_v_q,child_ov,child_leaf_v,warm_emit};
        assign {retired_we,raw_tag_out,raw_v_out,retired_ov,retired_leaf_v,retired_warm_payload}=retired;
        assign retired_leaf=0; assign o_addr=0; assign o_mask=0; assign o_data=0;
    end else begin : g_wide
        assign packet={q_leaf,o_we_q,q_o_addr,q_o_mask,q_o_data,r_tag_q,r_v_q,child_ov,child_leaf_v,warm_emit};
        assign {retired_leaf,retired_we,o_addr,o_mask,o_data,raw_tag_out,raw_v_out,
            retired_ov,retired_leaf_v,retired_warm_payload}=retired;
    end endgenerate
    generate if(OREG) begin : g_oreg
`ifndef SYNTHESIS
        initial if (!(LRET && SAFE)) $fatal(1, "OREG needs LRET and SAFE");
`endif
`ifdef OT_FH_OREG_MUTANT
        wire [3:0] we_nx = rv ? (retired_we & ~write_veto) : 4'b0;   // negative control: one cycle late
`else
        wire [3:0] we_nx = rv_nx ? (retired_nx[PW-1-:4] & ~write_veto_nx) : 4'b0;
`endif
        (* keep=1 *) reg [3:0] o_we_r; (* keep=1 *) reg warm_r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin o_we_r <= 4'b0; warm_r <= 1'b0; end
            else begin o_we_r <= we_nx; warm_r <= rw_nx && (|we_nx); end
        assign o_we = o_we_r; assign commit_warm = warm_r;
    end else begin : g_ocomb
        assign o_we=rv?(retired_we&~write_veto):4'b0;
        assign commit_warm=rw&&(|o_we);
    end endgenerate
    genvar l;
    for(l=0;l<64;l=l+1) begin : g_local_veto
        assign leaf[l*49+:49]={retired_leaf[l*49+48]&&!veto[l],retired_leaf[l*49+:48]};
    end
    assign fault=parent_fault;
    assign r_tag = raw_tag_out; assign r_v = raw_v_out;
    wire [(1+32+NW)*(G*W/2)-1:0] argmax_level1_full;
    wire argmax_fold;
    assign argmax_level1 = LRET ? 1'b0 : argmax_fold;
    for(genvar p=0;p<(LRET?0:G*W/2);p=p+1) begin : g_argmax_consumer
        localparam integer CW=1+32+NW;
        wire [CW-1:0] x0=leaf[CW*(2*p)+:CW];
        wire [CW-1:0] x1=leaf[CW*(2*p+1)+:CW];
        wire x0_wins=x0[CW-1]&&(!x1[CW-1]||x0[CW-2-:32]>x1[CW-2-:32]||
            (x0[CW-2-:32]==x1[CW-2-:32]&&x0[NW-1:0]<x1[NW-1:0]));
        reg [CW-1:0] c;
        if(SAFE) begin : g_rin   // SAFE: the stand-in consumer registers its operands first (as the MARGIN glue faces)
            reg [CW-1:0] r0,r1;
            always @(posedge clk) begin r0<=x0; r1<=x1; end
            wire r0_wins=r0[CW-1]&&(!r1[CW-1]||r0[CW-2-:32]>r1[CW-2-:32]||(r0[CW-2-:32]==r1[CW-2-:32]&&r0[NW-1:0]<r1[NW-1:0]));
            always @(posedge clk) c<=r0_wins?r0:r1;
        end else begin : g_rdir
            always @(posedge clk) c<=x0_wins?x0:x1;
        end
        assign argmax_level1_full[CW*p+:CW]=c;
    end
    if(SAFE) begin : g_fold_reg   // stand-in observation fold, registered (SAFE)
            localparam integer NF=((1+32+NW)*(G*W/2)+63)/64;
            wire [NF*64-1:0] ff={{(NF*64-(1+32+NW)*(G*W/2)){1'b0}},argmax_level1_full};
            reg [NF-1:0] f1; reg f2;
            integer fi;
            always @(posedge clk) begin for(fi=0;fi<NF;fi=fi+1) f1[fi]<=^ff[fi*64+:64]; f2<=^f1; end
            assign argmax_fold=f2;
        end else begin : g_fold_direct
            assign argmax_fold=^argmax_level1_full;
        end
endmodule
