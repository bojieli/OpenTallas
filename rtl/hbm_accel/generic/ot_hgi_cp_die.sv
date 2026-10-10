`timescale 1ns/1ps
`default_nettype none
// HGI-1 command processor die body (hgi-takeover 2026-10-09; die gap 4): hbm-forks' ot_hgi_cp (config path + v1.0
// record sequencer) bound to the die:
//   * host: the loader link (ot_hgi_loader_cp): CFG window writes, doorbell, completion, CF-0 read-back, die id;
//   * record-ring fetch: f_req / f_rsp through the loader link onto the loader's memory lane 1 (HBM, read only);
//   * VM reads (vr_*: indexed ids, N_FROM_VM, END / TOKX tokens): a packet client of hfd_hgi_vm (word from sector);
//   * record dispatch: one die bus per record-capable unit (tools/hgi_die_dispatch.py layout) with ONE credit per unit
//     (a unit holds one record; the credit returns on its done / fault); units without a record adapter yet are the
//     ux_* ports (bound when hgi-adapters lands them; a record for such a unit waits: fail-closed);
//   * the config station bus to the units that decode static MD fields (coll: word 46);
//   * VM status: an uncorrectable VM error / VM fault freezes dispatch (the CP halts; recovery = drained reset).
//   * MTP=1 (hgi-1010 2026-10-10; decision 3 of 10-09, stage B): the MTP backend translator ot_hgi_mtp_xlate lives here.
//     Its native-operation side is the x_* ports (the MX1 MTP collar's t_backend / f_backend / f_am); its doorbells
//     {entry 3 KERNEL, kind, G26 L' x kstride} share the one doorbell station with the host (the host pulse wins a tie,
//     the translator holds its valid), and the completion of a translator-launched job returns to the translator, not
//     the loader.  Kernel entries / kstride = the committed MD words 16-26 / 49.  MTP=0: x_* unused, as before.
module ot_hgi_cp_die #(
    parameter integer RW = 512,
    parameter integer USE_MACRO = 1,
    parameter integer MUT = 0,         // bench mutant: 1 VM read returns the neighbouring word; 2 the G26 layer offset dropped
    parameter integer MTP = 0,         // 1: the MTP backend translator (x_* ports)
    parameter integer FQCR = 4         // fetch queue credits = the loader's queue depth (16 with ot_hgi_loader_cp BURST 1)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [418:0]  lcp,           // from the loader
    output reg  [221:0]  cpl,           // to the loader
    output reg  [337:0]  vmq,           // VM client {v, req 337}
    input  wire [273:0]  vmr,           // VM client {v, rsp 273}
    input  wire [18:0]   vmstat,        // {proto_fault, mask_fault, ue, ce}
    output reg  [967:0]  coll_rec,      // unit 6
    input  wire [2:0]    coll_ret,      // {fault, done, ready}
    output reg  [682:0]  quant_rec,     // unit 4
    input  wire [2:0]    quant_ret,
    output reg  [1818:0] idx_rec,       // unit 9 {die_id 8, pos 20, n_R, n_O, n_D, n_C, n_B, n_A, R, O, D, C, B, A, header, valid}
    input  wire [2:0]    idx_ret,
    output reg  [690:0]  am_rec,        // unit 7 ARGMAX {die_id 8, n_O, n_A, O, A, header, valid} (mtp-lead (1): 683 -> 691)
    input  wire [2:0]    am_ret,
    // hgi-e2e DIE GAP (hgi-takeover): every record unit's payload on a die record bus (tools/hgi_die_dispatch.py layout,
    // LSB first {valid, header, [SUT], descriptors, effective n, sidebands}), one credit each; return {fault, done, ready}
    output reg  [938:0]  sm_rec,        // unit 1  {n_B, n_A, O, B, A, header, valid}
    input  wire [2:0]    sm_ret,
    output reg  [2197:0] su_rec,        // unit 2  {n_A, I, R, O, D, C, B, A, SUT, header, valid}
    input  wire [2:0]    su_ret,
    output reg  [1173:0] sfu_rec,       // unit 3  {n_A, O, C, B, A, header, valid}
    input  wire [2:0]    sfu_ret,
    output reg  [1471:0] att_rec,       // unit 5  {pos1, n_C, n_B, O, C, B, A, SUT, header, valid}
    input  wire [2:0]    att_ret,
    output reg  [703:0]  dma_rec,       // unit 8  {pos1, n_O, n_A, O, A, header, valid}
    input  wire [2:0]    dma_ret,
    output reg  [938:0]  hc_rec,        // unit 10 {n_O, n_A, O, B, A, header, valid}
    input  wire [2:0]    hc_ret,
    output wire [39:0]   cfg_bus,
    // units without a record adapter yet (index = unit code; 4, 6 and 9 unused here)
    output wire [15:0]   ux_v,
    input  wire [15:0]   ux_rdy,
    input  wire [15:0]   ux_done,
    input  wire [15:0]   ux_fault,
    input  wire          wr_quiet,
    // MTP=1: native DSpark operations (MX1 collar backend side) and the merged argmax ids
    input  wire          x_cmd_v,
    output wire          x_cmd_ready,
    input  wire [200:0]  x_cmd,
    input  wire [31:0]   x_cmd_job,
    input  wire [3:0]    x_cmd_gen,
    input  wire [31:0]   x_cmd_seq,
    output wire          x_cpl_v,
    input  wire          x_cpl_ready,
    output wire [31:0]   x_cpl_job,
    output wire [3:0]    x_cpl_gen,
    output wire [31:0]   x_cpl_seq,
    output wire          x_cpl_fault,
    output wire          x_am_v,
    output wire [16:0]   x_am_idx,
    output wire          x_drained_ready,
    input  wire          x_ext_fault,
    input  wire [16:0]   x_noise
);
    // ---------------------------------------------------------------- loader link fields
    wire        cfg_we = lcp[0];      wire [5:0] cfg_addr = lcp[6:1];   wire [63:0] cfg_wdata = lcp[70:7];
    wire        l_db_v = lcp[71];     wire [17:0] l_tok = lcp[89:72];   wire [19:0] l_pos = lcp[109:90];
    wire [31:0] l_job = lcp[141:110]; wire [3:0] l_gen = lcp[145:142];  wire [1:0] l_ent = lcp[147:146];
    wire        l_cpl_ack = lcp[148]; wire l_frsp_v = lcp[149];         wire [255:0] l_frsp = lcp[405:150];
    wire        l_freq_ack = lcp[406]; wire [7:0] rank = lcp[414:407]; wire [3:0] l_ncol = lcp[418:415];
    // ---------------------------------------------------------------- CP
    wire db_rdy, f_req_v, vr_v, cpl_v; wire [39:0] f_req_addr; wire [17:0] vr_addr;
    wire [15:0] u_v; wire [127:0] d_hdr; wire [255:0] d_sut; wire [1791:0] d_desc; wire [146:0] d_n;
    wire [20:0] d_pos1, d_pslot1; wire [15:0] d_L, d_L1;
    wire [17:0] cpl_token; wire [19:0] cpl_pos; wire [31:0] cpl_job, cpl_cycles; wire [3:0] cpl_gen, cpl_status;
    wire cpl_tokx; wire cfg_loaded; wire [2:0] cfg_err; wire [63:0] cfg_cp_act;
    reg  [15:0] u_rdy, u_done, u_fault;
    reg  db_hold; reg [79:0] db_q;                       // one doorbell station
    reg  [3:0] db_k; reg [31:0] db_lo; reg db_x;         // its kernel / G26 offset / translator-owned flag
    reg  x_run;                                          // the running job is the translator's
    wire [11*32-1:0] md_kent; wire [31:0] md_kstride;
    wire xdb_v, xdb_rdy; wire [17:0] xdb_tok; wire [19:0] xdb_pos; wire [31:0] xdb_job, xdb_off, xdb_loff;
    wire [3:0] xdb_gen, xdb_kind; wire [1:0] xdb_ent;
    reg  [4:0] fq_cr; reg [6:0] fq_in;                  // F5: fetch credits (the loader's 4-entry queue) / sectors in flight (<= 48)
    reg  cpl_hold;                                       // completion station: waits for the loader's ack
    reg  vr_busy, vr_rv; reg [31:0] vr_rd; reg [2:0] vr_w;
    reg  [3:0] credit;                                   // {argmax, idx, quant, coll}
    reg  [5:0] credx;                                    // {hc, dma, att, sfu, su, sm}
    reg  halt;
    wire units_busy = ~credit[0] | ~credit[1] | ~credit[2] | ~credit[3] | ~(&credx) | (|ux_v);
    localparam [15:0] RECU = 16'b0000_0111_1111_1110;   // units 1-10 have a record bus (0 CTL internal, 11 SIMT absent)
    ot_hgi_cp #(.RW(RW), .USE_MACRO(USE_MACRO)) u_cp (.clk(clk), .rst_n(rst_n), .cmd_we(cfg_we), .cmd_addr(cfg_addr),
        .cmd_wdata(cfg_wdata), .units_busy(units_busy), .cfg_bus(cfg_bus), .cfg_loaded(cfg_loaded), .cfg_err(cfg_err),
        .cfg_cp_act(cfg_cp_act), .rank(rank),
        .db_v(db_hold), .db_rdy(db_rdy), .db_token(db_q[17:0]), .db_pos(db_q[37:18]), .db_job(db_q[69:38]),
        .db_gen(db_q[73:70]), .db_entry(db_q[75:74]), .db_ncol(db_q[79:76]), .db_kernel(db_k), .db_loff(MUT == 2 ? 32'd0 : db_lo),
        .md_kent(md_kent), .md_kstride(md_kstride),
        .f_req_v(f_req_v), .f_req_rdy(fq_cr != 5'd0 && fq_in < 7'd48), .f_req_addr(f_req_addr), .f_rsp_v(l_frsp_v), .f_rsp_data(l_frsp),
        .vr_v(vr_v), .vr_rdy(!vr_busy), .vr_addr(vr_addr), .vr_rsp_v(vr_rv), .vr_rsp_data(vr_rd),
        .u_v(u_v), .u_rdy(u_rdy), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .d_n(d_n), .d_pos1(d_pos1),
        .d_pslot1(d_pslot1), .d_L(d_L), .d_L1(d_L1), .u_done(u_done), .u_fault(u_fault), .wr_quiet(wr_quiet),
        .cpl_v(cpl_v), .cpl_rdy(!cpl_hold || x_run), .cpl_token(cpl_token), .cpl_pos(cpl_pos), .cpl_job(cpl_job),
        .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .cpl_tokx(cpl_tokx));
    // ---------------------------------------------------------------- MTP backend translator (MTP=1)
    generate if (MTP) begin : g_mtp
        ot_hgi_mtp_xlate u_xlate (.clk(clk), .rst_n(rst_n), .external_fault(x_ext_fault), .backend_quiescent(!units_busy),
            .kent(md_kent), .kstride(md_kstride), .noise_token(x_noise),
            .cmd_v(x_cmd_v), .cmd_ready(x_cmd_ready), .cmd(x_cmd), .cmd_job(x_cmd_job), .cmd_generation(x_cmd_gen),
            .cmd_sequence(x_cmd_seq), .cpl_v(x_cpl_v), .cpl_ready(x_cpl_ready), .cpl_job(x_cpl_job),
            .cpl_generation(x_cpl_gen), .cpl_sequence(x_cpl_seq), .cpl_fault(x_cpl_fault), .am_v(x_am_v), .am_idx(x_am_idx),
            .drained_ready(x_drained_ready),
            .db_v(xdb_v), .db_rdy(xdb_rdy), .db_token(xdb_tok), .db_pos(xdb_pos), .db_job(xdb_job), .db_gen(xdb_gen),
            .db_entry(xdb_ent), .db_off(xdb_off), .db_kind(xdb_kind), .db_loff(xdb_loff),
            .c_v(cpl_v && x_run), .c_rdy(), .c_token(cpl_token), .c_pos(cpl_pos), .c_job(cpl_job), .c_gen(cpl_gen),
            .c_status(cpl_status), .c_tokx(cpl_tokx));
    end else begin : g_nomtp
        assign x_cmd_ready = 1'b0; assign x_cpl_v = 1'b0; assign x_cpl_job = 32'd0; assign x_cpl_gen = 4'd0;
        assign x_cpl_seq = 32'd0; assign x_cpl_fault = 1'b0; assign x_am_v = 1'b0; assign x_am_idx = 17'd0;
        assign x_drained_ready = 1'b1; assign xdb_v = 1'b0; assign xdb_tok = 18'd0; assign xdb_pos = 20'd0;
        assign xdb_job = 32'd0; assign xdb_gen = 4'd0; assign xdb_ent = 2'd0; assign xdb_off = 32'd0;
        assign xdb_kind = 4'd0; assign xdb_loff = 32'd0;
    end endgenerate
    assign xdb_rdy = !db_hold && !l_db_v;                // the host pulse wins a tie; the translator holds its valid
    // ---------------------------------------------------------------- unit credits and dispatch packing
    always @* begin
        u_rdy = ux_rdy & ~RECU & {16{!halt}};
        u_rdy[6] = credit[0] && coll_ret[0] && !halt;
        u_rdy[4] = credit[1] && quant_ret[0] && !halt;
        u_rdy[9] = credit[2] && idx_ret[0] && !halt;
        u_rdy[7] = credit[3] && am_ret[0] && !halt;
        u_rdy[1] = credx[0] && sm_ret[0] && !halt;  u_rdy[2] = credx[1] && su_ret[0] && !halt;
        u_rdy[3] = credx[2] && sfu_ret[0] && !halt; u_rdy[5] = credx[3] && att_ret[0] && !halt;
        u_rdy[8] = credx[4] && dma_ret[0] && !halt; u_rdy[10] = credx[5] && hc_ret[0] && !halt;
        u_done = ux_done & ~RECU; u_done[6] = coll_ret[1]; u_done[4] = quant_ret[1]; u_done[9] = idx_ret[1]; u_done[7] = am_ret[1];
        u_done[1] = sm_ret[1]; u_done[2] = su_ret[1]; u_done[3] = sfu_ret[1]; u_done[5] = att_ret[1]; u_done[8] = dma_ret[1]; u_done[10] = hc_ret[1];
        u_fault = ux_fault & ~RECU; u_fault[6] = coll_ret[2]; u_fault[4] = quant_ret[2]; u_fault[9] = idx_ret[2]; u_fault[7] = am_ret[2];
        u_fault[1] = sm_ret[2]; u_fault[2] = su_ret[2]; u_fault[3] = sfu_ret[2]; u_fault[5] = att_ret[2]; u_fault[8] = dma_ret[2]; u_fault[10] = hc_ret[2];
    end
    assign ux_v = u_v & ~RECU & {16{!halt}};
    // descriptor index: A 0, B 1, C 2, D 3, O 4, R 5, I 6
    wire [255:0] dA = d_desc[0*256 +: 256], dB = d_desc[1*256 +: 256], dC = d_desc[2*256 +: 256], dD = d_desc[3*256 +: 256],
                 dO = d_desc[4*256 +: 256], dR = d_desc[5*256 +: 256],
                 dI = d_desc[6*256 +: 256];
    wire [20:0] nA = d_n[0*21 +: 21], nB = d_n[1*21 +: 21], nC = d_n[2*21 +: 21], nD = d_n[3*21 +: 21], nO = d_n[4*21 +: 21],
                nR = d_n[5*21 +: 21], nI = d_n[6*21 +: 21];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            credit <= 4'b1111; coll_rec <= 968'd0; quant_rec <= 683'd0; idx_rec <= 1819'd0; am_rec <= 691'd0; halt <= 1'b0; credx <= 6'b111111;
            sm_rec <= 939'd0; su_rec <= 2198'd0; sfu_rec <= 1174'd0; att_rec <= 1472'd0; dma_rec <= 704'd0; hc_rec <= 939'd0;
            db_hold <= 1'b0; db_k <= 4'd0; db_lo <= 32'd0; db_x <= 1'b0; x_run <= 1'b0; fq_cr <= 5'(FQCR); fq_in <= 7'd0; cpl_hold <= 1'b0; vr_busy <= 1'b0; vr_rv <= 1'b0; cpl <= 222'd0;
            vmq <= 338'd0;
        end else begin
            // dispatch (the bus carries one valid edge per record)
            coll_rec[0] <= 1'b0; quant_rec[0] <= 1'b0; idx_rec[0] <= 1'b0; am_rec[0] <= 1'b0;
            sm_rec[0] <= 1'b0; su_rec[0] <= 1'b0; sfu_rec[0] <= 1'b0; att_rec[0] <= 1'b0; dma_rec[0] <= 1'b0; hc_rec[0] <= 1'b0;
            if (u_v[6] && u_rdy[6]) begin coll_rec <= {rank, nI, nO, nA, dI, dO, dA, d_hdr, 1'b1}; credit[0] <= 1'b0; end
            else if (coll_ret[1] || coll_ret[2]) credit[0] <= 1'b1;
            if (u_v[4] && u_rdy[4]) begin quant_rec <= {nO, nA, dO, dA, d_hdr, 1'b1}; credit[1] <= 1'b0; end
            else if (quant_ret[1] || quant_ret[2]) credit[1] <= 1'b1;
            if (u_v[9] && u_rdy[9]) begin
                idx_rec <= {rank, 20'(d_pos1 - 21'd1), nR, nO, nD, nC, nB, nA, dR, dO, dD, dC, dB, dA, d_hdr, 1'b1}; credit[2] <= 1'b0;
            end
            else if (idx_ret[1] || idx_ret[2]) credit[2] <= 1'b1;
            if (u_v[7] && u_rdy[7]) begin am_rec <= {rank, nO, nA, dO, dA, d_hdr, 1'b1}; credit[3] <= 1'b0; end
            else if (am_ret[1] || am_ret[2]) credit[3] <= 1'b1;
            if (u_v[1] && u_rdy[1]) begin sm_rec <= {nB, nA, dO, dB, dA, d_hdr, 1'b1}; credx[0] <= 1'b0; end
            else if (sm_ret[1] || sm_ret[2]) credx[0] <= 1'b1;
            if (u_v[2] && u_rdy[2]) begin su_rec <= {nA, dI, dR, dO, dD, dC, dB, dA, d_sut, d_hdr, 1'b1}; credx[1] <= 1'b0; end
            else if (su_ret[1] || su_ret[2]) credx[1] <= 1'b1;
            if (u_v[3] && u_rdy[3]) begin sfu_rec <= {nA, dO, dC, dB, dA, d_hdr, 1'b1}; credx[2] <= 1'b0; end
            else if (sfu_ret[1] || sfu_ret[2]) credx[2] <= 1'b1;
            if (u_v[5] && u_rdy[5]) begin att_rec <= {d_pos1, nC, nB, dO, dC, dB, dA, d_sut, d_hdr, 1'b1}; credx[3] <= 1'b0; end
            else if (att_ret[1] || att_ret[2]) credx[3] <= 1'b1;
            if (u_v[8] && u_rdy[8]) begin dma_rec <= {d_pos1, nO, nA, dO, dA, d_hdr, 1'b1}; credx[4] <= 1'b0; end
            else if (dma_ret[1] || dma_ret[2]) credx[4] <= 1'b1;
            if (u_v[10] && u_rdy[10]) begin hc_rec <= {nO, nA, dO, dB, dA, d_hdr, 1'b1}; credx[5] <= 1'b0; end
            else if (hc_ret[1] || hc_ret[2]) credx[5] <= 1'b1;
            if (vmstat[18] || vmstat[17] || vmstat[16]) halt <= 1'b1;
            // doorbell station
            if (l_db_v && !db_hold) begin
                db_hold <= 1'b1; db_q <= {l_ncol, l_ent, l_gen, l_job, l_pos, l_tok}; db_k <= 4'd0; db_lo <= 32'd0; db_x <= 1'b0;
            end else if (xdb_v && xdb_rdy) begin               // MTP: one KERNEL launch (ncol 1)
                db_hold <= 1'b1; db_q <= {4'd1, xdb_ent, xdb_gen, xdb_job, xdb_pos, xdb_tok}; db_k <= xdb_kind;
                db_lo <= xdb_loff; db_x <= 1'b1;
            end
            cpl[0] <= 1'b0;
            if (db_hold && db_rdy) begin db_hold <= 1'b0; cpl[0] <= !db_x; x_run <= db_x; end   // db_taken (host only)
            // completion station (a translator job's completion is the translator's, consumed the edge it is valid)
            cpl[1] <= 1'b0;
            if (cpl_v && x_run) x_run <= 1'b0;
            else if (cpl_v && !cpl_hold) begin
                cpl_hold <= 1'b1; cpl[1] <= 1'b1;
                cpl[112:2] <= {cpl_tokx, cpl_cycles, cpl_status, cpl_gen, cpl_job, cpl_pos, cpl_token};
            end
            if (l_cpl_ack) cpl_hold <= 1'b0;
            // record-ring fetch station
            cpl[113] <= 1'b0;
            // F5: a request leaves on a credit (the loader's queue slot), the slot returns on the loader's f_req_ack (the
            // memory lane took it), not on the data; sectors return in order, at most 48 in flight (the sequencer's NOS)
            begin : fetch
                reg snd; snd = f_req_v && fq_cr != 5'd0 && fq_in < 7'd48;
                if (snd) begin cpl[113] <= 1'b1; cpl[153:114] <= f_req_addr; end
                fq_cr <= fq_cr - {4'd0, snd} + {4'd0, l_freq_ack};
                fq_in <= fq_in + {6'd0, snd} - {6'd0, l_frsp_v};
            end
            cpl[221:154] <= {cfg_cp_act, cfg_err, cfg_loaded};
            // VM read client: one word, read as its sector
            vmq[337] <= 1'b0; vr_rv <= 1'b0;
            if (vr_v && !vr_busy) begin
                vr_busy <= 1'b1; vr_w <= vr_addr[2:0];
                vmq <= {1'b1, 1'b0, {12'd0, vr_addr[17:3], 5'd0}, 256'd0, 32'd0, 16'h0c00};
            end
            if (vmr[273]) begin vr_busy <= 1'b0; vr_rv <= 1'b1; vr_rd <= vmr[(vr_w ^ (MUT == 1 ? 3'd1 : 3'd0))*32 +: 32]; end
        end
    end
endmodule
`default_nettype wire
