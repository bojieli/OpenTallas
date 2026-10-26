`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_stage_seq_c (s81die-1011/ctrl, 2026-10-11): the die stage sequencer of decision A (dsfd_stage_seq: the WFC
// kit's start / done + the stage program) with the engine command plane on the die pins of
// physical/s81_ctrl/ADAPTER_CONTRACT_1011 (--ctrl-adapters): per engine e = 0..11
//     c<e> [84:0] = {v, descriptor 84}  -> slab c_cmd     (ot_s81_slab_ep / ot_s81_engine_adapter, QD 8)
//     d<e> [8:0]  = {v, tag 8}          <- slab c_done
//     s<e> [1:0]  = {online, fault}     <- slab c_st
// dsfd_stage_seq runs ot_s81_stage_seq on the serial clock ckv and leaves the engine ports as flat t_cmdv / t_cmdd /
// f_dnv / f_dntag; the slab endpoints take their command pulses on the STREAM clock (c_clk = ck in every *_c master),
// so here ot_s81_stage_seq runs on ck and the serial-domain faces cross once, at this block:
//   kit start f_ks (pulse + context, ckv)  -> async FIFO (4) -> job_v            (a start is never dropped: a full
//   kit done  t_kd (pulse + token, ck)     -> async FIFO (4) -> t_kd (ckv)        FIFO is a sticky fault)
//   program write f_pw (pulses, ckv)       -> async FIFO (4) -> pw_*; f_plen (static after boot) -> 2-flop sync,
//                                             taken when two successive samples agree
//   status t_st (ckv) = 2-flop sync of {fault, code, busy} (sticky / level).
// fault = sequencer fault | any FIFO overflow / underflow | any bound engine's c_st fault; code 5 = an
// engine fault (s<e>[0]), the first such engine index is held in the status snapshot (not a die pin).
// Every die input lands in a pin flop, every output leaves a flop.  Cost vs dsfd_stage_seq: the kit crossing
// (~3 ck + ~3 ckv cycles each way) moves from the engine nets to the kit face; the engine nets gain no CDC.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_stage_seq_c #(
    parameter integer NOPS = 128, parameter integer NENG = 12, parameter integer ARGW = 24,
    parameter integer USER_W = 10, parameter integer NW = 21, parameter integer QD = 8, parameter integer FQ = 4,
    parameter integer OPW = $clog2(NOPS), parameter integer PEW = 4 + ARGW,
    // s81-die-rtl-bind 2026-10-14 (die item F4): the engines this die HAS.  A die variant without engine e (layer1: no
    // head 8 / emb 9 / Engram 10 / spare 11) instantiates this core through a variant master that has no c/d/s pins for
    // e (dsfd_stage_seq_c8); here d<e> / s<e> of an absent engine are not read and c<e> stays 0.  A program op routed
    // to an absent engine is a FAULT (code 8, sticky, fail closed: the op is never issued, the job never completes).
    parameter [12:0] ENG_PRESENT = 13'h0FFF,
    // s81-die-rtl-bind 2026-10-14 (F4 hop): KDX = the stage hand-off engine whose op the KIT done does not wait for
    // (the kit sends the HIDDEN after its done; the hop op completes when the kit's message has left: ot_s81_stage_seq
    // job_kdone).  -1 = the kit done is the job done (unchanged).
    parameter integer KDX = -1
) (
    input  wire [0:0] ckv, rsv,                         // serial clock / reset (kit, program, status)
    input  wire [0:0] ck, rst,                          // stream clock / reset (engine command plane)
    input  wire [52:0]           f_ks,                  // {start, user 10, token 21, pos 21} from the kit
    output wire [53:0]           t_kd,                  // {done, next_token 21, next_val 32} to the kit
    input  wire [35:0]           f_pw,                  // {v, a 7, d 28} program write
    input  wire [7:0]            f_plen,
    output wire [5:0]            t_st,                  // {fault, code[3:0], busy}
    output wire [84:0] c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12,
    input  wire [8:0]  d0, d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, d12,
    input  wire [1:0]  s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12
);
    localparam integer CMDW = 1 + USER_W + 2 * NW + ARGW + OPW, TAGW = 1 + OPW;   // 84 / 8
    // ---------------- resets
    reg [1:0] rsq, rvq;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rsq <= 2'b00; else rsq <= {rsq[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rvq <= 2'b00; else rvq <= {rvq[0], 1'b1};
    wire rn = rsq[1], rvn = rvq[1];
    // ---------------- serial-side pin flops
    reg [52:0] ks_q; reg [35:0] pw_q; reg [7:0] plen_v;
    always @(posedge ckv[0]) begin ks_q <= rvn ? f_ks : '0; pw_q <= rvn ? f_pw : '0; plen_v <= f_plen; end
    // ---------------- kit start: ckv -> ck
    wire ks_wr, ks_v, ks_ovf, ks_unf, ks_take, job_rdy; wire [51:0] ks_d;
`ifdef OT_SSEQC_MUT_DROP_START
    reg [1:0] dcnt; always @(posedge ckv[0]) if (!rvn) dcnt <= 0; else if (ks_q[52]) dcnt <= dcnt + 1'b1;
    wire ks_push = ks_q[52] && dcnt != 2'd2;            // MUTANT: every 4th kit start is lost
