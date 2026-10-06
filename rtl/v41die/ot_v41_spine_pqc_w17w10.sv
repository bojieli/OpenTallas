// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_spine_pqc_w17w10: TIMING-CLOSED SUCCESSOR of ot_v41_spine_pq_w17w10 (Claude:dsrom-field-spine, 2026-10-04).
// Same ports, same parameters, same op semantics (PQ = 0: one op in flight, the pinned sequencing; PQ = 1: up to four
// pipelined ops), same broadcast bus.  The as-built / PQ spine fails 1.2 GHz SS by 684 / 723 / 906 ps on register-to-
// register loops inside the spine (results/rtl/dsrom_recovery_20261004/field_pq_phys/spw*_ss_violations_by_register
// .json); this module restructures exactly those loops.  Every change below adds latency only where a register is
// inserted, and every added cycle is priced by re-running the field exactness campaign on this RTL.
//
//  1. STREAM-ROM READER (was: sw -> need vs have -> s_ok -> next stream-ROM address -> ROM -> sw, one cycle).
//     A reader walks the stream ROM ahead of the streamer in op order, with a REGISTERED ROM address and a
//     registered ROM word, and pushes each word with everything the streamer derives from it precomputed (need,
//     buffer parity, last-of-position / last-of-op flags, op tag, position, x-buffer read indices) into an 8-entry
//     credit FIFO.  The streamer only compares a registered `need` with a registered `have` (both buffers in
//     parallel) and pops; the ROM read left the loop.  The reader prefetches the next op's words while the current
//     op streams, so the first beat of an op is not delayed: the go -> first-beat timing of the pinned spine (one
//     arming cycle after go) is kept.
//  2. BEAT ASSEMBLY one stage deeper (was: sw -> index arithmetic -> x-buffer read -> bt_*): stage 1 registers the
//     beat's (replicated) buffer read indices, stage 2 reads.  The whole broadcast (configuration, go and beats)
//     moves by the same one cycle, so every relative broadcast timing the elements see is unchanged.
//  3. RETURN: REGISTERED ROOT INPUTS + REGISTERED REGION-LOCAL DECODE (was: r_row tag -> per-tag base/stride/format
//     mux -> base + row + pos * stride -> w_addr, one cycle, fanning one tag-indexed configuration out to every
//     region).  Stage 0 registers each region root's row; stage 1 selects the op's configuration from a REPLICA of
//     the per-tag table owned by the row's region group (RG regions; kept ot_v41_kreg copies) and computes base +
//     row, pos * stride (a select among the tag's precomputed 1/3/5/7 x stride and their shifts) and the format
//     select; stage 2 adds (the select copied, kept); stage 3 writes.  +3 cycles on every row write (the node tail).
//     PQ = 0 (elements return no op tag): a row belongs to the op issued last (the inherited PQ spine took row bits
//     [15:14] as the tag at PQ = 0 too, so back-to-back ops of distinct tags wrote at the first op's base; fixed).
//  4. ROW COUNTS from the registered root inputs: per group popcount, groups of four summed, total; an op's rows-left
//     counter is loaded at its go (rows arrive only after it) and the op retires one cycle after it reads zero.
//  5. GO TIMERS: the 16-bit since1/since2 counters and their >= GAP / >= GUARD compares become saturating count-down
//     timers with registered zero flags, loaded from a registered stream-end pulse (identical go cycles; the ev_end
//     debug event and an op's `sent` flag follow one cycle later); the configuration settle count is a count-down
//     with a registered zero flag (identical go cycles).  A buffer's `have` clears the cycle after its loader starts
//     (the streamer masks it meanwhile).
//  6. LOADER: the x read address base + pos * stride + k is an incremental pointer (identical addresses and cycles);
//     the BF16 x-buffer write is registered once (data rounded and one-hot block enable decoded a cycle earlier), and
//     the buffer's `have` count follows the write (one cycle later than before).  The write address is the
//     registered block index concatenated with the constant word index (no address adder on the write).
//  7. ACCEPT / ROMS: both ROMs are read as two-cycle synchronous macros (address register + internal pipeline
//     register; the screen models them so): the phase word lands two cycles after the accept (a slot is usable by
//     the loader / reader / issuer two cycles after its accept), the stream reader has R0 (address), RA (macro
//     stage), R1 (word), R2 (derived fields) and pushes into a queue behind a registered HEAD entry, so the
//     streamer's advance cone is need-vs-have of the head's registers only.
//
// v9 (2026-10-05, R = 128 closure revision; every class of the routed v8 R = 16 / 128 screens): the FP8 quantiser is
// ot_dsrom_aq12 (LATENCY 18; the qb / eb row enables are registered one-hots from the spine's own delayed request,
// 8 kept slice copies); the BF16 x-buffer write is two stages (+1 cycle on the BF16 load) with registered one-hot
// block enables (16 kept copies); the reader's last max level is a stage R3 (+1 reader cycle, prefetched); the
// queue's write enable no longer depends on the streamer's advance; the accept writes the slot's wide fields one
// cycle later from registered copies; the return's rsplit compare is registered before the kept select copies;
// replica groups of RG = 8 regions; RPT = 1 registered repeater stage on the broadcast out, the root inputs and the
// row-write outputs (+1 cycle each, measured in the vehicle).
//
// v10 (2026-10-05, R = 128 quantiser classes of the v9 routes): the quantiser instance is ot_dsrom_aq12f (same
// function and latency as ot_dsrom_aq12; four kept copies of the S11 exponent broadcast, Kogge-Stone max compares,
// the nonfinite OR split at S1).  No cycle changes.
//
// The broadcast wire to the regions and the return wire from them are NOT in this module: they are the S81 floorplan's
// registered wire stages at the measured SS reach of 504 um a stage (results/rtl/dsrom_s81_fulldie_20261004/
// floorplan.json trunk_stages.stages_at_504, field_one_way 41), charged once per node by the field composition.
// ---------------------------------------------------------------------------
module ot_v41_spine_pqc_w17w10 #(
    parameter integer PHW = 6,
    parameter integer SAW = 14,
    parameter integer R = 2,
    parameter integer VAW = 19,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer NSEG = 8,
    parameter integer PQ = 0,
    parameter integer GAP = 12,
    parameter integer GUARD = 180,
    parameter integer GSLACK = 6,
    parameter integer RG = 8,            // regions per replica group (return configuration replicas; v9: 16 -> 8)
    parameter integer RPT = 2,           // v9: registered repeater stages on the broadcast out, the root inputs and
                                         // the row-write outputs (long die-scale nets; each adds RPT cycles)
    parameter integer BW = 1 + PHW + 3 + 1 + 1 + 2 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    input  wire [1:0]        i_fmt,
    output wire              ready,
    output wire              idle,
    output reg               x_re,
    output reg  [VAW-1:0]    x_addr,
    input  wire [VRD*32-1:0] x_q,
    output wire [R-1:0]      w_we,
    output wire [R*VAW-1:0]  w_addr,
    output wire [R*32-1:0]   w_data,
    output wire              f_cfg_go,
    output wire [PHW-1:0]    f_cfg_ph,
    output wire [2:0]        f_cfg_np,
    output wire              f_go,
    output wire              f_go_bf,
    output wire [1:0]        f_go_tag,
    output wire              f_xs_v,
    output wire [7:0]        f_xs_p,
    output wire [2:0]        f_xs_b,
    output wire [1:0]        f_xs_sv,
    output wire [255:0]      f_xs_q0,
    output wire [9:0]        f_xs_e0,
    output wire [255:0]      f_xs_q1,
    output wire [9:0]        f_xs_e1,
    output wire [2:0]        f_xs_pos,
    output wire [2:0]        f_xb_pos,
    output wire              f_xb_v,
    output wire [2:0]        f_xb_b,
    output wire [3:0]        f_xb_sv,
    output wire [31:0]       f_xb_u,
    output wire [1023:0]     f_xb_d,
    output wire [BW-1:0]     f_bus,
    input  wire [R-1:0]      r_v,
    input  wire [16*R-1:0]   r_row,
    input  wire [3*R-1:0]    r_pos,
    input  wire [32*R-1:0]   r_fp32,
    input  wire [16*R-1:0]   r_bf16,
    input  wire [R-1:0]      r_e,
    input  wire              f_fault,
    output reg               fault,
    output reg  [31:0]       phase_cycles,    // cycles from the first accepted op to idle (last node)
    output reg               ev_go,
    output reg               ev_end,
    output reg  [1:0]        ev_tag
