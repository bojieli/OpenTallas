`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_stage_seq (stream ds-control, 2026-10-08): the S81 die's stage program sequencer.  It replaces the reduced
// array's hardwired decode core (ot_hdc_core) behind the package controller's start / done handshake: a stage of the
// S81 array is a static program of engine JOBS (field phases through the PQ core, SU / HC chains, collectives, the
// HBM scan service, selector, collector / gather, the stage hop, the head), and this block streams the job
// descriptors of that program to the engines in a fixed order, tracks their completions and reports the stage done.
//
// Execution model (decoupled issue, dataflow start).  Every engine port keeps a command queue of QD entries at the
// engine; the sequencer may run ahead of execution by up to QD outstanding jobs per port (credits).  An engine starts
// its oldest queued job when the job's inputs are present (the hub buses' valids: the producer's result in the VM /
// on the bus), never on a sequencer event, so the sequencer adds NO cycle to the dependency chain as long as every
// job's descriptor is queued at its engine before its inputs arrive.  The program is in golden start order (ASAP
// schedule of the stage's operator graph, tools/s81_ctrl/stage_programs.py), so each port's jobs are issued in the
// order the port starts them.  The exactness bench (tb_s81_stage_seq) checks, for every S81 stage program, that every
// job starts exactly at its golden cycle (no descriptor ever arrives late) and that `job_done` fires a fixed DONE_LAT
// cycles after the last job's completion.
//
// Jobs.  A job is accepted (job_v && job_rdy) with its context {user, pos, tok}; up to 2 jobs are held (the running
// one and the next one, whose context the package controller knows at the HIDDEN header, ~XWORDS cycles before its
// payload has landed), so the next job's descriptors are queued while the current job drains.  Descriptors carry
// {job slot, user, pos, tok, arg, op index}; a completion returns {job slot, op index} on the engine's done port.
// job_done pulses when every op of the OLDEST job has completed (then its slot is freed).
//
// Program entry (PEW = 4 + ARGW bits): {eng[3:0], arg[ARGW-1:0]}; eng = engine port (0..NENG-1), arg = the
// engine-specific job descriptor (phase index, SU microprogram entry, service job type ...).  The program memory is
// written at boot through pw_* (cfg path); prog_len = number of entries (static while jobs are held).
//
// Faults (sticky, first code): 1 completion for an op not outstanding on that port, 2 completion count overflow,
// 3 entry with eng >= NENG, 4 job accepted with prog_len = 0 or > NOPS.
// Timing: every input is captured in a pin flop; every output is driven by a flop.  The issue path is
// read (registered) -> per-port FIFO (registered) -> credit check -> command register.
// MUT (bench negative controls): 1 = issue only after the previous op of the program has COMPLETED (a sequencer that
// waits for each predecessor: the start-on-done design); 2 = drop the job context (descriptors carry user 0).
// ---------------------------------------------------------------------------
module ot_s81_stage_seq #(
    parameter integer NOPS   = 128,                 // program entries
    parameter integer NENG   = 12,                  // engine ports
    parameter integer ARGW   = 24,
    parameter integer USER_W = 10,
    parameter integer NW     = 21,                  // position / token bits
    parameter integer QD     = 4,                   // engine-side command queue (credits) per port
    parameter integer FQ     = 4,                   // sequencer-side per-port FIFO
    parameter integer MUT    = 0,
    parameter integer OPW    = $clog2(NOPS),
    parameter integer PEW    = 4 + ARGW,
    parameter integer CMDW   = 1 + USER_W + 2 * NW + ARGW + OPW,
    parameter integer TAGW   = 1 + OPW
) (
    input  wire                    clk,
    input  wire                    rst_n,
    // program load (boot cfg path)
    input  wire                    pw_v,
    input  wire [OPW-1:0]          pw_a,
    input  wire [PEW-1:0]          pw_d,
    input  wire [OPW:0]            prog_len,
    // jobs from the package controller
    input  wire                    job_v,
    output wire                    job_rdy,
    input  wire [USER_W-1:0]       job_user,
    input  wire [NW-1:0]           job_pos,
    input  wire [NW-1:0]           job_tok,
    output reg                     job_done,
    // engines
    output reg  [NENG-1:0]         cmd_v,
    output reg  [NENG*CMDW-1:0]    cmd_d,
    input  wire [NENG-1:0]         dn_v,
    input  wire [NENG*TAGW-1:0]    dn_tag,
    // status
    output wire                    busy,
    output reg                     fault,
    output reg  [3:0]              fault_code,
    output reg  [31:0]             st_jobs,
    output reg  [31:0]             st_cmds,
    output reg  [31:0]             st_credit_stall     // cycles a port had a queued descriptor but no credit
);
    localparam integer FB = (FQ > 1) ? $clog2(FQ) : 1;
    localparam integer CB = $clog2(QD + 1);
`ifndef SYNTHESIS
    initial begin
        if (NENG > 16 || NENG < 1) $fatal(1, "ot_s81_stage_seq: NENG in 1..16");
        if ((1 << FB) != FQ || FQ < 2) $fatal(1, "ot_s81_stage_seq: FQ a power of two >= 2");
        if (QD < 1) $fatal(1, "ot_s81_stage_seq: QD >= 1");
    end
