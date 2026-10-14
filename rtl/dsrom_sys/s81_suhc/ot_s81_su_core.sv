`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_core (stream s81-suhc-1011, 2026-10-11): the engine of the S81 SU slab master (dsfd_sp_su), driven by the
// stage sequencer through the dsfd_sp_ctrl engine adapter (ENG su = 1, physical/s81_ctrl/ADAPTER_CONTRACT_1011.json):
//   e_cmd_v / e_cmd_d[83:0] = {slot, user, pos, tok, arg[30:7], op[6:0]} / e_cmd_ready;  e_done_v / e_done_tag = {slot,
//   op}, pulsed when the job's last result row has been issued to the VM (the VM applies ops in issue order).
//
// The SU runs the fused full-width units the token path is built on, one job at a time (in-order engine), on the
// 1.2 GHz stream clock, fed from a WIDE VM read port (S_RD rows of 512 b a cycle: the operands are in the VM when the
// producer's done has fired -- the field's capture, the collective, the scan service) and draining into S_WR VM write
// row slots.  No per-op VM round trips inside a chain: each unit fuses its whole chain.
//
//   QN   q RMSNorm -> FP8 act-quant             ot_dsrom_su_norm HC=0 (QN_N lanes, D 1280)           attn.q_quant
//   KV   kv RMSNorm -> RoPE tail -> FP8 QDQ      ot_dsrom_su_norm HC=0 RD 64 (KV_N lanes, D 512)      attn.kv_rope_qdq
//   QB   act-quant bank (FP8 / FP4)              ot_dsrom_su_qbank (QB_NB blocks a beat)              attn.z_quant, idx q
//   SW   SwiGLU -> route weight -> act-quant     ot_dsrom_su_swiglu ROUTED (SW_W lanes; shared expert: w = 1.0, exact)
//                                                                                                       ffn.swiglu/route_w/quant2
//   SE   softmax scores -> e (P), den            ot_dsrom_su_softmax (SM_H heads x SM_LPH lanes)      attn.max/exp/den/sink
//   SO   P.V -> o / den -> inverse RoPE -> BF16  the same unit (den held from the slot's SE)          attn.normalize
//   GQ / GK  gain set load for QN / KV (layer constants: on silicon a ROM image; loaded at boot through the VM)
//   RA   sqrt(softplus) of the router scores     ot_s81_su_rx (RAL ot_hdc_v41x_softplus_s lanes)    ffn.softplus_sqrt
//   RB   router scores + bias                    ot_s81_su_rx (16 binary32 adders)                   ffn.bias
//   QR   RoPE tail of each q head (forward)      ot_s81_su_rx (16 lanes: 2 multiplies + 1 add)       attn.q_rope
//        (s81-functional-token 2026-10-14, die item F1: the stage programs issue these three to the SU)
//
// Descriptor.  arg[23:20] kind (0 QN, 1 KV, 2 QB, 3 SW, 4 SE, 5 SO, 6 GQ, 7 GK, 8 RA, 9 RB, 10 QR; 11..15 fault), arg[19:18] gain set, arg[14] FP4 (QB),
// arg[13:0] = the job's DESCRIPTOR ROW in the VM (compiler-written).  Descriptor row words: 0 out_base, 1 in_base,
// 2 count (QB beats / SW vectors / SE score vectors nv), 3 eps (QN, KV) / lim (SW) / scale (SE), 4 lt (SE),
// 5.. 5+NSW-1 routing weights (SW, one per vector).  Parameter rows after it: KV / SO cos (2 rows) + sin (2 rows);
// SE sink (SM_H words).
// RA / RB / QR (one operand beat = every operand row of the job): count = rows (RA, RB) / q heads (QR).
//   RA rows ibase .. +count-1 -> result rows out_base .. (binary32 r);  RB scores ibase .., bias rows from word 4 (bias
//   base, layer constant rows resident in the VM) -> out_base .. (binary32 scores + bias);  QR the 4 rope rows of each
//   head (head h: rows ibase + 32 h + 28 .. 31, the last 64 of its 512) -> the same offsets from out_base (out_base =
//   in_base rotates in place); parameter rows cos (2) + sin (2) as KV / SO.
// Operand rows (from in_base, beat-major: each engine beat is RPB consecutive rows):
//   QN NV_Q beats of QN_N/16 rows; KV 1 beat of KV_N/16; QB count beats of 2*QB_NB; SW count x (g W/16 rows, u W/16);
//   SE nv beats of SM_H*SM_LPH/16; SO 512/SM_LPH beats; GQ 1280/16 rows, GK 512/16 rows.
// Result rows (from out_base, in emission order): QN per vector codes QN_N/64 + exps 1; KV codes KV_N/64 + exps 1 +
// QDQ BF16 KV_N/32; QB per beat codes QB_NB/2 (8-bit slots, FP4 codes zero-extended) + exps 1 + y QB_NB; SW per vector codes W/64 +
// exps 1 + y BF16 W/32; SE per beat e SM_H*SM_LPH/16 (binary32); SO per beat o BF16 SM_H*SM_LPH/32.
//
// MUT (bench negative controls): 1 done one beat early; 2 done tag flipped; 3 SO uses a stale den (SE of the slot not
// observed: the unit's den is cleared); 4 the gain set index ignored (always set 0); 5 stale den: the softmax lanes'
// den (denl) loads on the first SE after reset only, so every later SO divides by the first SE's den.
// MUT 3 is behaviour-equivalent to MUT 0 (kept as a record): its one-cycle unit reset at SO parameter load hits only
// valid / counter flops that already hold their reset values once SE is done; denl has no reset, so it is not cleared.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_core #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16,            // VM read rows a cycle (every operand beat is a multiple)
    parameter integer S_WR = 16,            // VM write rows a cycle
    parameter integer LM = 5, LA = 4,
    parameter integer OQ = 1024,            // result row FIFO
    parameter integer MUT = 0,
    parameter integer RAL = 16,             // RA lanes (ot_s81_su_rx)
    parameter integer XMUT = 0              // ot_s81_su_rx negative controls (1 RA, 2 RB, 3 QR)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output reg                    e_done_v,
    output reg  [7:0]             e_done_tag,
    output reg  [S_RD-1:0]        rq_v,
    output reg  [S_RD*14-1:0]     rq_row,
    input  wire [S_RD-1:0]        rs_v,
    input  wire [S_RD*512-1:0]    rs_d,
    output reg  [S_WR-1:0]        wq_v,
    output reg  [S_WR*14-1:0]     wq_row,
    output reg  [S_WR*16-1:0]     wq_mask,
    output reg  [S_WR*512-1:0]    wq_d,
    output wire                   busy,
    output reg                    fault,
    output reg  [3:0]             fault_code,
    output reg  [31:0]            st_jobs
);
    localparam integer DQ = 1280, DK = 512, NVQ = DQ / QN_N;
    localparam integer SMW = SM_H * SM_LPH;                      // softmax lanes
    localparam integer RQN = QN_N / 16, RKV = KV_N / 16, RQB = 2 * QB_NB, RSW = SW_W / 16, RSM = SMW / 16;
    localparam integer BMAX = 2 * RSW > RQB ? (2 * RSW > RKV ? 2 * RSW : RKV) : (RQB > RKV ? RQB : RKV);
    localparam integer NPV = 512 / SM_LPH;
    localparam integer OW = 14 + 512, OQB = $clog2(OQ);
    localparam integer MAXP = 8;                                 // descriptor + parameter rows
`ifndef SYNTHESIS
    initial begin
        if (RQN % S_RD || RKV % S_RD || RQB % S_RD || RSW % S_RD || RSM % S_RD || 1280 / 16 % S_RD || 512 / 16 % S_RD)
            $fatal(1, "ot_s81_su_core: every operand beat a multiple of S_RD rows");
    end