`ifdef OT_PQ_ROM_PORTS
    // physical screen only: the phase and stream ROMs as macro ports (address out, word in)
    ,
    output wire [PHW:0]      rom_pa0,
    output wire [PHW:0]      rom_pa1,
    input  wire [63:0]       rom_pq0,
    input  wire [63:0]       rom_pq1,
    output wire [SAW-1:0]    rom_sa,
    input  wire [47:0]       rom_sq
`endif
);
    localparam integer CW = 3 * NSEG + 1;
    localparam integer NBLK = KMAX / 32;
    localparam integer BAW = $clog2(NBLK);
    localparam integer NGR = (R + RG - 1) / RG;          // replica / row-count groups
    localparam integer NGB = (NGR + 3) / 4;              // groups of four groups
    localparam integer NWB = 2 * KMAX / VRD;             // BF16 x-buffer write blocks (VRD words)
    localparam integer WBW = (NWB > 1) ? $clog2(NWB) : 1;
    localparam integer VB = $clog2(VRD);
    localparam integer TW = $clog2(((GAP > GUARD) ? GAP : GUARD) + 2);   // go-timer width
    localparam integer FD = 8;                           // stream words in flight + queued + head (round trip 6 cycles)
    localparam [5:0] CFG_WAIT = 6'(CW + 1 + GSLACK);