`endif

    // ---- pin flops ----------------------------------------------------------------------------------------------
    reg              pw_v_q;  reg [OPW-1:0] pw_a_q;  reg [PEW-1:0] pw_d_q;
    reg [OPW:0]      len_q;
    reg              jv_q;    reg [USER_W-1:0] ju_q; reg [NW-1:0] jp_q, jt_q;
    reg [NENG-1:0]   dv_q;    reg [NENG*TAGW-1:0] dt_q;
    always @(posedge clk) begin
        pw_a_q <= pw_a; pw_d_q <= pw_d; len_q <= prog_len;
        ju_q <= job_user; jp_q <= job_pos; jt_q <= job_tok; dt_q <= dn_tag;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pw_v_q <= 1'b0; jv_q <= 1'b0; dv_q <= 0; end
        else begin pw_v_q <= pw_v; jv_q <= job_v && job_rdy; dv_q <= dn_v; end

    // ---- program memory (1R1W, registered read) -----------------------------------------------------------------
    reg [PEW-1:0] pmem [0:NOPS-1];
    always @(posedge clk) if (pw_v_q) pmem[pw_a_q] <= pw_d_q;

    // ---- job slots: FIFO of 2 (slot index = job bit) ------------------------------------------------------------
    reg [1:0]         js_v;                       // slot holds a job
    reg [1:0]         js_i;                       // every entry of the slot's job has been fetched
    reg [USER_W-1:0]  js_u [0:1];
    reg [NW-1:0]      js_p [0:1], js_t [0:1];
    reg [OPW:0]       js_dn [0:1];                // completions counted
    reg               old;                        // oldest slot
    reg               nslot;                      // slot the next accepted job takes
    reg               jrdy_r;                     // registered: a slot is free after this cycle
    assign job_rdy = jrdy_r;
    reg               iss_v;                      // the issue cursor is on a job
    reg               iss_s;                      // its slot
    reg [OPW:0]       ip;                         // next entry to fetch
    assign busy = |js_v;

    // ---- fetch register and per-port FIFOs ----------------------------------------------------------------------
    reg               f_v;
    reg               f_s;
    reg [OPW-1:0]     f_op;
    reg [PEW-1:0]     f_e;
    wire [3:0]        f_eng = f_e[PEW-1 -: 4];
    localparam integer FEW = 1 + OPW + ARGW;      // {slot, op, arg}
    reg [FEW-1:0]     fq_d [0:NENG-1][0:FQ-1];
    reg [FB-1:0]      fq_w [0:NENG-1], fq_r [0:NENG-1];
    reg [FB:0]        fq_n [0:NENG-1];
    reg [CB-1:0]      cred [0:NENG-1];
    reg [NOPS-1:0]    outst [0:1];                // per slot: op issued and not yet completed
    reg               prev_open;                  // MUT 1: the previous fetched op has not completed
    wire              f_room = (f_eng < NENG) && (fq_n[f_eng] < FQ);
    wire              f_take = f_v && f_room;
    wire              f_free = !f_v || f_take;    // the fetch register can load this cycle
    wire              fin    = iss_v && (ip == len_q) && f_free;      // the cursor's job is fully fetched
    wire              can_fetch = iss_v && (ip < len_q) && f_free && !(MUT == 1 && (prev_open || f_v));

    integer e, k;
    reg [NENG-1:0]    pop;                        // port FIFO -> command register
    always @(*) begin
        for (e = 0; e < NENG; e = e + 1)
            pop[e] = (fq_n[e] != 0) && (cred[e] != 0);
    end
    reg [OPW:0]       add0, add1;
    reg               nxt_other;                  // the other slot has a job to issue after `fin`
    always @(*) nxt_other = (js_v[~iss_s] && !js_i[~iss_s]) || (jv_q && nslot == ~iss_s);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            js_v <= 2'b00; js_i <= 2'b00; old <= 1'b0; nslot <= 1'b0; jrdy_r <= 1'b1;
            iss_v <= 1'b0; iss_s <= 1'b0; ip <= 0;
            f_v <= 1'b0; f_s <= 1'b0; f_op <= 0; f_e <= 0;
            cmd_v <= 0; cmd_d <= 0; job_done <= 1'b0;
            fault <= 1'b0; fault_code <= 4'd0; st_jobs <= 0; st_cmds <= 0; st_credit_stall <= 0;
            prev_open <= 1'b0;
            outst[0] <= 0; outst[1] <= 0;
            js_dn[0] <= 0; js_dn[1] <= 0;
            for (e = 0; e < NENG; e = e + 1) begin fq_w[e] <= 0; fq_r[e] <= 0; fq_n[e] <= 0; cred[e] <= CB'(QD); end
        end else begin
            job_done <= 1'b0;
            // ---- accept a job (pin-flopped) ----
            if (jv_q) begin
                js_v[nslot] <= 1'b1; js_i[nslot] <= 1'b0;
                js_u[nslot] <= (MUT == 2) ? {USER_W{1'b0}} : ju_q; js_p[nslot] <= jp_q; js_t[nslot] <= jt_q;
                nslot <= ~nslot;
                st_jobs <= st_jobs + 1;
                if (len_q == 0 || len_q > NOPS) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd4; end
            end
            // ---- issue cursor ----
            if (!iss_v) begin
                if (jv_q) begin iss_v <= 1'b1; iss_s <= nslot; ip <= 0; end
            end else if (fin) begin
                js_i[iss_s] <= 1'b1;
                if (nxt_other) begin iss_s <= ~iss_s; ip <= 0; end
                else iss_v <= 1'b0;
            end
            // ---- fetch ----
            if (can_fetch) begin
                f_v <= 1'b1; f_s <= iss_s; f_op <= ip[OPW-1:0]; f_e <= pmem[ip[OPW-1:0]];
                ip <= ip + 1'b1;
            end else if (f_take) begin
                f_v <= 1'b0;
            end
            if (f_v && f_eng >= NENG) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd3; end
            if (f_take) begin
                fq_d[f_eng][fq_w[f_eng]] <= {f_s, f_op, f_e[ARGW-1:0]};
                fq_w[f_eng] <= fq_w[f_eng] + 1'b1;
                if (MUT == 1) prev_open <= 1'b1;
            end
            // ---- per port: FIFO -> command register under credit ----
            for (e = 0; e < NENG; e = e + 1) begin
                cmd_v[e] <= 1'b0;
                if (pop[e]) begin
                    cmd_v[e] <= 1'b1;
                    cmd_d[e*CMDW +: CMDW] <= {fq_d[e][fq_r[e]][FEW-1],
                                             js_u[fq_d[e][fq_r[e]][FEW-1]],
                                             js_p[fq_d[e][fq_r[e]][FEW-1]],
                                             js_t[fq_d[e][fq_r[e]][FEW-1]],
                                             fq_d[e][fq_r[e]][ARGW-1:0],
                                             fq_d[e][fq_r[e]][ARGW +: OPW]};
                    fq_r[e] <= fq_r[e] + 1'b1;
                end else if (fq_n[e] != 0) begin
                    st_credit_stall <= st_credit_stall + 1;
                end
                fq_n[e] <= fq_n[e] + ((f_take && f_eng == e) ? 1'b1 : 1'b0) - (pop[e] ? 1'b1 : 1'b0);
                cred[e] <= cred[e] - (pop[e] ? 1'b1 : 1'b0) + (dv_q[e] ? 1'b1 : 1'b0);
            end
            st_cmds <= st_cmds + $countones(pop);
            // ---- completions ----
            add0 = 0; add1 = 0;
            for (e = 0; e < NENG; e = e + 1) begin
                if (dv_q[e]) begin
                    if (!outst[dt_q[e*TAGW + OPW]][dt_q[e*TAGW +: OPW]] || !js_v[dt_q[e*TAGW + OPW]] ||
                        cred[e] == CB'(QD)) begin
                        fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd1;
                    end
                    if (dt_q[e*TAGW + OPW]) add1 = add1 + 1'b1; else add0 = add0 + 1'b1;
                    if (MUT == 1) prev_open <= 1'b0;
                end
            end
            for (k = 0; k < 2; k = k + 1) begin
                for (e = 0; e < NENG; e = e + 1)
                    if (pop[e] && fq_d[e][fq_r[e]][FEW-1] == k[0]) outst[k][fq_d[e][fq_r[e]][ARGW +: OPW]] <= 1'b1;
                for (e = 0; e < NENG; e = e + 1)
                    if (dv_q[e] && dt_q[e*TAGW + OPW] == k[0]) outst[k][dt_q[e*TAGW +: OPW]] <= 1'b0;
            end
            // ---- the oldest job is done: every entry fetched and every completion counted ----
            if (js_v[old] && js_i[old] && js_dn[old] == len_q) begin
                job_done <= 1'b1;
                js_v[old] <= 1'b0;
                old <= ~old;
            end
            js_dn[0] <= (js_v[old] && js_i[old] && js_dn[old] == len_q && !old) ? {(OPW+1){1'b0}} : js_dn[0] + add0;
            js_dn[1] <= (js_v[old] && js_i[old] && js_dn[old] == len_q &&  old) ? {(OPW+1){1'b0}} : js_dn[1] + add1;
            if (js_dn[0] > len_q || js_dn[1] > len_q) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd2; end
            // ---- job_rdy: a slot is free after this cycle's accept / retire ----
            jrdy_r <= ((js_v[0] ? 1 : 0) + (js_v[1] ? 1 : 0) + (jv_q ? 1 : 0) + ((job_v && jrdy_r) ? 1 : 0)) < 2;
        end
    end
endmodule
