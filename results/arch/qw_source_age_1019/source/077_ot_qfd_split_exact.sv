`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen ROM core split across die masters WITH pin stations, kept exact (qwen-split-exact 2026-10-07).
//
// The partition (tools/qwen_missing/emit_partition.py: controller = qfd_sp_constants_sequencer, matrix-engine
// spine = qfd_sp_tree_top, stream unit = qfd_sp_su64_sfu) puts DCU registered stations on every controller -> unit
// net and DUC on every unit -> controller net (DCU = sequencer OS + unit IS, DUC = unit OS + sequencer IS).  The
// core was written for zero-cycle crossings.  Crossing classes (results/rtl/qwen_split_exact_20261007/crossings.json):
//
//   A  issue handshake   go + NEXT fields down, ready back.  The base issues on the SAME cycle ready is seen
//                        (su ready is even combinational in the stream unit's i_sfu).  Stationed, a go would land on
//                        a unit that is no longer ready and be dropped.  FIX (ot_qfd_issue_shell, controller side):
//                        after a go the unit is held not-ready for RT = DCU + DUC unit edges, the delayed status is
//                        then post-accept; ready is rebuilt from monotone state (SU: !active, cls, inflight == 0 --
//                        cls is the last issued class, kept here; ME: !active && !pend).  Between a status sample
//                        and the go's arrival no accept can happen (one go in flight per unit), and that state only
//                        moves towards ready, so a go issued on the rebuilt ready is always accepted.
//   B  status / chaining idle, progress, progress_rows: registered, cleared on the accepting edge.  A delayed copy
//                        would show the PREVIOUS op as drained or progressed right after a go.  FIX: masked (idle 0,
//                        progress 0) for the same RT window; after it they are post-accept and, being monotone within
//                        an op, a stale value is conservative (idle: idle since the sample with no go in flight).
//   C  sampled result    am_idx / am_val / am_any, read by the argmax fold ON the go of the next AMAX op.  The base
//                        samples the engine's pre-accept value; stationed, the engine may still fold rows between the
//                        sample and the go's arrival.  FIX: with stations an AMAX op also waits for the engine idle
//                        (delayed, masked), so am_* are frozen from the sample to the accept.  RT = 0: no wait.
//   D  memory read loop  the stream unit's va read goes THROUGH the controller (INT8 embedding decode muxes va_q):
//                        fixed one-edge latency, cannot take stations.  FIX: the decode moves to the stream-unit side
//                        (ot_qfd_su_embed); its per-op selector (a_src) travels with the go, the per-token constants
//                        (token, scale) are stationed like any field (static from the token start).  vb / vc / vm
//                        write and the engine's memory ports never crossed: they are the units' own buses (SU <-> VM
//                        abutted: tools/qwen_rom_fulldie_b3r2.py su_vm_abut).
//   E  clock-enable path me_en (engine ICG enable) gates the engine's VM write enables in the same cycle.  It is
//                        the ICG enable that travels with the gated clock pin po_me_clk: not stationed (a clock-gating
//                        check, like the clock).  The engine-side stations run on the GATED clock (engine time), so a
//                        held engine edge is an exact pause of engine + stations, and the shell counts engine edges.
//   F  posted / sticky   fault, kv_we -> kv_write_flush, wrom observation: delayed is safe (sticky fault; flush is
//                        idle-qualified with the masked idle).
//
// COMP = 0 keeps the stations and drops A-C (the negative bench: must fail).  RT_ME = RT_SU = 0 makes the shell a
// wire-equivalent of the base (the rebuilt SU ready equals the unit's own ready term for term).
// ---------------------------------------------------------------------------
module ot_qfd_issue_shell #(
    parameter integer RT_ME = 0,       // engine edges from a go to post-accept status at the controller (DCU + DUC)
    parameter integer RT_SU = 0,
    parameter integer COMP  = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    // controller issue (the base's same-cycle go) and its view of NEXT
    input  wire        me_go,
    input  wire        su_go,
    input  wire        me_en,          // this edge clocks the engine
    input  wire [2:0]  su_sfu,         // NEXT's stream class (po_su_i_sfu)
    input  wire        me_amax,        // NEXT's AMAX flag (po_me_i_amax)
    // stationed unit status (DUC behind the unit)
    input  wire        d_me_ready, d_me_idle,
    input  wire [15:0] d_me_progress,
    input  wire        d_su_ready, d_su_idle, d_su_active,
    input  wire [7:0]  d_su_inflight,
    input  wire [15:0] d_su_progress, d_su_rows,
    // what the controller sees
    output wire        c_me_ready, c_me_idle,
    output wire [15:0] c_me_progress,
    output wire        c_su_ready, c_su_idle,
    output wire [15:0] c_su_progress, c_su_rows
);
    localparam integer CW = 8;
    reg [CW-1:0] sh_me, sh_su;
    reg [2:0]    cls_c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sh_me <= {CW{1'b0}}; sh_su <= {CW{1'b0}}; cls_c <= 3'd0;
        end else begin
            //: the go edge itself is an engine edge (issue requires me_en); count RT engine edges after it
            if (me_go) sh_me <= RT_ME[CW-1:0];
            else if (sh_me != 0 && me_en) sh_me <= sh_me - 1'b1;
            if (su_go) begin sh_su <= RT_SU[CW-1:0]; cls_c <= su_sfu; end
            else if (sh_su != 0) sh_su <= sh_su - 1'b1;
        end
    end
    wire m_me = (COMP != 0) && (sh_me != 0);
    wire m_su = (COMP != 0) && (sh_su != 0);
    wire am_wait = (COMP != 0) && (RT_ME != 0) && me_amax && !(d_me_idle && !m_me);
    assign c_me_ready    = !m_me && d_me_ready && !am_wait;
    assign c_me_idle     = !m_me && d_me_idle;
    assign c_me_progress = m_me ? 16'd0 : d_me_progress;
    assign c_su_ready    = (COMP != 0) ? (!m_su && !d_su_active && ((su_sfu == cls_c) || (d_su_inflight == 8'd0)))
                                       : d_su_ready;
    assign c_su_idle     = !m_su && d_su_idle;
    assign c_su_progress = m_su ? 16'd0 : d_su_progress;
    assign c_su_rows     = m_su ? 16'd0 : d_su_rows;
endmodule


// INT8 embedding decode on the stream-unit side of the split (class D above): the logic of ot_hdc_core_vector_weight
// g_int8_embed term for term, clocked with the stream unit; go / a_src are the stationed issue, tok / scale the
// stationed per-token constants.
module ot_qfd_su_embed #(
    parameter integer SW = 64,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer HID = 4096,
    parameter integer EMB_CODE_LANES = 64,
    parameter integer EMB_ADDR_BASE = 0,
    parameter integer QWEN_FULLSHAPE = 1,
    parameter integer INT8_EMBED = 1
) (
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       go,
    input  wire                       a_src,
    input  wire [NW-1:0]              tok,
    input  wire [15:0]                scale,
    input  wire [SW-1:0]              su_va_re,
    input  wire [SW*AW-1:0]           su_va_addr,
    output wire [SW*32-1:0]           su_va_q,
    output wire [SW-1:0]              va_re,
    output wire [SW*AW-1:0]           va_addr,
    input  wire [SW*32-1:0]           va_q,
    output wire                       embed_code_re,
    output wire [AW-1:0]              embed_code_addr,
    input  wire [EMB_CODE_LANES*8-1:0] embed_code_q,
    output wire                       fault
);
    localparam integer ELI = $clog2(EMB_CODE_LANES);
    reg embed_active;
    reg [SW-1:0] embed_sel;
    reg [SW*ELI-1:0] embed_lanes;
    wire [SW-1:0] embed_faults;
    assign embed_code_re = (INT8_EMBED != 0) && (|(su_va_re & {SW{embed_active}}));
    assign embed_code_addr = (QWEN_FULLSHAPE != 0) ?
        ((tok * (HID / EMB_CODE_LANES)) +
         (((su_va_addr[0 +: AW] - EMB_ADDR_BASE) & (HID - 1)) /
          EMB_CODE_LANES)) :
        ((su_va_addr[0 +: AW] - EMB_ADDR_BASE) >> $clog2(EMB_CODE_LANES));
    assign va_re = su_va_re & ~({SW{(INT8_EMBED != 0) && embed_active}});
    assign va_addr = su_va_addr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            embed_active <= 1'b0;
            embed_sel <= 0;
        end else begin
            if (go) embed_active <= (INT8_EMBED != 0) && a_src;
            embed_sel <= su_va_re & {SW{(INT8_EMBED != 0) && embed_active}};
        end
    end
    genvar el;
    generate if (INT8_EMBED != 0) begin : g_int8_embed
    for (el = 0; el < SW; el = el + 1) begin : g_embed_decode
        always @(posedge clk) embed_lanes[el*ELI +: ELI] <= su_va_addr[el*AW +: ELI];
        wire [31:0] decoded;
        wire bad;
        ot_hdc_qwen_int8_embed_decode u_decode (
            .code(embed_code_q[8*embed_lanes[el*ELI +: ELI] +: 8]),
            .scale(scale), .value(decoded), .fault(bad));
        assign su_va_q[el*32 +: 32] = embed_sel[el] ? decoded : va_q[el*32 +: 32];
        assign embed_faults[el] = embed_sel[el] && bad;
    end
    end else begin : g_plain_embed
        assign su_va_q = va_q;
        assign embed_faults = 0;
    end endgenerate
    assign fault = |embed_faults;
endmodule