`endif
    localparam [3:0] K_QN = 0, K_KV = 1, K_QB = 2, K_SW = 3, K_SE = 4, K_SO = 5, K_GQ = 6, K_GK = 7;
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10;
    function automatic is_rx(input [3:0] k);
        is_rx = (k == K_RA || k == K_RB || k == K_QR);
    endfunction

    // ------------------------------------------------------------------ job state
    reg         run;
    reg  [3:0]  kind;
    reg         jslot, fp4;
    reg  [1:0]  gsel;
    reg  [7:0]  jtag;
    reg  [13:0] dbase;
    reg  [2:0]  ph;                                  // 0 params, 1 wait params, 2 operands, 3 drain
    reg  [511:0] prow [0:MAXP-1];
    reg  [15:0] ri, rr;                              // rows issued / received in the phase
    reg  [15:0] np, nrow, rpb;                       // param rows, operand rows, rows a beat
    reg  [15:0] nw, cw;                              // result rows expected / written
    reg  [15:0] beats;
    assign e_cmd_ready = !run && !fault;
    assign busy = run;
    wire take = e_cmd_v && e_cmd_ready;
    wire [23:0] c_arg = e_cmd_d[30:7];
    wire [1:0] gs = (MUT == 4) ? 2'd0 : gsel;
    wire [13:0] obase = prow[0][13:0], ibase = prow[0][32 +: 14];
    wire [15:0] cnt = prow[0][64 +: 16];
    wire [31:0] w3 = prow[0][96 +: 32];
    wire [2:0]  lt4 = prow[0][128 +: 3];
    function automatic [15:0] nparams(input [3:0] k);
        nparams = (k == K_KV || k == K_SO || k == K_QR) ? 5 : (k == K_SE) ? 1 + (SM_H + 15) / 16 : 1;
    endfunction

    // ------------------------------------------------------------------ gain tables (layer constants)
    reg [QN_N*32-1:0] gq [0:4*NVQ-1];
    reg [KV_N*32-1:0] gk [0:3];
    reg               sm_owner_v; reg sm_owner;      // slot whose den the softmax unit holds
    reg               sm_dn;                         // this SE's den has reached the lanes

    // ------------------------------------------------------------------ operand beat assembly
    reg [512*BMAX-1:0] bb;                           // rows landing (blocking: the beat being assembled)
    reg [512*BMAX-1:0] bq;                           // the completed beat
    reg [512*BMAX-1:0] be;                           // the beat at the engine pins, with its strobe
    reg                beat_v;                       // a full beat assembled this cycle (registered strobe)
    reg [15:0]         beat_i;

    // ------------------------------------------------------------------ engines
    // QN
    reg qn_go, qn_in, qn_wl; reg [7:0] qn_wi; reg [QN_N*32-1:0] qn_wd; reg [QN_N*32-1:0] qn_x;
    wire qn_yv, qn_rv, qn_qv, qn_rov, qn_f; wire [7:0] qn_yi, qn_qi; wire [QN_N*32-1:0] qn_y, qn_ro; wire [31:0] qn_r;
    wire [(QN_N/32)*256-1:0] qn_qc; wire [(QN_N/32)*10-1:0] qn_qe; wire [(QN_N/32)*512-1:0] qn_qy;
    ot_dsrom_su_norm #(.N(QN_N), .D(DQ), .HC(0), .RD(0), .QUANT(1), .LM(LM), .LA(LA)) u_qn (
        .clk(clk), .rst_n(rst_n), .go(qn_go), .in_v(qn_in), .in_x(qn_x), .pre(128'd0), .n_f(32'h44A00000), .eps(w3),
        .wl_v(qn_wl), .wl_i(qn_wi), .wl_d(qn_wd), .cos_t(32'd0), .sin_t(32'd0), .y_v(qn_yv), .y_i(qn_yi), .y(qn_y),
        .r_v(qn_rv), .r(qn_r), .q_v(qn_qv), .q_i(qn_qi), .q_codes(qn_qc), .q_e(qn_qe), .q_y(qn_qy), .ro_v(qn_rov),
        .ro(qn_ro), .fault(qn_f));
    // KV
    reg kv_go, kv_in, kv_wl; reg [KV_N*32-1:0] kv_wd, kv_x;
    wire kv_yv, kv_rv, kv_qv, kv_rov, kv_f; wire [7:0] kv_yi, kv_qi; wire [KV_N*32-1:0] kv_y, kv_ro; wire [31:0] kv_r;
    wire [(KV_N/32)*256-1:0] kv_qc; wire [(KV_N/32)*10-1:0] kv_qe; wire [(KV_N/32)*512-1:0] kv_qy;
    ot_dsrom_su_norm #(.N(KV_N), .D(DK), .HC(0), .RD(64), .QUANT(1), .LM(LM), .LA(LA)) u_kv (
        .clk(clk), .rst_n(rst_n), .go(kv_go), .in_v(kv_in), .in_x(kv_x), .pre(128'd0), .n_f(32'h44000000), .eps(w3),
        .wl_v(kv_wl), .wl_i(8'd0), .wl_d(kv_wd), .cos_t({prow[2], prow[1]}), .sin_t({prow[4], prow[3]}),
        .y_v(kv_yv), .y_i(kv_yi), .y(kv_y), .r_v(kv_rv), .r(kv_r), .q_v(kv_qv), .q_i(kv_qi), .q_codes(kv_qc),
        .q_e(kv_qe), .q_y(kv_qy), .ro_v(kv_rov), .ro(kv_ro), .fault(kv_f));
    // QB
    reg qb_v; wire qb_vo, qb_f; wire [256*QB_NB-1:0] qb_q; wire [10*QB_NB-1:0] qb_e; wire [512*QB_NB-1:0] qb_y;
    ot_dsrom_su_qbank #(.NB(QB_NB), .NIN(1), .NOUT(1), .ROPE(0), .LM(LM), .LA(LA)) u_qb (
        .clk(clk), .rst_n(rst_n), .v(qb_v), .fp4(fp4), .x(be[0 +: 1024 * QB_NB]), .cs(2048'd0), .vo(qb_vo), .q(qb_q),
        .e(qb_e), .y(qb_y), .fault(qb_f));
    // SW
    reg sw_v; reg [32*SW_W-1:0] sw_w;
    wire sw_vo, sw_f; wire [8*SW_W-1:0] sw_q; wire [10*SW_W/32-1:0] sw_e; wire [16*SW_W-1:0] sw_y;
    ot_dsrom_su_swiglu #(.W(SW_W), .NIN(1), .NOUT(1), .ROUTED(1), .LM(LM), .LA(LA)) u_sw (
        .clk(clk), .rst_n(rst_n), .v(sw_v), .g(be[0 +: 32 * SW_W]), .u(be[32 * SW_W +: 32 * SW_W]), .w(sw_w), .lim(w3),
        .vo(sw_vo), .q(sw_q), .e(sw_e), .y(sw_y), .fault(sw_f));
    // SE / SO
    reg sm_sv, sm_pv;
    reg [6:0] sm_nv; reg [2:0] sm_lt; reg [31:0] sm_scale; reg [SM_H*32-1:0] sm_sink;
    reg [16*64-1:0] sm_cos, sm_sin;
    wire sm_ev, sm_mxv, sm_esv, sm_denv, sm_ov, sm_f;
    wire [SMW*32-1:0] sm_ed; wire [SM_H*32-1:0] sm_mx, sm_es, sm_den; wire [SMW*16-1:0] sm_od;
    reg sm_rst_n;                                     // MUT 3: the unit's den lost between SE and SO
    ot_dsrom_su_softmax #(.H(SM_H), .LPH(SM_LPH), .NVMAX(SM_NVMAX), .DIN(1), .DOUT(1), .RWU(1), .RWD(1), .LM(LM),
                          .LA(LA), .STALEDEN(MUT == 5)) u_sm (
        .clk(clk), .rst_n(rst_n && sm_rst_n), .nv(sm_nv), .lt(sm_lt), .scale(sm_scale), .sink(sm_sink),
        .cosv(sm_cos), .sinv(sm_sin), .s_v(sm_sv), .s_d(be[0 +: SMW * 32]), .e_v(sm_ev), .e_d(sm_ed), .mx_v(sm_mxv),
        .mx_d(sm_mx), .es_v(sm_esv), .es_d(sm_es), .den_v(sm_denv), .den_d(sm_den), .pv_v(sm_pv), .pv_d(be[0 +: SMW * 32]),
        .o_v(sm_ov), .o_d(sm_od), .fault(sm_f));

    // RA / RB / QR (die item F1)
    reg rx_st;
    wire rx_ov, rx_f; wire [15:0] rx_oi; wire [511:0] rx_od;
    ot_s81_su_rx #(.BR(BMAX), .RAL(RAL), .LM(LM), .LA(LA), .MUT(XMUT)) u_rx (
        .clk(clk), .rst_n(rst_n), .start(rx_st), .knd(kind[1:0]), .nr(nrow), .bt(be), .cos_t({prow[2], prow[1]}),
        .sin_t({prow[4], prow[3]}), .o_v(rx_ov), .o_i(rx_oi), .o_d(rx_od), .fault(rx_f));
    // operand row address of operand row i (RB: the bias rows follow the scores; QR: the head's 4 rope rows)
    wire [13:0] bbase = prow[0][128 +: 14];
    function automatic [13:0] oaddr(input [3:0] k, input [15:0] i, input [15:0] c, input [13:0] ib, input [13:0] bb_);
        case (k)
            K_RB: oaddr = (i < c) ? ib + i[13:0] : bb_ + i[13:0] - c[13:0];
            K_QR: oaddr = ib + {i[13:2], 5'd0} + 14'd28 + {12'd0, i[1:0]};
            default: oaddr = ib + i[13:0];
        endcase
    endfunction

    // ------------------------------------------------------------------ result row FIFO
    reg [OW-1:0]  oq [0:OQ-1];
    reg [OQB:0]   oq_n;
    reg [OQB-1:0] oq_w, oq_r;
    reg [15:0]    ocur;                               // next result row offset from out_base

    function automatic [15:0] rows_out(input [3:0] k, input [15:0] c, input f4);
        case (k)
            K_QN: rows_out = NVQ * (QN_N / 64 + 1);
            K_KV: rows_out = KV_N / 64 + 1 + KV_N / 32;
            K_QB: rows_out = c * (QB_NB / 2 + 1 + QB_NB);        // FP4 codes sit in 8-bit slots as FP8's
            K_SW: rows_out = c * (SW_W / 64 + 1 + SW_W / 32);
            K_SE: rows_out = c * RSM;
            K_SO: rows_out = NPV * (SMW / 32);
            K_RA, K_RB: rows_out = c;
            K_QR: rows_out = 4 * c;
            default: rows_out = 0;
        endcase
    endfunction
    function automatic [15:0] rows_in(input [3:0] k, input [15:0] c);
        case (k)
            K_QN: rows_in = NVQ * RQN;  K_KV: rows_in = RKV;  K_QB: rows_in = c * RQB;  K_SW: rows_in = c * 2 * RSW;
            K_SE: rows_in = c * RSM;    K_SO: rows_in = NPV * RSM; K_GQ: rows_in = DQ / 16; K_GK: rows_in = DK / 16;
            K_RA: rows_in = c;          K_RB: rows_in = 2 * c;     K_QR: rows_in = 4 * c;
            default: rows_in = 0;
        endcase
    endfunction
    function automatic [15:0] rows_beat(input [3:0] k);
        case (k)
            K_QN: rows_beat = RQN; K_KV: rows_beat = RKV; K_QB: rows_beat = RQB; K_SW: rows_beat = 2 * RSW;
            K_SE, K_SO: rows_beat = RSM; K_GQ: rows_beat = RQN; default: rows_beat = RKV;
        endcase
    endfunction

    integer s, q, g;
    reg [15:0] go_pend;                               // QN / KV: go issued, vectors pending
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; kind <= 0; jslot <= 0; fp4 <= 0; gsel <= 0; jtag <= 0; dbase <= 0; ph <= 0;
            ri <= 0; rr <= 0; np <= 0; nrow <= 0; rpb <= 0; nw <= 0; cw <= 0; beats <= 0;
            e_done_v <= 0; e_done_tag <= 0; fault <= 0; fault_code <= 0; st_jobs <= 0;
            rq_v <= 0; wq_v <= 0; beat_v <= 0; beat_i <= 0; go_pend <= 0;
            qn_go <= 0; qn_in <= 0; qn_wl <= 0; qn_wi <= 0; kv_go <= 0; kv_in <= 0; kv_wl <= 0; qb_v <= 0; sw_v <= 0;
            rx_st <= 0; sm_sv <= 0; sm_pv <= 0; sm_rst_n <= 1'b1; sm_owner_v <= 0; sm_owner <= 0; sm_dn <= 0;
            oq_n <= 0; oq_w <= 0; oq_r <= 0; ocur <= 0;
        end else begin
            e_done_v <= 0; rq_v <= 0; wq_v <= 0; beat_v <= 0;
            qn_go <= 0; qn_in <= 0; qn_wl <= 0; kv_go <= 0; kv_in <= 0; kv_wl <= 0; qb_v <= 0; sw_v <= 0; sm_sv <= 0;
            sm_pv <= 0; sm_rst_n <= 1'b1; rx_st <= 0;
            if (qn_f || kv_f || qb_f || sw_f || sm_f || rx_f) begin fault <= 1; if (!fault) fault_code <= 1; end
            if (take) begin
                run <= 1; kind <= c_arg[23:20]; jslot <= e_cmd_d[83]; jtag <= {e_cmd_d[83], e_cmd_d[6:0]};
                gsel <= c_arg[19:18]; fp4 <= c_arg[14]; dbase <= c_arg[13:0];
                ph <= 0; ri <= 0; rr <= 0; np <= nparams(c_arg[23:20]); cw <= 0; beats <= 0; ocur <= 0; beat_i <= 0;
                if (c_arg[23:20] > K_QR) begin fault <= 1; fault_code <= 3; end
                if (c_arg[23:20] == K_SO && !(sm_owner_v && sm_owner == e_cmd_d[83])) begin fault <= 1; fault_code <= 6; end
            end
            if (run && !fault) begin
                // ---------------------------------------------------------- phase 0/1: descriptor + parameter rows
                if (ph == 0) begin
                    for (s = 0; s < S_RD; s = s + 1)
                        if (ri + s < np) begin rq_v[s] <= 1; rq_row[14 * s +: 14] <= dbase + ri + s; end
                    if (ri + S_RD >= np) ph <= 1;
                    ri <= ri + S_RD;
                end
                if (ph == 1 || ph == 0) begin
                    begin : prsp
                        reg [15:0] c;
                        c = rr;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin prow[c] = rs_d[512 * s +: 512]; c = c + 1; end
                        rr <= c;
                        if (c == np) begin
                            ph <= 2; ri <= 0; rr <= 0;
                            nrow <= rows_in(kind, prow[0][64 +: 16]);
                            rpb <= is_rx(kind) ? rows_in(kind, prow[0][64 +: 16]) : rows_beat(kind);
                            nw <= rows_out(kind, prow[0][64 +: 16], fp4);
                            if (kind == K_SE) begin
                                sm_nv <= prow[0][64 +: 7]; sm_lt <= prow[0][128 +: 3]; sm_scale <= prow[0][96 +: 32];
                                sm_sink <= prow[1][0 +: SM_H * 32]; sm_owner_v <= 1; sm_owner <= jslot;
                            end
                            if (kind == K_SO) begin
                                sm_cos <= {prow[2][0 +: 512], prow[1][0 +: 512]};
                                sm_sin <= {prow[4][0 +: 512], prow[3][0 +: 512]};
                                if (MUT == 3) sm_rst_n <= 1'b0;
                            end
                        end
                    end
                end
                // ---------------------------------------------------------- phase 2: operand rows -> beats -> engine
                if (ph == 2) begin
                    // QN / KV: operands only after the unit's go (gain vectors loaded first)
                    if ((kind != K_QN && kind != K_KV) || go_pend == 16'hFFFF) begin
                        for (s = 0; s < S_RD; s = s + 1)
                            if (ri + s < nrow) begin
                                rq_v[s] <= 1; rq_row[14 * s +: 14] <= oaddr(kind, ri + s, cnt, ibase, bbase);
                            end
                        ri <= ri + S_RD;
                    end
                    begin : orsp
                        reg [15:0] c;
                        c = rr;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin bb[512 * (c % rpb) +: 512] = rs_d[512 * s +: 512]; c = c + 1; end
                        rr <= c;
                        if (c != rr && c % rpb == 0) begin
                            beat_v <= 1; beat_i <= (c / rpb) - 1; bq <= bb;
                        end
                    end
                end
                // ---------------------------------------------------------- beat -> engine strobe
                if (beat_v) begin
                    be <= bq;
                    case (kind)
                        K_QN: begin
                            // go a cycle ahead of the first vector, gain vector beat_i loaded beside it
                            qn_in <= 1; qn_x <= bq[0 +: QN_N * 32];
                        end
                        K_KV: begin kv_in <= 1; kv_x <= bq[0 +: KV_N * 32]; end
                        K_QB: qb_v <= 1;
                        K_SW: begin
                            sw_v <= 1;
                            for (g = 0; g < SW_W; g = g + 1) sw_w[32 * g +: 32] <= prow[0][32 * (5 + beat_i) +: 32];
                        end
                        K_SE: sm_sv <= 1;
                        K_SO: sm_pv <= 1;
                        K_GQ: gq[gsel * NVQ + beat_i] <= bq[0 +: QN_N * 32];
                        K_GK: gk[gsel] <= bq[0 +: KV_N * 32];
                        K_RA, K_RB, K_QR: rx_st <= 1;            // the beat is in be from the next cycle
                        default: ;
                    endcase
                    beats <= beats + 1;
                end
                // QN / KV: gain load + go before the first operand beat lands (ph 1 -> 2 edge)
                if (ph == 1 && kind == K_QN) begin
                    if (go_pend < NVQ) begin
                        qn_wl <= 1; qn_wi <= go_pend[7:0]; qn_wd <= gq[gs * NVQ + go_pend]; go_pend <= go_pend + 1;
                    end
                end
                if (ph == 1 && kind == K_KV && go_pend == 0) begin kv_wl <= 1; kv_wd <= gk[gs]; go_pend <= 1; end
                if (ph == 2 && (kind == K_QN || kind == K_KV) && go_pend != 16'hFFFF) begin
                    if (kind == K_QN && go_pend < NVQ) begin
                        qn_wl <= 1; qn_wi <= go_pend[7:0]; qn_wd <= gq[gs * NVQ + go_pend]; go_pend <= go_pend + 1;
                    end else begin
                        if (kind == K_QN) qn_go <= 1; else kv_go <= 1;
                        go_pend <= 16'hFFFF;
                    end
                end
                // gain loads complete when every row is in
                if ((kind == K_GQ || kind == K_GK) && ph == 2 && rr == nrow && nrow != 0 && !beat_v) begin
                    run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag; st_jobs <= st_jobs + 1;
                end
            end
            // ---------------------------------------------------------- results -> row FIFO -> VM
            begin : outp
                reg [OQB:0] n_in, n_out;
                reg [OQB-1:0] wp, rp;
                reg [15:0] oc;
                reg [511:0] row;
                n_in = 0; wp = oq_w; oc = take ? 16'd0 : ocur;   // a new job's rows start at its out_base
                if (qn_qv) begin
                    for (q = 0; q < QN_N / 64; q = q + 1) begin oq[wp] <= {obase + oc, qn_qc[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                    row = 0; for (g = 0; g < QN_N / 32; g = g + 1) row[16 * g +: 16] = {6'd0, qn_qe[10 * g +: 10]};
                    oq[wp] <= {obase + oc, row}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                end
                if (kv_qv) begin
                    for (q = 0; q < KV_N / 64; q = q + 1) begin oq[wp] <= {obase + oc, kv_qc[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                    row = 0; for (g = 0; g < KV_N / 32; g = g + 1) row[16 * g +: 16] = {6'd0, kv_qe[10 * g +: 10]};
                    oq[wp] <= {obase + oc, row}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                    for (q = 0; q < KV_N / 32; q = q + 1) begin
                        for (g = 0; g < 32; g = g + 1) row[16 * g +: 16] = kv_qy[16 * (32 * q + g) +: 16];
                        oq[wp] <= {obase + oc, row}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                    end
                end
                if (qb_vo) begin
                    for (q = 0; q < QB_NB / 2; q = q + 1) begin
                        oq[wp] <= {obase + oc, qb_q[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                    end
                    row = 0; for (g = 0; g < QB_NB; g = g + 1) row[16 * g +: 16] = {6'd0, qb_e[10 * g +: 10]};
                    oq[wp] <= {obase + oc, row}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                    for (q = 0; q < QB_NB; q = q + 1) begin oq[wp] <= {obase + oc, qb_y[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                end
                if (sw_vo) begin
                    for (q = 0; q < SW_W / 64; q = q + 1) begin oq[wp] <= {obase + oc, sw_q[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                    row = 0; for (g = 0; g < SW_W / 32; g = g + 1) row[16 * g +: 16] = {6'd0, sw_e[10 * g +: 10]};
                    oq[wp] <= {obase + oc, row}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1;
                    for (q = 0; q < SW_W / 32; q = q + 1) begin oq[wp] <= {obase + oc, sw_y[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                end
                if (sm_ev && kind == K_SE) begin
                    for (q = 0; q < RSM; q = q + 1) begin oq[wp] <= {obase + oc, sm_ed[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                end
                if (rx_ov) begin
                    oq[wp] <= {(kind == K_QR) ? obase + {rx_oi[13:2], 5'd0} + 14'd28 + {12'd0, rx_oi[1:0]} : obase + rx_oi[13:0], rx_od};
                    wp = wp + 1; n_in = n_in + 1;
                end
                if (sm_ov) begin
                    for (q = 0; q < SMW / 32; q = q + 1) begin oq[wp] <= {obase + oc, sm_od[512 * q +: 512]}; wp = wp + 1; oc = oc + 1; n_in = n_in + 1; end
                end
                ocur <= oc;
                n_out = 0; rp = oq_r;
                for (s = 0; s < S_WR; s = s + 1)
                    if (n_out < oq_n) begin
                        wq_v[s] <= 1; wq_row[14 * s +: 14] <= oq[rp][OW-1:512]; wq_mask[16 * s +: 16] <= 16'hFFFF;
                        wq_d[512 * s +: 512] <= oq[rp][511:0]; rp = rp + 1; n_out = n_out + 1;
                    end
                oq_w <= wp; oq_r <= rp; oq_n <= oq_n + n_in - n_out;
                if (oq_n + n_in > OQ) begin fault <= 1; fault_code <= 5; end
                if (run && ph == 2 && nw != 0) begin
                    cw <= cw + n_out;
                    // SE completes when its e rows are written AND the denominators are in the lanes (SO reads them)
                    if (cw + n_out >= nw - ((MUT == 1) ? 1 : 0) && (kind != K_SE || sm_dn || sm_denv)) begin
                        run <= 0; e_done_v <= 1; e_done_tag <= (MUT == 2) ? (jtag ^ 8'h01) : jtag;
                        st_jobs <= st_jobs + 1; go_pend <= 0;
                    end
                end
            end
            if (take) go_pend <= 0;
            if (take) sm_dn <= 1'b0; else if (sm_denv) sm_dn <= 1'b1;
        end
    end
endmodule
