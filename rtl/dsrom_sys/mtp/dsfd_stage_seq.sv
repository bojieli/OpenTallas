`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_stage_seq: the S81 stage-program sequencer as a die master between the WFC kit and the stage engines
// (mtp-wfc 2026-10-11; main decision A: the WFC kit is the single stage controller; ds-1010 keeps ot_s81_stage_seq +
// the engine adapters, retires hop_tx / pkg_ctrl).
//
//   kit  t_ks {start, user, token, pos} --> f_ks   : job_v with the job context (the stage start)
//   kit  f_kd {done, next_token, next_val} <-- t_kd : job_done of the OLDEST job (stage done); next_token = the job's
//                                                     token (a stage die forwards it; the head role is not on this die),
//                                                     next_val 0
//   engines cmd_* / dn_* (NENG ports)              : ot_s81_stage_seq descriptors / completions -> the engine adapters
//                                                     (ot_s81_engine_adapter; binding owned by s81-ctl-1011)
//   program load f_pw {v, a, d}, f_plen            : from the die's cfg path (host)
// The kit's start is a one-cycle pulse; the sequencer holds up to two jobs (job_rdy); a start while job_rdy is low is
// a protocol violation (sticky fault) -- the kit starts the next job only after the previous done (one job a stage).
// Every input is captured in a pin flop; every output leaves a flop.  Serial-domain kit ports (ks / kd are the kit's
// vmx slow side) -> this master runs on the serial clock ckv.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_stage_seq #(
    parameter integer NOPS = 128, parameter integer NENG = 12, parameter integer ARGW = 24,
    parameter integer USER_W = 10, parameter integer NW = 21, parameter integer QD = 4, parameter integer FQ = 4,
    parameter integer OPW = $clog2(NOPS), parameter integer PEW = 4 + ARGW,
    parameter integer CMDW = 1 + USER_W + 2 * NW + ARGW + OPW, parameter integer TAGW = 1 + OPW
) (
    input  wire [0:0] ckv, rsv,
    input  wire [USER_W+2*NW:0]  f_ks,                  // {start, user, token, pos} from the kit
    output wire [NW+32:0]        t_kd,                  // {done, next_token, next_val} to the kit
    input  wire [OPW+PEW:0]      f_pw,                  // {v, a, d} program write
    input  wire [OPW:0]          f_plen,
    output wire [NENG-1:0]       t_cmdv, output wire [NENG*CMDW-1:0] t_cmdd,
    input  wire [NENG-1:0]       f_dnv,  input  wire [NENG*TAGW-1:0] f_dntag,
    output wire [5:0]            t_st                   // {fault, code[3:0], busy}
);
    wire clk = ckv[0];
    reg [1:0] rs; always @(posedge clk or negedge rsv[0]) if (!rsv[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    // pin flops
    reg [USER_W+2*NW:0] ks_q; reg [OPW+PEW:0] pw_q; reg [OPW:0] plen_q; reg [NENG-1:0] dnv_q; reg [NENG*TAGW-1:0] dnt_q;
    always @(posedge clk) begin
        ks_q <= rn ? f_ks : '0; pw_q <= rn ? f_pw : '0; plen_q <= f_plen; dnv_q <= rn ? f_dnv : '0; dnt_q <= f_dntag;
    end
`ifdef OT_SSEQ_MUT_DROP_START
    reg [1:0] dcnt; always @(posedge clk) if (!rn) dcnt <= 0; else if (ks_q[USER_W+2*NW]) dcnt <= dcnt + 1'b1;
    wire start = ks_q[USER_W+2*NW] && dcnt != 2'd2;         // MUTANT: every 4th start is lost
`else
    wire start = ks_q[USER_W+2*NW];
`endif
    wire [USER_W-1:0] ju = ks_q[2*NW +: USER_W]; wire [NW-1:0] jt = ks_q[NW +: NW], jp = ks_q[NW-1:0];
    wire job_rdy, job_done, busy, fault; wire [3:0] fcode;
    ot_s81_stage_seq #(.NOPS(NOPS), .NENG(NENG), .ARGW(ARGW), .USER_W(USER_W), .NW(NW), .QD(QD), .FQ(FQ)) u_seq (
        .clk(clk), .rst_n(rn), .pw_v(pw_q[OPW+PEW]), .pw_a(pw_q[PEW +: OPW]), .pw_d(pw_q[PEW-1:0]), .prog_len(plen_q),
        .job_v(start), .job_rdy(job_rdy), .job_user(ju), .job_pos(jp), .job_tok(jt), .job_done(job_done),
        .cmd_v(t_cmdv), .cmd_d(t_cmdd), .dn_v(dnv_q), .dn_tag(dnt_q), .busy(busy), .fault(fault), .fault_code(fcode),
        .st_jobs(), .st_cmds());
    // the oldest job's token rides with its done (stage dies forward the token)
    reg [NW-1:0] tq [0:1]; reg tw, tr; reg kerr;
`ifdef OT_SSEQ_MUT_EARLY_DONE
    wire done_out = job_done || (start && job_rdy);     // MUTANT: done the cycle the job is accepted
`else
    wire done_out = job_done;
`endif
    reg [NW+32:0] kd_q;
    always @(posedge clk) begin
        if (!rn) begin tw <= 1'b0; tr <= 1'b0; kd_q <= '0; kerr <= 1'b0; end
        else begin
            if (start && job_rdy) begin tq[tw] <= jt; tw <= ~tw; end
            if (start && !job_rdy) kerr <= 1'b1;
            kd_q <= done_out ? {1'b1, tq[tr], 32'h0} : '0;
            if (done_out) tr <= ~tr;
        end
    end
    assign t_kd = kd_q;
    reg [5:0] st_q; always @(posedge clk) st_q <= {fault || kerr, fcode, busy};
    assign t_st = st_q;
endmodule
