`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_accel_smh_attn: the static production SM (ot_hbm_accel_smh_static, 8 columns x 2 tiles x 2 leaves, 512 MAC/cycle)
// with ATTENTION ON THE SM ENGINES (H-SM-ATT r2 2026-10-15, owner-adopted option B).  Opt-in successor: the original
// static SM and every closed master stay byte-identical; the attention variants carry their own names and no inherited
// physical view.
//   front  ot_hbm_sm_attn_front_static: 192-bit revisioned fixed calendar (command[82:0] = the legacy static schedule,
//          normal ops run through the unchanged ot_smh_static_front), separate 64-bit KV_DESC input, KV converter
//          (ot_hbm_sm_kv_line) in front of the row launch, probability store (ot_hbm_sm_attn_pstore) for PV x.
//   tiles  ot_hbm_sm_attn_tile: the closed XS / block-dot / pass-through children; the BF16 column = the closed tcl
//          halves + tct (QK) + ot_hbm_sm_pv_merge (PV, PUBLISH) via ot_hbm_sm_attn_native_col; static column / row straps.
//   BE     ot_hbm_sm_attn_be: closed tree + stack for normal ops, QK score landing (DS: one row slot a column; Qwen h128:
//          the 4-leaf combine bypassed) and PV publication lanes; its 29-bit control is command[111:83] (bit 111 = a
//          must-be-zero check bit), broadcast to the 8 columns and delayed BE_DELAY + HOPD x hop cycles inside each BE (in step with the column's rows).
// No credit, ready or retry on any on-die path: every slot is compiler-assigned; a missing beat, packet or score is a
// sticky schedule_fault (never a stall).  Only the DS FP8/FP4/BF16 production shape is supported (as the static SM).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_accel_smh_attn #(
    parameter integer KVMUT = 0,        // bench negative control only (converter mutant, ot_hbm_sm_kv_line MUT)
    parameter integer BE_DELAY = 8,
    parameter integer HOPD = 4,         // row-bundle registers per column hop (pt_w/pt_e incl. PT4): a column's control is
                                        // delayed with its rows, so the front's result deskew ((5 + PT4) a hop) aligns it
    parameter integer ENABLE_INT8 = 0   // SMB-INT8 (10-19) opt-in, default off (0 = the netlist / behaviour as before):
                                        // Qwen fmt-3 INT8 weights.  command[116] marks the cycle's packet as ONE packed
                                        // line of 128 INT8 codes; ot_smh_static_int8 (the real ot_hbm_accel_int8_line
                                        // converter, PIPE 1) turns it into two BF16 lines (low 64 codes first) that
                                        // reach the front 2 and 3 cycles later with the packet's tag, where the compiler
                                        // issues them as ordinary fmt-0 (BF16) lines (codes are exact in BF16, products
                                        // exact in FP32: the fmt-3 golden sm_int8 == the fmt-0 path on the widened image);
                                        // the row scale is applied after the reduction by the SU consumer (qwen_compiler
                                        // row_scale_*).  One packed line per two edges (the converter's fixed rate);
                                        // an overlap, a raw packet colliding with a converted beat, a mark without a
                                        // packet or a mark on an attention word is a sticky schedule_fault (no stall).
                                        // 1 = hard SAFE tile ot_smh_int8_tile (kit smh_int8_t1, LH-SMATT/INT8 10-19),
                                        // 2 = the soft reference glue ot_smh_static_int8 (cycle-exact, benches only).
    ,parameter integer INT8W = 0        // HBM-QINT8B (10-20) opt-in, default off: the WIDE INT8 front (ot_hbm_sm_i8w_front,
                                        // command mode 3): one packed 128-code line an edge = rows A (columns 0..3 side)
                                        // and B (columns 4..7 side) of one chunk as ordinary BF16 rows; column 4 leaves
                                        // as rdata column 1 while the result mode is set (VM slot 1).  128 codes/edge.
    // HBM-P4-SM (10-23, COORD R6(1), physical/die_plan/hbm/sm_split/README.md "RTL changes (Step C)"): opt-in, default off
    // (0 = the netlist / behaviour as before).  1 = the SM is built for the 4 stacked plan partitions a/b/c/d
    // (d = c0,c1 | c = c2,c3 + front + int8 + top | b = c4,c5 | a = c6,c7) with EVERY quarter crossing flop -> flop:
    //   R1      u_qs_c_r1l/u_qs_c_r1r (c): one output register on the front's rl, rr, bl, br together (rows leave from
    //           flops, rows and x-write beats in step); BE_DELAY + 1, front result deskew unchanged.            +1 cycle
    //   R2-alt  u_qs_c_land (c): the SM inputs (command, kv_desc, packet, xw_*) land on quarter c in ONE register, all in
    //           step (incl. the int8 packet select command[116]); everything inside sees the landed copy.     +1 cycle
    //   R3      u_qs_c_pin (c) + u_qs_b_out (b): rv / rrow / rdata / fault / schedule_fault pin register in c and a
    //           relay in b (the result lanes land in a).                                                       +2 cycles
    //   R4      u_qs_b_becmd (b): be_cmd relay for the c6 / c7 BEs (quarter a); their CONTROL_DELAY - 1.         0 cycles
    // Command -> result: +4 cycles, uniform (static pipeline, throughput unchanged).  The default build is unchanged.
    ,parameter integer QSPLIT =
`ifdef OT_SM_QSPLIT
        1