`ifndef OT_PQ_ROM_PORTS
    // ------------------------------------------------------------------ ROMs
    reg [63:0] phrom [0:(2 << PHW)-1] /*verilator public_flat_rw*/;
    reg [47:0] strom [0:(1 << SAW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (2 << PHW); ii = ii + 1) phrom[ii] = 64'd0;
        for (ii = 0; ii < (1 << SAW); ii = ii + 1) strom[ii] = 48'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) begin
            $readmemh({rom_dir, "/spine_phase.hex"}, phrom);
            $readmemh({rom_dir, "/spine_stream.hex"}, strom);
        end
    end
`endif
    // ------------------------------------------------------------------ op slots (tag = slot)
    reg           sv [0:3];          // accepted, not retired
    reg           sr [0:3];          // phase word landed (usable)
    reg           s_rd [0:3];        // stream words being / been read by the reader
    reg           si [0:3];          // configuration issued
    reg           sd [0:3];          // last beat sent
    reg [PHW-1:0] s_ph [0:3];
    reg [VAW-1:0] s_xb [0:3];
    reg [VAW-1:0] s_ob [0:3];
    reg [1:0]     s_fm [0:3];
    reg [63:0]    s_pw [0:3];
    reg [15:0]    s_rs [0:3];
    reg [18:0]    s_rl [0:3];        // rows left (loaded at go)
    reg [18:0]    s_tot [0:3];       // rows of the op (all positions): two registered steps, read at go
    reg [18:0]    s_tm0 [0:3];
    reg [18:0]    s_tm1 [0:3];
    reg [2:0]     s_np [0:3];        // positions - 1
    reg [3:0]     s_np1 [0:3];       // positions
    reg [VAW-1:0] s_xps [0:3];
    reg [VAW-1:0] s_ops [0:3];
    reg [1:0]     acc, ldt, ist, rdt; // next tag to accept / load / issue / read
    reg [1:0]     iss_tag;           // tag of the op issued last (PQ = 0 rows belong to it)
    reg [31:0]    cyc;
    reg           any_v;
    always @* any_v = sv[0] | sv[1] | sv[2] | sv[3];
    assign ready = !sv[acc];
    assign idle = !any_v;
    // accept pipeline: registered phase-ROM address, the word lands one cycle later
    reg           a_v, a_v2;
    reg [1:0]     a_tag, a_tag2;
    reg [PHW-1:0] a_ph;
    // v9: the slot's wide fields are written the cycle after the accept from registered copies of the op inputs,
    // with the slot enable a registered one-hot (kept, two copies): the accept cone (go, acc -> 4 x ~100 slot
    // flops) was an SS class at R = 128 (acc -> s_ops).  The fields are read only once the slot's phase word has
    // landed (two cycles after the accept), so the cycles are unchanged.
    reg [VAW-1:0] a_xb, a_ob, a_xps, a_ops;
    reg [1:0]     a_fm;
    reg [2:0]     a_np;
    wire [3:0]    a_oh_d = (go && !sv[acc]) ? (4'b0001 << acc) : 4'b0000;
    wire [7:0]    a_oh;
    ot_v41_kreg #(.W(4), .AR(1)) u_aoh0 (.clk(clk), .arst_n(rst_n), .d(a_oh_d), .q(a_oh[3:0]));
    ot_v41_kreg #(.W(4), .AR(1)) u_aoh1 (.clk(clk), .arst_n(rst_n), .d(a_oh_d), .q(a_oh[7:4]));
    always @(posedge clk) begin
        a_xb <= i_xbase; a_ob <= i_obase; a_xps <= i_xps; a_ops <= i_ops; a_fm <= i_fmt; a_np <= i_np;
    end
    integer ka;
    always @(posedge clk)
        for (ka = 0; ka < 4; ka = ka + 1) begin
            if (a_oh[ka]) begin s_xb[ka] <= a_xb; s_ob[ka] <= a_ob; s_xps[ka] <= a_xps; s_ops[ka] <= a_ops; end
            if (a_oh[4 + ka]) begin s_ph[ka] <= a_ph; s_fm[ka] <= a_fm; s_np[ka] <= a_np; s_np1[ka] <= 4'(a_np) + 4'd1; end
        end
    wire [63:0] ph_q0, ph_q1;
`ifdef OT_PQ_ROM_PORTS
    // macro ports: the NEXT address (a_ph registers it at accept); the macro registers it itself
    wire [PHW-1:0] a_ph_n = (go && !sv[acc]) ? i_ph : a_ph;
    assign rom_pa0 = {a_ph_n, 1'b0}; assign rom_pa1 = {a_ph_n, 1'b1};
    assign ph_q0 = rom_pq0; assign ph_q1 = rom_pq1;           // two-cycle synchronous macro: valid with a_v2
`else
    reg [63:0] ph_q0r, ph_q1r;
    always @(posedge clk) begin ph_q0r <= phrom[{a_ph, 1'b0}]; ph_q1r <= phrom[{a_ph, 1'b1}]; end
    assign ph_q0 = ph_q0r; assign ph_q1 = ph_q1r;
`endif
    // ------------------------------------------------------------------ loader
    reg        ld_run, ld_more;
    reg [1:0]  ld_tag;
    reg [2:0]  ld_pos;
    reg [13:0] ld_k, ld_kk;
    reg        ld_fam;
    reg [VAW-1:0] ld_pb, ld_ptr;     // position base, read pointer
    reg [VAW-1:0] ld_xps;            // the op's x position stride
    wire [VAW-1:0] ld_pbn, ld_ptrn;
    wire [13:0]    ld_kn;
    wire           ld_end;
    ot_v41_ksadd #(.W(VAW)) u_ldpb (.a(ld_pb), .b(ld_xps), .cin(1'b0), .s(ld_pbn), .cout());
    ot_v41_ksadd #(.W(VAW)) u_ldpt (.a(ld_ptr), .b(VAW'(VRD)), .cin(1'b0), .s(ld_ptrn), .cout());
    ot_v41_ksadd #(.W(14)) u_ldk (.a(ld_k), .b(14'(VRD)), .cin(1'b0), .s(ld_kn), .cout());
    ot_v41_ksadd #(.W(14)) u_lde (.a(ld_kn), .b(~ld_kk), .cin(1'b1), .s(), .cout(ld_end));   // ld_k + VRD >= ld_kk
    reg        rq_v, rq_par, rq_fam;
    reg [13:0] rq_k, is_k;
    reg        is_par, is_fam;
    reg        bufbusy [0:1];        // buffer parity holds an op's x not yet fully streamed
    wire [1:0] aq_vo, aq_f;
    wire [511:0] aq_q;
    wire [19:0]  aq_e;
    // v9: the FP8 quantiser is ot_dsrom_aq12 (rtl/hdc/v41x/ot_dsrom_aq12.sv: the FP8 path of the pinned
    // ot_hdc_actquant bit for bit, re-staged for 0.833 ns at SS; LATENCY 18 instead of 13).  The spine passes fp4 = 0
    // to the pinned module, so the function is the same.  v10: ot_dsrom_aq12f (rtl/hdc/v41x/ot_dsrom_aq12f.sv), the same
    // function and LATENCY with the v9 R = 128 quantiser classes fixed (kept s11 copies, prefix compares, split
    // nonfinite OR); lockstep-equivalent to ot_dsrom_aq12 on every output every cycle.
    localparam integer AQL = 18;
    genvar gq;
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_aq
        wire [511:0] unused_y;
        wire signed [9:0] e1;
        ot_dsrom_aq12f u_aq (.clk(clk), .rst_n(rst_n), .v(rq_v && !rq_fam),
            .x(x_q[1024*gq +: 1024]), .vo(aq_vo[gq]), .q(aq_q[256*gq +: 256]), .e(e1), .y(unused_y),
            .fault(aq_f[gq]));
        assign aq_e[10*gq +: 10] = e1;
    end endgenerate
    // the qb / eb write and the `have` update are driven from the spine's own copy of the request, delayed to the
    // quantiser's output cycle, never from the quantiser's vo (v8: vo drove every qb row enable, a single flop with a
    // 4,096-flop cone, the SS critical class at R = 128):
    //   AQL - 2 delay registers of {v, block, parity}; then 8 kept copies (one per 32-bit qb slice) and one for the
    //   `have` update; then, per slice, the row enables decoded into a kept register (row b takes the low half of
    //   the block pair, row b + 1 the high half), so each enable drives 32 flops.
    localparam integer NQR = 2 * NBLK;                  // qb rows
    wire           aq_v_n = rq_v && !rq_fam;
    wire [BAW+1:0] aqi_d;                               // {v, block, parity} at AQL - 2
    ot_hdc_delay #(.W(BAW + 2), .D(AQL - 2), .RESET(1)) u_aqi (.clk(clk), .rst_n(rst_n),
        .d({aq_v_n, rq_k[BAW+4:5], rq_par}), .q(aqi_d));
    wire [9*(BAW+2)-1:0] aqi;                           // AQL - 1: 8 slice copies + 1 `have` copy
    genvar gq2;
    generate for (gq2 = 0; gq2 < 9; gq2 = gq2 + 1) begin : g_aqi
        ot_v41_kreg #(.W(BAW + 2), .AR(1)) u_c (.clk(clk), .arst_n(rst_n), .d(aqi_d), .q(aqi[(BAW+2)*gq2 +: BAW+2]));
    end endgenerate
    wire [8*2*NQR-1:0] qwe;                             // AQL: per slice {hi enables, lo enables}
    generate for (gq2 = 0; gq2 < 8; gq2 = gq2 + 1) begin : g_qwe
        wire [BAW+1:0] c = aqi[(BAW+2)*gq2 +: BAW+2];
        wire [15:0]    b = (c[0] ? 16'(NBLK) : 16'd0) + 16'(c[BAW:1]);
        reg  [2*NQR-1:0] dec;
        integer r;
        always @* for (r = 0; r < NQR; r = r + 1) begin
            dec[r] = c[BAW+1] && (b == 16'(r));
            dec[NQR + r] = c[BAW+1] && (b + 16'd1 == 16'(r));
        end
        ot_v41_kreg #(.W(2 * NQR), .AR(1)) u_we (.clk(clk), .arst_n(rst_n), .d(dec), .q(qwe[2*NQR*gq2 +: 2*NQR]));
    end endgenerate
    wire [BAW+1:0] aqh;                                 // AQL: the `have` copy
    ot_v41_kreg #(.W(BAW + 2), .AR(1)) u_aqh (.clk(clk), .arst_n(rst_n), .d(aqi[(BAW+2)*8 +: BAW+2]), .q(aqh));
    wire           aq_wv = aqh[BAW+1];
    wire [BAW-1:0] aq_blk = aqh[BAW:1];
    wire           aq_par = aqh[0];
    reg [255:0] qb [0:2*NBLK-1];
    reg [9:0]   eb [0:2*NBLK-1];
    reg [15:0]  bb [0:2*KMAX-1];
    reg [14:0]  have [0:1];
    // BF16 x-buffer write (v9: two stages, +1 cycle on the BF16 load path).  Stage A registers each word's high half
    // and its rounding increment and the written block; stage B increments (prefix incrementers) and decodes the
    // block into registered one-hot enables, 16 kept copies (one per VRD/16 words); the write is at stage B + 1, and
    // the buffer's `have` follows the write.  (v8: bw_v -> every bb row enable and q_x -> rounding -> bw_d were SS
    // classes at R = 128.)
    reg            bw_v, bw_par;     // stage B (the write and the `have` update are the cycle after)
    reg [13:0]     bw_k;
    reg            ba_v, ba_par;     // stage A
    reg [13:0]     ba_k;
    reg [WBW-1:0]  ba_blk;
    reg [VRD*16-1:0] ba_hi;
    reg [VRD-1:0]    ba_inc;
    wire [WBW-1:0] bw_blk_n = WBW'(((rq_par ? KMAX : 0) + 32'(rq_k)) / VRD);
    localparam integer NBC = (VRD >= 16) ? 16 : VRD;    // enable copies
    wire [NBC*NWB-1:0] bwe;
    reg  [NWB-1:0]     bwe_d;
    integer kbw;
    always @* for (kbw = 0; kbw < NWB; kbw = kbw + 1) bwe_d[kbw] = ba_v && (ba_blk == WBW'(kbw));
    genvar gbw;
    generate for (gbw = 0; gbw < NBC; gbw = gbw + 1) begin : g_bwb
        ot_v41_kreg #(.W(NWB), .AR(1)) u_bwb (.clk(clk), .arst_n(rst_n), .d(bwe_d), .q(bwe[NWB*gbw +: NWB]));
    end endgenerate
    reg [VRD*16-1:0] bw_d;
    wire [VRD*16-1:0] bw_rn;         // rounded to BF16 (the pinned rounding increment, prefix incrementers)
    genvar gw;
    generate for (gw = 0; gw < VRD; gw = gw + 1) begin : g_rn
        ot_v41_inc #(.W(16)) u_rn (.a(ba_hi[16*gw +: 16]), .inc(ba_inc[gw]), .y(bw_rn[16*gw +: 16]), .co());
    end endgenerate
    integer kbi;
    always @(posedge clk) begin
        ba_blk <= bw_blk_n;
        for (kbi = 0; kbi < VRD; kbi = kbi + 1) begin
            ba_hi[16*kbi +: 16] <= x_q[32*kbi + 16 +: 16];
            ba_inc[kbi] <= x_q[32*kbi + 15] & ((x_q[32*kbi +: 15] != 15'd0) | x_q[32*kbi + 16]);
        end
    end

    // ------------------------------------------------------------------ stream-ROM reader
    reg        rd_run, rd_last;
    reg [1:0]  rd_tag;
    reg [2:0]  rd_pos, rd_np;
    reg [15:0] rd_i, rd_nb;
    reg [SAW-1:0] rd_a, rd_sb;
    reg        rd_fam;
    reg [3:0]  cred;                 // free FIFO entries not claimed by a read in flight
    wire       rd_iss = rd_run && cred != 4'd0;
    // R0: registered ROM address + the word's attributes; RA: the macro's own pipeline register; R1: the ROM word
    reg           r0_v, r0_lp, r0_lo, r0_fam;
    reg [1:0]     r0_tag;
    reg [2:0]     r0_pos;
    reg [SAW-1:0] r0_a;
    reg           ra_v, ra_lp, ra_lo, ra_fam;
    reg [1:0]     ra_tag;
    reg [2:0]     ra_pos;
    wire [47:0] st_q;
`ifdef OT_PQ_ROM_PORTS
    // macro port: the NEXT address (rd_a, which r0_a registers every cycle); the macro is a two-cycle synchronous ROM
    // (address register, internal pipeline register) and returns the word of r0_a two cycles later, as below
    assign rom_sa = rd_a; assign st_q = rom_sq;
`else
    reg [47:0] st_q1;
    always @(posedge clk) st_q1 <= strom[r0_a];
    assign st_q = st_q1;
`endif
    reg           r1_v, r1_lp, r1_lo, r1_fam;
    reg [1:0]     r1_tag;
    reg [2:0]     r1_pos;
    reg [47:0]    r1_w;
    // R2: derived fields
    wire          r1_spar = r1_tag[0] ^ r1_pos[0];
    wire [7:0]    r1_u  = r1_w[8:1];
    wire [2:0]    r1_b  = r1_w[11:9];
    wire [1:0]    r1_sv = r1_w[13:12];
    // max over the byte lanes whose bit is set (0 if none): a balanced tree, the same value as the pinned serial scan
    wire [7:0]    r1_g0 = r1_w[4] ? r1_w[15:8]  : 8'd0;
    wire [7:0]    r1_g1 = r1_w[5] ? r1_w[23:16] : 8'd0;
    wire [7:0]    r1_g2 = r1_w[6] ? r1_w[31:24] : 8'd0;
    wire [7:0]    r1_g3 = r1_w[7] ? r1_w[39:32] : 8'd0;
    wire [7:0]    r1_m01 = (r1_g1 > r1_g0) ? r1_g1 : r1_g0;
    wire [7:0]    r1_m23 = (r1_g3 > r1_g2) ? r1_g3 : r1_g2;
    // v9: the final max level is in R3 (r1_w -> r2_umax was an SS class at R = 128); +1 reader cycle, hidden by
    // the prefetch (the 8 credits cover the 7-cycle round trip)
    // need_q = ({u, sv[1], b, 5'd0} + 32) mod 2^15, need_b = ({umax, 7'd0} + 128) mod 2^15 (the pinned formulas);
    // need_q is formed in R2, need_b's increment at the push
    wire [9:0]  r1_nq;
    ot_v41_inc #(.W(10)) u_nq (.a({r1_u[5:0], r1_sv[1], r1_b}), .inc(1'b1), .y(r1_nq), .co());
    wire [15:0] r1_blk0 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b0, r1_b};
    wire [15:0] r1_blk1 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b1, r1_b};
    reg           r2_v, r2_lp, r2_lo, r2_fam, r2_spar;
    reg [1:0]     r2_tag;
    reg [2:0]     r2_pos;
    reg [47:0]    r2_w;
    reg [9:0]     r2_nq;
    reg [7:0]     r2_m01, r2_m23;
    reg [15:0]    r2_b0, r2_b1;
    reg [35:0]    r2_hi;
    // R3: the last max level; need_b's increment at the push
    reg           r3_v, r3_lp, r3_lo, r3_fam, r3_spar;
    reg [1:0]     r3_tag;
    reg [2:0]     r3_pos;
    reg [47:0]    r3_w;
    reg [9:0]     r3_nq;
    reg [7:0]     r3_umax;
    reg [15:0]    r3_b0, r3_b1;
    reg [35:0]    r3_hi;
    wire [7:0]    r3_nb;
    ot_v41_inc #(.W(8)) u_nb (.a(r3_umax), .inc(1'b1), .y(r3_nb), .co());
    // an entry: {w 48, need 15, spar, lp, lo, fam, tag 2, pos 3, b0 16, b1 16, hi 36}
    localparam integer EW = 48 + 15 + 4 + 2 + 3 + 16 + 16 + 36;
    wire [EW-1:0] r3_e = {r3_w, r3_fam ? {r3_nb, 7'd0} : {r3_nq, 5'd0}, r3_spar, r3_lp, r3_lo, r3_fam, r3_tag, r3_pos,
                          r3_b0, r3_b1, r3_hi};
    // queue behind a registered HEAD entry: the streamer reads only the head's registers
    reg [EW-1:0] fq [0:FD-1];
    reg [2:0]  qrp, qwp;
    reg [3:0]  qcnt;
    reg        hv;
    reg [EW-1:0] he;
    wire [47:0] hw     = he[EW-1 -: 48];
    wire [14:0] h_need = he[EW-49 -: 15];
    wire        h_spar = he[EW-64];
    wire        s_lp_c, s_lo_c;      // control copies (below)
    wire        h_fam  = he[EW-67];
    wire [1:0]  h_tag  = he[EW-68 -: 2];
    wire [2:0]  h_pos  = he[EW-70 -: 3];
    wire [15:0] h_b0   = he[EW-73 -: 16];
    wire [15:0] h_b1   = he[EW-89 -: 16];
    wire [35:0] h_hi   = he[35:0];
    // ------------------------------------------------------------------ streamer
    reg        sm_run, sm_arm;
    reg [1:0]  sm_tag;
    // next states of `have` and of the head (the registers below and their kept control copies load them)
    reg  [14:0] have_n [0:1];
    reg  [1:0]  clr_q;               // loader started on buffer p last cycle
    wire        ld_st0 = !ld_run && !ld_more && sv[ldt] && sr[ldt] && !bufbusy[ldt[0]];
    wire        ld_st1 = !ld_run && ld_more && !bufbusy[ld_tag[0] ^ ~ld_pos[0]];
    integer kh;
    always @* begin
        for (kh = 0; kh < 2; kh = kh + 1) have_n[kh] = have[kh];
        // a buffer's count is cleared the cycle after its loader starts (clr_q); during that cycle the streamer sees
        // it as empty through the mask below, exactly as the pinned same-edge clear
        for (kh = 0; kh < 2; kh = kh + 1) if (clr_q[kh]) have_n[kh] = 15'd0;
        if (bw_v) have_n[bw_par] = 15'(bw_k) + 15'(VRD);
        if (aq_wv) have_n[aq_par] = {aq_blk, 5'd0} + 15'd64;
    end
    wire        h_take;                          // the head is (re)loaded this cycle
    wire [EW-1:0] he_n = !h_take ? he : (qcnt != 4'd0) ? fq[qrp] : r3_e;
    wire        hv_n = !h_take ? hv : (qcnt != 4'd0) || r3_v;
    // the streamer's control copy (kept): {hv, need, spar, w[0], lp, lo, tag} and both `have` counts
    localparam integer CCW = 1 + 15 + 1 + 1 + 1 + 1 + 2 + 30;
    wire [CCW-1:0] cc;
    ot_v41_kreg #(.W(CCW), .AR(1)) u_cc (.clk(clk), .arst_n(rst_n),
        .d({hv_n, he_n[EW-49 -: 15], he_n[EW-64], he_n[EW-48], he_n[EW-65], he_n[EW-66], he_n[EW-68 -: 2],
            have_n[1], have_n[0]}), .q(cc));
    wire        c_hv = cc[CCW-1];
    wire [14:0] c_need = cc[CCW-2 -: 15];
    wire        c_spar = cc[CCW-17];
    wire        c_w0 = cc[CCW-18];
    assign      s_lp_c = cc[CCW-19];
    assign      s_lo_c = cc[CCW-20];
    wire [1:0]  c_tag = cc[CCW-21 -: 2];
    wire [14:0] c_have1 = cc[29:15], c_have0 = cc[14:0];
    wire       h_ge0, h_ge1;            // need <= have: the carry of have + ~need + 1 (prefix adders)
    ot_v41_ksadd #(.W(15)) u_g0 (.a(c_have0), .b(~c_need), .cin(1'b1), .s(), .cout(h_ge0));
    ot_v41_ksadd #(.W(15)) u_g1 (.a(c_have1), .b(~c_need), .cin(1'b1), .s(), .cout(h_ge1));
    // (need >= 32 for every stream word, so an empty buffer never satisfies it: masking the compare = clearing have)
    wire        s_ok = !c_w0 || (c_spar ? (h_ge1 && !clr_q[1]) : (h_ge0 && !clr_q[0]));
    wire        s_adv = sm_run && sm_arm && c_hv && s_ok;
    assign      h_take = s_adv || !hv;
    reg         tm_bad;              // a beat of another op than the streamer's (registered check)
    reg         st_end;              // the last beat of an op was sent last cycle
    reg  [1:0]  st_tag;
    // go timers: count-down with registered zero flags
    reg [TW-1:0] t_gap, t_g1, t_g2;
    reg        gap_ok, guard_ok;
    reg [5:0]  cfg_rem;
    reg        cfg_ok;
    // issue condition for op ist
    localparam [1:0] I_IDLE = 2'd0, I_CFG = 2'd1;
    reg [1:0]  ist_st;
    reg inflight;                    // PQ = 0: an issued op not yet retired
    always @* inflight = (sv[0] && si[0]) | (sv[1] && si[1]) | (sv[2] && si[2]) | (sv[3] && si[3]);
    reg inflight_mtp;                // an issued multi-position op not yet retired (it runs alone)
    always @* inflight_mtp = (sv[0] && si[0] && s_np[0] != 3'd0) | (sv[1] && si[1] && s_np[1] != 3'd0) |
                             (sv[2] && si[2] && s_np[2] != 3'd0) | (sv[3] && si[3] && s_np[3] != 3'd0);
    wire can_issue = sv[ist] && sr[ist] && !si[ist] && ist_st == I_IDLE &&
                     ((PQ != 0 && s_np[ist] == 3'd0 && !inflight_mtp) ? 1'b1 : (!inflight && !sm_run));
    wire can_go = ist_st == I_CFG && cfg_ok && !sm_run && ((PQ != 0) ? (gap_ok && guard_ok) : 1'b1);
    // ------------------------------------------------------------------ beat assembly, stage 1 (registered indices)
    reg         p1_xs_v, p1_xb_v, p1_go, p1_gobf, p1_cfg;
    reg [7:0]   p1_p;
    reg [2:0]   p1_b, p1_pos, p1_np;
    reg [1:0]   p1_sv, p1_tag;
    reg [3:0]   p1_bsv;
    reg [31:0]  p1_u;
    reg [PHW-1:0] p1_ph;
    // replicated read indices: kept copies (ot_v41_kreg, never merged by synthesis), 8 for the qb read (one per 32-bit
    // slice of each half) and 8 per byte lane for the bb read (one per pair of 16-bit lanes)
    wire [127:0] p1_i0, p1_i1;             // qb read index per 32-bit slice
    wire [7:0]   p1_g0, p1_g1;             // sv[0] / sv[1] gates per slice
    wire [32*9-1:0] p1_hi;                 // bb read row per (byte lane, lane pair)
    wire [32*3-1:0] p1_bb;                 // bb read sub-index per (byte lane, lane pair)
    wire [31:0]  p1_bg;                    // byte-lane gate per (byte lane, lane pair)
    genvar gc;
    generate for (gc = 0; gc < 8; gc = gc + 1) begin : g_ixq
        ot_v41_kreg #(.W(34)) u_ix (.clk(clk), .arst_n(rst_n), .d({h_b0, h_b1, hw[13], hw[12]}),
                                   .q({p1_i0[16*gc +: 16], p1_i1[16*gc +: 16], p1_g1[gc], p1_g0[gc]}));
    end
    for (gc = 0; gc < 32; gc = gc + 1) begin : g_ixb
        ot_v41_kreg #(.W(13)) u_ix (.clk(clk), .arst_n(rst_n), .d({h_hi[9*(gc / 8) +: 9], hw[3:1], hw[4 + gc / 8]}),
                                   .q({p1_hi[9*gc +: 9], p1_bb[3*gc +: 3], p1_bg[gc]}));
    end endgenerate
    // stage 2: the broadcast registers
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p;
    reg [2:0]   bt_b;
    reg [1:0]   bt_sv;
    reg [255:0] bt_q0, bt_q1;
    reg [9:0]   bt_e0, bt_e1;
    reg [3:0]   bt_bsv;
    reg [31:0]  bt_u;
    // v11: the BF16 read is two stages (v9 R = 128: g_ixb copy -> bb read mux -> bt_d was an SS class, -17.6 ps): stage
    // 2 reads, per 16-bit lane, the 8 words of the lane's row (selected by the row index p1_hi) into bra; stage 3 selects
    // one by the sub-index (kept copies g_ixc of p1_bb / p1_bg) into bt_d.  Every other broadcast field passes one
    // register (bc_hr) so the broadcast stays aligned: +1 cycle on the broadcast.  bb is read at the same cycle as before.
    reg [127:0] bra [0:63];
    reg [1023:0] bt_d;
    reg         bt_go, bt_gobf, bt_cfg;
    reg [1:0]   bt_tag;
    reg [2:0]   bt_np, bt_pos;
    reg [PHW-1:0] bt_ph;
    integer kl, ku, kc, kj;
    wire [32*3-1:0] p2_bb;                 // stage-3 copies of p1_bb / p1_bg (kept: identical per byte lane)
    wire [31:0]     p2_bg;
    generate for (gc = 0; gc < 32; gc = gc + 1) begin : g_ixc
        ot_v41_kreg #(.W(4)) u_ix (.clk(clk), .arst_n(rst_n), .d({p1_bb[3*gc +: 3], p1_bg[gc]}),
                                  .q({p2_bb[3*gc +: 3], p2_bg[gc]}));
    end endgenerate
    always @(posedge clk) begin
        p1_p <= hw[8:1]; p1_b <= h_fam ? hw[3:1] : hw[11:9]; p1_sv <= hw[13:12]; p1_pos <= h_pos;
        p1_bsv <= hw[7:4]; p1_u <= hw[39:8];
        // stage 2
        bt_p <= p1_p; bt_b <= p1_b; bt_sv <= p1_sv; bt_pos <= p1_pos; bt_bsv <= p1_bsv; bt_u <= p1_u;
        for (kc = 0; kc < 8; kc = kc + 1) begin
            bt_q0[32*kc +: 32] <= p1_g0[kc] ? qb[p1_i0[16*kc +: 16]][32*kc +: 32] : 32'd0;
            bt_q1[32*kc +: 32] <= p1_g1[kc] ? qb[p1_i1[16*kc +: 16]][32*kc +: 32] : 32'd0;
        end
        bt_e0 <= p1_g0[0] ? eb[p1_i0[15:0]] : 10'd0;
        bt_e1 <= p1_g1[0] ? eb[p1_i1[15:0]] : 10'd0;
        for (ku = 0; ku < 4; ku = ku + 1)
            for (kl = 0; kl < 16; kl = kl + 1)
                for (kj = 0; kj < 8; kj = kj + 1)
                    bra[16*ku + kl][16*kj +: 16] <= bb[{p1_hi[9*(8*ku + kl/2) +: 9], 4'(kl), 3'(kj)}];
        // stage 3 of the BF16 read
        for (ku = 0; ku < 4; ku = ku + 1)
            for (kl = 0; kl < 16; kl = kl + 1)
                bt_d[256*ku + 16*kl +: 16] <= p2_bg[8*ku + kl/2] ? bra[16*ku + kl][16*p2_bb[3*(8*ku + kl/2) +: 3] +: 16] : 16'd0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p1_xs_v <= 1'b0; p1_xb_v <= 1'b0; bt_xs_v <= 1'b0; bt_xb_v <= 1'b0;
            bt_go <= 1'b0; bt_gobf <= 1'b0; bt_cfg <= 1'b0; bt_tag <= 2'd0; bt_ph <= '0; bt_np <= 3'd0;
        end else begin
            p1_xs_v <= s_adv && hw[0] && !h_fam;
            p1_xb_v <= s_adv && hw[0] && h_fam;
            bt_xs_v <= p1_xs_v; bt_xb_v <= p1_xb_v;
            bt_go <= p1_go; bt_gobf <= p1_gobf; bt_cfg <= p1_cfg; bt_tag <= p1_tag; bt_ph <= p1_ph; bt_np <= p1_np;
        end
    end
    // ------------------------------------------------------------------ broadcast wire stages
    wire [BW-1025:0] bc_h = {bt_cfg, bt_ph, bt_np, bt_go, bt_gobf, bt_tag, bt_xs_v, bt_p, bt_b, bt_sv, bt_q0, bt_e0, bt_q1,
                             bt_e1, bt_pos, bt_pos, bt_xb_v, bt_b, bt_bsv, bt_u};
    reg  [BW-1025:0] bc_hr;                // v11: the non-BF16 fields wait one cycle for the two-stage BF16 read
    always @(posedge clk or negedge rst_n) if (!rst_n) bc_hr <= '0; else bc_hr <= bc_h;
    wire [BW-1:0] bc_in = {bc_hr, bt_d};
    wire [BW-1:0] bc;
    generate if (BST + RPT > 0) begin : g_bst
        ot_hdc_delay #(.W(BW), .D(BST + RPT), .RESET(1)) u_bst (.clk(clk), .rst_n(rst_n), .d(bc_in), .q(bc));
    end else begin : g_nobst
        assign bc = bc_in;
    end endgenerate
    assign {f_cfg_go, f_cfg_ph, f_cfg_np, f_go, f_go_bf, f_go_tag, f_xs_v, f_xs_p, f_xs_b, f_xs_sv, f_xs_q0, f_xs_e0,
            f_xs_q1, f_xs_e1, f_xs_pos, f_xb_pos, f_xb_v, f_xb_b, f_xb_sv, f_xb_u, f_xb_d} = bc;
    assign f_bus = bc;

    // ------------------------------------------------------------------ return: stage 0 (registered root inputs)
    reg [R-1:0]    q0_v, q0_e;
    reg [14*R-1:0] q0_row;
    reg [16*R-1:0] q0_bf;
    reg [3*R-1:0]  q0_pos;
    reg [32*R-1:0] q0_f32;
    // v9: RPT registered repeater stages in front of stage 0 (the root inputs cross the die-scale return wires)
    wire [R-1:0]   p_v, p_e;
    wire [16*R-1:0] p_row, p_bf;
    wire [3*R-1:0] p_pos;
    wire [32*R-1:0] p_f32;
    ot_hdc_delay #(.W(R), .D(RPT), .RESET(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(r_v), .q(p_v));
    ot_hdc_delay #(.W(R + 16*R + 16*R + 3*R + 32*R), .D(RPT)) u_prd (.clk(clk), .rst_n(rst_n),
        .d({r_e, r_row, r_bf16, r_pos, r_fp32}), .q({p_e, p_row, p_bf, p_pos, p_f32}));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q0_v <= {R{1'b0}};
        else q0_v <= p_v;
    integer kr0;
    always @(posedge clk) begin
        q0_e <= p_e; q0_bf <= p_bf; q0_pos <= p_pos; q0_f32 <= p_f32;
        for (kr0 = 0; kr0 < R; kr0 = kr0 + 1) q0_row[14*kr0 +: 14] <= p_row[16*kr0 +: 14];
    end
    // per-group replicas of the per-tag return configuration (one-cycle copies of the masters, kept)
    // per tag: {ob, 7 ops, 5 ops, 3 ops, ops, rs, pw63, pw62, fmt == 0, fmt == 1} (CFW bits)
    localparam integer CFW = 5 * VAW + 18;
    localparam integer GRW = 4 * CFW + 4 + 2;               // one group's replica word (+ the issued op's tag)
    wire [GRW-1:0] g_md;                                    // the masters, packed
    genvar gt, gg;
    generate for (gt = 0; gt < 4; gt = gt + 1) begin : g_mt
        wire [VAW-1:0] o1 = s_ops[gt];
        wire [VAW-1:0] o3, o5, o7;
        ot_v41_ksadd #(.W(VAW)) u_o3 (.a(o1), .b({o1[VAW-2:0], 1'b0}), .cin(1'b0), .s(o3), .cout());
        ot_v41_ksadd #(.W(VAW)) u_o5 (.a(o1), .b({o1[VAW-3:0], 2'b0}), .cin(1'b0), .s(o5), .cout());
        ot_v41_ksadd #(.W(VAW)) u_o7 (.a({o1[VAW-4:0], 3'b0}), .b(~o1), .cin(1'b1), .s(o7), .cout());
        assign g_md[CFW*gt +: CFW] = {s_ob[gt], o7, o5, o3, o1, s_rs[gt][13:0],
                                      s_pw[gt][63], s_pw[gt][62], s_fm[gt] == 2'd0, s_fm[gt] == 2'd1};
        assign g_md[4*CFW + gt] = sv[gt] && si[gt];
    end endgenerate
    assign g_md[4*CFW + 4 +: 2] = iss_tag;
    // v11: the masters (slot registers -> stride adders -> packing) are registered once at the spine before the group
    // replicas, so the replicas' D is a wire from one register (v9 R = 128: s_ops -> o3/o5/o7 -> 16 replicas across
    // the die was an SS class, -21.1 ps; +1 cycle on the configuration's way to the return stage)
    reg  [GRW-1:0]     g_mdr;
    always @(posedge clk) g_mdr <= g_md;
    wire [NGR*GRW-1:0] g_rep;                               // per region group, kept copies (ot_v41_kreg)
    generate for (gg = 0; gg < NGR; gg = gg + 1) begin : g_grp
        ot_v41_kreg #(.W(GRW)) u_rep (.clk(clk), .arst_n(rst_n), .d(g_mdr), .q(g_rep[GRW*gg +: GRW]));
    end endgenerate
    // stages 1 and 2, region-local: the row's op tag registered as kept one-hot copies (0: base, 1: 1/3 x stride,
    // 2: 5/7 x stride, 3: rsplit / format / live (valid-gated), 4: row count (valid-gated))
    reg [R-1:0]     w_we_r;
    reg [R*VAW-1:0] w_addr_r;
    reg [R*32-1:0]  w_data_r;
    reg [R-1:0]     q1_v, q1_f;
    reg [R*VAW-1:0] q1_a, q1_p;
    reg [R*32-1:0]  q1_f32;
    reg [R*16-1:0]  q1_bf;
    wire [4*R-1:0]  oh_cnt;                                 // copy 4 of every region (row counts)
    genvar gk;
    generate for (gk = 0; gk < R; gk = gk + 1) begin : g_reg
        // PQ = 1: the row's own op tag (row bits [15:14], set by the PQ elements); PQ = 0: the elements return no
        // tag (one op in flight), so the row belongs to the op issued last (registered group copy)
        wire [GRW-1:0] rep = g_rep[GRW*(gk / RG) +: GRW];
        wire [1:0] rtag = (PQ != 0) ? p_row[16*gk + 14 +: 2] : rep[4*CFW + 4 +: 2];
        wire [3:0] ohd = 4'b0001 << rtag;
        wire [19:0] oh;
        ot_v41_kreg #(.W(4)) u_oh0 (.clk(clk), .arst_n(rst_n), .d(ohd), .q(oh[3:0]));
        ot_v41_kreg #(.W(4)) u_oh1 (.clk(clk), .arst_n(rst_n), .d(ohd), .q(oh[7:4]));
        ot_v41_kreg #(.W(4)) u_oh2 (.clk(clk), .arst_n(rst_n), .d(ohd), .q(oh[11:8]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh3 (.clk(clk), .arst_n(rst_n), .d(ohd & {4{p_v[gk]}}), .q(oh[15:12]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh4 (.clk(clk), .arst_n(rst_n), .d(ohd & {4{p_v[gk]}}), .q(oh[19:16]));
        assign oh_cnt[4*gk +: 4] = oh[19:16];
        // stage 0 also selects the op's rsplit and format bits (by the decoded input tag) and registers them
        // (a kept register per region: at PQ = 0 every region of a group selects the same tag, and merged flops would
        // drive the whole group's comparators across the die)
        reg  [17:0]   rsfm_d;
        wire [13:0]   rs_m;
        wire [3:0]    fm_m;
        integer t0, t2;
        always @* begin
            rsfm_d = '0;
            for (t0 = 0; t0 < 4; t0 = t0 + 1) rsfm_d = rsfm_d | (rep[CFW*t0 +: 18] & {18{ohd[t0]}});
        end
        ot_v41_kreg #(.W(18)) u_rsfm (.clk(clk), .arst_n(rst_n), .d(rsfm_d), .q({rs_m, fm_m}));
        // one-hot selects of the row's op configuration
        reg [VAW-1:0] ob_m, o1_m, o3_m, o5_m, o7_m;
        reg           live_m;
        integer t;
        always @* begin
            ob_m = '0; o1_m = '0; o3_m = '0; o5_m = '0; o7_m = '0; live_m = 1'b0;
            for (t = 0; t < 4; t = t + 1) begin
                ob_m = ob_m | (rep[CFW*t + 4*VAW + 18 +: VAW] & {VAW{oh[t]}});
                o7_m = o7_m | (rep[CFW*t + 3*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o5_m = o5_m | (rep[CFW*t + 2*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o3_m = o3_m | (rep[CFW*t + VAW + 18 +: VAW] & {VAW{oh[4 + t]}});
                o1_m = o1_m | (rep[CFW*t + 18 +: VAW] & {VAW{oh[4 + t]}});
                live_m = live_m | (rep[4*CFW + t] & oh[12 + t]);
            end
        end
        wire [VAW-1:0] a_s;
        wire           row_ge;                              // row >= rsplit
        ot_v41_ksadd #(.W(VAW)) u_a (.a(ob_m), .b(VAW'(q0_row[14*gk +: 14])), .cin(1'b0), .s(a_s), .cout());
        ot_v41_ksadd #(.W(14)) u_rs (.a(q0_row[14*gk +: 14]), .b(~rs_m), .cin(1'b1), .s(), .cout(row_ge));
        always @(posedge clk) begin
            q1_a[VAW*gk +: VAW] <= a_s;
            case (q0_pos[3*gk +: 3])                        // pos * ops (mod 2^VAW)
                3'd0: q1_p[VAW*gk +: VAW] <= '0;
                3'd1: q1_p[VAW*gk +: VAW] <= o1_m;
                3'd2: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-2:0], 1'b0};
                3'd3: q1_p[VAW*gk +: VAW] <= o3_m;
                3'd4: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-3:0], 2'b0};
                3'd5: q1_p[VAW*gk +: VAW] <= o5_m;
                3'd6: q1_p[VAW*gk +: VAW] <= {o3_m[VAW-2:0], 1'b0};
                default: q1_p[VAW*gk +: VAW] <= o7_m;
            endcase
            q1_f32[32*gk +: 32] <= q0_f32[32*gk +: 32];
            q1_bf[16*gk +: 16] <= q0_bf[16*gk +: 16];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin q1_v[gk] <= 1'b0; q1_f[gk] <= 1'b0; end
            else begin
                q1_v[gk] <= q0_v[gk];
                q1_f[gk] <= q0_v[gk] && (q0_e[gk] || !live_m);
            end
        // stage 1 also registers the fp32-row select locally (pinned rule)
        // v9: row_ge and the format bits are registered; the select is formed in front of the kept g_sel copies
        // (v8: q0_row -> row >= rsplit -> select -> q1_s was an SS class at R = 128)
        // v12: the select's two outcomes (row >= rsplit: fm0 | fm1 & fm3, else fm0 | fm1 & fm2) are formed before stage
        // 1 and registered with row_ge in four kept copies, one per g_sel lane; the lane's select is one mux in front of
        // its u_s (v11 R = 128: one q1_ge flop -> select -> four g_sel copies across the byte lanes was the only routed
        // baseline SS class, -72 ps post-CTS).  Same function and latency as v11.
        wire       s_hi = fm_m[0] || (fm_m[1] && fm_m[3]);
        wire       s_lo = fm_m[0] || (fm_m[1] && fm_m[2]);
        // stage 2: the address add; the select in four kept copies (one per byte of the word), the data forwarded
        wire [VAW-1:0] w_s;
        ot_v41_ksadd #(.W(VAW)) u_w (.a(q1_a[VAW*gk +: VAW]), .b(q1_p[VAW*gk +: VAW]), .cin(1'b0), .s(w_s), .cout());
        wire [3:0] q2_sel;
        genvar gsl;
        for (gsl = 0; gsl < 4; gsl = gsl + 1) begin : g_sel
            wire [2:0] q1_g;                                // {row_ge, select if ge, select if not}
            ot_v41_kreg #(.W(3)) u_g (.clk(clk), .arst_n(rst_n), .d({row_ge, s_hi, s_lo}), .q(q1_g));
            ot_v41_kreg #(.W(1)) u_s (.clk(clk), .arst_n(rst_n), .d(q1_g[2] ? q1_g[1] : q1_g[0]), .q(q2_sel[gsl]));
        end
        reg [VAW-1:0] q2_a;
        reg [31:0]    q2_f32;
        reg [15:0]    q2_bf;
        always @(posedge clk) begin
            q2_a <= w_s; q2_f32 <= q1_f32[32*gk +: 32]; q2_bf <= q1_bf[16*gk +: 16];
        end
        // stage 3: write
        always @(posedge clk) begin
            w_addr_r[VAW*gk +: VAW] <= q2_a;
            for (t2 = 0; t2 < 4; t2 = t2 + 1)
                w_data_r[32*gk + 8*t2 +: 8] <= q2_sel[t2] ? q2_f32[8*t2 +: 8] : ((t2 < 2) ? 8'd0 : q2_bf[8*(t2-2) +: 8]);
        end
    end endgenerate
    integer kg, kt, kr, kq;
    // v9: RPT registered repeater stages on the row-write outputs
    ot_hdc_delay #(.W(R), .D(RPT), .RESET(1)) u_pwv (.clk(clk), .rst_n(rst_n), .d(w_we_r), .q(w_we));
    ot_hdc_delay #(.W(R*VAW + R*32), .D(RPT)) u_pwd (.clk(clk), .rst_n(rst_n), .d({w_addr_r, w_data_r}),
                                                     .q({w_addr, w_data}));
    reg [NGR-1:0] q2_f;
    reg [R-1:0]   q2_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin w_we_r <= {R{1'b0}}; q2_v <= {R{1'b0}}; q2_f <= {NGR{1'b0}}; end
        else begin
            q2_v <= q1_v; w_we_r <= q2_v;
            for (kg = 0; kg < NGR; kg = kg + 1) begin
                q2_f[kg] <= 1'b0;
                for (kr = 0; kr < RG; kr = kr + 1) if (RG * kg + kr < R && q1_f[RG * kg + kr]) q2_f[kg] <= 1'b1;
            end
        end

    // ------------------------------------------------------------------ row counts from the registered root tags
    // stage A: per group of 8 regions and per tag, a popcount; stage B: groups of four summed; stage C: total
    localparam integer NCA = (R + 7) / 8;
    localparam integer NCB = (NCA + 3) / 4;
    reg [3:0] ga [0:NCA-1][0:3];
    reg [7:0] gb [0:NCB-1][0:3];
    reg [7:0] rc [0:3];
    reg [7:0] gm;
    reg [7:0] racc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (kt = 0; kt < 4; kt = kt + 1) begin
                rc[kt] <= 8'd0;
                for (kg = 0; kg < NCA; kg = kg + 1) ga[kg][kt] <= 4'd0;
                for (kq = 0; kq < NCB; kq = kq + 1) gb[kq][kt] <= 8'd0;
            end
        end else begin
            for (kg = 0; kg < NCA; kg = kg + 1)
                for (kt = 0; kt < 4; kt = kt + 1) begin
                    gm = 8'd0;
                    for (kr = 0; kr < 8; kr = kr + 1)
                        if (8 * kg + kr < R) gm[kr] = oh_cnt[4 * (8 * kg + kr) + kt];
                    ga[kg][kt] <= 4'($countones(gm));
                end
            for (kt = 0; kt < 4; kt = kt + 1) begin
                for (kq = 0; kq < NCB; kq = kq + 1) begin
                    racc = 8'd0;
                    for (kg = 4 * kq; kg < 4 * kq + 4; kg = kg + 1) if (kg < NCA) racc = racc + 8'(ga[kg][kt]);
                    gb[kq][kt] <= racc;
                end
                racc = 8'd0;
                for (kq = 0; kq < NCB; kq = kq + 1) racc = racc + gb[kq][kt];
                rc[kt] <= racc;
            end
        end
    end
    // ------------------------------------------------------------------ control
    integer ks;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ld_more <= 1'b0; p1_np <= 3'd0;
            fault <= 1'b0; tm_bad <= 1'b0; st_end <= 1'b0; st_tag <= 2'd0; clr_q <= 2'b00; p1_go <= 1'b0; p1_gobf <= 1'b0; p1_cfg <= 1'b0; p1_tag <= 2'd0; p1_ph <= '0;
            ld_run <= 1'b0; rq_v <= 1'b0; sm_run <= 1'b0; sm_arm <= 1'b0; sm_tag <= 2'd0; x_re <= 1'b0;
            have[0] <= 15'd0; have[1] <= 15'd0; phase_cycles <= 32'd0; cyc <= 32'd0;
            acc <= 2'd0; ldt <= 2'd0; ist <= 2'd0; rdt <= 2'd0; iss_tag <= 2'd0; ist_st <= I_IDLE;
            t_gap <= '0; t_g1 <= '0; t_g2 <= '0; gap_ok <= 1'b1; guard_ok <= 1'b1;
            cfg_rem <= 6'd0; cfg_ok <= 1'b0;
            bufbusy[0] <= 1'b0; bufbusy[1] <= 1'b0; ev_go <= 1'b0; ev_end <= 1'b0; ev_tag <= 2'd0;
            a_v <= 1'b0; a_v2 <= 1'b0; bw_v <= 1'b0; ba_v <= 1'b0;
            rd_run <= 1'b0; cred <= 4'(FD); r0_v <= 1'b0; ra_v <= 1'b0; r1_v <= 1'b0; r2_v <= 1'b0; r3_v <= 1'b0;
            qrp <= 3'd0; qwp <= 3'd0; qcnt <= 4'd0; hv <= 1'b0;
            for (ks = 0; ks < 4; ks = ks + 1) begin
                sv[ks] <= 1'b0; sr[ks] <= 1'b0; s_rd[ks] <= 1'b0; si[ks] <= 1'b0; sd[ks] <= 1'b0; s_rl[ks] <= 19'd0;
            end
        end else begin
            p1_go <= 1'b0; p1_gobf <= 1'b0; p1_cfg <= 1'b0; ev_go <= 1'b0; ev_end <= 1'b0;
            cyc <= any_v ? cyc + 32'd1 : 32'd0;
            tm_bad <= s_adv && c_tag != sm_tag;
            if (f_fault || (|aq_f) || (|q2_f) || tm_bad) fault <= 1'b1;
            // accept: slot claimed now, phase word one cycle later
            a_v <= 1'b0;
            if (go && !sv[acc]) begin
                sv[acc] <= 1'b1; sr[acc] <= 1'b0; s_rd[acc] <= 1'b0; si[acc] <= 1'b0; sd[acc] <= 1'b0;
                a_v <= 1'b1; a_tag <= acc; a_ph <= i_ph;
                acc <= acc + 2'd1;
            end
            a_v2 <= a_v; a_tag2 <= a_tag;
            if (a_v2) begin
                s_pw[a_tag2] <= ph_q0; s_rs[a_tag2] <= ph_q1[15:0]; sr[a_tag2] <= 1'b1;
            end
            for (ks = 0; ks < 4; ks = ks + 1) begin       // rows * (np + 1), np + 1 in 1..8
                s_tm0[ks] <= ({3'd0, s_pw[ks][61:46]} & {19{s_np1[ks][0]}}) + ({2'd0, s_pw[ks][61:46], 1'b0} & {19{s_np1[ks][1]}});
                s_tm1[ks] <= ({1'd0, s_pw[ks][61:46], 2'b0} & {19{s_np1[ks][2]}}) + ({s_pw[ks][61:46], 3'b0} & {19{s_np1[ks][3]}});
                s_tot[ks] <= s_tm0[ks] + s_tm1[ks];
            end
            // issue: configuration, then go
            case (ist_st)
                I_IDLE: if (can_issue) begin
                    p1_cfg <= 1'b1; p1_ph <= s_ph[ist]; p1_np <= s_np[ist]; ist_st <= I_CFG;
                    cfg_rem <= CFG_WAIT; cfg_ok <= 1'b0;
                    si[ist] <= 1'b1; iss_tag <= ist;
                end
                I_CFG: begin
                    if (cfg_rem != 6'd0) cfg_rem <= cfg_rem - 6'd1;
                    cfg_ok <= cfg_rem <= 6'd1;
                    if (can_go) begin
                        p1_go <= 1'b1; p1_gobf <= s_pw[ist][0]; p1_tag <= ist; ist_st <= I_IDLE;
                        ev_go <= 1'b1; ev_tag <= ist;
                        sm_run <= 1'b1; sm_arm <= 1'b0; sm_tag <= ist;
                        ist <= ist + 2'd1;
                    end
                end
                default: ist_st <= I_IDLE;
            endcase
            // loader: (op, position) into buffer tag[0] ^ position[0] once that buffer's previous user has sent its
            // last beat
            x_re <= 1'b0; rq_v <= x_re; rq_k <= is_k; rq_par <= is_par; rq_fam <= is_fam;
            if (!ld_run && !ld_more && sv[ldt] && sr[ldt] && !bufbusy[ldt[0]]) begin
                ld_run <= 1'b1; ld_tag <= ldt; ld_pos <= 3'd0; ld_k <= 14'd0; ld_kk <= {1'b0, s_pw[ldt][13:1]};
                ld_fam <= s_pw[ldt][0]; ld_more <= s_np[ldt] != 3'd0;
                ld_pb <= s_xb[ldt]; ld_ptr <= s_xb[ldt]; ld_xps <= s_xps[ldt];
                bufbusy[ldt[0]] <= 1'b1;
                ldt <= ldt + 2'd1;
            end else if (!ld_run && ld_more && !bufbusy[ld_tag[0] ^ ~ld_pos[0]]) begin
                ld_run <= 1'b1; ld_pos <= ld_pos + 3'd1; ld_k <= 14'd0; ld_more <= ld_pos + 3'd1 != s_np[ld_tag];
                ld_pb <= ld_pbn; ld_ptr <= ld_pbn;
                bufbusy[ld_tag[0] ^ ~ld_pos[0]] <= 1'b1;
            end else if (ld_run) begin
                x_re <= 1'b1; is_k <= ld_k; is_par <= ld_tag[0] ^ ld_pos[0]; is_fam <= ld_fam;
                x_addr <= ld_ptr; ld_ptr <= ld_ptrn;
                if (ld_end) ld_run <= 1'b0;
                else ld_k <= ld_kn;
            end
            ba_v <= rq_v && rq_fam; ba_par <= rq_par; ba_k <= rq_k;
            bw_v <= ba_v; bw_par <= ba_par; bw_k <= ba_k;
            have[0] <= have_n[0]; have[1] <= have_n[1];
            clr_q[0] <= (ld_st0 && ldt[0] == 1'b0) || (!ld_st0 && ld_st1 && (ld_tag[0] ^ ~ld_pos[0]) == 1'b0);
            clr_q[1] <= (ld_st0 && ldt[0] == 1'b1) || (!ld_st0 && ld_st1 && (ld_tag[0] ^ ~ld_pos[0]) == 1'b1);
            // stream-ROM reader (op order; a slot's words are read once)
            if (!rd_run && sv[rdt] && sr[rdt] && !s_rd[rdt]) begin
                rd_run <= 1'b1; rd_tag <= rdt; rd_pos <= 3'd0; rd_i <= 16'd0; rd_np <= s_np[rdt];
                rd_nb <= s_pw[rdt][29:14]; rd_sb <= SAW'(s_pw[rdt][45:30]); rd_a <= SAW'(s_pw[rdt][45:30]);
                rd_last <= s_pw[rdt][29:14] == 16'd1; rd_fam <= s_pw[rdt][0];
                s_rd[rdt] <= 1'b1; rdt <= rdt + 2'd1;
            end else if (rd_iss) begin
                if (rd_last) begin
                    rd_i <= 16'd0; rd_a <= rd_sb; rd_last <= rd_nb == 16'd1;
                    if (rd_pos != rd_np) rd_pos <= rd_pos + 3'd1;
                    else rd_run <= 1'b0;
                end else begin
                    rd_i <= rd_i + 16'd1; rd_a <= rd_a + SAW'(1); rd_last <= rd_i + 16'd2 == rd_nb;
                end
            end
            r0_v <= rd_iss; r0_a <= rd_a; r0_lp <= rd_last; r0_lo <= rd_last && rd_pos == rd_np; r0_fam <= rd_fam;
            r0_tag <= rd_tag; r0_pos <= rd_pos;
            ra_v <= r0_v; ra_lp <= r0_lp; ra_lo <= r0_lo; ra_fam <= r0_fam; ra_tag <= r0_tag; ra_pos <= r0_pos;
            r1_v <= ra_v; r1_w <= st_q; r1_lp <= ra_lp; r1_lo <= ra_lo; r1_fam <= ra_fam; r1_tag <= ra_tag;
            r1_pos <= ra_pos;
            // R2: the derived fields registered once more
            r2_v <= r1_v; r2_w <= r1_w; r2_nq <= r1_nq; r2_m01 <= r1_m01; r2_m23 <= r1_m23; r2_spar <= r1_spar;
            r2_lp <= r1_lp; r2_lo <= r1_lo; r2_fam <= r1_fam; r2_tag <= r1_tag; r2_pos <= r1_pos;
            r2_b0 <= r1_blk0; r2_b1 <= r1_blk1;
            for (kc = 0; kc < 4; kc = kc + 1)
                r2_hi[9*kc +: 9] <= (r1_spar ? 9'(KMAX / 128) : 9'd0) + {1'b0, r1_w[8 + 8*kc +: 8]};
            // head / queue: the head takes the queue's oldest entry, else the arriving one (bypass)
            r3_v <= r2_v; r3_w <= r2_w; r3_nq <= r2_nq; r3_umax <= (r2_m23 > r2_m01) ? r2_m23 : r2_m01;
            r3_spar <= r2_spar; r3_lp <= r2_lp; r3_lo <= r2_lo; r3_fam <= r2_fam; r3_tag <= r2_tag; r3_pos <= r2_pos;
            r3_b0 <= r2_b0; r3_b1 <= r2_b1; r3_hi <= r2_hi;
            // head / queue (v9): every arriving entry is written at qwp; a bypass (the head takes the arriving entry
            // of an empty queue) also advances qrp, so the queue's write enable does not depend on the streamer's
            // advance (v8: u_cc -> s_adv -> h_take -> fq enables was an SS class at R = 128)
            he <= he_n; hv <= hv_n;
            if (h_take && (qcnt != 4'd0 || r3_v)) qrp <= qrp + 3'd1;
            if (r3_v) begin fq[qwp] <= r3_e; qwp <= qwp + 3'd1; end
            qcnt <= qcnt + 4'(r3_v) - 4'(h_take && (qcnt != 4'd0 || r3_v));
            cred <= cred - 4'(rd_iss) + 4'(s_adv);
            // go timers (cycles since the last / the previous last beat; identical go cycles).  The stream end is
            // registered (st_end) and the timers are loaded one cycle later with the value they would have had;
            // in the end cycle itself only gap_ok is forced low, so no go can be issued in between.
            st_end <= s_adv && s_lo_c; st_tag <= sm_tag;
            if (st_end) begin
                t_gap <= TW'((GAP > 0) ? GAP - 1 : 0); t_g1 <= TW'((GUARD > 0) ? GUARD - 1 : 0); t_g2 <= t_g1;
                gap_ok <= GAP <= 1; guard_ok <= t_g1 == '0;
                sd[st_tag] <= 1'b1;
                ev_end <= 1'b1; ev_tag <= st_tag;
            end else begin
                if (t_gap != '0) t_gap <= t_gap - TW'(1);
                if (t_g1 != '0) t_g1 <= t_g1 - TW'(1);
                if (t_g2 != '0) t_g2 <= t_g2 - TW'(1);
                gap_ok <= (s_adv && s_lo_c) ? 1'b0 : (t_gap <= TW'(1)); guard_ok <= t_g2 <= TW'(1);
            end
            // streamer
            if (sm_run && !sm_arm) sm_arm <= 1'b1;
            if (s_adv) begin
                if (s_lp_c) bufbusy[c_spar] <= 1'b0;
                if (s_lo_c) sm_run <= 1'b0;
            end
            // rows: counted against their op (loaded at go); retire one cycle after the count reads zero
            for (ks = 0; ks < 4; ks = ks + 1) begin
                if (can_go && ist == 2'(ks)) s_rl[ks] <= s_tot[ks];
                else s_rl[ks] <= s_rl[ks] - 19'(rc[ks]);
                if (sv[ks] && si[ks] && sd[ks] && s_rl[ks] == 19'd0 && !(go && !sv[acc] && acc == 2'(ks))) begin
                    sv[ks] <= 1'b0; si[ks] <= 1'b0; sd[ks] <= 1'b0; sr[ks] <= 1'b0; s_rd[ks] <= 1'b0;
                end
            end
            if (any_v) phase_cycles <= cyc + 32'd1;
        end
    end
    // buffers
    integer kw, kq2;
    always @(posedge clk) begin
        for (kq2 = 0; kq2 < 8; kq2 = kq2 + 1)
            for (kw = 0; kw < NQR; kw = kw + 1) begin
                if (qwe[2*NQR*kq2 + kw]) qb[kw][32*kq2 +: 32] <= aq_q[32*kq2 +: 32];
                else if (qwe[2*NQR*kq2 + NQR + kw]) qb[kw][32*kq2 +: 32] <= aq_q[256 + 32*kq2 +: 32];
            end
        for (kw = 0; kw < NQR; kw = kw + 1) begin
            if (qwe[kw]) eb[kw] <= aq_e[9:0];
            else if (qwe[NQR + kw]) eb[kw] <= aq_e[19:10];
        end
        bw_d <= bw_rn;
        for (kw = 0; kw < VRD; kw = kw + 1)
            for (kq2 = 0; kq2 < NWB; kq2 = kq2 + 1)
                if (bwe[NWB*(NBC*kw/VRD) + kq2]) bb[{WBW'(kq2), VB'(kw)}] <= bw_d[16*kw +: 16];
    end
endmodule
