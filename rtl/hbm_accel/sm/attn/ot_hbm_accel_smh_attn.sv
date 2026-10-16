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
    parameter integer BE_DELAY = 8,
    parameter integer HOPD = 4          // row-bundle registers per column hop (pt_w/pt_e incl. PT4): a column's control is
                                        // delayed with its rows, so the front's result deskew ((5 + PT4) a hop) aligns it
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

    wire [SUB*RBW-1:0] f_rl, f_rr;
    wire [NP*BBW-1:0]  f_bl, f_br;
    wire [NH*QLW-1:0]  f_ql, f_qr;
    ot_hbm_sm_attn_front_static u_front (.clk(clk), .rst_n(rst_n), .command(command), .kv_desc(kv_desc), .packet(packet),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .request(request),
        .rl(f_rl), .rr(f_rr), .bl(f_bl), .br(f_br), .ql(f_ql), .qr(f_qr),
        .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .schedule_fault(schedule_fault));
    // BE control: one broadcast register at the front, delayed inside every BE
    reg [28:0] be_cmd;
    always @(posedge clk or negedge rst_n) if (!rst_n) be_cmd <= 29'd0; else be_cmd <= command[111:83];

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
        ot_hbm_sm_attn_be #(.CONTROL_DELAY(BE_DELAY + HOPD * HOP), .SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW),
                            .NH(NH)) u_be (
            .clk(clk), .rst_n(rst_n), .attn_column(3'(c)), .command(be_cmd), .gin(t_go[(c*NP+NP-1)*SUB*GLW +: SUB*GLW]),
            .qin(e_qi[c*(NH-1)*QLW +: (NH-1)*QLW]), .qout(e_qo[c*NH*QLW +: NH*QLW]));
    end
    endgenerate
    assign f_ql = e_qo[(NL-1)*NH*QLW +: NH*QLW];
    assign f_qr = e_qo[NL*NH*QLW +: NH*QLW];
endmodule
`default_nettype wire
