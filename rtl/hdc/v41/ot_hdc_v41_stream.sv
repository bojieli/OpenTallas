`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Stream unit of the DeepSeek-V4.1 hardwired decode core (tools/hdc_isa_v41.py).
//
// SW lanes.  A 2-D loop (outer o, inner i) issues one VECTOR of up to SW
// elements per cycle and never stalls (in SEQ-reduction ops, one element every
// 8 cycles).  The instruction's `su_vec` picks the lane axis:
//
//   SCALAR  one element per cycle (lane 0)
//   VI      lanes take consecutive inner indices i .. i+SW-1 of one outer o
//   VO      lanes take consecutive outer indices o .. o+SW-1 at one inner i;
//           every lane owns whole segments, so its reducer sums its segment in
//           exactly the scalar order (P=8 interleaved partials, pairwise tree)
//
// Every lane is the whole scalar datapath (ot_hdc_v41_su_lane): each element
// reads four operands and passes one fixed pipeline of qualified binary32
// units:
//
//   F0  loop state -> address parts; gather-index read (a_ind)
//   F1  (index returns)
//   F2  element addresses (A gathered, C = A ^ 1 in pair mode) -> memories
//   F3  (memories answer)            F4  capture, source select
//   PRE A' = min(relu(rnd?(A)), imm3), C' = clip(C, +-imm3)          1
//   M1  P  = A' | A'*B | A'*A' | A'*imm1 | A'/B | A'/imm1 | max(A',B) 5, or 31 (divide)
//       Q  = C' * (+-D)  (sign per element parity in RoPE modes), delayed to meet P2
//   M2  P2 = P | P*C' | P*imm1                                         5
//   AD  R  = P2 | +Q | +C' | -B | +imm2 | +D                            5
//   SFU S  = R | exp | rsqrt | sqrt | sigmoid | silu | sqrt(softplus) | Engram gate
//   E1  T  = S | *C' | +C' | *imm2 | +imm2                              5
//   E2  U  = T | *B | *imm1                                             5
//   RND out = bf16?(U)                                                  1
//   -> vector memory, KV SRAM (element or transposed-KV address), reducer
//
// sigmoid(R) = 1 / (exp(-R) + 1), silu(R) = R / (exp(-R) + 1) and the Engram gate
// sigmoid(+-sqrt(max(|R|, 1e-6))) divide with the correctly rounded pipe
// ot_hdc_fdiv, exactly as tools/hdc_golden_v41.py does.  Lane 0 is FULL (every
// SFU function); lanes 1.. carry exp, the sigmoid/SiLU chain and the M1
// divider only -- rsqrt, sqrt, sqrt(softplus) and the Engram gate act on at
// most a dozen elements per op, so the program issues those ops SCALAR.  The
// depth of an element depends on its op's CLASS (M1 divides or not, and the
// SFU function); a new op of another class waits for the unit to drain, so
// writes stay in order.  Everything travelling beside the data rides tapped
// delay lines whose tap is the class depth.  Lanes run in lockstep.
//
// Reductions: each lane's reducer (ot_hdc_reduce) takes out, or out*out, per
// outer segment, or (SCALAR only, `red_whole`) over the whole op; SEQ is its
// SUM with one partial (elements 8 cycles apart).  `red_tree` sums every
// segment in its lane, collects the (at most 16) segment sums and adds them by
// a pairwise tree ((s0+s1)+(s2+s3))+... padded with +0 -- the golden's
// segmented long sum.  A result may be rounded to BF16.
// ---------------------------------------------------------------------------
module ot_hdc_v41_tapline #(
    parameter integer W = 32,
    parameter integer D = 8
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    input  wire [15:0]  depth,          // 1 .. D, constant while data is in flight
    output wire [W-1:0] q
);
    reg [W*D-1:0] line;                 // tap n (1-based) = line[W*n-1 -: W]
    always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
    assign q = line[W*depth-1 -: W];
endmodule

module ot_hdc_v41_vtap #(
    parameter integer D = 8
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clr,
    input  wire        v,
    input  wire [15:0] depth,
    output wire        q
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else if (clr) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign q = line[depth];
endmodule

// One lane: the element datapath from the loop position to the writes and the
// lane's reducer.  The loop state is the controller's (lane 0's position); a
// lane adds its constant offset.
module ot_hdc_v41_su_lane #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer WR = 64,
    parameter integer KVT_SH = 9,
    parameter integer LANE = 0,
    parameter integer FULL = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // loop position (controller registers, sampled on emit)
    input  wire              emit,
    input  wire [1:0]        vmode,
    input  wire [NW-1:0]     o, i, nout_r, nin_r,
    input  wire              i_last_r,
    input  wire [31:0]       g, total,
    input  wire [NW:0]       fin_th,
    input  wire              seq,
    input  wire [AW-1:0]     arow, acol, brow, bcol, crow, ccol, drow, dcol, orow_a, ocol, rrow, krow,
    // op registers
    input  wire [AW-1:0]     abase, aso, asi, aibase, bso, bsi, cso, csi, dso, dsi, oso, osi, rso, obase,
    input  wire [1:0]        aind, dst,
    input  wire              bhalf, cpair, redwhole, redtree, redrnd,
    input  wire [3:0]        cls,
    input  wire              clrv,
    input  wire [2*4+1+1+1+1+3+2+3+3+3+2+1+2+2+1+32*3-1:0] op_now,
    // memories
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output reg  [3:0]        vm_re,
    output reg  [4*AW-1:0]   vm_addr,
    input  wire [4*32-1:0]   vm_q,
    output reg  [3:0]        cr_re,
    output reg  [4*AW-1:0]   cr_addr,
    input  wire [4*64-1:0]   cr_q,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    // writes
    output reg               vm_we,
    output reg  [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output reg  [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output reg               red_we,
    output reg  [AW-1:0]     red_addr,
    output reg  [31:0]       red_data,
    // segment sums of a red_tree op (to the controller's tree)
    output reg               seg_v,
    output reg  [3:0]        seg_idx,
    output reg  [31:0]       seg_data,
    // status
    output wire              retire,
    output wire              busy,
    output wire              fault
);
    localparam [1:0] V_SCALAR = 0, V_VI = 1, V_VO = 2;
    localparam [2:0] M1_BYP = 0, M1_AB = 1, M1_AA = 2, M1_AIMM = 3, M1_DIVB = 4, M1_DIVIMM = 5, M1_MAXB = 6;
    localparam [1:0] M2_BYP = 0, M2_C = 1, M2_IMM = 2;
    localparam [2:0] QM_OFF = 0, QM_POS = 1, QM_NEG = 2, QM_ALT_NP = 3, QM_ALT_PN = 4;
    localparam [2:0] AD_BYP = 0, AD_Q = 1, AD_C = 2, AD_NEGB = 3, AD_IMM = 4, AD_D = 5;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SIGM = 4, SFU_SILU = 5,
                     SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam [2:0] E1_BYP = 0, E1_MULC = 1, E1_ADDC = 2, E1_MULIMM = 3, E1_ADDIMM = 4;
    localparam [1:0] E2_BYP = 0, E2_MULB = 1, E2_MULIMM = 2;
    localparam [1:0] RED_NONE = 0, RED_SUM = 1, RED_MAX = 2, RED_SEQ = 3;
    localparam integer D_EXP = 92, D_RSQ = 61, D_SQRT = 31, D_DIV = 31, D_SP = 259;
    localparam integer D_SIGC = D_EXP + 5 + D_DIV;          // sigmoid chain: exp, +1, divide
    localparam integer D_EGIN = 1 + D_SQRT + 1;             // |x| max, sqrt, sign
    localparam integer SFU_MAX = D_SP;
    localparam integer LW = $clog2(WR);
    localparam integer OPW = 2*4 + 1+1+1+1 + 3+2+3+3+3+2 + 1 + 2 + 2 + 1 + 32*3;

    function automatic [31:0] bf16(input [31:0] x);
        bf16 = (x + 32'h7FFF + {31'd0, x[16]}) & 32'hFFFF0000;
    endfunction
    function [15:0] sfu_depth(input [2:0] s);
        case (s)
            SFU_EXP: sfu_depth = D_EXP;
            SFU_RSQRT: sfu_depth = D_RSQ;
            SFU_SQRT: sfu_depth = D_SQRT;
            SFU_SIGM, SFU_SILU: sfu_depth = D_SIGC;
            SFU_SPSQRT: sfu_depth = D_SP;
            SFU_EGATE: sfu_depth = D_EGIN + D_SIGC;
            default: sfu_depth = 1;
        endcase
    endfunction

    // -- F0: this lane's element, address parts, gather index -----------------------------
    localparam integer TT = 2 + 3 + 3 + 2 + 1 + 2 + AW + 2 + 1 + 1 + 1 + 1 + 1 + 3 + (AW + 2) + 32 + 32 + 1;
    wire [AW-1:0] L = LANE;
    wire vi_m = (vmode == V_VI), vo_m = (vmode == V_VO);
    wire lane_v = emit && (vo_m ? ({{(32-NW){1'b0}}, o} + LANE < {{(32-NW){1'b0}}, nout_r}) :
                           vi_m ? ({{(32-NW){1'b0}}, i} + LANE < {{(32-NW){1'b0}}, nin_r}) : (LANE == 0));
    wire [NW-1:0] il = vi_m ? i + LANE[NW-1:0] : i;
    wire [NW-1:0] ol = vo_m ? o + LANE[NW-1:0] : o;
    wire [AW-1:0] kl = vo_m ? krow + L : krow;
    wire [AW-1:0] a_row_off = vo_m ? L * aso : {AW{1'b0}};
    wire [AW-1:0] a_col_off = vi_m ? L * asi : {AW{1'b0}};
    wire [AW-1:0] b_off = vo_m ? L * bso : vi_m ? (bhalf ? (L >> 1) * bsi : L * bsi) : {AW{1'b0}};
    wire [AW-1:0] c_off = vo_m ? L * cso : vi_m ? L * csi : {AW{1'b0}};
    wire [AW-1:0] d_off = vo_m ? L * dso : vi_m ? (bhalf ? (L >> 1) * dsi : L * dsi) : {AW{1'b0}};
    wire [AW-1:0] o_off = vo_m ? L * oso : vi_m ? L * osi : {AW{1'b0}};
    wire [AW-1:0] r_off = vo_m ? L * rso : {AW{1'b0}};
    // i-derived reduction flags of a segment (SCALAR and VO: il == i)
    wire          il_last = vi_m ? ({{(32-NW){1'b0}}, il} + 1 == {{(32-NW){1'b0}}, nin_r}) : i_last_r;

    reg          f0_v, f1_v, f2_v, f3_v, f4_v;
    reg [AW-1:0] f0_arow, f0_acol, f0_b, f0_c, f0_d, f0_o;
    reg          f0_par, f0_ifirst, f0_first8, f0_final, f0_last;
    reg [2:0]    f0_p;
    reg [AW+1:0] f0_r;                  // {tree, rnd, address or segment index}
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin f0_v <= 0; f1_v <= 0; f2_v <= 0; f3_v <= 0; f4_v <= 0; vi_re <= 0; end
        else begin
            f0_v <= lane_v; f1_v <= f0_v; f2_v <= f1_v; f3_v <= f2_v; f4_v <= f3_v;
            vi_re <= lane_v && (aind != 2'd0);
        end
    end
    wire [AW-1:0] kv_t = (kl >> 4) << KVT_SH;
    always @(posedge clk) begin
        vi_addr <= aibase + ((aind == 2'd1) ? {{(AW-NW){1'b0}}, il} : {{(AW-NW){1'b0}}, ol});
        f0_arow <= arow + a_row_off; f0_acol <= acol + a_col_off;
        f0_b <= brow + bcol + b_off; f0_c <= crow + ccol + c_off; f0_d <= drow + dcol + d_off;
        f0_o <= (dst == 2'd3) ? obase + kv_t + ({{(AW-NW){1'b0}}, il} << 4) + {{(AW-4){1'b0}}, kl[3:0]}
                              : orow_a + ocol + o_off;
        f0_par <= il[0];
        if (redwhole && !redtree) begin
            f0_ifirst <= (g == 0); f0_first8 <= (g < 8); f0_final <= (g + 8 >= total); f0_last <= (g + 1 == total);
            f0_p <= g[2:0];
        end else if (seq) begin
            f0_ifirst <= (i == 0); f0_first8 <= (i == 0); f0_final <= i_last_r; f0_last <= i_last_r; f0_p <= 3'd0;
        end else begin
            f0_ifirst <= (il == 0); f0_first8 <= (il < 8);
            f0_final <= ($signed({1'b0, il}) >= $signed(fin_th)); f0_last <= il_last; f0_p <= il[2:0];
        end
        f0_r <= redtree ? {1'b1, 1'b0, {(AW-NW){1'b0}}, ol} : {1'b0, redrnd, rrow + r_off};
    end
    // F1: index arrives next cycle
    reg [AW-1:0] f1_arow, f1_acol, f1_b, f1_c, f1_d, f1_o;
    reg          f1_par, f1_ifirst, f1_first8, f1_final, f1_last;
    reg [2:0]    f1_p;
    reg [AW+1:0] f1_r;
    always @(posedge clk) begin
        f1_arow <= f0_arow; f1_acol <= f0_acol; f1_b <= f0_b; f1_c <= f0_c; f1_d <= f0_d; f1_o <= f0_o;
        f1_par <= f0_par; f1_ifirst <= f0_ifirst; f1_first8 <= f0_first8; f1_final <= f0_final;
        f1_last <= f0_last; f1_p <= f0_p; f1_r <= f0_r;
    end
    // F2: element addresses to the memories
    wire [1:0] s0_asrc = op_now[OPW-1 -: 2], s0_bsrc = op_now[OPW-3 -: 2], s0_csrc = op_now[OPW-5 -: 2],
               s0_dsrc = op_now[OPW-7 -: 2];
    reg  [1:0] f1_asrc, f1_bsrc, f1_csrc, f1_dsrc, f0_asrc, f0_bsrc, f0_csrc, f0_dsrc;
    always @(posedge clk) begin
        f0_asrc <= s0_asrc; f0_bsrc <= s0_bsrc; f0_csrc <= s0_csrc; f0_dsrc <= s0_dsrc;
        f1_asrc <= f0_asrc; f1_bsrc <= f0_bsrc; f1_csrc <= f0_csrc; f1_dsrc <= f0_dsrc;
    end
    wire [AW-1:0] idx = vi_q[AW-1:0];
    wire [AW-1:0] a_addr = abase + ((aind == 2'd2) ? idx * aso : f1_arow) + ((aind == 2'd1) ? idx * asi : f1_acol);
    wire [AW-1:0] c_addr = cpair ? (a_addr ^ {{(AW-1){1'b0}}, 1'b1}) : f1_c;
    reg [AW-1:0] f2_o;
    reg          f2_par, f2_ifirst, f2_first8, f2_final, f2_last;
    reg [2:0]    f2_p;
    reg [AW+1:0] f2_r;
    reg [LW-1:0] f2_lane;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vm_re <= 0; cr_re <= 0; wrom_re <= 0; end
        else begin
            vm_re <= {4{f1_v}} & {f1_dsrc == 2'd0, f1_csrc == 2'd0, f1_bsrc == 2'd0, f1_asrc == 2'd0};
            cr_re <= {4{f1_v}} & {f1_dsrc != 2'd0, f1_csrc != 2'd0, f1_bsrc != 2'd0,
                                  f1_asrc == 2'd1 || f1_asrc == 2'd2};
            wrom_re <= f1_v && f1_asrc == 2'd3;
        end
    end
    always @(posedge clk) begin
        vm_addr <= {f1_d, c_addr, f1_b, a_addr};
        cr_addr <= {f1_d, c_addr, f1_b, a_addr};
        wrom_addr <= a_addr >> LW; f2_lane <= a_addr[LW-1:0];
        f2_o <= f1_o; f2_par <= f1_par; f2_ifirst <= f1_ifirst; f2_first8 <= f1_first8; f2_final <= f1_final;
        f2_last <= f1_last; f2_p <= f1_p; f2_r <= f1_r;
    end
    // F3: memories answer; carry the tags
    reg [AW-1:0] f3_o;
    reg          f3_par, f3_ifirst, f3_first8, f3_final, f3_last;
    reg [2:0]    f3_p;
    reg [AW+1:0] f3_r;
    reg [LW-1:0] f3_lane;
    always @(posedge clk) begin
        f3_o <= f2_o; f3_par <= f2_par; f3_ifirst <= f2_ifirst; f3_first8 <= f2_first8; f3_final <= f2_final;
        f3_last <= f2_last; f3_p <= f2_p; f3_r <= f2_r; f3_lane <= f2_lane;
    end
    // F4: capture and select sources.  Op constants travel with the element as a
    // snapshot taken at emit (a following op may be accepted meanwhile).
    function automatic [31:0] pick(input [1:0] src, input [31:0] v, input [63:0] c, input [31:0] w);
        case (src)
            2'd0: pick = v;
            2'd1: pick = c[31:0];
            2'd2: pick = c[63:32];
            default: pick = w;
        endcase
    endfunction
    wire [OPW-1:0] op4;
    ot_hdc_delay #(.W(OPW), .D(4)) u_opd (.clk(clk), .rst_n(rst_n), .d(op_now), .q(op4));
    wire [1:0]  s_asrc, s_bsrc, s_csrc, s_dsrc, s_dst, s_red;
    wire        s_arnd, s_arelu, s_amin, s_cclip, s_rnd, s_redsq;
    wire [2:0]  s_m1, s_qm, s_ad, s_e1;
    wire [1:0]  s_m2, s_e2;
    wire [31:0] s_imm1, s_imm2, s_imm3;
    assign {s_asrc, s_bsrc, s_csrc, s_dsrc, s_arnd, s_arelu, s_amin, s_cclip, s_m1, s_m2, s_qm, s_ad, s_e1,
            s_e2, s_rnd, s_dst, s_red, s_redsq, s_imm1, s_imm2, s_imm3} = op4;
    reg [31:0] x_a, x_b, x_c, x_d;
    reg [TT-1:0] x_tail;
    reg [2:0]  x_m1, x_qm, x_ad;
    reg [1:0]  x_m2;
    reg        x_arnd, x_arelu, x_amin, x_cclip, x_par;
    reg [31:0] x_imm3;
    always @(posedge clk) begin
        x_a <= pick(s_asrc, vm_q[31:0], cr_q[63:0], {wrom_q[16*f3_lane +: 16], 16'h0000});
        x_b <= pick(s_bsrc, vm_q[63:32], cr_q[127:64], 32'd0);
        x_c <= pick(s_csrc, vm_q[95:64], cr_q[191:128], 32'd0);
        x_d <= pick(s_dsrc, vm_q[127:96], cr_q[255:192], 32'd0);
        x_m1 <= s_m1; x_m2 <= s_m2; x_qm <= s_qm; x_ad <= s_ad; x_par <= f3_par;
        x_arnd <= s_arnd; x_arelu <= s_arelu; x_amin <= s_amin; x_cclip <= s_cclip; x_imm3 <= s_imm3;
        x_tail <= {s_m2, s_e1, s_ad, s_e2, s_rnd, s_dst, f3_o, s_red, s_redsq, f3_ifirst, f3_first8, f3_final,
                   f3_last, f3_p, f3_r, s_imm1, s_imm2, f3_par};
    end
    // -- PRE -----------------------------------------------------------------------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic [31:0] fmin(input [31:0] a, input [31:0] b);   // min on ordered keys
        fmin = (okey(a) <= okey(b)) ? a : b;
    endfunction
    function automatic [31:0] fmax(input [31:0] a, input [31:0] b);
        fmax = (okey(a) >= okey(b)) ? a : b;
    endfunction
    wire [31:0] a_r = x_arnd ? bf16(x_a) : x_a;
    wire [31:0] a_l = (x_arelu && a_r[31]) ? 32'd0 : a_r;
    wire [31:0] a_m = x_amin ? fmin(a_l, x_imm3) : a_l;
    wire [31:0] c_m = x_cclip ? fmin(fmax(x_c, {1'b1, x_imm3[30:0]}), x_imm3) : x_c;
    reg  [31:0] p_a, p_b, p_c, p_d;
    reg  [2:0]  p_m1, p_qm;
    reg  [TT-1:0] p_tail;
    reg         p_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p_v <= 1'b0; else p_v <= f4_v;
    end
    always @(posedge clk) begin
        p_a <= a_m; p_b <= x_b; p_c <= c_m; p_d <= x_d; p_m1 <= x_m1; p_qm <= x_qm; p_tail <= x_tail;
    end
    wire [31:0] p_imm1 = p_tail[33 +: 32];
    // -- M1 (5 or 31) and Q -------------------------------------------------------------------
    wire        m1div = cls[3];
    wire [15:0] d_m1 = m1div ? 16'd31 : 16'd5;
    wire [31:0] mul1_y, div1_y, byp1;
    wire f_m1, f_d1, dv1;
    ot_hdc_fmul u_m1 (clk, rst_n, p_v && (p_m1 == M1_AB || p_m1 == M1_AA || p_m1 == M1_AIMM), p_a,
                      (p_m1 == M1_AB) ? p_b : (p_m1 == M1_AA) ? p_a : p_imm1, mul1_y, f_m1);
    ot_hdc_fdiv u_d1 (.clk(clk), .rst_n(rst_n), .v(p_v && m1div), .a(p_a), .b((p_m1 == M1_DIVB) ? p_b : p_imm1),
                      .y(div1_y), .vo(dv1), .fault(f_d1));
    wire [31:0] byp_in = (p_m1 == M1_MAXB && okey(p_b) > okey(p_a)) ? p_b : p_a;
    ot_hdc_delay #(.W(32), .D(5)) u_b1 (.clk(clk), .rst_n(rst_n), .d(byp_in), .q(byp1));
    wire [2:0] m1_5;
    ot_hdc_delay #(.W(3), .D(5)) u_m1k (.clk(clk), .rst_n(rst_n), .d(p_m1), .q(m1_5));
    wire [31:0] P = m1div ? div1_y : (m1_5 == M1_BYP || m1_5 == M1_MAXB) ? byp1 : mul1_y;
    // Q = C' * (+-D)
    wire        qneg = (p_qm == QM_NEG) || (p_qm == QM_ALT_NP && !p_tail[0]) || (p_qm == QM_ALT_PN && p_tail[0]);
    wire [31:0] q_y, q_d;
    wire f_q;
    ot_hdc_fmul u_q (clk, rst_n, p_v && p_qm != QM_OFF, p_c, {p_d[31] ^ qneg, p_d[30:0]}, q_y, f_q);
    ot_hdc_v41_tapline #(.W(32), .D(31)) u_qd (.clk(clk), .d(q_y), .depth(d_m1), .q(q_d));
    // tags across M1
    localparam integer MT = 32 + 32 + 32 + TT;         // B, C', D, tail
    wire [MT-1:0] m1_tag;
    ot_hdc_v41_tapline #(.W(MT), .D(31)) u_t1 (.clk(clk), .d({p_b, p_c, p_d, p_tail}), .depth(d_m1), .q(m1_tag));
    wire v_m1;
    ot_hdc_v41_vtap #(.D(31)) u_v1 (.clk(clk), .rst_n(rst_n), .clr(clrv), .v(p_v), .depth(d_m1), .q(v_m1));
    wire [31:0] t1_b = m1_tag[MT-1 -: 32], t1_c = m1_tag[MT-33 -: 32], t1_d = m1_tag[MT-65 -: 32];
    wire [TT-1:0] t1_tail = m1_tag[TT-1:0];
    // -- M2 --------------------------------------------------------------------------------------
    wire [1:0]  t1_m2 = t1_tail[TT-1 -: 2];
    wire [31:0] t1_imm1 = t1_tail[33 +: 32];
    wire [31:0] m2_y, m2_byp;
    wire [31:0] m2_q = q_d;             // Q already meets P2 (delayed by the M1 depth)
    wire [31:0] a2_b, a2_c, a2_d;
    wire [TT-1:0] a2_tail;
    wire [1:0] a2_m2;
    wire f_m2;
    ot_hdc_fmul u_m2 (clk, rst_n, v_m1 && t1_m2 != M2_BYP, P, (t1_m2 == M2_C) ? t1_c : t1_imm1, m2_y, f_m2);
    ot_hdc_delay #(.W(32 * 4 + TT + 2), .D(5)) u_d2 (.clk(clk), .rst_n(rst_n),
        .d({P, t1_b, t1_c, t1_d, t1_tail, t1_m2}), .q({m2_byp, a2_b, a2_c, a2_d, a2_tail, a2_m2}));
    wire [5:0] vm2;
    ot_hdc_vline #(.D(5)) u_vm2 (.clk(clk), .rst_n(rst_n), .v(v_m1), .vd(vm2));
    wire [31:0] P2 = (a2_m2 == M2_BYP) ? m2_byp : m2_y;
    // -- AD ----------------------------------------------------------------------------------------
    wire [2:0]  a2_ad = a2_tail[TT-6 -: 3];
    wire [31:0] a2_imm2 = a2_tail[1 +: 32];
    reg  [31:0] ad_y;
    always @(*) begin
        case (a2_ad)
            AD_Q:    ad_y = m2_q;
            AD_C:    ad_y = a2_c;
            AD_NEGB: ad_y = {~a2_b[31], a2_b[30:0]};
            AD_IMM:  ad_y = a2_imm2;
            default: ad_y = a2_d;
        endcase
    end
    wire [31:0] add_y, add_byp;
    wire f_ad;
    ot_hdc_fadd u_ad (clk, rst_n, vm2[5] && a2_ad != AD_BYP, P2, ad_y, add_y, f_ad);
    wire [31:0] r_b, r_c;
    wire [TT-1:0] r_tail;
    wire [2:0] r_ad;
    ot_hdc_delay #(.W(32 + 32 + 32 + TT + 3), .D(5)) u_d3 (.clk(clk), .rst_n(rst_n),
        .d({P2, a2_b, a2_c, a2_tail, a2_ad}), .q({add_byp, r_b, r_c, r_tail, r_ad}));
    wire [5:0] vad;
    ot_hdc_vline #(.D(5)) u_vad (.clk(clk), .rst_n(rst_n), .v(vm2[5]), .vd(vad));
    wire [31:0] R = (r_ad == AD_BYP) ? add_byp : add_y;
    wire        v_r = vad[5];
    // -- SFU -----------------------------------------------------------------------------------------
    wire [2:0]  sfu = cls[2:0];
    wire [15:0] d_sfu = sfu_depth(sfu);
    wire [31:0] y_exp, y_rsq, y_sqrt, y_spr, y_div;
    wire f_e, f_r, f_s, f_sp, f_den, f_div;
    // sigmoid chain: exp(-x); +1; (1 | x) / that.  Input: R (sigmoid, silu) or the gate's signed root.
    wire        eg_yv;
    wire [31:0] eg_y;
    wire        sc_v = (sfu == SFU_EGATE) ? eg_yv : (v_r && (sfu == SFU_SIGM || sfu == SFU_SILU));
    wire [31:0] sc_x = (sfu == SFU_EGATE) ? eg_y : R;
    wire        ex_v = (sfu == SFU_EXP) ? v_r : sc_v;
    wire [31:0] ex_x = (sfu == SFU_EXP) ? R : {~sc_x[31], sc_x[30:0]};
    wire vo_e, vo_div;
    ot_hdc_exp u_exp (.clk(clk), .rst_n(rst_n), .v(ex_v), .x(ex_x), .y(y_exp), .vo(vo_e), .fault(f_e));
    wire [31:0] den, num_d;
    ot_hdc_fadd u_den (clk, rst_n, vo_e && sfu != SFU_EXP, y_exp, 32'h3F800000, den, f_den);
    ot_hdc_delay #(.W(32), .D(D_EXP + 5)) u_num (.clk(clk), .rst_n(rst_n), .d(sc_x), .q(num_d));
    wire [5:0] vden;
    ot_hdc_vline #(.D(5)) u_vden (.clk(clk), .rst_n(rst_n), .v(vo_e && sfu != SFU_EXP), .vd(vden));
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vden[5]), .a((sfu == SFU_SILU) ? num_d : 32'h3F800000),
                       .b(den), .y(y_div), .vo(vo_div), .fault(f_div));
    generate
        if (FULL != 0) begin : g_full
            wire vo_r, vo_s, vo_sp;
            wire [31:0] y_sp;
            ot_hdc_rsqrt u_rsq (.clk(clk), .rst_n(rst_n), .v(v_r && sfu == SFU_RSQRT), .x(R), .y(y_rsq), .vo(vo_r),
                                .fault(f_r));
            ot_hdc_softplus u_sp (.clk(clk), .rst_n(rst_n), .v(v_r && sfu == SFU_SPSQRT), .x(R), .sp(y_sp),
                                  .r(y_spr), .vo(vo_sp), .fault(f_sp));
            // Engram gate prologue: m = max(|R|, 1e-6); sqrt; restore the sign
            reg  [31:0] eg_m;
            reg         eg_v;
            reg  [D_SQRT+1:0] eg_sgn;
            wire [31:0] absr = {1'b0, R[30:0]};
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) eg_v <= 1'b0; else eg_v <= v_r && sfu == SFU_EGATE;
            end
            always @(posedge clk) begin
                eg_m <= (absr > 32'h358637BD) ? absr : 32'h358637BD;      // 1e-6 (positive keys order as integers)
                eg_sgn <= {eg_sgn[D_SQRT:0], R[31] && (R[30:0] != 31'd0)};
            end
            // sqrt serves both the SQRT class and the gate
            wire sq_in_v = (sfu == SFU_EGATE) ? eg_v : (v_r && sfu == SFU_SQRT);
            ot_hdc_fsqrt u_sq (.clk(clk), .rst_n(rst_n), .v(sq_in_v), .a((sfu == SFU_EGATE) ? eg_m : R),
                               .y(y_sqrt), .vo(vo_s), .fault(f_s));
            reg  [31:0] eg_yr;
            reg         eg_yvr;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) eg_yvr <= 1'b0; else eg_yvr <= vo_s && sfu == SFU_EGATE;
            end
            always @(posedge clk) eg_yr <= {y_sqrt[31] ^ eg_sgn[D_SQRT], y_sqrt[30:0]};
            assign eg_y = eg_yr;
            assign eg_yv = eg_yvr;
        end else begin : g_vec
            assign y_rsq = 32'd0; assign y_spr = 32'd0; assign y_sqrt = 32'd0;
            assign eg_y = 32'd0; assign eg_yv = 1'b0;
            //: a vector lane has no rsqrt / sqrt / softplus / gate: an element of such a class fails closed
            assign f_r = v_r && (sfu == SFU_RSQRT || sfu == SFU_SQRT || sfu == SFU_SPSQRT || sfu == SFU_EGATE);
            assign f_sp = 1'b0; assign f_s = 1'b0;
        end
    endgenerate
    reg [31:0] s_none;
    always @(posedge clk) s_none <= R;
    reg [31:0] S;
    always @(*) begin
        case (sfu)
            SFU_EXP: S = y_exp;
            SFU_RSQRT: S = y_rsq;
            SFU_SQRT: S = y_sqrt;
            SFU_SIGM, SFU_SILU, SFU_EGATE: S = y_div;
            SFU_SPSQRT: S = y_spr;
            default: S = s_none;
        endcase
    end
    localparam integer ST = 32 + 32 + TT;
    wire [ST-1:0] s_tag;
    ot_hdc_v41_tapline #(.W(ST), .D(SFU_MAX)) u_ts (.clk(clk), .d({r_b, r_c, r_tail}), .depth(d_sfu), .q(s_tag));
    wire v_s;
    ot_hdc_v41_vtap #(.D(SFU_MAX)) u_vs (.clk(clk), .rst_n(rst_n), .clr(clrv), .v(v_r), .depth(d_sfu), .q(v_s));
    wire [31:0] s_b = s_tag[ST-1 -: 32], s_c = s_tag[ST-33 -: 32];
    wire [TT-1:0] s_tail = s_tag[TT-1:0];
    // -- E1 -------------------------------------------------------------------------------------------------
    wire [2:0]  s_e1t = s_tail[TT-3 -: 3];
    wire [31:0] s_imm2t = s_tail[1 +: 32];
    wire [31:0] e1m, e1a, e1_byp;
    wire f_e1m, f_e1a;
    ot_hdc_fmul u_e1m (clk, rst_n, v_s && (s_e1t == E1_MULC || s_e1t == E1_MULIMM), S,
                       (s_e1t == E1_MULC) ? s_c : s_imm2t, e1m, f_e1m);
    ot_hdc_fadd u_e1a (clk, rst_n, v_s && (s_e1t == E1_ADDC || s_e1t == E1_ADDIMM), S,
                       (s_e1t == E1_ADDC) ? s_c : s_imm2t, e1a, f_e1a);
    wire [31:0] e_b;
    wire [TT-1:0] e_tail;
    ot_hdc_delay #(.W(32 + 32 + TT), .D(5)) u_d5 (.clk(clk), .rst_n(rst_n), .d({S, s_b, s_tail}),
                                                 .q({e1_byp, e_b, e_tail}));
    wire [5:0] ve1;
    ot_hdc_vline #(.D(5)) u_ve1 (.clk(clk), .rst_n(rst_n), .v(v_s), .vd(ve1));
    wire [2:0]  e_e1t = e_tail[TT-3 -: 3];
    wire [31:0] T = (e_e1t == E1_MULC || e_e1t == E1_MULIMM) ? e1m :
                    (e_e1t == E1_ADDC || e_e1t == E1_ADDIMM) ? e1a : e1_byp;
    // -- E2 --------------------------------------------------------------------------------------------------
    wire [1:0]  e_e2t = e_tail[TT-9 -: 2];
    wire [31:0] e_imm1 = e_tail[33 +: 32];
    wire [31:0] e2m, e2_byp;
    wire f_e2;
    wire [TT-1:0] u_tail;
    ot_hdc_fmul u_e2 (clk, rst_n, ve1[5] && e_e2t != E2_BYP, T, (e_e2t == E2_MULB) ? e_b : e_imm1, e2m, f_e2);
    ot_hdc_delay #(.W(32 + TT), .D(5)) u_d6 (.clk(clk), .rst_n(rst_n), .d({T, e_tail}), .q({e2_byp, u_tail}));
    wire [5:0] ve2;
    ot_hdc_vline #(.D(5)) u_ve2 (.clk(clk), .rst_n(rst_n), .v(ve1[5]), .vd(ve2));
    wire [1:0]  u_e2t = u_tail[TT-9 -: 2];
    wire [31:0] U = (u_e2t == E2_BYP) ? e2_byp : e2m;
    // -- RND and write --------------------------------------------------------------------------------------------
    wire        u_rnd = u_tail[TT-11];
    wire [1:0]  u_dst = u_tail[TT-12 -: 2];
    wire [AW-1:0] u_o = u_tail[TT-14 -: AW];
    wire [1:0]  u_redk = u_tail[TT-14-AW -: 2];
    wire        u_redsq = u_tail[TT-16-AW];
    wire        u_ifirst = u_tail[TT-17-AW], u_first8 = u_tail[TT-18-AW], u_final = u_tail[TT-19-AW],
                u_last = u_tail[TT-20-AW];
    wire [2:0]  u_p = u_tail[TT-21-AW -: 3];
    wire [AW+1:0] u_r = u_tail[TT-24-AW -: AW+2];
    reg  [31:0] out;
    reg         ov, o_redsq, o_ifirst, o_first8, o_final, o_last;
    reg  [1:0]  o_dst, o_red;
    reg  [AW-1:0] o_addr;
    reg  [2:0]  o_p;
    reg  [AW+1:0] o_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0; else ov <= ve2[5];
    end
    always @(posedge clk) begin
        out <= u_rnd ? bf16(U) : U;
        o_dst <= u_dst; o_addr <= u_o; o_red <= u_redk; o_redsq <= u_redsq; o_ifirst <= u_ifirst;
        o_first8 <= u_first8; o_final <= u_final; o_last <= u_last; o_p <= u_p; o_r <= u_r;
    end
    assign retire = ov;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vm_we <= 1'b0; kv_we <= 1'b0; end
        else begin
            vm_we <= ov && o_dst == 2'd1;
            kv_we <= ov && (o_dst == 2'd2 || o_dst == 2'd3);
        end
    end
    always @(posedge clk) begin
        vm_waddr <= o_addr; vm_wdata <= out;
        kv_waddr <= o_addr; kv_wdata <= bf16(out);
    end
    // -- reducer ---------------------------------------------------------------------------------------------------
    wire red_we0;
    wire [AW+1:0] red_addr0;
    wire [31:0] red_data0;
    wire f_red, red_busy;
    ot_hdc_reduce #(.AW(AW + 2)) u_red (.clk(clk), .rst_n(rst_n), .v_in(ov && o_red != RED_NONE),
        .mode_in(o_red == RED_MAX ? 2'd2 : 2'd1), .sq(o_redsq), .x_in(out), .ifirst_in(o_ifirst),
        .first8_in(o_first8), .final_in(o_final), .last_in(o_last), .p_in(o_p), .raddr_in(o_r),
        .o_we(red_we0), .o_addr(red_addr0), .o_data(red_data0), .busy(red_busy), .fault(f_red));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin red_we <= 1'b0; seg_v <= 1'b0; end
        else begin red_we <= red_we0 && !red_addr0[AW+1]; seg_v <= red_we0 && red_addr0[AW+1]; end
    end
    always @(posedge clk) begin
        red_addr <= red_addr0[AW-1:0];
        red_data <= red_addr0[AW] ? bf16(red_data0) : red_data0;
        seg_idx <= red_addr0[3:0];
        seg_data <= red_data0;
    end
    // -- status --------------------------------------------------------------------------------------------------------
    assign busy = vm_we || kv_we || red_we || seg_v || red_busy || red_we0 ||
                  f0_v || f1_v || f2_v || f3_v || f4_v;
    reg [2:0] fault_q;
    reg       fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q <= 0; fault_r <= 1'b0; end
        else begin
            fault_q <= {f_m1 | f_d1 | f_q | f_m2 | f_ad, f_e | f_r | f_s | f_sp | f_den | f_div,
                        f_e1m | f_e1a | f_e2 | f_red};
            fault_r <= |fault_q;
        end
    end
    assign fault = fault_r;
endmodule

// The stream unit: the vector loop, SW lanes, the segment tree.
module ot_hdc_v41_stream #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer WR = 64,          // bf16 lanes per weight-ROM word
    parameter integer KVT_SH = 9,       // log2(head_dim * W): transposed-KV tile stride
    parameter integer SW = 8            // lanes (elements per cycle), a power of two
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    // instruction (DYN already added to the bases and counts)
    input  wire [NW-1:0]     i_nout, i_nin,
    input  wire [1:0]        i_vec,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    // per lane: gather-index read (vector memory)
    output wire [SW-1:0]      vi_re,
    output wire [SW*AW-1:0]   vi_addr,
    input  wire [SW*32-1:0]   vi_q,
    // per lane: operand reads, vector memory and constant ROM per stream, weight ROM for A
    output wire [4*SW-1:0]    vm_re,
    output wire [4*SW*AW-1:0] vm_addr,
    input  wire [4*SW*32-1:0] vm_q,
    output wire [4*SW-1:0]    cr_re,
    output wire [4*SW*AW-1:0] cr_addr,
    input  wire [4*SW*64-1:0] cr_q,
    output wire [SW-1:0]      wrom_re,
    output wire [SW*AW-1:0]   wrom_addr,
    input  wire [SW*WR*16-1:0] wrom_q,
    // per lane: writes
    output wire [SW-1:0]      vm_we,
    output wire [SW*AW-1:0]   vm_waddr,
    output wire [SW*32-1:0]   vm_wdata,
    output wire [SW-1:0]      kv_we,
    output wire [SW*AW-1:0]   kv_waddr,
    output wire [SW*32-1:0]   kv_wdata,
    output wire [SW-1:0]      red_we,        // lane 0's port also carries the segment tree's result
    output wire [SW*AW-1:0]   red_addr,
    output wire [SW*32-1:0]   red_data,
    output reg               fault
);
    localparam [1:0] V_SCALAR = 0, V_VI = 1, V_VO = 2;
    localparam [2:0] M1_DIVB = 4, M1_DIVIMM = 5;
    localparam [1:0] RED_SEQ = 3;
    localparam integer SL = $clog2(SW);
    localparam integer OPW = 2*4 + 1+1+1+1 + 3+2+3+3+3+2 + 1 + 2 + 2 + 1 + 32*3;

    // -- class and issue ---------------------------------------------------------------
    reg              active;
    reg [3:0]        cls;                   // {m1 divides, sfu}
    reg [15:0]       inflight;
    reg              tree_busy;
    wire [3:0]       i_cls = {(i_m1 == M1_DIVB || i_m1 == M1_DIVIMM), i_sfu};
    assign ready = !active && !tree_busy && ((i_cls == cls) || (inflight == 0));
    wire   accept = go && ready;
    wire   retire;
    reg              seq;                   // SEQ reduction: one element per 8 cycles
    reg [2:0]        gap;
    wire             emit = active && (!seq || gap == 3'd0);
    reg [NW-1:0]     o, i, nout_r, nin_r;
    reg              i_last_r, o_last_r;
    reg [31:0]       g, total;
    reg [AW-1:0]     arow, acol, brow, bcol, crow, ccol, drow, dcol, orow_a, ocol, rrow, krow;
    reg [AW-1:0]     abase, aso, asi, aibase, bso, bsi, cso, csi, dso, dsi, oso, osi, rso, obase;
    reg [AW-1:0]     st_a, st_b, st_c, st_d, st_o, st_r;    // per-vector strides of the stepped axis
    reg [1:0]        asrc, bsrc, csrc, dsrc, aind, dst, red, vmode;
    reg              bhalf, cpair, arnd, arelu, amin, cclip, rnd, redsq, redwhole, redtree, redrnd;
    reg [2:0]        m1, qm, ad, e1;
    reg [1:0]        m2, e2;
    reg [31:0]       imm1, imm2, imm3;
    reg [NW:0]       fin_th;
    reg [NW-1:0]     istep, ostep;

    wire [NW-1:0] i_istep = (i_vec == V_VI) ? SW[NW-1:0] : {{(NW-1){1'b0}}, 1'b1};
    wire [NW-1:0] i_ostep = (i_vec == V_VO) ? SW[NW-1:0] : {{(NW-1){1'b0}}, 1'b1};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; cls <= 4'd0; inflight <= 0; gap <= 0;
        end else begin
            inflight <= inflight + (emit ? 16'd1 : 16'd0) - (retire ? 16'd1 : 16'd0);
            if (accept) begin
                active <= 1'b1; cls <= i_cls; gap <= 0;
            end else if (active) begin
                gap <= gap + 1'b1;
                if (emit && i_last_r && o_last_r) active <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (accept) begin
            o <= 0; i <= 0; nout_r <= i_nout; nin_r <= i_nin; g <= 0; total <= i_nout * i_nin;
            i_last_r <= (i_nin <= i_istep); o_last_r <= (i_nout <= i_ostep);
            istep <= i_istep; ostep <= i_ostep; vmode <= i_vec;
            fin_th <= {1'b0, i_nin} - 17'd8;
            seq <= (i_red == RED_SEQ);
            arow <= 0; acol <= 0; brow <= i_bbase; bcol <= 0; crow <= i_cbase; ccol <= 0;
            drow <= i_dbase; dcol <= 0; orow_a <= i_obase; ocol <= 0; rrow <= i_rbase; krow <= i_orow;
            abase <= i_abase; aso <= i_aso; asi <= i_asi; aibase <= i_aibase; aind <= i_aind;
            bso <= i_bso; bsi <= i_bsi; cso <= i_cso; csi <= i_csi; dso <= i_dso; dsi <= i_dsi;
            oso <= i_oso; osi <= i_osi; rso <= i_rso; obase <= i_obase;
            // a vector step along the lane axis moves every stream by SW elements
            if (i_vec == V_VI) begin
                st_a <= i_asi << SL; st_c <= i_csi << SL; st_o <= i_osi << SL; st_r <= 0;
                st_b <= i_bhalf ? (i_bsi << SL) >> 1 : i_bsi << SL;
                st_d <= i_bhalf ? (i_dsi << SL) >> 1 : i_dsi << SL;
            end else if (i_vec == V_VO) begin
                st_a <= i_aso << SL; st_b <= i_bso << SL; st_c <= i_cso << SL; st_d <= i_dso << SL;
                st_o <= i_oso << SL; st_r <= i_rso << SL;
            end else begin
                st_a <= i_aso; st_b <= i_bso; st_c <= i_cso; st_d <= i_dso; st_o <= i_oso; st_r <= i_rso;
            end
            asrc <= i_asrc; bsrc <= i_bsrc; csrc <= i_csrc; dsrc <= i_dsrc; dst <= i_dst; red <= i_red;
            bhalf <= i_bhalf; cpair <= i_cpair; arnd <= i_arnd; arelu <= i_arelu; amin <= i_amin; cclip <= i_cclip;
            rnd <= i_rnd; redsq <= i_redsq; redwhole <= i_redwhole; redtree <= i_redtree; redrnd <= i_redrnd;
            m1 <= i_m1; m2 <= i_m2; qm <= i_qm; ad <= i_ad; e1 <= i_e1; e2 <= i_e2;
            imm1 <= i_imm1; imm2 <= i_imm2; imm3 <= i_imm3;
        end else if (emit) begin
            g <= g + 1;
            if (!i_last_r) begin
                i <= i + istep; i_last_r <= ({{(32-NW){1'b0}}, i} + 2 * istep >= {{(32-NW){1'b0}}, nin_r});
                if (vmode == V_VI) begin
                    acol <= acol + st_a; ccol <= ccol + st_c; ocol <= ocol + st_o;
                    bcol <= bcol + st_b; dcol <= dcol + st_d;
                end else begin
                    acol <= acol + asi; ccol <= ccol + csi; ocol <= ocol + osi;
                    if (!bhalf || i[0]) begin bcol <= bcol + bsi; dcol <= dcol + dsi; end
                end
            end else begin
                i <= 0; i_last_r <= (nin_r <= istep);
                o <= o + ostep; o_last_r <= ({{(32-NW){1'b0}}, o} + 2 * ostep >= {{(32-NW){1'b0}}, nout_r});
                if (vmode == V_VI) begin
                    arow <= arow + aso; brow <= brow + bso; crow <= crow + cso; drow <= drow + dso;
                    orow_a <= orow_a + oso; rrow <= rrow + rso; krow <= krow + 1'b1;
                end else begin
                    arow <= arow + st_a; brow <= brow + st_b; crow <= crow + st_c; drow <= drow + st_d;
                    orow_a <= orow_a + st_o; rrow <= rrow + st_r; krow <= krow + ostep;
                end
                acol <= 0; bcol <= 0; ccol <= 0; dcol <= 0; ocol <= 0;
            end
        end
    end
    wire [OPW-1:0] op_now = {asrc, bsrc, csrc, dsrc, arnd, arelu, amin, cclip, m1, m2, qm, ad, e1, e2, rnd,
                             dst, red, redsq, imm1, imm2, imm3};
    wire clrv = accept && (i_cls != cls);

    // -- lanes ---------------------------------------------------------------------------
    wire [SW-1:0] l_retire, l_busy, l_fault, l_red_we, l_seg_v;
    wire [SW*AW-1:0] l_red_addr;
    wire [SW*32-1:0] l_red_data, l_seg_data;
    wire [SW*4-1:0]  l_seg_idx;
    genvar l;
    generate
        for (l = 0; l < SW; l = l + 1) begin : g_lane
            ot_hdc_v41_su_lane #(.AW(AW), .NW(NW), .WR(WR), .KVT_SH(KVT_SH), .LANE(l), .FULL(l == 0)) u_lane (
                .clk(clk), .rst_n(rst_n),
                .emit(emit), .vmode(vmode), .o(o), .i(i), .nout_r(nout_r), .nin_r(nin_r), .i_last_r(i_last_r),
                .g(g), .total(total), .fin_th(fin_th), .seq(seq),
                .arow(arow), .acol(acol), .brow(brow), .bcol(bcol), .crow(crow), .ccol(ccol), .drow(drow),
                .dcol(dcol), .orow_a(orow_a), .ocol(ocol), .rrow(rrow), .krow(krow),
                .abase(abase), .aso(aso), .asi(asi), .aibase(aibase), .bso(bso), .bsi(bsi), .cso(cso), .csi(csi),
                .dso(dso), .dsi(dsi), .oso(oso), .osi(osi), .rso(rso), .obase(obase),
                .aind(aind), .dst(dst), .bhalf(bhalf), .cpair(cpair), .redwhole(redwhole), .redtree(redtree),
                .redrnd(redrnd), .cls(cls), .clrv(clrv), .op_now(op_now),
                .vi_re(vi_re[l]), .vi_addr(vi_addr[l*AW +: AW]), .vi_q(vi_q[l*32 +: 32]),
                .vm_re(vm_re[4*l +: 4]), .vm_addr(vm_addr[4*l*AW +: 4*AW]), .vm_q(vm_q[4*l*32 +: 4*32]),
                .cr_re(cr_re[4*l +: 4]), .cr_addr(cr_addr[4*l*AW +: 4*AW]), .cr_q(cr_q[4*l*64 +: 4*64]),
                .wrom_re(wrom_re[l]), .wrom_addr(wrom_addr[l*AW +: AW]), .wrom_q(wrom_q[l*WR*16 +: WR*16]),
                .vm_we(vm_we[l]), .vm_waddr(vm_waddr[l*AW +: AW]), .vm_wdata(vm_wdata[l*32 +: 32]),
                .kv_we(kv_we[l]), .kv_waddr(kv_waddr[l*AW +: AW]), .kv_wdata(kv_wdata[l*32 +: 32]),
                .red_we(l_red_we[l]), .red_addr(l_red_addr[l*AW +: AW]), .red_data(l_red_data[l*32 +: 32]),
                .seg_v(l_seg_v[l]), .seg_idx(l_seg_idx[4*l +: 4]), .seg_data(l_seg_data[l*32 +: 32]),
                .retire(l_retire[l]), .busy(l_busy[l]), .fault(l_fault[l]));
        end
    endgenerate
    assign retire = l_retire[0];                // lane 0 carries every vector

    // -- segment tree (red_tree): up to 16 segment sums, ((s0+s1)+(s2+s3))+... ------------------
    reg  [31:0]    sbuf [0:15];
    reg  [4:0]     sgot;
    reg  [NW-1:0]  t_nseg;
    reg  [AW-1:0]  t_base;
    reg            t_rnd, t_go;
    integer q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tree_busy <= 1'b0; sgot <= 0; t_go <= 1'b0; end
        else begin
            t_go <= 1'b0;
            if (accept && i_redtree) begin
                tree_busy <= 1'b1; sgot <= 0;
            end else if (tv[23]) begin
                tree_busy <= 1'b0;
            end else if (tree_busy) begin
                sgot <= sgot + $countones(l_seg_v);
                if (!t_go && sgot + $countones(l_seg_v) == t_nseg[4:0] && sgot != t_nseg[4:0]) t_go <= 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        if (accept && i_redtree) begin
            t_nseg <= i_nout; t_base <= i_rbase; t_rnd <= i_redrnd;
            for (q = 0; q < 16; q = q + 1) sbuf[q] <= 32'd0;
        end else begin
            for (q = 0; q < SW; q = q + 1)
                if (l_seg_v[q]) sbuf[l_seg_idx[4*q +: 4]] <= l_seg_data[32*q +: 32];
        end
    end
    // four pipelined adder levels, 6 cycles each (5 in the adder, 1 register)
    wire [31:0] t1 [0:7];
    wire [31:0] t2 [0:3];
    wire [31:0] t3 [0:1];
    wire [31:0] t4;
    wire [14:0] tf;
    reg  [31:0] r1 [0:7];
    reg  [31:0] r2 [0:3];
    reg  [31:0] r3 [0:1];
    wire [24:0] tv;
    ot_hdc_vline #(.D(24)) u_tv (.clk(clk), .rst_n(rst_n), .v(t_go), .vd(tv));
    genvar k;
    generate
        for (k = 0; k < 8; k = k + 1) begin : g_t1
            ot_hdc_fadd u_add (clk, rst_n, t_go, sbuf[2*k], sbuf[2*k+1], t1[k], tf[k]);
            always @(posedge clk) r1[k] <= t1[k];
        end
        for (k = 0; k < 4; k = k + 1) begin : g_t2
            ot_hdc_fadd u_add (clk, rst_n, tv[6], r1[2*k], r1[2*k+1], t2[k], tf[8+k]);
            always @(posedge clk) r2[k] <= t2[k];
        end
        for (k = 0; k < 2; k = k + 1) begin : g_t3
            ot_hdc_fadd u_add (clk, rst_n, tv[12], r2[2*k], r2[2*k+1], t3[k], tf[12+k]);
            always @(posedge clk) r3[k] <= t3[k];
        end
    endgenerate
    ot_hdc_fadd u_t4 (clk, rst_n, tv[18], r3[0], r3[1], t4, tf[14]);
    reg        t_we;
    reg [31:0] t_data;
    function automatic [31:0] bf16(input [31:0] x);
        bf16 = (x + 32'h7FFF + {31'd0, x[16]}) & 32'hFFFF0000;
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t_we <= 1'b0;
        else t_we <= tv[23];
    end
    always @(posedge clk) t_data <= t_rnd ? bf16(t4) : t4;

    // lane 0's reducer port also carries the tree's result (never both: a tree op
    // holds the unit until its result is written, and its lanes write no sums)
    assign red_we = {l_red_we[SW-1:1], l_red_we[0] | t_we};
    assign red_addr = {l_red_addr[SW*AW-1:AW], t_we ? t_base : l_red_addr[AW-1:0]};
    assign red_data = {l_red_data[SW*32-1:32], t_we ? t_data : l_red_data[31:0]};

    // -- status --------------------------------------------------------------------------------------------------------
    wire idle_c = !active && inflight == 0 && !(|l_busy) && !tree_busy && !t_go && !(|tv) && !t_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !accept;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= (|l_fault) || (|tf);
    end
endmodule