`else
    wire ks_push = ks_q[52];
`endif
    ot_async_fifo #(.WIDTH(52), .DEPTH(4)) u_ks (.wr_clk(ckv[0]), .wr_rst_n(rvn), .wr_valid(ks_push), .wr_ready(ks_wr),
        .wr_data(ks_q[51:0]), .wr_overflow(ks_ovf), .rd_clk(ck[0]), .rd_rst_n(rn), .rd_valid(ks_v), .rd_ready(ks_take),
        .rd_data(ks_d), .rd_underflow(ks_unf));
    assign ks_take = ks_v && job_rdy;                     // the kit starts the next job only after the previous done
    // ---------------- program write: ckv -> ck
    wire pw_wr, pw_v, pw_ovf, pw_unf; wire [34:0] pw_d;
    ot_async_fifo #(.WIDTH(35), .DEPTH(4)) u_pw (.wr_clk(ckv[0]), .wr_rst_n(rvn), .wr_valid(pw_q[35]), .wr_ready(pw_wr),
        .wr_data(pw_q[34:0]), .wr_overflow(pw_ovf), .rd_clk(ck[0]), .rd_rst_n(rn), .rd_valid(pw_v), .rd_ready(1'b1),
        .rd_data(pw_d), .rd_underflow(pw_unf));
    reg [7:0] pl_s0, pl_s1, plen_q;
    always @(posedge ck[0]) begin
        pl_s0 <= plen_v; pl_s1 <= pl_s0;
        if (!rn) plen_q <= 8'd0; else if (pl_s1 == pl_s0) plen_q <= pl_s1;
    end
    // ---------------- engine pins
    wire [NENG*85-1:0] c_w;
    wire [NENG*9-1:0]  d_w = {d12, d11, d10, d9, d8, d7, d6, d5, d4, d3, d2, d1, d0};
    wire [NENG*2-1:0]  s_w = {s12, s11, s10, s9, s8, s7, s6, s5, s4, s3, s2, s1, s0};
    assign {c12, c11, c10, c9, c8, c7, c6, c5, c4, c3, c2, c1, c0} = c_w;
    reg [NENG-1:0] dnv_q; reg [NENG*TAGW-1:0] dnt_q; reg [NENG-1:0] ef_q;
    integer i;
    always @(posedge ck[0]) begin
        for (i = 0; i < NENG; i = i + 1) begin
            dnv_q[i] <= rn & ENG_PRESENT[i] & d_w[9*i + 8];
            dnt_q[TAGW*i +: TAGW] <= d_w[9*i +: 8];
            ef_q[i] <= rn & ENG_PRESENT[i] & s_w[2*i];
        end
    end
    wire [NENG-1:0] cmd_v; wire [NENG*CMDW-1:0] cmd_d;
    wire job_done, job_kdone, busy, sfault; wire [3:0] fcode;
    ot_s81_stage_seq #(.NOPS(NOPS), .NENG(NENG), .ARGW(ARGW), .USER_W(USER_W), .NW(NW), .QD(QD), .FQ(FQ), .KDX(KDX)) u_seq (
        .clk(ck[0]), .rst_n(rn), .pw_v(pw_v), .pw_a(pw_d[34:28]), .pw_d(pw_d[27:0]), .prog_len(plen_q),
        .job_v(ks_take), .job_rdy(job_rdy), .job_user(ks_d[51:42]), .job_pos(ks_d[20:0]), .job_tok(ks_d[41:21]),
        .job_done(job_done), .job_kdone(job_kdone), .cmd_v(cmd_v), .cmd_d(cmd_d), .dn_v(dnv_q), .dn_tag(dnt_q), .busy(busy), .fault(sfault),
        .fault_code(fcode), .st_jobs(), .st_cmds());
    reg [NENG*85-1:0] c_q;
    always @(posedge ck[0])
        for (i = 0; i < NENG; i = i + 1) c_q[85*i +: 85] <= ENG_PRESENT[i] ? {rn & cmd_v[i], cmd_d[CMDW*i +: CMDW]} : 85'd0;
    // an op issued to an engine this die does not have (F4): sticky fault, code 8
    reg aerr;
