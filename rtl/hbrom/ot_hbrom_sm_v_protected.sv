`timescale 1ns/1ps
// Opt-in protected full-shape NC1 integration. Original source preserved.
// Leaf handles +2 read codec edges; start/op pipeline adds +2 write-fence edges.
// Shared vector/RF service and ROM feed belong outside this compute block.
module ot_hbrom_sm_v_protected #(
    parameter integer PROTECT = 0,
    parameter integer ENABLE = 0,
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 1,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer TCK  = 1,         // ENABLE = 1: BF16 column with the bubble gate off the multiplier's first
                                        // stage (ot_hbm_accel_tc16, bit-identical, 0 cycles); 0 = ot_gpu_tc16
    parameter integer DS   = 2,         // per-sub distribution stages between s1 and the sub-half copy
    parameter integer DW   = 4,         // per-sub x-write stages between the pin register and the sub-half copy
    parameter integer DG   = 3,         // gather stages between a leaf's G1 and its column's tree input
    parameter integer PIO  = 2,         // boundary stages between the pins and the hub, each way
    parameter integer STK  = 1          // 1: ot_hbm_accel_stack (look-ahead levels, +1 cycle); 0: ot_gpu_stack
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    output wire                    busy,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [6:0]              xw_grp,
    input  wire [8*256-1:0]        xw_data,
    output wire                    rv,
    output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0]        rdata,
    output wire                    fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    generate if (PROTECT == 0) begin : g_original
        ot_hbm_accel_sm_v #(.ENABLE(ENABLE),.SUB(SUB),.LBS(LBS),.LSB(LSB),.NC(NC),.IL(IL),
          .RMAX(RMAX),.LEV(LEV),.XD(XD),.MAX_OUT(MAX_OUT),.TCK(TCK),.DS(DS),.DW(DW),.DG(DG),.PIO(PIO),.STK(STK)) original (.*);
    end else begin : g_protected
    if (ENABLE!=1 || NC!=1 || SUB!=4 || LBS!=2 || LSB!=16 || IL!=8 || RMAX!=4096 || LEV!=4 || XD!=128 || MAX_OUT!=512 || STK!=1)
      initial $fatal(1,"protected NC1 requires priced full shape");
    wire bulk_fault,issue_fault,descriptor_fault,request_fault;
    wire metadata_fault;
    wire boundary_fault;
    wire [SUB-1:0] distribution_fault,l2_fault;
    wire [NC*SUB-1:0] gather_fault;
    wire [NC-1:0] combine_metadata_fault;
    wire output_metadata_fault;
    wire storage_control_fault=bulk_fault|issue_fault|descriptor_fault|request_fault|metadata_fault|boundary_fault|(|distribution_fault)|(|l2_fault)|(|gather_fault)|(|combine_metadata_fault)|output_metadata_fault|(halt!=halt_shadow);
    (* keep *) reg halt,halt_shadow;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin halt<=0;halt_shadow<=0;end
      else begin halt<=halt|halt_shadow|storage_control_fault;halt_shadow<=halt_shadow|halt|storage_control_fault;end
    localparam integer LB    = SUB * LBS;
    localparam integer LF    = SUB * LSB;
    localparam integer XC    = LB * 266 + LF * 16;     // x bits per column (the fragment layout of ot_gpu_sm_v)
    localparam integer FRAGW = NC * XC;
    localparam integer NBEAT = (FRAGW + 2047) / 2048;   // x-write beats per fragment
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer SLW   = LBS * 266 + LSB * 16;   // x slice of one leaf
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;   // unpacked weight slice of one sub
    localparam integer CW    = 6 + TAGW;               // control: iv_b, iv_f, first, last, fp4, bf16-op
    localparam integer HC    = 4;                       // columns per sub half (L2 group)
    localparam integer NH    = (NC + HC - 1) / HC;
    localparam integer OPW   = (RW + 1) + 16 + 8 + 1 + 2;
    localparam integer CHD   = 2 * PIO + 3;             // channel FIFO depth (credits): one transfer a cycle

    // ---------------- boundary: pins <-> hub ----------------
    wire          h_start;
    wire [OPW-1:0] h_op;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO+2), .RST(1)) u_pst (.clk(clk), .rst_n(rst_n), .d(start), .q(h_start));
    ot_hbm_accel_smv_chain #(.W(OPW), .D(PIO+2), .RST(0)) u_pop (.clk(clk), .rst_n(rst_n),
        .d({op_rows, op_c, op_g, op_gs, op_fmt}), .q(h_op));
    wire [RW:0] h_rows = h_op[OPW-1 -: RW+1];
    wire [15:0] h_c    = h_op[11 +: 16];
    wire [7:0]  h_g    = h_op[3 +: 8];
    wire        h_gs   = h_op[2];
    wire [1:0]  h_fmt  = h_op[1:0];
    wire h_rsp_v; wire [9:0] h_rsp_tag; wire [1087:0] h_rsp_data;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(rsp_v), .q(h_rsp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(PIO), .RST(0)) u_prd (.clk(clk), .rst_n(rst_n), .d({rsp_tag, rsp_data}),
        .q({h_rsp_tag, h_rsp_data}));
    wire h_release;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prl (.clk(clk), .rst_n(rst_n), .d(release_in), .q(h_release));
    wire pst_shadow,release_shadow,rspv_shadow;
    wire [OPW-1:0] pop_shadow;
    wire [9:0] rspt_shadow;
    ot_hbm_accel_smv_chain #(.W(1),.D(PIO+2),.RST(1)) mirror_start(.clk(clk),.rst_n(rst_n),.d(start),.q(pst_shadow));
    ot_hbm_accel_smv_chain #(.W(OPW),.D(PIO+2),.RST(1)) mirror_op(.clk(clk),.rst_n(rst_n),.d({op_rows,op_c,op_g,op_gs,op_fmt}),.q(pop_shadow));
    ot_hbm_accel_smv_chain #(.W(1),.D(PIO),.RST(1)) mirror_release(.clk(clk),.rst_n(rst_n),.d(release_in),.q(release_shadow));
    ot_hbm_accel_smv_chain #(.W(1),.D(PIO),.RST(1)) mirror_rspv(.clk(clk),.rst_n(rst_n),.d(rsp_v),.q(rspv_shadow));
    ot_hbm_accel_smv_chain #(.W(10),.D(PIO),.RST(1)) mirror_rspt(.clk(clk),.rst_n(rst_n),.d(rsp_tag),.q(rspt_shadow));
    assign boundary_fault=(h_start!=pst_shadow)||(h_start&&(h_op!=pop_shadow))||(h_release!=release_shadow)
      ||(h_rsp_v!=rspv_shadow)||(h_rsp_v&&(h_rsp_tag!=rspt_shadow));
    // descriptor and request handshakes: credit channels (inputs land in a flop, ready / valid leave one)
    wire h_d_valid, h_d_ready; wire [55:0] h_d;
    ot_hbrom_control_channel #(.W(56), .P(PIO), .DEPTH(CHD)) u_dch (.clk(clk), .rst_n(rst_n),
        .s_valid(d_valid), .s_ready(d_ready), .s_data({d_base, d_lines}),
        .m_valid(h_d_valid), .m_ready(h_d_ready), .m_data(h_d),.fault(descriptor_fault));
    wire h_req_v, h_req_ready; wire [31:0] h_req_addr; wire [9:0] h_req_tag;
    ot_hbrom_control_channel #(.W(42), .P(PIO), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rst_n),
        .s_valid(h_req_v), .s_ready(h_req_ready), .s_data({h_req_addr, h_req_tag}),
        .m_valid(req_v), .m_ready(req_ready), .m_data({req_addr, req_tag}),.fault(request_fault));

    // ---------------- bulk copy (routed-closed successor) ----------------
    wire          w_valid, w_ready;
    wire [1087:0] w_data;
    ot_hbrom_bulk_copy_protected #(.PROTECT(1),.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1),
                             .RING_MACRO(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(h_d_valid), .d_ready(h_d_ready), .d_base(h_d[55:24]), .d_lines(h_d[23:0]),
        .req_v(h_req_v), .req_ready(h_req_ready), .req_addr(h_req_addr), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v&&!boundary_fault&&!halt), .rsp_tag(h_rsp_tag), .rsp_data(h_rsp_data),
        .s_valid(w_valid), .s_ready(w_ready), .s_data(w_data), .outstanding(), .idle(),.fault(bulk_fault));

    // ---------------- issue (routed-closed successor) ----------------
    reg  [1:0]  fmt_q;
    wire        sv, h_busy, h_arrive, h_released;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fmt_q <= 2'd0;
        else if (h_start && !h_busy) fmt_q <= h_fmt;
    ot_hbrom_issue_protected #(.PROTECT(1),.ENABLE(1), .IL(IL), .RMAX(RMAX), .XDEPTH(XD)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(h_start&&!boundary_fault&&!halt), .op_rows(h_rows), .op_c(h_c), .op_g(h_g), .op_gs(h_gs),
        .w_valid(w_valid&&!halt&&!bulk_fault), .x_rdy(!halt&&!bulk_fault), .w_ready(w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release&&!boundary_fault&&!halt),
        .released(h_released),.fault(issue_fault));
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q({busy, arrive, released}));

    // ---------------- stage s1: the issue's outputs and the line, registered ----------------
    reg              s1_v, s1_first, s1_last;
    reg [TAGW-1:0]   s1_tag;
    reg [1087:0]     s1_w;
    reg [XW-1:0]     s1_xa;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_first <= 1'b0; s1_last <= 1'b0; end
        else begin s1_v <= adv && row_ok; s1_first <= i_first; s1_last <= i_last; end
    end
    always @(posedge clk) begin
        s1_tag <= {row_now[RW-1:0], i_glast, si};
        s1_w <= w_data;
        s1_xa <= xa;
    end

    // ---------------- x-write beat, registered at the pins ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;                 // one-hot beat group
    reg [2047:0]     w0_data;
    integer gq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w0_en <= 1'b0;
        else w0_en <= xw_en;
    always @(posedge clk) begin
        w0_addr <= xw_addr; w0_data <= xw_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (xw_grp == gq);
    end

    // Independent top control register copies. Data arithmetic remains single.
    (* keep *) reg [1:0] fmt_shadow;
    (* keep *) reg s1_v_shadow,s1_first_shadow,s1_last_shadow,w0_en_shadow;
    (* keep *) reg [TAGW-1:0] s1_tag_shadow;
    (* keep *) reg [XW-1:0] s1_xa_shadow,w0_addr_shadow;
    (* keep *) reg [NBEAT-1:0] w0_oh_shadow;
    (* keep *) reg metadata_bad,metadata_bad_shadow;
    wire metadata_mismatch=(fmt_q!=fmt_shadow)||(s1_v!=s1_v_shadow)||(w0_en!=w0_en_shadow)
      ||(s1_v&&({s1_first,s1_last,s1_tag,s1_xa}!={s1_first_shadow,s1_last_shadow,s1_tag_shadow,s1_xa_shadow}))
      ||(w0_en&&({w0_addr,w0_oh}!={w0_addr_shadow,w0_oh_shadow}));
    assign metadata_fault=metadata_bad||metadata_bad_shadow||metadata_mismatch;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n)begin fmt_shadow<=0;s1_v_shadow<=0;s1_first_shadow<=0;s1_last_shadow<=0;w0_en_shadow<=0;metadata_bad<=0;metadata_bad_shadow<=0;end
      else begin
        if(h_start&&!h_busy)fmt_shadow<=h_fmt;
        s1_v_shadow<=adv&&row_ok;s1_first_shadow<=i_first;s1_last_shadow<=i_last;
        w0_en_shadow<=xw_en;
        metadata_bad<=metadata_bad|metadata_bad_shadow|metadata_mismatch;
        metadata_bad_shadow<=metadata_bad_shadow|metadata_bad|metadata_mismatch;
      end
    end
    integer shadow_gq;
    always @(posedge clk)begin
      s1_tag_shadow<={row_now[RW-1:0],i_glast,si};s1_xa_shadow<=xa;
      w0_addr_shadow<=xw_addr;
      for(shadow_gq=0;shadow_gq<NBEAT;shadow_gq=shadow_gq+1)w0_oh_shadow[shadow_gq]<=(xw_grp==shadow_gq);
    end

    // ---------------- per sub: unpack, DS / DW stage chains ----------------
    localparam integer XBW = 1 + XW;                     // x-read bundle: ce, address
    localparam integer WBW = 1 + XW + NBEAT + 2048;      // x-write bundle
    wire [SUB*CW-1:0]  l1_c;
    wire [SUB*WSW-1:0] l1_w;
    wire [SUB*XBW-1:0] l1_x;
    wire [SUB*WBW-1:0] l1_b;
    wire bf_op = (fmt_q == 2'd0);
    genvar sp, h, c, q, bb;
    for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
        // the sub's unpacked weight slice: {iwf (LSB x 16), iwe (LBS x 10), iwq (LBS x 256)}, as ot_gpu_sm_v stage 2
        wire [WSW-1:0] un;
        for (q = 0; q < LBS; q = q + 1) begin : g_q
            localparam integer J = sp * LBS + q;
            wire [255:0] fp4w, fp8w;
            for (bb = 0; bb < 32; bb = bb + 1) begin : g_b
                assign fp4w[8*bb +: 8] = {4'd0, s1_w[128*J + 4*bb +: 4]};
                assign fp8w[8*bb +: 8] = (J < LB / 2) ? s1_w[256*J + 8*bb +: 8] : 8'd0;
            end
            assign un[256*q +: 256] = (fmt_q == 2'd2) ? fp4w : fp8w;
            assign un[LBS*256 + 10*q +: 10] = {2'b00, s1_w[1024 + 8*J +: 8]} - 10'sd127;
        end
        assign un[LBS*266 +: LSB*16] = s1_w[sp*LSB*16 +: LSB*16];
        wire [CW-1:0] c_in = {s1_v && !bf_op, s1_v && bf_op, s1_first, s1_last, fmt_q == 2'd2, bf_op, s1_tag};
        ot_hbm_accel_smv_chain #(.W(2), .D(DS), .RST(1)) u_cv (.clk(clk), .rst_n(rst_n), .d(c_in[CW-1 -: 2]),
            .q(l1_c[CW*sp + CW - 2 +: 2]));
        ot_hbm_accel_smv_chain #(.W(CW-2), .D(DS), .RST(0)) u_cd (.clk(clk), .rst_n(rst_n), .d(c_in[CW-3:0]),
            .q(l1_c[CW*sp +: CW-2]));
        ot_hbm_accel_smv_chain #(.W(WSW), .D(DS), .RST(0)) u_w (.clk(clk), .rst_n(rst_n), .d(un),
            .q(l1_w[WSW*sp +: WSW]));
        ot_hbm_accel_smv_chain #(.W(1), .D(DS), .RST(1)) u_xv (.clk(clk), .rst_n(rst_n), .d(s1_v), .q(l1_x[XBW*sp]));
        ot_hbm_accel_smv_chain #(.W(XW), .D(DS), .RST(0)) u_xa (.clk(clk), .rst_n(rst_n), .d(s1_xa),
            .q(l1_x[XBW*sp + 1 +: XW]));
        ot_hbm_accel_smv_chain #(.W(1), .D(DW), .RST(1)) u_bv (.clk(clk), .rst_n(rst_n), .d(w0_en), .q(l1_b[WBW*sp]));
        ot_hbm_accel_smv_chain #(.W(WBW - 1), .D(DW), .RST(0)) u_bd (.clk(clk), .rst_n(rst_n),
            .d({w0_data, w0_oh, w0_addr}), .q(l1_b[WBW*sp + 1 +: WBW - 1]));
        wire [CW-1:0] c_shadow;
        wire [XBW-1:0] x_shadow;
        wire [1+XW+NBEAT-1:0] b_shadow;
        ot_hbm_accel_smv_chain #(.W(CW),.D(DS),.RST(1)) mirror_c(.clk(clk),.rst_n(rst_n),.d(c_in),.q(c_shadow));
        ot_hbm_accel_smv_chain #(.W(XBW),.D(DS),.RST(1)) mirror_x(.clk(clk),.rst_n(rst_n),.d({s1_xa,s1_v}),.q(x_shadow));
        ot_hbm_accel_smv_chain #(.W(1+XW+NBEAT),.D(DW),.RST(1)) mirror_b(.clk(clk),.rst_n(rst_n),.d({w0_oh,w0_addr,w0_en}),.q(b_shadow));
        assign distribution_fault[sp]=(l1_c[CW*sp+CW-2+:2]!=c_shadow[CW-1-:2])
          ||((|c_shadow[CW-1-:2])&&(l1_c[CW*sp+:CW]!=c_shadow))
          ||(l1_x[XBW*sp]!=x_shadow[0])||(x_shadow[0]&&(l1_x[XBW*sp+:XBW]!=x_shadow))
          ||(l1_b[WBW*sp]!=b_shadow[0])||(b_shadow[0]&&(l1_b[WBW*sp+:1+XW+NBEAT]!=b_shadow));
    end

    // ---------------- per sub half: L2 copies; leaves ----------------
    wire [NC*SUB-1:0]      g_v, g_f;
    wire [NC*SUB*32-1:0]   g_y;
    wire [NC*SUB*TAGW-1:0] g_t;
    for (sp = 0; sp < SUB; sp = sp + 1) begin : g_l2s
        for (h = 0; h < NH; h = h + 1) begin : g_h
            wire [CW-1:0]  c2;
            wire [WSW-1:0] w2;
            wire [XBW-1:0] x2;
            wire [WBW-1:0] b2;
            ot_hbm_accel_bc_kreg #(.W(2)) u_cv (.clk(clk), .rst_n(rst_n), .d(l1_c[CW*sp + CW - 2 +: 2]), .q(c2[CW-1 -: 2]));
            ot_hbm_accel_smv_pipe #(.W(CW-2)) u_cd (.clk(clk), .d(l1_c[CW*sp +: CW-2]), .q(c2[CW-3:0]));
            ot_hbm_accel_smv_pipe #(.W(WSW)) u_w (.clk(clk), .d(l1_w[WSW*sp +: WSW]), .q(w2));
            ot_hbm_accel_bc_kreg #(.W(1)) u_xv (.clk(clk), .rst_n(rst_n), .d(l1_x[XBW*sp]), .q(x2[0]));
            ot_hbm_accel_smv_pipe #(.W(XW)) u_xa (.clk(clk), .d(l1_x[XBW*sp + 1 +: XW]), .q(x2[1 +: XW]));
            ot_hbm_accel_bc_kreg #(.W(1)) u_bv (.clk(clk), .rst_n(rst_n), .d(l1_b[WBW*sp]), .q(b2[0]));
            ot_hbm_accel_smv_pipe #(.W(WBW - 1)) u_bd (.clk(clk), .d(l1_b[WBW*sp + 1 +: WBW - 1]),
                                                      .q(b2[1 +: WBW - 1]));
            (* keep *) reg [CW-1:0] c2_shadow;
            (* keep *) reg [XBW-1:0] x2_shadow;
            (* keep *) reg [1+XW+NBEAT-1:0] b2_shadow;
            always @(posedge clk or negedge rst_n)
              if(!rst_n)begin c2_shadow<=0;x2_shadow<=0;b2_shadow<=0;end
              else begin c2_shadow<=l1_c[CW*sp+:CW];x2_shadow<=l1_x[XBW*sp+:XBW];b2_shadow<=l1_b[WBW*sp+:1+XW+NBEAT];end
            assign l2_fault[sp]=(c2[CW-1-:2]!=c2_shadow[CW-1-:2])
              ||((|c2_shadow[CW-1-:2])&&(c2!=c2_shadow))
              ||(x2[0]!=x2_shadow[0])||(x2_shadow[0]&&(x2!=x2_shadow))
              ||(b2[0]!=b2_shadow[0])||(b2_shadow[0]&&(b2[0+:1+XW+NBEAT]!=b2_shadow));
            for (c = h * HC; c < NC && c < (h + 1) * HC; c = c + 1) begin : g_c
                wire gv1, gf1; wire [31:0] gy1; wire [TAGW-1:0] gt1;
                ot_hbrom_smv_leaf_protected #(.PROTECT(1),.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                                        .NBEAT(NBEAT), .COL(c), .SP(sp), .TCK(TCK)) u_leaf (
                    .clk(clk), .rst_n(rst_n), .c_in({c2[CW-1 -: 2]&{2{!storage_control_fault&&!halt}},c2[CW-3:0]}), .w_in(w2), .x_ce(x2[0]&&!storage_control_fault&&!halt), .x_addr(x2[1 +: XW]),
                    .b_en(b2[0]&&!storage_control_fault&&!halt), .b_addr(b2[1 +: XW]), .b_oh(b2[1 + XW +: NBEAT]), .b_data(b2[1 + XW + NBEAT +: 2048]),
                    .gv(gv1), .gy(gy1), .gt(gt1), .gf(gf1));
                wire [1+TAGW:0] gathered_shadow;
                ot_hbm_accel_smv_chain #(.W(2+TAGW),.D(DG),.RST(1)) mirror_gather(.clk(clk),.rst_n(rst_n),.d({gt1,gv1,gf1}),.q(gathered_shadow));
                assign gather_fault[c*SUB+sp]=({g_v[c*SUB+sp],g_f[c*SUB+sp]}!=gathered_shadow[1:0])
                  ||(g_v[c*SUB+sp]&&(g_t[TAGW*(c*SUB+sp)+:TAGW]!=gathered_shadow[2+:TAGW]));
                // gather toward the hub
                ot_hbm_accel_smv_chain #(.W(2), .D(DG), .RST(1)) u_gv (.clk(clk), .rst_n(rst_n), .d({gv1, gf1}),
                    .q({g_v[c*SUB + sp], g_f[c*SUB + sp]}));
                ot_hbm_accel_smv_chain #(.W(32 + TAGW), .D(DG), .RST(0)) u_gd (.clk(clk), .rst_n(rst_n),
                    .d({gy1, gt1}), .q({g_y[32*(c*SUB + sp) +: 32], g_t[TAGW*(c*SUB + sp) +: TAGW]}));
            end
        end
    end

    // ---------------- per column: tree input register, combine tree, streaming stack ----------------
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*RW-1:0] crow;
    for (c = 0; c < NC; c = c + 1) begin : g_col
        reg              tv_in;
        reg [SUB*32-1:0] td_in;
        reg [TAGW-1:0]   tt_in;
        reg              gfault;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin tv_in <= 1'b0; gfault <= 1'b0; end
            else begin tv_in <= g_v[c*SUB]; gfault <= |g_f[c*SUB +: SUB]; end
        always @(posedge clk) begin
            td_in <= g_y[32*c*SUB +: 32*SUB];
            tt_in <= g_t[TAGW*c*SUB +: TAGW];
        end
        (* keep *) reg tv_in_shadow,gfault_shadow;
        (* keep *) reg [TAGW-1:0] tt_in_shadow;
        always @(posedge clk or negedge rst_n)
          if(!rst_n)begin tv_in_shadow<=0;gfault_shadow<=0;tt_in_shadow<=0;end
          else begin tv_in_shadow<=g_v[c*SUB];gfault_shadow<=|g_f[c*SUB+:SUB];tt_in_shadow<=g_t[TAGW*c*SUB+:TAGW];end
        assign combine_metadata_fault[c]=(tv_in!=tv_in_shadow)||(gfault!=gfault_shadow)
          ||(tv_in&&(tt_in!=tt_in_shadow));
        wire tv, tf;
        wire [31:0] ty;
        wire [TAGW-1:0] tt;
        ot_hbrom_tree_protected #(.PROTECT(1),.N(SUB), .TAGW(TAGW), .ALAT(7)) u_comb (.clk(clk), .rst_n(rst_n), .v(tv_in), .d(td_in),
                                                              .tag(tt_in), .ov(tv), .y(ty), .otag(tt), .fault(tf));
        wire kf;
        if (STK != 0) begin : g_stk
            ot_hbrom_stack_protected #(.PROTECT(1),.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
                .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
                .itag(tt[TAGW-1:SW+1]), .ov(cv[c]), .y(cy[32*c +: 32]), .otag(crow[RW*c +: RW]), .fault(kf));
        end else begin : g_stk0
            ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
                .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
                .itag(tt[TAGW-1:SW+1]), .ov(cv[c]), .y(cy[32*c +: 32]), .otag(crow[RW*c +: RW]), .fault(kf));
        end
        assign cf[c] = gfault | tf | kf;
    end
    assign sv = cv[0];
    reg              rv_q, fault_q;
    reg [RW-1:0]     rrow_q;
    reg [NC*32-1:0]  rdata_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv_q <= 1'b0; fault_q <= 1'b0; end
        else begin rv_q <= cv[0]&&!storage_control_fault&&!(|cf); fault_q <= fault_q | (|cf) | storage_control_fault; end
    end
    always @(posedge clk) begin rrow_q <= crow[RW-1:0]; rdata_q <= cy; end
    (* keep *) reg rv_q_shadow,fault_q_shadow;
    (* keep *) reg [RW-1:0] rrow_q_shadow;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin rv_q_shadow<=0;fault_q_shadow<=0;rrow_q_shadow<=0;end
      else begin
        rv_q_shadow<=cv[0]&&!storage_control_fault&&!(|cf);
        fault_q_shadow<=fault_q_shadow|(|cf)|storage_control_fault;
        rrow_q_shadow<=crow[RW-1:0];
      end
    wire [1+RW:0] result_control_shadow;
    ot_hbm_accel_smv_chain #(.W(2+RW),.D(PIO),.RST(1)) mirror_result_control(.clk(clk),.rst_n(rst_n),
      .d({rrow_q_shadow,rv_q_shadow,fault_q_shadow}),.q(result_control_shadow));
    assign output_metadata_fault=(rv_q!=rv_q_shadow)||(fault_q!=fault_q_shadow)
      ||(rv_q&&(rrow_q!=rrow_q_shadow))
      ||({final_rv,final_fault}!=result_control_shadow[1:0])
      ||(final_rv&&(rrow!=result_control_shadow[2+:RW]));
    wire final_rv,final_fault;
    assign rv=final_rv&&!final_fault&&!storage_control_fault&&!halt;
    assign fault=final_fault|storage_control_fault|halt;
    ot_hbm_accel_smv_chain #(.W(2), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d({rv_q, fault_q}),
        .q({final_rv, final_fault}));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({rrow_q, rdata_q}), .q({rrow, rdata}));
    end endgenerate
endmodule