`else
        0
`endif
    ,parameter integer QSMUT =          // bench negative controls only (QSPLIT 1): 1 = R1 on the west side only (east rows /
                                        // beats one cycle early), 2 = R2 drops the packet's landing stage, 3 = R4 relay
                                        // without the CONTROL_DELAY - 1, 4 = R3 drops rdata's relay stage
`ifdef OT_SM_QSPLIT_MUT
        `OT_SM_QSPLIT_MUT
`else
        0
`endif
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [191:0]  command,
    input  wire [63:0]   kv_desc,
    input  wire [1098:0] packet,
    output wire [42:0]   request,
    input  wire          xw_en,
    input  wire [6:0]    xw_addr,
    input  wire [6:0]    xw_grp,
    input  wire [2047:0] xw_data,
    output wire          rv,
    output wire [11:0]   rrow,
    output wire [255:0]  rdata,
    output wire          fault,
    output wire          schedule_fault
);
    localparam integer SUB = 4, LBS = 2, LSB = 16, NC = 8, IL = 8, RMAX = 4096, LEV = 4, XD = 128, TCK = 1, RPT = 2;
    localparam integer LB    = SUB * LBS;
    localparam integer LF    = SUB * LSB;
    localparam integer XC    = LB * 266 + LF * 16;
    localparam integer FRAGW = NC * XC;
    localparam integer NBEAT = (FRAGW + 2047) / 2048;
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;
    localparam integer CW    = 6 + TAGW;
    localparam integer RBW   = CW + WSW + 1 + XW;
    localparam integer BBW   = 1 + XW + NBEAT + 2048;
    localparam integer GLW   = 2 + 32 + TAGW;
    localparam integer QLW   = 2 + 32 + RW;
    localparam integer NL    = NC / 2;
    localparam integer NR    = NC - NL;
    localparam integer NH    = (NL > NR) ? NL : NR;
    function automatic integer lg2g(input integer a, input integer b, input integer cc);
        integer k;
        begin
            k = 0;
            while (k < 11 && (a % (2 << k)) == 0 && (b % (2 << k)) == 0 && (cc % (2 << k)) == 0) k = k + 1;
            lg2g = k;
        end
    endfunction
    localparam integer A1B = 11 - lg2g(LBS * 266, XC, XC);
    localparam integer A2B = 11 - lg2g(LSB * 16, LB * 266, XC);
    localparam integer NP  = SUB / RPT;
    initial if (RBW != 818 || BBW != 2069 || QLW != 46) $fatal(1, "ot_hbm_accel_smh_attn: production shape only");

    wire [SUB*RBW-1:0] f_rl, f_rr, u_rl, u_rr;
    wire [NP*BBW-1:0]  f_bl, f_br, u_bl, u_br;
    // ---- R2-alt: SM input landing (quarter c) ----
    wire [191:0]  s_command;
    wire [63:0]   s_kv_desc;
    wire [1098:0] s_packet;
    wire          s_xw_en;
    wire [6:0]    s_xw_addr, s_xw_grp;
    wire [2047:0] s_xw_data;
    wire          u_rv, u_fault, u_schedule_fault;
    wire [11:0]   u_rrow;
    wire [255:0]  u_rdata;
    localparam integer INW = 192 + 64 + 1099 + 1 + 7 + 7 + 2048;      // 3418
    // reset: the whole command word (zero = idle), packet valid, xw_en; data fields are not reset
    localparam [INW-1:0] IN_RM = {{192{1'b1}}, 64'd0, 1'b1, 1098'd0, 1'b1, 14'd0, 2048'd0};
    generate if (QSPLIT != 0) begin : g_qs_in
        wire [INW-1:0] land_q;
        ot_smh_qs_reg #(.W(INW), .RM(IN_RM)) u_qs_c_land (.clk(clk), .rst_n(rst_n),
            .d({command, kv_desc, packet, xw_en, xw_addr, xw_grp, xw_data}), .q(land_q));
        assign {s_command, s_kv_desc} = land_q[INW-1 -: 256];
        assign s_packet = (QSMUT == 2) ? packet : land_q[INW-257 -: 1099];
        assign {s_xw_en, s_xw_addr, s_xw_grp, s_xw_data} = land_q[2062:0];
    end else begin : g_no_qs_in
        assign s_command = command; assign s_kv_desc = kv_desc; assign s_packet = packet;
        assign s_xw_en = xw_en; assign s_xw_addr = xw_addr; assign s_xw_grp = xw_grp; assign s_xw_data = xw_data;
    end endgenerate
    wire [NH*QLW-1:0]  f_ql, f_qr;
    wire [191:0]  f_command;
    wire [1098:0] f_packet;
    wire          f_schedule_fault, i8_schedule_fault;
    generate if (ENABLE_INT8) begin : g_int8
        wire          i8_mark = s_command[116];
        wire [1098:0] i8_out;
        wire [34:0]   i8_sel;                                // kept copies of i8_out[1098]: bit b selects with copy b/32
        if (ENABLE_INT8 == 2) begin : g_soft                 // reference form (SMB-INT8 e592ae5d0): soft converter glue
            ot_smh_static_int8 u_int8 (.clk(clk), .rst_n(rst_n), .packet_in({s_packet[1098] & i8_mark, s_packet[1097:0]}),
                .packet_out(i8_out));
            assign i8_sel = {35{i8_out[1098]}};
        end else begin : g_hard                              // LH-SMATT/INT8 10-19: hard SAFE tile (kit smh_int8_t1),
            wire          t_v;                               // cycle-exact with g_soft; reset release +2 (face landing)
            wire [9:0]    t_tag;
            wire [1023:0] t_data;
            ot_smh_int8_tile u_int8 (.clk(clk), .rst_n(rst_n), .i_v(s_packet[1098] & i8_mark), .i_tag(s_packet[1097:1088]),
                .i_codes(s_packet[1023:0]), .o_v(t_v), .o_tag(t_tag), .o_data(t_data), .o_sel(i8_sel));
            assign i8_out = {t_v, t_tag, 64'd0, t_data};
        end
        assign f_command = {s_command[191:117], 1'b0, s_command[115:0]};
        genvar i8b;
        for (i8b = 0; i8b < 1099; i8b = i8b + 1) begin : g_i8mux
            assign f_packet[i8b] = i8_sel[i8b / 32] ? i8_out[i8b] : (!i8_mark && s_packet[i8b]);
        end
        reg i8_fault, i8_busy;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin i8_fault <= 1'b0; i8_busy <= 1'b0; end
            else begin
                i8_busy <= s_packet[1098] && i8_mark;              // the converter's second (high-half) edge
                if ((i8_mark && (!s_packet[1098] || s_command[183] || i8_busy)) || (!i8_mark && s_packet[1098] && i8_out[1098]))
                    i8_fault <= 1'b1;
            end
        assign i8_schedule_fault = i8_fault;
    end else begin : g_no_int8
        assign f_command = s_command;
        assign f_packet  = s_packet;
        assign i8_schedule_fault = 1'b0;
    end endgenerate
    ot_hbm_sm_attn_front_static #(.KVMUT(KVMUT), .INT8W(INT8W)) u_front (.clk(clk), .rst_n(rst_n), .command(f_command), .kv_desc(s_kv_desc), .packet(f_packet),
        .xw_en(s_xw_en), .xw_addr(s_xw_addr), .xw_grp(s_xw_grp), .xw_data(s_xw_data), .request(request),
        .rl(u_rl), .rr(u_rr), .bl(u_bl), .br(u_br), .ql(f_ql), .qr(f_qr),
        .rv(u_rv), .rrow(u_rrow), .rdata(u_rdata), .fault(u_fault), .schedule_fault(f_schedule_fault));
    assign u_schedule_fault = f_schedule_fault | i8_schedule_fault;
    // ---- R1: front row-bundle / beat launch registers (quarter c); R3: SM output pin registers (c) + relay (b) ----
    localparam [RBW-1:0] ROW_RM = {2'b11, {(RBW-10){1'b0}}, 1'b1, 7'd0};    // vb, vf, ce (ot_hbm_sm_attn_row_launch)
    localparam [BBW-1:0] BEAT_RM = {1'b1, {(BBW-1){1'b0}}};                // beat valid
    localparam integer SDW = SUB * RBW + NP * BBW;
    localparam [SDW-1:0] SIDE_RM = {{SUB{ROW_RM}}, {NP{BEAT_RM}}};
    localparam integer OW = 1 + 12 + 256 + 1 + 1;
    localparam [OW-1:0] OUT_RM = {1'b1, 12'd0, 256'd0, 1'b1, 1'b1};
    generate if (QSPLIT != 0) begin : g_qs_out
        ot_smh_qs_reg #(.W(SDW), .RM(SIDE_RM)) u_qs_c_r1l (.clk(clk), .rst_n(rst_n), .d({u_rl, u_bl}), .q({f_rl, f_bl}));
        if (QSMUT == 1) begin : g_mut1
            assign f_rr = u_rr; assign f_br = u_br;
        end else begin : g_r1r
            ot_smh_qs_reg #(.W(SDW), .RM(SIDE_RM)) u_qs_c_r1r (.clk(clk), .rst_n(rst_n), .d({u_rr, u_br}), .q({f_rr, f_br}));
        end
        wire [OW-1:0] pin_q, out_q;
        ot_smh_qs_reg #(.W(OW), .RM(OUT_RM)) u_qs_c_pin (.clk(clk), .rst_n(rst_n),
            .d({u_rv, u_rrow, u_rdata, u_fault, u_schedule_fault}), .q(pin_q));
        ot_smh_qs_reg #(.W(OW), .RM(OUT_RM)) u_qs_b_out (.clk(clk), .rst_n(rst_n), .d(pin_q), .q(out_q));
        assign {rv, rrow} = out_q[OW-1 -: 13];
        assign rdata = (QSMUT == 4) ? pin_q[257 -: 256] : out_q[257 -: 256];
        assign {fault, schedule_fault} = out_q[1:0];
    end else begin : g_no_qs_out
        assign f_rl = u_rl; assign f_rr = u_rr; assign f_bl = u_bl; assign f_br = u_br;
        assign rv = u_rv; assign rrow = u_rrow; assign rdata = u_rdata; assign fault = u_fault;
        assign schedule_fault = u_schedule_fault;
    end endgenerate
    // BE control: one broadcast register at the front, delayed inside every BE
    reg [28:0] be_cmd;
    always @(posedge clk or negedge rst_n) if (!rst_n) be_cmd <= 29'd0; else be_cmd <= s_command[111:83];
    // R4: be_cmd relay in quarter b for the quarter-a BEs (c6, c7), their CONTROL_DELAY - 1 (0 cycles)
    wire [28:0] be_cmd_a;
    localparam integer BED = BE_DELAY + ((QSPLIT != 0) ? 1 : 0);              // R1: rows leave one cycle later
    generate if (QSPLIT != 0) begin : g_qs_be
        ot_smh_qs_reg #(.W(29), .RM({29{1'b1}})) u_qs_b_becmd (.clk(clk), .rst_n(rst_n), .d(be_cmd), .q(be_cmd_a));
    end else begin : g_no_qs_be
        assign be_cmd_a = be_cmd;
    end endgenerate

    localparam integer TRW = RPT * RBW;
    localparam integer TGI = (SUB - RPT) * GLW;
    wire [NC*NP*TRW-1:0]  t_ri, t_ro;
    wire [NC*NP*BBW-1:0]  t_bi, t_bo;
    wire [NC*NP*TGI-1:0]  t_gi;
    wire [NC*NP*SUB*GLW-1:0] t_go;
    wire [NC*(NH-1)*QLW-1:0] e_qi;
    wire [NC*NH*QLW-1:0]     e_qo;
    genvar c, p, j;
    generate
    for (c = 0; c < NC; c = c + 1) begin : g_c
        for (p = 0; p < NP; p = p + 1) begin : g_p
            localparam integer T = c * NP + p;
            if (c == NL - 1) begin : g_fl
                assign t_ri[T*TRW +: TRW] = f_rl[p*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = f_bl[p*BBW +: BBW];
            end else if (c < NL - 1) begin : g_wl
                assign t_ri[T*TRW +: TRW] = t_ro[((c+1)*NP+p)*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = t_bo[((c+1)*NP+p)*BBW +: BBW];
            end else if (c == NL) begin : g_fr
                assign t_ri[T*TRW +: TRW] = f_rr[p*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = f_br[p*BBW +: BBW];
            end else begin : g_er
                assign t_ri[T*TRW +: TRW] = t_ro[((c-1)*NP+p)*TRW +: TRW];
                assign t_bi[T*BBW +: BBW] = t_bo[((c-1)*NP+p)*BBW +: BBW];
            end
            if (p == 0) begin : g_g0
                assign t_gi[T*TGI +: TGI] = {TGI{1'b0}};
            end else begin : g_gn
                assign t_gi[T*TGI +: TGI] = t_go[(T-1)*SUB*GLW +: TGI];
            end
            wire [RPT*A1B-1:0] sa1; wire [RPT*5-1:0] sg1; wire [RPT*A2B-1:0] sa2; wire [RPT*5-1:0] sg2;
            for (j = 0; j < RPT; j = j + 1) begin : g_s
                localparam integer R  = p * RPT + j;
                localparam integer FA = c * XC + R * LBS * 266;
                localparam integer FB = c * XC + LB * 266 + R * LSB * 16;
                localparam [10:0] SA1 = FA % 2048;
                localparam [10:0] SA2 = FB % 2048;
                localparam [4:0]  SG1 = FA / 2048;
                localparam [4:0]  SG2 = FB / 2048;
                assign sa1[j*A1B +: A1B] = SA1[10 -: A1B];
                assign sa2[j*A2B +: A2B] = SA2[10 -: A2B];
                assign sg1[j*5 +: 5] = SG1;
                assign sg2[j*5 +: 5] = SG2;
            end
            ot_hbm_sm_attn_tile #(.SUB(SUB), .RPT(RPT), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW),
                                  .XD(XD), .NBEAT(NBEAT), .TCK(TCK), .A1B(A1B), .A2B(A2B)) u_t (
                .clk(clk), .rst_n(rst_n), .attn_column(3'(c)), .attn_rowbase(2'(p * RPT)),
                .xs_a1(sa1), .xs_g1(sg1), .xs_a2(sa2), .xs_g2(sg2),
                .rin(t_ri[T*TRW +: TRW]), .bin(t_bi[T*BBW +: BBW]), .rout(t_ro[T*TRW +: TRW]),
                .bout(t_bo[T*BBW +: BBW]), .gin(t_gi[T*TGI +: TGI]), .gout(t_go[T*SUB*GLW +: SUB*GLW]));
        end
        if (c < NL) begin : g_ql
            if (c == 0) begin : g_q0
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = {(NH-1)*QLW{1'b0}};
            end else begin : g_qn
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = e_qo[(c-1)*NH*QLW +: (NH-1)*QLW];
            end
        end else begin : g_qr
            if (c == NC - 1) begin : g_q0
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = {(NH-1)*QLW{1'b0}};
            end else begin : g_qn
                assign e_qi[c*(NH-1)*QLW +: (NH-1)*QLW] = e_qo[(c+1)*NH*QLW +: (NH-1)*QLW];
            end
        end
        localparam integer HOP = (c < NL) ? (NL - 1 - c) : (c - NL);
        localparam integer QA = (QSPLIT != 0) && (c >= NC - 2);               // quarter a (c6, c7): relayed be_cmd
        localparam integer CDQ = (QA && QSMUT != 3) ? 1 : 0;
        ot_hbm_sm_attn_be #(.CONTROL_DELAY(BED + HOPD * HOP - CDQ), .SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW),
                            .NH(NH)) u_be (
            .clk(clk), .rst_n(rst_n), .attn_column(3'(c)), .command(QA ? be_cmd_a : be_cmd), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
            .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
    end
    endgenerate
    assign f_ql = e_qo[(NL-1)*NH*QLW +: NH*QLW];
    assign f_qr = e_qo[NL*NH*QLW +: NH*QLW];
endmodule

// HBM-P4-SM (10-23): one quarter-crossing register stage (QSPLIT).  Bits with RM set are async-reset flops (valids, the
// command word), the rest plain flops; a named instance per quarter (u_qs_<quarter>_*) so the partition tools and
// physical/die_plan/hbm/sm_split/tools/qsplit_check.py can place it and check every crossing is flop -> flop.
module ot_smh_qs_reg #(
    parameter integer W = 1,
    parameter [W-1:0] RM = {W{1'b0}}
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    genvar i;
    generate for (i = 0; i < W; i = i + 1) begin : g_b
        if (RM[i]) begin : g_r
            reg r;
            always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= d[i];
            assign q[i] = r;
        end else begin : g_n
            reg r;
            always @(posedge clk) r <= d[i];
            assign q[i] = r;
        end
    end endgenerate
endmodule
`default_nettype wire