`ifdef OT_SSEQC_MUT_ABSENT
    always @(posedge ck[0]) aerr <= 1'b0;                 // MUTANT: absent-engine issue not detected (silent hang)
`else
    always @(posedge ck[0]) if (!rn) aerr <= 1'b0; else if (|(cmd_v & ~ENG_PRESENT[NENG-1:0])) aerr <= 1'b1;
`endif
    assign c_w = c_q;
    // ---------------- kit done: ck -> ckv (the oldest job's token rides with its done)
    reg [NW-1:0] tq [0:1]; reg tw, tr;
    always @(posedge ck[0])
        if (!rn) begin tw <= 1'b0; tr <= 1'b0; end
        else begin
            if (ks_take) begin tq[tw] <= ks_d[41:21]; tw <= ~tw; end
            if (job_kdone) tr <= ~tr;
        end
    wire kd_wr, kd_v, kd_ovf, kd_unf; wire [NW-1:0] kd_d;
    ot_async_fifo #(.WIDTH(NW), .DEPTH(4)) u_kd (.wr_clk(ck[0]), .wr_rst_n(rn), .wr_valid(job_kdone), .wr_ready(kd_wr),
        .wr_data(tq[tr]), .wr_overflow(kd_ovf), .rd_clk(ckv[0]), .rd_rst_n(rvn), .rd_valid(kd_v), .rd_ready(1'b1),
        .rd_data(kd_d), .rd_underflow(kd_unf));
    reg [53:0] kd_q;
    always @(posedge ckv[0]) kd_q <= (rvn && kd_v) ? {1'b1, kd_d, 32'h0} : '0;
    assign t_kd = kd_q;
    // ---------------- status (ck -> ckv: sticky fault, level busy)
    reg xerr, eerr; reg [3:0] code;
    always @(posedge ck[0])
        if (!rn) begin xerr <= 0; eerr <= 0; code <= 0; end
        else begin
            if (ks_unf || pw_unf || kd_ovf || kd_unf) xerr <= 1'b1;
            if (|ef_q) eerr <= 1'b1;
            if (code == 0) code <= sfault ? fcode : aerr ? 4'd8 : (|ef_q) ? 4'd5 : (ks_unf || pw_unf || kd_ovf || kd_unf) ? 4'd6 : 4'd0;
        end
    reg kv_err; always @(posedge ckv[0]) if (!rvn) kv_err <= 1'b0; else if (ks_ovf || pw_ovf || (ks_push && !ks_wr) || (pw_q[35] && !pw_wr)) kv_err <= 1'b1;
    wire [5:0] st_c = {sfault | xerr | eerr | aerr, code, busy};
    reg [5:0] st_s0, st_s1, st_q;
    always @(posedge ckv[0]) begin st_s0 <= st_c; st_s1 <= st_s0; st_q <= {st_s1[5] | kv_err, st_s1[4:1] | (kv_err ? 4'd7 : 4'd0), st_s1[0]}; end
    assign t_st = st_q;
endmodule

// ---------------------------------------------------------------------------------------------------------------
// dsfd_stage_seq_c8 (s81-die-rtl-bind 2026-10-14, die item F4): the stage sequencer master of a die with engines 0..7
// plus VM engine 12 (S81 layer1: fld 0, su 1, hc 2, coll 3, svc 4, sel 5, col 6, hop 7 -- results/rtl/s81_ctrl_20261008/programs
// engine_ports; head 8 / emb 9 / Engram 10 / spare 11 live on the head, source and Engram-home dies).  Same core and
// cycles as dsfd_stage_seq_c; engine 12 is the compact VM arming endpoint; the absent engines have no die pins (an op routed to one faults, code 8).
// KDX 7: the kit done (t_kd) is given when every op but the hop (engine 7 = the kit's HIDDEN hand-off) has completed;
// the hop op completes at the kit (dsfd_wfc_stg hop endpoint: its link-out message last flit) and retires the job.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_stage_seq_c8 #(parameter integer NOPS = 128, parameter integer QD = 8, parameter integer FQ = 4) (
    input  wire [0:0] ckv, rsv,
    input  wire [0:0] ck, rst,
    input  wire [52:0]  f_ks,
    output wire [53:0]  t_kd,
    input  wire [35:0]  f_pw,
    input  wire [7:0]   f_plen,
    output wire [5:0]   t_st,
    output wire [84:0]  c0, c1, c2, c3, c4, c5, c6, c7, c12,
    input  wire [8:0]   d0, d1, d2, d3, d4, d5, d6, d7, d12,
    input  wire [1:0]   s0, s1, s2, s3, s4, s5, s6, s7, s12
);
    // engines 8..11 do not exist on this die: their completion / status inputs are the constant "no engine" (never
    // read: ENG_PRESENT masks them), their command outputs are left open inside this master
`ifdef OT_SSEQC_MUT_VM_ABSENT
    localparam [12:0] PRESENT = 13'h00FF; // negative control: VM commands must not disappear
`else
    localparam [12:0] PRESENT = 13'h10FF;
`endif
    dsfd_stage_seq_c #(.NOPS(NOPS), .QD(QD), .FQ(FQ), .NENG(13), .ENG_PRESENT(PRESENT), .KDX(7)) u_s (.ckv(ckv), .rsv(rsv), .ck(ck), .rst(rst),
        .f_ks(f_ks), .t_kd(t_kd), .f_pw(f_pw), .f_plen(f_plen), .t_st(t_st),
        .c0(c0), .c1(c1), .c2(c2), .c3(c3), .c4(c4), .c5(c5), .c6(c6), .c7(c7), .c8(), .c9(), .c10(), .c11(), .c12(c12),
        .d0(d0), .d1(d1), .d2(d2), .d3(d3), .d4(d4), .d5(d5), .d6(d6), .d7(d7), .d8(9'd0), .d9(9'd0), .d10(9'd0), .d11(9'd0), .d12(d12),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3), .s4(s4), .s5(s5), .s6(s6), .s7(s7), .s8(2'd0), .s9(2'd0), .s10(2'd0), .s11(2'd0), .s12(s12));
endmodule
