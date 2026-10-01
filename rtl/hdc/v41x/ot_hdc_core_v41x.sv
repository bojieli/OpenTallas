`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hardwired decode core, DeepSeek-V4.1 configuration: decodes one token of the
// reduced DeepSeek-V4.1-Flash (tools/hdc_program_v41.py, format
// tools/hdc_isa_v41.py).
//
// The adopted configuration dispatches matrix operations to dedicated weight,
// attention and pooled-index engines. It also uses the vector stream unit,
// quantised block-dot unit, streaming select, Engram gather and hyper-
// connection projection unit. The X_* parameters select these engines for
// focused gates; the all-unit design enables them together.
//
// The sequencer fetches an instruction, adds the per-token DYN values, skips it
// when its predicate fails or a count is zero, waits for the units named in
// its `wait` mask to drain (the program generator derives the mask from region
// hazards, so independent units overlap), and issues it when its unit is
// ready.  Every unit is a fixed pipeline that never stalls on its own data.
//
// Memories sit outside the core behind synchronous-read ports.
//
// W_HBM = 1: the quantised (FP8/FP4) weights live in HBM behind the QE weight
// streamer (rtl/hdc/hbm/ot_hdc_qstream.sv), which serves the same qrom port
// from its window.  A LINQ op announces its shape (qd_*) when the sequencer
// reaches it (and it will not be skipped) and issues only once the streamer
// raises q_ok (its start threshold is in the window: the QE never stalls); the
// issue of an instruction marked wrel pulses wrel_v, releasing the fetch of the
// expert-indexed ops whose ids it waited for.
// KV_HBM = 1: an attention-class ME op announces its KV window descriptor
// (kvd_*) and waits for kv_ok before issuing. Index-key ops use the pooled
// indexer's separate HBM path. The prefetcher maps the descriptor to its HBM
// sector layout.
//
// MULTI-TOKEN PREDICTION (NSLOT > 1; tools/hdc_isa_v41.py, tools/hdc_program_v41.py
// build_mtp).  `start` runs the program at `entry` (the image holds the one-
// position STEP program at 0 and the speculative ITER program after it).  The
// core holds NSLOT position slots: slot j at pos + j with token stok[j]
// (ot_hdc_accept; stok[0] = `token`) and its own DYN bank, computed one slot a
// cycle at the start and at a DYN control step; an instruction's dslot picks
// its bank, its predicate position and (EHASH) its token.  Control steps
// (unit 0): TOKX latches the XU's SELECT result as a draft token, AMAX the ME
// argmax (lane ctl_lane) as a verify target, DYN recomputes the banks, ACCEPT
// takes the longest matching prefix a and restores the Engram hash history to
// slot a's snapshot; END reports n_emit = a + 1 tokens ttok[0 .. a] (acc_tok)
// and next_token = ttok[a].  MP > 1: the ME, QE and HE serve up to MP slots per
// weight read (mx_m), and the stream unit is MP copies, copy p running slot p of
// a batched static stream op (every vector-memory stream moved by p slot
// strides); their vector-memory ports widen by MP.
// ---------------------------------------------------------------------------
module ot_hdc_core_v41x #(
    parameter integer FULL_SHAPE = 0,
    parameter integer INSTR_BITS = FULL_SHAPE ? 2048 : 1536,
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer IL   = 8,
    parameter integer BL   = 16,
    parameter integer QLB  = 272,
    parameter integer AW   = FULL_SHAPE ? 30 : 24,
    parameter integer NW   = FULL_SHAPE ? 21 : 16,
    parameter integer PAW  = 14,
    parameter integer DIM  = FULL_SHAPE ? 5120 : 160,
    parameter integer TOPK = FULL_SHAPE ? 512 : 16,
    parameter integer HDIM = FULL_SHAPE ? 512 : 32,
    parameter integer ROPE_PAIR = FULL_SHAPE ? 32 : 2,
    parameter integer FULL_WINDOW = 128,
    parameter integer FULL_SCAN_CAP = 16384,
    parameter integer FULL_TP = 4,
    parameter integer XU_KW = FULL_SHAPE ? 12 : 5,
    parameter integer HNL  = 3,            // HE lanes
    parameter integer SW   = 8,            // stream-unit lanes (elements per cycle)
    parameter integer HS   = 8,            // HE K chunks (hdc_golden_v41.HC_SPLIT)
    parameter integer W_HBM = 0,
    parameter integer KV_HBM = 0,
    parameter integer ME0_HBM = 0,       // selected re-specified ME weight op uses an HBM window
    parameter integer NSLOT = 1,           // position slots (1: the one-position core)
    parameter integer MP    = 1,           // lane multiplier of the ME, QE and HE
    // re-specified units (1) or the as-built unit (0), per unit: the bring-up switches
    parameter integer X_HE  = 1,
    parameter integer X_ME  = 0,           // ME weight ops -> the BF16/FP32 weight engine
    parameter integer X_ME_XBANK = 0,     // banked activation SRAM inside the ME adapter
    parameter integer X_ATT = 0,           // ME KV-sourced attention ops -> the attention engine
    parameter integer X_IDX = 0,           // ME KV-sourced index-key ops -> the indexer engine
    parameter integer PIKH_HAW = FULL_SHAPE ? 30 : 28, // pooled index physical HBM sector address
    parameter integer IDX_SHARDED = 0,      // opt-in paired compact key writer and reader
    parameter integer IDX_MULTIUSER = 0,    // per-user sector base is applied before PC selection
    parameter integer IDX_KEY_SLICE_SECTORS = 0,
    parameter integer IDX_RING = 0,         // opt-in W11 quarter-per-stack ring key layout (X_IDX = 2)
    parameter integer IDX_RING_RSB = 1,
    parameter integer IDX_RING_RTAIL = 0,
    parameter integer X_SEL = 0,           // XU index-score SELECT -> the streaming-filter select
    parameter integer X_EG  = 0,           // XU EGATHER -> the per-bank Engram gather
    parameter integer XSQ   = 4,           // select: quarters
    parameter integer XSW   = 16,          // select: lanes per quarter
    parameter integer X_SU  = 0,           // SU -> the vector unit ot_hdc_v41x_vec
    // SU: ot_hdc_v41x_vec geometry
    parameter integer SUN   = 16,          // light lanes (elements a cycle)
    parameter integer SUM   = 8,           // SFU lanes
    parameter integer SULV  = 7,           // reducer time levels, 1..7 (was 8: silently clamped to 7)
    // SU wire stages (ot_hdc_v41x_vec BCAST_STAGES / RET_STAGES; 0 / 0 = no wire).  The spec die (N 1,024,
    // M 256, W1 hub placement, 0.92 ns, 0.76 ps/um) is SUBCAST 4 (controller at the lane array's centre ->
    // corner lane, 3,458 um) and SURET 5 (farthest lane -> HUB_VM, 3,850 um): results/rtl/w11_su_spec.json
    // wire_stage_derivation
    parameter integer SUBCAST = 0,         // broadcast-tree register stages, controller -> lanes
    parameter integer SURET = 0,           // return register stages, lanes / reducer -> vector memory
    // HE: ot_hdc_v41x_hcp geometry
    parameter integer HHW   = 8,           // HCP lanes per group (8 x HHW FP32 MAC lanes)
    parameter integer HTL   = 9,           // HCP tail levels
    parameter integer HBAW  = 16,          // HCP weight-bank word address
    // ME weight ops: ot_hdc_v41x_wgt_tile KIND 1 geometry
    parameter integer MG    = 8,           // chunk units (8 x MG BF16/FP32 MAC lanes)
    parameter integer MBAW  = FULL_SHAPE ? 18 : 17, // weight-bank word address
    // DISTRIBUTED VM (rtl/chip/ot_v41_vm_dist.sv; spec results/floorplan/v41_vm_dist_spec.json).  1: the vector
    // memory is lane-group banks inside the stream unit's region; the non-SU clients reach it through trees:
    //   X_GATHER_STAGES     the matvec x-gather read: an ME / QE / XU / HE op issues that many cycles later
    //                       (its first x word arrives that much later; the sequencer holds the op)
    //   RET_SCATTER_STAGES  the matvec result scatter: every ME / QE / HE / XU vector-memory write lands that
    //                       many cycles later; the unit counts idle / ready only once its writes have landed
    //   SU_RES_STAGES       the stream unit's reducer results (ot_hdc_v41x_vec RES_STAGES; cr_rseq / idle follow)
    //   SU_EWR_STAGES       the stream unit's element writes into the lane's own group (ot_hdc_v41x_vec RET_STAGES)
    //   VM_DIST_H           option H (results/uarch/w11_vm_options.json): the stream unit decides per op whether it
    //                       needs the residual rotate network (SU_ROT_STAGES each way), the gather network
    //                       (SU_GATH_STAGES) or the per-row scalar fetch (SU_SCAL_STAGES), and holds the op for them
    //                       (ot_hdc_v41x_vec VMD_NG = SUN / 8); 0: the networks are free (the first VM_DIST gate)
    // The collective write tree is the tile's (ot_chip_v41x_tile COLL_WRITE_STAGES).  0: the flat memory,
    // bit- and cycle-identical to the core before VM_DIST.
    parameter integer VM_DIST = 0,
    parameter integer X_GATHER_STAGES = 10,
    parameter integer RET_SCATTER_STAGES = 10,
    parameter integer SU_RES_STAGES = 7,
    parameter integer SU_EWR_STAGES = 1,
    parameter integer VM_DIST_H = 0,
    parameter integer SU_ROT_STAGES = 17,
    parameter integer SU_GATH_STAGES = 18,
    parameter integer SU_SCAL_STAGES = 8,
    // C_ROTATE VM (rtl/chip/ot_v41_vm_crot.sv, root ruling 2026-10-01; needs VM_DIST = 1): the central banked strip
    // with a rotate network between banks and lanes; every SU op pays the strip round trip, no per-op decision.
    //   CR_LEAD  controller -> strip address stages (emit -> the strip's read)
    //   CR_RD    strip -> lane operand stages (bank register, rotate mux stages, wire)
    //   CR_GX    extra stages of a gathered A (the permutation network beyond the rotate)
    //   CR_WR    lane -> strip element-write stages
    //   CR_RES   reducer -> strip result stages
    // The stream unit is then built with BCAST_STAGES = CR_LEAD + CR_RD, RET_STAGES = CR_WR, RES_STAGES = CR_RES,
    // RD_LEAD = CR_LEAD, CROT_GX = CR_GX (SUBCAST / SU_EWR / SU_RES / VM_DIST_H are ignored).  0: as before.
    parameter integer VM_CROT = 0,
    parameter integer CR_LEAD = 1,
    parameter integer CR_RD = 8,
    parameter integer CR_GX = 1,
    parameter integer CR_WR = 8,
    parameter integer CR_RES = 8
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    input  wire [PAW-1:0]    entry,           // program entry (MTP: STEP 0, ITER after it)
    output reg               done,
    output wire [3:0]        acc_n,           // tokens the step emitted (0: no ACCEPT ran)
    output wire [NSLOT*NW-1:0] acc_tok,       // ttok[0 .. acc_n-1] are those tokens
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg  [31:0]       cycles,
    output reg               fault,
    // Engram hash history priming (single-step tests)
    input  wire              prime_v,
    input  wire              prime_first,
    input  wire [11:0]       prime_cid,
    // program ROM
    output reg               prog_re,
    output reg  [PAW-1:0]    prog_addr,
    input  wire [INSTR_BITS-1:0] prog_q,
    // BF16 weight ROM: matrix engine, and the stream unit's embedding port
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [G*W*16-1:0] wrom_q,
    output wire [MP*SW-1:0]  ewrom_re,
    output wire [MP*SW*AW-1:0] ewrom_addr,
    input  wire [MP*SW*G*W*16-1:0] ewrom_q,
    // HE weight ROM (HS x HNL binary32 lanes per word)
    output wire              hrom_re,
    output wire [AW-1:0]     hrom_addr,
    input  wire [HS*HNL*32-1:0] hrom_q,
    // the KV word address where the index keys start (the ME slot's class of a KV-sourced op)
    input  wire [AW-1:0]     cfg_ik_base,
    input  wire [PIKH_HAW-1:0] idx_user_base_sec,
    // the ME weight-tile base shift (tools/hdc_images_v41x.py me_xs)
    input  wire [3:0]        cfg_me_xs,
    // BF16/FP32 weight-tile banks (X_ME): 8 request buses, bank b = 8u + c of chain position c
    output wire [7:0]        mb_re,
    output wire [8*MBAW-1:0] mb_addr,
    input  wire [8*MG*32-1:0] mb_q,
    // vector-unit ports (X_SU): per lane a gather-index read, four operand reads (the source selected by
    // xs_rd_src: 0 vector memory, 1 / 2 constant ROM lo / hi word, 3 the BF16 weight ROM element in
    // bits 31:16), an element write to vector memory and the KV staging port; SUN/8 reducer result writes
    output wire [SUN-1:0]    xs_vi_re,
    output wire [SUN*AW-1:0] xs_vi_addr,
    input  wire [SUN*32-1:0] xs_vi_q,
    output wire [4*SUN-1:0]  xs_rd_re,
    output wire [4*SUN*AW-1:0] xs_rd_addr,
    output wire [8*SUN-1:0]  xs_rd_src,
    input  wire [4*SUN*32-1:0] xs_rd_q,
    output wire [SUN-1:0]    xs_vm_we,
    output wire [SUN*AW-1:0] xs_vm_waddr,
    output wire [SUN*32-1:0] xs_vm_wdata,
    output wire [SUN-1:0]    xs_kv_we,
    output wire [SUN*AW-1:0] xs_kv_waddr,
    output wire [SUN*32-1:0] xs_kv_wdata,
    output wire [SUN/8-1:0]  xs_res_we,
    output wire [SUN/8*AW-1:0] xs_res_addr,
    output wire [SUN/8*32-1:0] xs_res_data,
    // HCP weight banks (X_HE): 8 banks of HHW binary32 lanes, bank k addressed by hb_addr[k]
    output wire [7:0]        hb_re,
    output wire [8*HBAW-1:0] hb_addr,
    input  wire [8*HHW*32-1:0] hb_q,
    // index-key HBM (X_IDX): one stack's 32 pseudo-channel request / response ports (the key stream), and
    // the key records the index-key writer produces (the bench applies them to its HBM model)
    output wire [31:0]       ikh_req_v,
    input  wire [31:0]       ikh_req_rdy,
    output wire [32*28-1:0]  ikh_req_addr,
    output wire [32*4-1:0]   ikh_req_len,
    output wire [32*16-1:0]  ikh_req_tag,
    input  wire [31:0]       ikh_rsp_v,
    output wire [31:0]       ikh_rsp_rdy,
    input  wire [32*16-1:0]  ikh_rsp_tag,
    input  wire [32*4-1:0]   ikh_rsp_beat,
    input  wire [32*256-1:0] ikh_rsp_data,
    output wire              ikw_v,
    output wire [27:0]       ikw_csec,
    output wire [127:0]      ikw_codes,
    output wire [27:0]       ikw_ssec,
    output wire [2:0]        ikw_sslot,
    output wire [7:0]        ikw_scale,
    // X_IDX=2 pooled indexer: four replicated HBM stacks and full K128 key updates
    output wire [127:0]      pikh_req_v,
    input  wire [127:0]      pikh_req_rdy,
    output wire [128*PIKH_HAW-1:0] pikh_req_addr,
    output wire [128*4-1:0] pikh_req_len,
    output wire [128*16-1:0] pikh_req_tag,
    input  wire [127:0]      pikh_rsp_v,
    output wire [127:0]      pikh_rsp_rdy,
    input  wire [128*16-1:0] pikh_rsp_tag,
    input  wire [128*4-1:0] pikh_rsp_beat,
    input  wire [128*256-1:0] pikh_rsp_data,
    output wire              pikw_v,
    input  wire              pikw_rdy,
    output wire [3:0]        pikw_stack_mask,
    output wire [PIKH_HAW-1:0] pikw_csec,
    output wire [511:0]      pikw_codes,
    output wire [PIKH_HAW-1:0] pikw_ssec,
    output wire [2:0]        pikw_sslot,
    output wire [31:0]       pikw_scales,
    // quantised weight ROM, Engram table ROM
    output wire              qrom_re,
    output wire [AW-1:0]     qrom_addr,
    input  wire [BL*QLB-1:0] qrom_q,
    output wire              erom_re,
    output wire [AW-1:0]     erom_addr,
    input  wire [263:0]      erom_q,
    // constant ROM: four stream ports per stream lane and one auxiliary port
    output wire [MP*4*SW-1:0] crom_re,
    output wire [MP*4*SW*AW-1:0] crom_addr,
    input  wire [MP*4*SW*64-1:0] crom_q,
    output wire              xcrom_re,
    output wire [AW-1:0]     xcrom_addr,
    input  wire [63:0]       xcrom_q,
    // KV SRAM
    output wire              kv_re,
    output wire [G*AW-1:0]   kv_raddr,
    input  wire [G*W*32-1:0] kv_q,
    output wire [MP*SW-1:0]  kv_we,
    output wire [MP*SW*AW-1:0] kv_waddr,
    output wire [MP*SW*32-1:0] kv_wdata,
    // Full-shape attention receives stored-format rows from the die service.
    input  wire              att_packed_kv_v,
    output wire              att_packed_kv_ready,
    input  wire [3:0]        att_packed_kv_m,
    input  wire [4*(HDIM/32)*265-1:0] att_packed_kv_w,
    input  wire              att_packed_kv_fault,
    output wire              att_packed_issue,
    output wire              att_packed_idle,
    // Full-shape window QDQ8 writes use an atomic packed block handoff.
    // Selected compressed KV still uses the scalar KV port above.
    output wire              win_blk_v,
    input  wire              win_blk_ready,
    output wire [AW-1:0]     win_blk_kvt_base,
    output wire [NW-1:0]     win_blk_row,      // absolute HBM position
    output wire [NW-1:0]     win_blk_kvt_row,  // local KVT row
    output wire [3:0]        win_blk_idx,
    output wire [AW-1:0]     win_blk_first_elem,
    output wire [255:0]      win_blk_codes,
    output wire [7:0]        win_blk_scale,
    // vector memory
    output wire [MP*G-1:0]   vx_re,           // matrix-engine x reads
    output wire [MP*G*AW-1:0] vx_addr,
    input  wire [MP*G*32-1:0] vx_q,
    output wire [MP*4*SW-1:0] vs_re,          // stream operand reads A..D, per lane (and copy)
    output wire [MP*4*SW*AW-1:0] vs_addr,
    input  wire [MP*4*SW*32-1:0] vs_q,
    output wire [MP*SW-1:0]  vi_re,           // stream gather index, per lane
    output wire [MP*SW*AW-1:0] vi_addr,
    input  wire [MP*SW*32-1:0] vi_q,
    output wire              vq_re,           // QE expert index
    output wire [AW-1:0]     vq_addr,
    input  wire [31:0]       vq_q,
    output wire              vr_re,           // XU element read
    output wire [AW-1:0]     vr_addr,
    input  wire [31:0]       vr_q,
    output wire              wqr_re,          // QE 32-element read
    output wire [AW-1:0]     wqr_addr,
    input  wire [1023:0]     wqr_q,
    output wire [MP*HS-1:0]  vh_re,           // HE x reads, one per K chunk
    output wire [MP*HS*AW-1:0] vh_addr,
    input  wire [MP*HS*32-1:0] vh_q,
    output wire              wxr_re,          // XU 32-element read
    output wire [AW-1:0]     wxr_addr,
    input  wire [1023:0]     wxr_q,
    output wire [XSQ-1:0]    vsl_re,          // X_SEL: the select's score reads, XSW elements per quarter
    output wire [XSQ*AW-1:0] vsl_addr,
    input  wire [XSQ*XSW*32-1:0] vsl_q,
    output wire [MP*G-1:0]   vw_me_we,
    output wire [MP*G*AW-1:0] vw_me_addr,
    output wire [MP*G*W-1:0] vw_me_mask,
    output wire [MP*G*W*32-1:0] vw_me_data,
    output wire [MP*SW-1:0]  vw_su_we,        // stream element writes, per lane
    output wire [MP*SW*AW-1:0] vw_su_addr,
    output wire [MP*SW*32-1:0] vw_su_data,
    output wire [MP*SW-1:0]  vw_rd_we,        // stream reducer writes, per lane
    output wire [MP*SW*AW-1:0] vw_rd_addr,
    output wire [MP*SW*32-1:0] vw_rd_data,
    output wire              vw_xe_we,        // XU element write
    output wire [AW-1:0]     vw_xe_addr,
    output wire [31:0]       vw_xe_data,
    output wire [MP-1:0]     ww_q_we,         // QE masked 32-element write
    output wire [MP*AW-1:0]  ww_q_addr,
    output wire [MP*32-1:0]  ww_q_mask,
    output wire [MP*1024-1:0] ww_q_data,
    output wire [MP-1:0]     ww_h_we,         // HE masked write
    output wire [MP*AW-1:0]  ww_h_addr,
    output wire [MP*32-1:0]  ww_h_mask,
    output wire [MP*1024-1:0] ww_h_data,
    output wire              ww_x_we,         // XU masked 32-element write
    output wire [AW-1:0]     ww_x_addr,
    output wire [31:0]       ww_x_mask,
    output wire [1023:0]     ww_x_data,
    // observation: every matrix-vector result word
    output wire              me_ov,
    output wire [MP*G*AW-1:0] me_oaddr,
    output wire [MP*G*W-1:0] me_omask,
    output wire [MP*G*W*32-1:0] me_odata,
    // per-unit activity (cycle accounting)
    output wire [4:0]        unit_busy,
    output reg  [2:0]        issue_unit,      // unit of the instruction issued this cycle (0: none)
    // Full-shape collective request. The die samples fields on coll_go and
    // keeps coll_busy high until its final destination write is complete.
    output reg               coll_go,
    output reg  [1:0]        coll_op,
    output reg  [AW-1:0]     coll_src, coll_dst, coll_ibase,
    output reg  [NW-1:0]     coll_n,
    output reg  [11:0]       coll_k,
    output reg  [7:0]        coll_seq,
    output reg               coll_rnd,
    input  wire              coll_busy, coll_fault,
    // QE weight-streaming handshake (W_HBM = 1 only)
    output reg               qd_v,            // shape of the LINQ op now waiting to issue
    output wire [AW-1:0]     qd_wbase,
    output wire [7:0]        qd_nb,
    output wire [NW-1:0]     qd_tiles,
    input  wire              q_ok,
    // Optional descriptor for one selected X_ME weight op. The array/die
    // wrapper chooses a bounded interval and asserts m0_select for that op.
    // The selected op waits until its window is complete; other ME ops keep
    // their existing weight-bank path.
    output reg               m0d_v,
    output wire [AW-1:0]     m0d_wbase,
    output wire [NW-1:0]     m0d_nout, m0d_tiles, m0d_k,
    output wire [AW-1:0]     m0d_xjs,
    output wire [1:0]        m0d_split,
    input  wire              m0_select,
    input  wire              m0_ok,
    // Attention KV prefetch handshake (KV_HBM = 1). The index-key engine has
    // its own pooled HBM path and does not use this descriptor.
    output reg               kvd_v,
    output wire [AW-1:0]     kvd_wbase, kvd_ts, kvd_ks, kvd_js,
    output wire [NW-1:0]     kvd_tiles, kvd_k, kvd_nout, kvd_pos,
    output wire [1:0]        kvd_hg,
    output wire              kvd_mmode,
    input  wire              kv_ok,
    // Full-shape read-only RoPE cache: a blocking prefetch before SU RoPE
    // and a release after its last dependent SU instruction.
    output wire              rope_pf_v,
    input  wire              rope_pf_rdy,
    output wire              rope_pf_kind,
    output wire [NW-1:0]     rope_pf_pos,
    input  wire              rope_pf_done,
    output wire              rope_pf_release,
    input  wire              rope_pf_fault,
    output reg               wrel_v           // an instruction marked wrel issued
);
    `include "ot_hdc_isa_v41_profiles.svh"
    localparam integer LG = $clog2(W * G);

    // -- sequencer -----------------------------------------------------------------------------
    localparam [3:0] S_IDLE = 0, S_DYN = 1, S_FETCH = 2, S_WAIT = 3, S_CAP = 4, S_DEC = 5,
                     S_ISSUE = 6, S_GO = 7, S_ACC = 8, S_RST = 9,
                     S_COLL_ARM = 10, S_COLL_WAIT = 11, S_COLL_HALT = 12,
                     S_ROPE_WAIT = 13;
    localparam integer SLW = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    reg [3:0]  st;
    reg [PAW-1:0] pc;
    reg [NW-1:0] tok_r, pos_r;
    localparam integer NDYN = FULL_SHAPE ? 64 : 32;
    reg [AW-1:0] dyn [0:NSLOT*NDYN-1];
    reg [2:0]    ds;                        // DYN bank being computed
    reg [INSTR_BITS-1:0] ir;
    reg        me_go, su_go, qe_go, xu_go, he_go;
    wire       me_ready, me_idle, su_ready, su_idle, qe_ready, qe_idle, xu_ready, xu_idle, he_ready, he_idle;
    wire       me_fault, su_fault, qe_fault, xu_fault, he_fault;
    wire [MP*NW-1:0] am_idx_v;
    wire [MP*32-1:0] am_val_v;
    wire [MP-1:0] am_any_v;
    wire [NW-1:0] am_idx = am_idx_v[NW-1:0];
    wire [31:0] am_val = am_val_v[31:0];
    wire [15:0] me_progress;
    wire win_idle, win_issue_ready, win_cap_ready, win_fault;
    wire [AW-1:0] win_cap_src_base;
    wire win_capture_v;
    wire [AW-1:0] win_capture_addr;
    wire [255:0] win_capture_codes;
    wire [7:0] win_capture_scale;
    wire win_capture_fault;
    // The captured QDQ8 VM row is the provenance for a packed window row.
    // A selected compressed-KV gather has a different source and keeps its
    // scalar write path; it must never be treated as a 528-byte FP8 row.
    wire win_su_match = FULL_SHAPE && KV_HBM && d_unit == 3'd2 &&
                        dst == 2'd3 && a_src == 2'd0 &&
                        su_nout == NW'(1) && su_nin == NW'(512) &&
                        a_base == win_cap_src_base;
    wire win_issue = su_go && win_su_match && win_issue_ready;
    reg win_scalar_suppress;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) win_scalar_suppress <= 1'b0;
        else if (win_issue) win_scalar_suppress <= 1'b1;
        else if (su_idle && !su_go) win_scalar_suppress <= 1'b0;
    end

    //: the instruction's DYN bank (its position slot)
    wire [2:0] c_dslot = (NSLOT > 1) ? ir[O_DSLOT +: W_DSLOT] : 3'd0;
    `define F(name) ir[O_``name +: W_``name]
    `define DY(name) dyn[c_dslot * NDYN + ir[O_``name +: W_``name]]

    reg [2:0]  d_unit;
    reg [2:0]  d_ctl, d_cslot, d_clane;
    reg [4:0]  d_wait;
    reg        d_wrel;
    reg        d_skip;
    // ME
    reg [2:0]    mx_m;
    reg [AW-1:0] mx_xps, mx_ops;
    reg [NW-1:0] xu_tok;
    reg          xu_first;
    reg [2:0]    xu_hslot;
    reg [NW-1:0] me_nout, me_tiles, me_k;
    reg [NW-1:0] me_pos;
    reg          me_wsrc, me_round, me_oen, me_amax, me_mmode, me_fuse;
    reg [AW-1:0] me_wts;
    reg [AW-1:0] me_wbase, me_ts, me_ks, me_js, me_xbase, me_obase, me_xks, me_xjs, me_ots, me_ojs, me_xcs;
    reg [2:0]    me_jsh;
    reg [1:0]    me_split, me_hg;
    reg [AW-1:0] me_ogs;
    // SU
    reg [NW-1:0] su_nout, su_nin, su_chase;
    reg [1:0]    a_src, b_src, c_src, d_src, a_ind, dst, red, m2, e2, su_vec;
    reg [AW-1:0] a_base, a_so, a_si, a_ibase, b_base, b_so, b_si, c_base, c_so, c_si, d_base, d_so, d_si;
    reg [AW-1:0] o_base, o_so, o_si, o_row, r_base, r_so;
    reg [NW-1:0] win_abs_row;
    reg          b_half, c_pair, a_rnd, a_relu, a_min, c_clip, rnd, red_sq, red_whole, red_tree, red_rnd;
    reg [2:0]    m1, qm, ad, sfu, e1;
    reg [31:0]   imm1, imm2, imm3;
    // QE
    reg [1:0]    qe_mode;
    reg          qe_fp4, qe_ind, qe_unrounded;
    reg [AW-1:0] qe_xbase, qe_wbase, qe_ibase, qe_istride, qe_obase;
    reg [7:0]    qe_nb;
    reg [NW-1:0] qe_nout, qe_tiles;
    // XU
    reg [1:0]    xu_op;
    reg [AW-1:0] xu_src, xu_dst;
    reg [NW-1:0] xu_n;
    reg [XU_KW-1:0] xu_k;
    reg          xu_layer;
    reg          xu_bf16;                   // SEL with a dynamic count: an index-score select (BF16 scores)
    // HE
    reg [NW-1:0] he_nout, he_k;
    reg [AW-1:0] he_wbase, he_xbase, he_obase;

    // VM_DIST: a unit whose result writes are still in the scatter tree is neither idle nor ready
    wire pend_me, pend_q, pend_h, pend_x;
    // the units' vector-memory writes as produced (VM_DIST: before the result scatter tree)
    wire [MP-1:0]      u_q_we, u_h_we;
    wire [MP*AW-1:0]   u_q_addr, u_h_addr;
    wire [MP*32-1:0]   u_q_mask, u_h_mask;
    wire [MP*1024-1:0] u_q_data, u_h_data;
    wire               u_xe_we, u_x_we;
    wire [AW-1:0]      u_xe_addr, u_x_addr;
    wire [31:0]        u_xe_data, u_x_mask;
    wire [1023:0]      u_x_data;
    wire unit_ready = (d_unit == 3'd1) ? (me_ready && !pend_me) : (d_unit == 3'd2) ? su_ready :
                      (d_unit == 3'd3) ? (qe_ready && !pend_q) : (d_unit == 3'd4) ? (xu_ready && !pend_x) :
                      (he_ready && !pend_h);
    wire [4:0] idles = {he_idle && !pend_h, xu_idle && !pend_x, qe_idle && !pend_q, su_idle, me_idle && !pend_me};
    // VM_DIST: an op of a unit that reads its operands through the x-gather tree issues X_GATHER_STAGES late
    localparam integer XGS = VM_DIST ? X_GATHER_STAGES : 0;
    reg [7:0] xg_cnt;
    wire xg_unit = (d_unit == 3'd1) || (d_unit == 3'd3) || (d_unit == 3'd4) || (d_unit == 3'd5);
    wire xg_hold = (XGS != 0) && xg_unit && (xg_cnt != 8'(XGS));
    wire [4:0] gos = {he_go, xu_go, qe_go, su_go, me_go};
    //: the wait mask names units whose in-flight work must have drained
    wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0);
    wire rope_ctl_ok = d_cslot < NSLOT && d_clane[2:1] == 2'b00;
    assign rope_pf_v = FULL_SHAPE && st == S_ISSUE && d_unit == 3'd0 &&
                       d_ctl == 3'd5 && waited && rope_ctl_ok;
    assign rope_pf_kind = d_clane[0];
    assign rope_pf_pos = NW'(dyn[d_cslot * NDYN + 4]);
    assign rope_pf_release = FULL_SHAPE && st == S_ISSUE && d_unit == 3'd0 &&
                             d_ctl == 3'd6 && waited && su_idle && rope_ctl_ok;

    // speculative-step registers (ot_hdc_accept): slot tokens, verify targets, ACCEPT
    wire [NSLOT*NW-1:0] stok, ttok;
    wire          acc_done, acc_any;
    wire [SLW-1:0] acc_a;
    wire [SLW:0]  acc_ne;
    wire [NW-1:0] acc_bonus;
    wire [15:0]   xu_sel_first;
    reg           tokx_v, amax_v, acc_v, xu_rst_v;
    reg  [SLW-1:0] c_slot_r;
    reg  [NW-1:0] amax_tok;
    generate
        if (NSLOT > 1) begin : g_acc
            ot_hdc_accept #(.NSLOT(NSLOT), .NW(NW)) u_acc (.clk(clk), .rst_n(rst_n),
                .start_v(start && st == S_IDLE), .start_tok(token),
                .tokx_v(tokx_v), .tokx_slot(c_slot_r), .tokx_tok(xu_sel_first[NW-1:0]),
                .amax_v(amax_v), .amax_slot(c_slot_r), .amax_tok(amax_tok),
                .acc_v(acc_v), .acc_g(c_slot_r), .stok(stok), .ttok(ttok), .acc_done(acc_done),
                .acc_any(acc_any), .acc_a(acc_a), .n_emit(acc_ne), .bonus(acc_bonus));
            assign acc_n = acc_any ? acc_ne : 4'd0;
        end else begin : g_noacc
            assign stok = tok_r; assign ttok = 0; assign acc_done = 1'b0; assign acc_any = 1'b0;
            assign acc_a = 0; assign acc_ne = 0; assign acc_bonus = 0; assign acc_n = 4'd0;
        end
    endgenerate
    assign acc_tok = ttok;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pc <= 0; done <= 1'b0; prog_re <= 1'b0;
            me_go <= 1'b0; su_go <= 1'b0; qe_go <= 1'b0; xu_go <= 1'b0; he_go <= 1'b0;
            coll_go <= 1'b0; cycles <= 0;
            next_token <= 0;
            issue_unit <= 0; ds <= 0;
            tokx_v <= 1'b0; amax_v <= 1'b0; acc_v <= 1'b0; xu_rst_v <= 1'b0;
            xg_cnt <= 8'd0;
        end else begin
            me_go <= 1'b0; su_go <= 1'b0; qe_go <= 1'b0; xu_go <= 1'b0; he_go <= 1'b0;
            coll_go <= 1'b0; prog_re <= 1'b0;
            issue_unit <= 0; wrel_v <= 1'b0;
            tokx_v <= 1'b0; amax_v <= 1'b0; acc_v <= 1'b0; xu_rst_v <= 1'b0;
            if (st != S_IDLE) cycles <= cycles + 1;
            if (FULL_SHAPE && (coll_fault || rope_pf_fault)) st <= S_COLL_HALT;
            else case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; pc <= entry; done <= 1'b0; cycles <= 0; ds <= 0;
                    st <= S_DYN;
                end
                //: one DYN bank a cycle
                S_DYN: begin
                    ds <= ds + 1'b1;
                    if (ds + 1 >= NSLOT) begin ds <= 0; st <= S_FETCH; end
                end
                S_FETCH: begin prog_re <= 1'b1; prog_addr <= pc; st <= S_WAIT; end
                S_WAIT: st <= S_CAP;
                S_CAP: begin ir <= prog_q; st <= S_DEC; end
                // Do not announce a dependent attention prefetch while a
                // packed window row is still being committed to HBM.
                S_DEC: if (!FULL_SHAPE || win_idle ||
                           (win_su_match && win_issue_ready)) st <= S_ISSUE;
                S_ISSUE: begin
                    if (d_unit == 3'd0) begin
                        if (waited) begin
                            c_slot_r <= d_cslot[SLW-1:0];
                            amax_tok <= am_idx_v[d_clane * NW +: NW];
                            case (d_ctl)
                                3'd1: begin tokx_v <= 1'b1; pc <= pc + 1'b1; st <= S_FETCH; end        // TOKX
                                3'd2: begin amax_v <= 1'b1; pc <= pc + 1'b1; st <= S_FETCH; end        // AMAX
                                3'd3: begin pc <= pc + 1'b1; ds <= 0; st <= S_DYN; end                 // DYN
                                3'd4: begin acc_v <= 1'b1; st <= S_ACC; end                          // ACCEPT
                                3'd5: if (FULL_SHAPE) begin
                                    if (!rope_ctl_ok) st <= S_COLL_HALT;
                                    else if (rope_pf_rdy) st <= S_ROPE_WAIT;
                                end else begin
                                    done <= 1'b1; next_token <= acc_any ? acc_bonus : am_idx;
                                    next_val <= am_val; st <= S_IDLE;
                                end
                                3'd6: if (FULL_SHAPE) begin
                                    if (!rope_ctl_ok) st <= S_COLL_HALT;
                                    else if (su_idle) begin pc <= pc + 1'b1; st <= S_FETCH; end
                                end else begin
                                    done <= 1'b1; next_token <= acc_any ? acc_bonus : am_idx;
                                    next_val <= am_val; st <= S_IDLE;
                                end
                                default: begin                                                       // END
                                    done <= 1'b1; next_token <= acc_any ? acc_bonus : am_idx;
                                    next_val <= am_val; st <= S_IDLE;
                                end
                            endcase
                        end
                    end else if (d_skip) begin
                        pc <= pc + 1'b1; st <= S_FETCH;
                    end else if (FULL_SHAPE && d_unit == 3'd6) begin
                        // Dedicated VM port B is exclusive during a collective.
                        // Drain every earlier engine before pulsing the request.
                        if (waited && (&idles) && !coll_busy) begin
                            coll_go <= 1'b1; issue_unit <= d_unit; st <= S_COLL_ARM;
                        end
                    end else if (waited && unit_ready && q_gate && kv_gate && m0_gate &&
                                 (!(FULL_SHAPE && KV_HBM && d_unit == 3'd2 && dst == 2'd3) ||
                                  win_idle || (win_su_match && win_issue_ready)) && xg_hold) begin
                        xg_cnt <= xg_cnt + 8'd1;
                    end else if (waited && unit_ready && q_gate && kv_gate && m0_gate &&
                                 (!(FULL_SHAPE && KV_HBM && d_unit == 3'd2 && dst == 2'd3) ||
                                  win_idle || (win_su_match && win_issue_ready))) begin
                        xg_cnt <= 8'd0;
                        wrel_v <= d_wrel;
                        me_go <= (d_unit == 3'd1); su_go <= (d_unit == 3'd2);
                        qe_go <= (d_unit == 3'd3); xu_go <= (d_unit == 3'd4); he_go <= (d_unit == 3'd5);
                        issue_unit <= d_unit;
                        st <= S_GO;
                    end
                end
                S_GO: begin pc <= pc + 1'b1; st <= S_FETCH; end
                // Busy is registered in the die. Spend one full cycle here so
                // a legal request cannot complete before busy has sampled go.
                S_COLL_ARM: st <= S_COLL_WAIT;
                S_COLL_WAIT: if (!coll_busy) begin pc <= pc + 1'b1; st <= S_FETCH; end
                S_ROPE_WAIT: if (rope_pf_done) begin pc <= pc + 1'b1; st <= S_FETCH; end
                S_COLL_HALT: st <= S_COLL_HALT;
                //: ACCEPT: a is registered; restore the hash history to slot a's snapshot
                S_ACC: if (acc_done) begin xu_rst_v <= 1'b1; st <= S_RST; end
                S_RST: begin pc <= pc + 1'b1; st <= S_FETCH; end
                default: st <= S_IDLE;
            endcase
        end
    end

    // DYN values (tools/hdc_isa_v41.dyn_values): bank ds from (stok[ds], pos + ds),
    // once per step and at a DYN control step
    wire [NW-1:0] b_tok = (NSLOT > 1) ? stok[ds * NW +: NW] : tok_r;
    wire [NW-1:0] b_pos = pos_r + ds;
    wire [NW-1:0] p1 = b_pos + 1'b1;
    wire [NW-1:0] n2 = p1 >> 1;
    wire [NW-1:0] ns1 = (p1 < TOPK) ? p1 : TOPK;
    wire [NW-1:0] ns2 = (n2 < TOPK) ? n2 : TOPK;
    function automatic [AW-1:0] rnds(input [NW-1:0] x);
        rnds = (x == 0) ? 0 : ((x - 1) >> LG) + 1;
    endfunction
    function automatic [AW-1:0] rnd16(input [NW-1:0] x);      // 16-row tiles: head-group KV ops
        rnd16 = (x == 0) ? 0 : ((x - 1) >> $clog2(W)) + 1;
    endfunction
    integer di;
    wire [$clog2(NSLOT*NDYN)-1:0] db = ds * NDYN;
    always @(posedge clk) if (st == S_DYN) begin
        for (di = 0; di < NDYN; di = di + 1) dyn[db + di] <= 0;
        dyn[db + 1] <= b_tok * DIM;
        dyn[db + 2] <= b_pos * ROPE_PAIR;
        dyn[db + 3] <= (b_pos == 0) ? 0 : (b_pos - 1) * ROPE_PAIR;
        dyn[db + 4] <= b_pos;
        dyn[db + 5] <= p1;
        dyn[db + 6] <= n2;
        dyn[db + 7] <= (n2 == 0) ? 0 : n2 - 1;
        dyn[db + 8] <= ns1;
        dyn[db + 9] <= ns2;
        dyn[db + 10] <= p1 + ns1;
        dyn[db + 11] <= p1 + ns2;
        dyn[db + 12] <= rnds(p1);
        dyn[db + 13] <= rnds(n2);
        dyn[db + 14] <= rnds(p1 + ns1);
        dyn[db + 15] <= rnds(p1 + ns2);
        dyn[db + 16] <= b_pos * HDIM;
        dyn[db + 17] <= p1 * HDIM;
        dyn[db + 18] <= b_pos[0] ? 4 : 0;
        dyn[db + 19] <= b_pos[0] ? 64 : 0;
        dyn[db + 20] <= (n2 == 0) ? 0 : (n2 - 1) * HDIM;
        dyn[db + 21] <= rnd16(p1);
        dyn[db + 22] <= rnd16(n2);
        dyn[db + 23] <= rnd16(p1 + ns1);
        dyn[db + 24] <= rnd16(p1 + ns2);
        if (NSLOT > 1) begin
            //: MTP: the compressor slot ring of 8, the pooled pair's base, the Markov row
            dyn[db + 25] <= {b_pos[2:0], 2'b00};
            dyn[db + 26] <= {b_pos[2:1], 7'd0};
            dyn[db + 27] <= b_tok * 32;
        end
        if (FULL_SHAPE) begin
            dyn[db + FDYN_WIN] <= (p1 < FULL_WINDOW) ? p1 : FULL_WINDOW;
            dyn[db + FDYN_NC1] <= p1;
            dyn[db + FDYN_NC2] <= n2;
            dyn[db + FDYN_NS1] <= ns1;
            dyn[db + FDYN_NS2] <= ns2;
            dyn[db + FDYN_T0] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW);
            dyn[db + FDYN_T1] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns1;
            dyn[db + FDYN_T2] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns2;
            dyn[db + FDYN_SC1] <= (p1 + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_SC2] <= (n2 + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_SCR] <= (((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_NSL1] <= (((p1 + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((p1 + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_NSL2] <= (((n2 + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((n2 + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_NSLR] <= (((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_CEIL_SC1_16] <= (((p1 + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_SC1_8] <= (((p1 + FULL_TP - 1) / FULL_TP) + 7) >> 3;
            dyn[db + FDYN_CEIL_SC2_16] <= (((n2 + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_SCR_16] <= (((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_T0_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + 31) >> 5;
            dyn[db + FDYN_CEIL_T1_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns1 + 31) >> 5;
            dyn[db + FDYN_CEIL_T2_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns2 + 31) >> 5;
            dyn[db + FDYN_WINM1] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) - 1;
            dyn[db + FDYN_WIN_ROW] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) * HDIM;
            dyn[db + FDYN_WINM1_ROW] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) - 1) * HDIM;
        end
    end

    // Decode: bases and counts add their DYN value.
    wire [NW-1:0] c_me_nout = `F(ME_NOUT) + `DY(ME_D_NOUT);
    wire [NW-1:0] c_me_tiles = `F(ME_TILES) + `DY(ME_D_TILES);
    wire [NW-1:0] c_me_k = `F(ME_K) + `DY(ME_D_K);
    wire [AW-1:0] c_me_wbase = `F(ME_WBASE) + `DY(ME_D_WBASE);
    wire [NW-1:0] c_su_nout = `F(SU_NOUT) + `DY(SU_D_NOUT);
    wire [NW-1:0] c_su_nin = `F(SU_NIN) + `DY(SU_D_NIN);
    wire [NW-1:0] c_xu_n = `F(XU_N) + `DY(XU_D_N);
    wire [AW-1:0] c_xu_k = `F(XU_K) + `DY(XU_D_K);
    wire [1:0]    c_pred = `F(PRED);
    wire [NW-1:0] c_pos = pos_r + c_dslot;           // the instruction's slot position
    wire          pred_ok = (c_pred == 2'd0) || (c_pred == 2'd1 && c_pos[0]) || (c_pred == 2'd2 && c_pos != 0);
    wire [2:0]    c_unit = `F(UNIT);
    wire          zero = (c_unit == 3'd1 && (c_me_nout == 0 || c_me_tiles == 0 || c_me_k == 0)) ||
                         (c_unit == 3'd2 && (c_su_nout == 0 || c_su_nin == 0)) ||
                         (c_unit == 3'd4 && `F(XU_OP) == 2'd0 && c_xu_n == 0);
    always @(posedge clk) if (st == S_DEC) begin
        d_unit <= c_unit; d_wait <= `F(WAIT); d_skip <= !pred_ok || zero; d_wrel <= `F(WREL);
        d_ctl <= (FULL_SHAPE || NSLOT > 1) ? `F(CTL) : 3'd0;
        d_cslot <= `F(CTL_SLOT); d_clane <= `F(CTL_LANE);
        mx_m <= `F(MX_M); mx_xps <= `F(MX_XPS); mx_ops <= `F(MX_OPS);
        if (c_unit == 3'd4) begin
            xu_tok <= (NSLOT > 1) ? stok[c_dslot * NW +: NW] : tok_r;
            xu_first <= (c_pos == 0); xu_hslot <= c_dslot;
        end
        me_nout <= c_me_nout; me_tiles <= c_me_tiles; me_k <= c_me_k;
        me_pos <= c_pos;
        me_wsrc <= `F(ME_WSRC); me_round <= `F(ME_ROUND); me_oen <= `F(ME_OEN); me_amax <= `F(ME_AMAX);
        me_wbase <= c_me_wbase;
        me_ts <= `F(ME_TS); me_ks <= `F(ME_KS); me_js <= `F(ME_JS);
        me_xbase <= `F(ME_XBASE) + `DY(ME_D_XBASE);
        me_obase <= `F(ME_OBASE) + `DY(ME_D_OBASE);
        me_xks <= `F(ME_XKS); me_xjs <= `F(ME_XJS); me_jsh <= `F(ME_JSH);
        me_ots <= `F(ME_OTS); me_ojs <= `F(ME_OJS); me_mmode <= `F(ME_MMODE);
        me_fuse <= `F(ME_FUSE); me_wts <= `F(ME_WTS);
        me_split <= `F(ME_SPLIT); me_xcs <= `F(ME_XCS); me_hg <= `F(ME_HG); me_ogs <= `F(ME_OGS);
        su_nout <= c_su_nout; su_nin <= c_su_nin; su_vec <= `F(SU_VEC); su_chase <= `F(SU_CHASE);
        a_src <= `F(A_SRC); a_base <= `F(A_BASE) + `DY(A_D); a_so <= `F(A_SO); a_si <= `F(A_SI);
        a_ind <= `F(A_IND); a_ibase <= `F(A_IBASE);
        b_src <= `F(B_SRC); b_base <= `F(B_BASE) + `DY(B_D); b_so <= `F(B_SO); b_si <= `F(B_SI); b_half <= `F(B_HALF);
        c_src <= `F(C_SRC); c_base <= `F(C_BASE) + `DY(C_D); c_so <= `F(C_SO); c_si <= `F(C_SI); c_pair <= `F(C_PAIR);
        d_src <= `F(D_SRC); d_base <= `F(D_BASE) + `DY(D_D); d_so <= `F(D_SO); d_si <= `F(D_SI);
        a_rnd <= `F(A_RND); a_relu <= `F(A_RELU); a_min <= `F(A_MIN); c_clip <= `F(C_CLIP);
        m1 <= `F(M1); m2 <= `F(M2); qm <= `F(QM); ad <= `F(AD); sfu <= `F(SFU); e1 <= `F(E1); e2 <= `F(E2);
        rnd <= `F(RND); dst <= `F(DST);
        //: transposed-KV writes take the DYN value as a row, not an offset
        o_base <= `F(O_BASE) + ((`F(DST) == 2'd3) ? {AW{1'b0}} : `DY(O_D));
        o_row <= `DY(O_D); o_so <= `F(O_SO); o_si <= `F(O_SI);
        // The local KVT row may saturate at window row 127 while the HBM
        // ring tag must keep the absolute token position across wraps.
        win_abs_row <= c_pos;
        red <= `F(RED); red_sq <= `F(RED_SQ); red_whole <= `F(RED_WHOLE); red_tree <= `F(RED_TREE); red_rnd <= `F(RED_RND);
        r_base <= `F(R_BASE); r_so <= `F(R_SO);
        imm1 <= `F(IMM1); imm2 <= `F(IMM2); imm3 <= `F(IMM3);
        qe_mode <= `F(QE_MODE); qe_fp4 <= `F(QE_FP4); qe_ind <= `F(QE_IND);
        qe_unrounded <= FULL_SHAPE ? `F(QE_UNROUNDED) : 1'b0;
        qe_xbase <= `F(QE_XBASE); qe_wbase <= `F(QE_WBASE); qe_ibase <= `F(QE_IBASE);
        qe_istride <= `F(QE_ISTRIDE); qe_obase <= `F(QE_OBASE) + `DY(QE_D_OBASE);
        qe_nb <= `F(QE_NB); qe_nout <= `F(QE_NOUT); qe_tiles <= `F(QE_TILES);
        xu_op <= `F(XU_OP); xu_src <= `F(XU_SRC); xu_dst <= `F(XU_DST); xu_n <= c_xu_n;
        xu_k <= c_xu_k[XU_KW-1:0]; xu_layer <= `F(XU_LAYER);
        //: the index-score SELECTs are the ones whose count is dynamic (xu_d_n: the positions so far);
        //: the router's top-k and a draft's top-1 have static counts and FP32 values
        xu_bf16 <= (`F(XU_D_N) != 0);
        he_nout <= `F(HE_NOUT); he_k <= `F(HE_K); he_wbase <= `F(HE_WBASE); he_xbase <= `F(HE_XBASE);
        he_obase <= `F(HE_OBASE);
        if (FULL_SHAPE) begin
            coll_op <= `F(COLL_OP); coll_src <= `F(COLL_SRC); coll_dst <= `F(COLL_DST);
            coll_ibase <= `F(COLL_IBASE); coll_n <= `F(COLL_N); coll_k <= `F(COLL_K);
            coll_seq <= `F(COLL_SEQ); coll_rnd <= `F(COLL_RND);
        end
    end
    `undef F
    `undef DY

    //: W_HBM: a LINQ op waits for the QE weight streamer; never on the cycle its
    //: shape is announced, when q_ok may still describe the previous op
    wire q_gate = ((W_HBM == 0) || !(d_unit == 3'd3 && qe_mode == 2'd0) || (q_ok && !qd_v)) &&
                  (!(FULL_SHAPE && KV_HBM && d_unit == 3'd3 && qe_mode == 2'd1) || win_idle);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) qd_v <= 1'b0;
        else qd_v <= (W_HBM != 0) && (st == S_DEC) && c_unit == 3'd3 && ir[O_QE_MODE +: W_QE_MODE] == 2'd0 && pred_ok;
    end
    assign qd_wbase = qe_wbase; assign qd_nb = qe_nb; assign qd_tiles = qe_tiles;

    wire m0_gate = (ME0_HBM == 0) || !(d_unit == 3'd1 && me_cls == MC_W && m0_select) ||
                   (m0_ok && !m0d_v);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) m0d_v <= 1'b0;
        else m0d_v <= (ME0_HBM != 0) && (st == S_DEC) && c_unit == 3'd1 &&
                      !ir[O_ME_WSRC] && pred_ok && !zero;
    end
    assign m0d_wbase = me_wbase;
    assign m0d_nout = me_nout;
    assign m0d_tiles = me_tiles;
    assign m0d_k = me_k;
    assign m0d_xjs = me_xjs;
    assign m0d_split = me_split;

    // Only an attention-class ME op reads the window KV through the shared KV
    // port. The descriptor is emitted after decode captures its dynamic fields.
    // Holding issue for one cycle after kvd_v also prevents a stale kv_ok from
    // the previous operation from granting this one.
    wire kv_gate = ((KV_HBM == 0) || !(d_unit == 3'd1 && me_cls == MC_A) || (kv_ok && !kvd_v)) &&
                   (!FULL_SHAPE || win_idle);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kvd_v <= 1'b0;
        else kvd_v <= (KV_HBM != 0) && (st == S_DEC) && c_unit == 3'd1 &&
                      ir[O_ME_WSRC] && (c_me_wbase < cfg_ik_base) &&
                      pred_ok && !zero && (!FULL_SHAPE || win_idle);
    end
    assign kvd_wbase = me_wbase; assign kvd_ts = me_ts; assign kvd_ks = me_ks; assign kvd_js = me_js;
    assign kvd_tiles = me_tiles; assign kvd_k = me_k; assign kvd_nout = me_nout;
    assign kvd_hg = me_hg; assign kvd_mmode = me_mmode; assign kvd_pos = me_pos;

    // -- units -----------------------------------------------------------------------------------------
    // -- the ME SLOT: one issue slot, up to four engines behind it ------------------------------------
    // An ME op's class: 0 a weight op (me_wsrc = 0: the BF16/FP32 weight engine), 1 a KV-sourced op of
    // attention (q.k, p.v: the attention engine), 2 a KV-sourced op on the index keys (the indexer
    // engine) -- derived from the KV base: the index keys are the KV region at and above cfg_ik_base
    // (words; tools/hdc_images_v41x.py writes it, the Layout places every IK region after the KT/KR ones).
    // A class runs on its re-specified engine when that engine is built (X_ME, X_ATT, X_IDX), else on
    // the as-built ot_hdc_v41_matvec.  The slot serialises its ops (an op issues only when every engine
    // of the slot is idle but the one it goes to, which must be ready), as the as-built single engine
    // did, so the vector-memory, KV and logit ports are multiplexed by the owner of the running op.
    localparam [1:0] MC_W = 2'd0, MC_A = 2'd1, MC_I = 2'd2;
    wire [1:0] me_cls = !me_wsrc ? MC_W : (me_wbase >= cfg_ik_base) ? MC_I : MC_A;
    //: which engine takes each class: 0 the as-built engine, 1 its re-specified one
    wire [1:0] me_eng = (me_cls == MC_W) ? ((X_ME != 0) ? 2'd1 : 2'd0) :
                        (me_cls == MC_A) ? ((X_ATT != 0) ? 2'd2 : 2'd0) : ((X_IDX != 0) ? 2'd3 : 2'd0);
    reg  [1:0] me_own;                          // engine of the op issued last
    always @(posedge clk or negedge rst_n) if (!rst_n) me_own <= 2'd0; else if (me_go) me_own <= me_eng;
    // per engine e (0 as built, 1 weight, 2 attention, 3 indexer): the as-built ME's port bundle
    wire [3:0]            e_go, e_ready, e_idle, e_fault, e_kv_re, e_ov;
    assign att_packed_issue = (FULL_SHAPE != 0) && e_go[2];
    assign att_packed_idle = e_idle[2];
    wire [4*AW-1:0]       e_wrom_addr_u;                     // (as built only)
    wire [4*G*AW-1:0]     e_kv_raddr;
    wire [4*MP*G-1:0]     e_vx_re, e_we;
    wire [4*MP*G*AW-1:0]  e_vx_addr, e_addr;
    wire [4*MP*G*W-1:0]   e_mask;
    wire [4*MP*G*W*32-1:0] e_data;
    wire [4*MP*NW-1:0]    e_am_idx;
    wire [4*MP*32-1:0]    e_am_val;
    wire [4*MP-1:0]       e_am_any;
    genvar ge;
    generate for (ge = 0; ge < 4; ge = ge + 1) begin : g_ego
        assign e_go[ge] = me_go && me_eng == ge;
    end endgenerate
    assign me_ready = e_ready[me_eng] && ((e_idle & ~(4'd1 << me_eng) & ~e_go) == (4'hF & ~(4'd1 << me_eng)));
    assign me_idle = &e_idle;
    //: a fused indexer op (me_fuse) has no engine but the indexer's: routed elsewhere it faults
    reg fuse_orphan;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fuse_orphan <= 1'b0; else fuse_orphan <= me_go && me_fuse && me_eng != 2'd3;
    assign me_fault = (|e_fault) || fuse_orphan;
    assign kv_re = e_kv_re[me_own];
    assign kv_raddr = e_kv_raddr[me_own*G*AW +: G*AW];
    assign vx_re = e_vx_re[me_own*MP*G +: MP*G];
    assign vx_addr = e_vx_addr[me_own*MP*G*AW +: MP*G*AW];
    assign me_ov = e_ov[me_own];
    wire [MP*G-1:0]      u_me_we = e_we[me_own*MP*G +: MP*G];
    wire [MP*G*AW-1:0]   u_me_addr = e_addr[me_own*MP*G*AW +: MP*G*AW];
    wire [MP*G*W-1:0]    u_me_mask = e_mask[me_own*MP*G*W +: MP*G*W];
    wire [MP*G*W*32-1:0] u_me_data = e_data[me_own*MP*G*W*32 +: MP*G*W*32];
    //: the argmax is a weight op's (the LM head, the Markov head)
    localparam integer EAM = (X_ME != 0) ? 1 : 0;
    assign am_idx_v = e_am_idx[EAM*MP*NW +: MP*NW];
    assign am_val_v = e_am_val[EAM*MP*32 +: MP*32];
    assign am_any_v = e_am_any[EAM*MP +: MP];
    // observation: the engine's result words as produced (before the VM_DIST scatter tree)
    assign me_oaddr = u_me_addr;
    assign me_omask = u_me_mask;
    assign me_odata = u_me_data;

    // engine 0: the as-built matrix engine (every class not re-specified)
    ot_hdc_v41_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .MP(MP)) u_me (
        .clk(clk), .rst_n(rst_n), .go(e_go[0]), .ready(e_ready[0]), .idle(e_idle[0]),
        .i_nout(me_nout), .i_tiles(me_tiles), .i_k(me_k), .i_wsrc(me_wsrc), .i_wbase(me_wbase),
        .i_ts(me_ts), .i_ks(me_ks), .i_js(me_js), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs),
        .i_xcs(me_xcs), .i_jsh(me_jsh), .i_split(me_split), .i_hg(me_hg), .i_ogs(me_ogs), .i_round(me_round), .i_obase(me_obase),
        .i_ots(me_ots), .i_ojs(me_ojs), .i_mmode(me_mmode), .i_oen(me_oen), .i_amax(me_amax),
        .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .kv_re(e_kv_re[0]), .kv_addr(e_kv_raddr[0 +: G*AW]), .kv_q(kv_q),
        .x_re(e_vx_re[0 +: MP*G]), .x_addr(e_vx_addr[0 +: MP*G*AW]), .x_q(vx_q),
        .ov(e_ov[0]), .o_we(e_we[0 +: MP*G]), .o_addr(e_addr[0 +: MP*G*AW]), .o_mask(e_mask[0 +: MP*G*W]),
        .o_data(e_data[0 +: MP*G*W*32]),
        .am_idx(e_am_idx[0 +: MP*NW]), .am_val(e_am_val[0 +: MP*32]), .am_any(e_am_any[0 +: MP]),
        .progress(me_progress), .fault(e_fault[0]));

    // engine 1: the BF16/FP32 weight engine (X_ME)
    generate if (X_ME != 0) begin : g_me_x
        ot_hdc_v41x_me_adapt #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .MP(MP), .MG(MG), .BAW(MBAW),
                                 .KMAX(FULL_SHAPE ? 5120 : 512), .XBANK(X_ME_XBANK)) u_mw (
            .clk(clk), .rst_n(rst_n), .go(e_go[1]), .ready(e_ready[1]), .idle(e_idle[1]),
            .i_nout(me_nout), .i_tiles(me_tiles), .i_k(me_k), .i_wbase(me_wbase), .i_xbase(me_xbase),
            .i_xjs(me_xjs), .i_split(me_split), .i_round(me_round), .i_obase(me_obase), .i_ots(me_ots),
            .i_ojs(me_ojs), .i_oen(me_oen), .i_amax(me_amax), .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
            .cfg_xs(cfg_me_xs), .wb_re(mb_re), .wb_addr(mb_addr), .wb_q(mb_q),
            .x_re(e_vx_re[1*MP*G +: MP*G]), .x_addr(e_vx_addr[1*MP*G*AW +: MP*G*AW]), .x_q(vx_q),
            .ov(e_ov[1]), .o_we(e_we[1*MP*G +: MP*G]), .o_addr(e_addr[1*MP*G*AW +: MP*G*AW]),
            .o_mask(e_mask[1*MP*G*W +: MP*G*W]), .o_data(e_data[1*MP*G*W*32 +: MP*G*W*32]),
            .am_idx(e_am_idx[1*MP*NW +: MP*NW]), .am_val(e_am_val[1*MP*32 +: MP*32]),
            .am_any(e_am_any[1*MP +: MP]), .fault(e_fault[1]));
        assign e_kv_re[1] = 1'b0;
        assign e_kv_raddr[1*G*AW +: G*AW] = 0;
    end else begin : g_me_n
        assign mb_re = 8'd0; assign mb_addr = 0;
        assign e_ready[1] = 1'b1; assign e_idle[1] = 1'b1; assign e_fault[1] = 1'b0; assign e_kv_re[1] = 1'b0;
        assign e_kv_raddr[1*G*AW +: G*AW] = 0; assign e_vx_re[1*MP*G +: MP*G] = 0;
        assign e_vx_addr[1*MP*G*AW +: MP*G*AW] = 0; assign e_ov[1] = 1'b0; assign e_we[1*MP*G +: MP*G] = 0;
        assign e_addr[1*MP*G*AW +: MP*G*AW] = 0; assign e_mask[1*MP*G*W +: MP*G*W] = 0;
        assign e_data[1*MP*G*W*32 +: MP*G*W*32] = 0; assign e_am_idx[1*MP*NW +: MP*NW] = 0;
        assign e_am_val[1*MP*32 +: MP*32] = 0; assign e_am_any[1*MP +: MP] = 0;
    end endgenerate

    // engine 2: the attention engine (X_ATT)
    generate if (X_ATT != 0) begin : g_att_x
        ot_hdc_v41x_att_adapt #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .MP(MP), .H(16), .D(HDIM), .TD(32),
                                .NL(4), .TROWS(FULL_SHAPE ? 640 : 160), .NHMAX(FULL_SHAPE ? 16 : 32),
                                .PACKED_KV(FULL_SHAPE != 0)) u_att (
            .clk(clk), .rst_n(rst_n), .go(e_go[2]), .ready(e_ready[2]), .idle(e_idle[2]),
            .i_nout(me_nout), .i_tiles(me_tiles), .i_k(me_k), .i_wbase(me_wbase), .i_ts(me_ts), .i_ks(me_ks),
            .i_js(me_js), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs), .i_xcs(me_xcs), .i_hg(me_hg),
            .i_ogs(me_ogs), .i_round(me_round), .i_obase(me_obase), .i_ots(me_ots), .i_ojs(me_ojs),
            .i_mmode(me_mmode), .i_oen(me_oen), .i_m(mx_m),
            .kv_re(e_kv_re[2]), .kv_addr(e_kv_raddr[2*G*AW +: G*AW]), .kv_q(kv_q),
            .packed_kv_v(att_packed_kv_v), .packed_kv_ready(att_packed_kv_ready),
            .packed_kv_m(att_packed_kv_m), .packed_kv_w(att_packed_kv_w),
            .packed_kv_fault(att_packed_kv_fault),
            .x_re(e_vx_re[2*MP*G +: MP*G]), .x_addr(e_vx_addr[2*MP*G*AW +: MP*G*AW]), .x_q(vx_q),
            .o_we(e_we[2*MP*G +: MP*G]), .o_addr(e_addr[2*MP*G*AW +: MP*G*AW]), .o_mask(e_mask[2*MP*G*W +: MP*G*W]),
            .o_data(e_data[2*MP*G*W*32 +: MP*G*W*32]), .fault(e_fault[2]));
        assign e_ov[2] = 1'b0;
        assign e_am_idx[2*MP*NW +: MP*NW] = 0; assign e_am_val[2*MP*32 +: MP*32] = 0; assign e_am_any[2*MP +: MP] = 0;
    end else begin : g_att_n
        assign att_packed_kv_ready = 1'b0;
        assign e_ready[2] = 1'b1; assign e_idle[2] = 1'b1; assign e_fault[2] = 1'b0; assign e_kv_re[2] = 1'b0;
        assign e_kv_raddr[2*G*AW +: G*AW] = 0; assign e_vx_re[2*MP*G +: MP*G] = 0;
        assign e_vx_addr[2*MP*G*AW +: MP*G*AW] = 0; assign e_ov[2] = 1'b0; assign e_we[2*MP*G +: MP*G] = 0;
        assign e_addr[2*MP*G*AW +: MP*G*AW] = 0; assign e_mask[2*MP*G*W +: MP*G*W] = 0;
        assign e_data[2*MP*G*W*32 +: MP*G*W*32] = 0; assign e_am_idx[2*MP*NW +: MP*NW] = 0;
        assign e_am_val[2*MP*32 +: MP*32] = 0; assign e_am_any[2*MP +: MP] = 0;
    end endgenerate

    // engine 3: the indexer engine (X_IDX)
    generate if (X_IDX != 0) begin : g_idx_x
        wire f_eng, f_kwr;
        // The key writer must observe the KV writes of the selected stream engine.
        // X_SU uses its own SUN-lane memory interface; the legacy KV ports are tied off there.
        localparam integer KNL = (X_SU != 0) ? SUN : MP*SW;
        wire [KNL-1:0] kwr_kv_we;
        wire [KNL*AW-1:0] kwr_kv_waddr;
        wire [KNL*32-1:0] kwr_kv_wdata;
        if (X_SU != 0) begin : g_kwr_vec
            assign kwr_kv_we = xs_kv_we;
            assign kwr_kv_waddr = xs_kv_waddr;
            assign kwr_kv_wdata = xs_kv_wdata;
        end else begin : g_kwr_legacy
            assign kwr_kv_we = kv_we;
            assign kwr_kv_waddr = kv_waddr;
            assign kwr_kv_wdata = kv_wdata;
        end
        if (X_IDX == 2) begin : g_pool
            ot_hdc_v41x_idx_pool_adapt #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .MP(MP),
                                           .HAW(PIKH_HAW), .SHARDED(IDX_SHARDED),
                                           .SLICE_SECTORS(IDX_KEY_SLICE_SECTORS), .RING(IDX_RING),
                                           .RING_RSB(IDX_RING_RSB), .RING_RTAIL(IDX_RING_RTAIL)) u_idx (
                .clk(clk), .rst_n(rst_n), .go(e_go[3]), .ready(e_ready[3]), .idle(e_idle[3]), .cfg_ik_base(cfg_ik_base),
                .i_user_base_sec(IDX_MULTIUSER ? idx_user_base_sec : PIKH_HAW'(0)),
                .i_nout(me_nout), .i_k(me_k), .i_wbase(me_wbase), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs),
                .i_xcs(me_xcs), .i_hg(me_hg), .i_round(me_round), .i_obase(me_obase), .i_mmode(me_mmode),
                .i_oen(me_oen), .i_fuse(me_fuse), .i_wts(me_wts),
                .x_re(e_vx_re[3*MP*G +: MP*G]), .x_addr(e_vx_addr[3*MP*G*AW +: MP*G*AW]), .x_q(vx_q),
                .ov(e_ov[3]), .o_we(e_we[3*MP*G +: MP*G]), .o_addr(e_addr[3*MP*G*AW +: MP*G*AW]),
                .o_mask(e_mask[3*MP*G*W +: MP*G*W]), .o_data(e_data[3*MP*G*W*32 +: MP*G*W*32]),
                .h_req_v(pikh_req_v), .h_req_rdy(pikh_req_rdy), .h_req_addr(pikh_req_addr), .h_req_len(pikh_req_len),
                .h_req_tag(pikh_req_tag), .h_rsp_v(pikh_rsp_v), .h_rsp_rdy(pikh_rsp_rdy), .h_rsp_tag(pikh_rsp_tag),
                .h_rsp_beat(pikh_rsp_beat), .h_rsp_data(pikh_rsp_data), .fault(f_eng),
                .dbg_ops(), .dbg_elems(), .dbg_keys_streamed(), .dbg_hbm_beats(), .dbg_keys_scored(),
                .dbg_headsums_fused());
            ot_hdc_v41x_idx_pool_kwr #(.AW(AW), .NW(NW), .NL(KNL), .HAW(PIKH_HAW),
                                         .SHARDED(IDX_SHARDED), .SLICE_SECTORS(IDX_KEY_SLICE_SECTORS),
                                         .RING(IDX_RING), .RING_UBLK(IDX_RING_RSB*17 +
                                             ((IDX_RING_RTAIL != 0) ? 1 + (IDX_RING_RTAIL + 63) / 64 : 0))) u_kwr (
                .clk(clk), .rst_n(rst_n), .cfg_ik_base(cfg_ik_base),
                .i_user_base_sec(IDX_MULTIUSER ? idx_user_base_sec : PIKH_HAW'(0)),
                .su_go(su_go), .i_dst(dst), .i_obase(o_base),
                .i_orow(o_row), .i_nout(su_nout), .i_kdim(su_nin), .kv_we(kwr_kv_we),
                .kv_waddr(kwr_kv_waddr), .kv_wdata(kwr_kv_wdata), .w_v(pikw_v), .w_rdy(pikw_rdy),
                .w_stack_mask(pikw_stack_mask), .w_csec(pikw_csec), .w_codes(pikw_codes),
                .w_ssec(pikw_ssec), .w_sslot(pikw_sslot), .w_scales(pikw_scales), .fault(f_kwr), .dbg_keys());
            assign ikh_req_v = 0; assign ikh_req_addr = 0; assign ikh_req_len = 0; assign ikh_req_tag = 0;
            assign ikh_rsp_rdy = 0; assign ikw_v = 0; assign ikw_csec = 0; assign ikw_codes = 0;
            assign ikw_ssec = 0; assign ikw_sslot = 0; assign ikw_scale = 0;
        end else begin : g_legacy
        ot_hdc_v41x_idx_adapt #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .MP(MP)) u_idx (
            .clk(clk), .rst_n(rst_n), .go(e_go[3]), .ready(e_ready[3]), .idle(e_idle[3]), .cfg_ik_base(cfg_ik_base),
            .i_nout(me_nout), .i_k(me_k), .i_wbase(me_wbase), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs),
            .i_xcs(me_xcs), .i_hg(me_hg), .i_round(me_round), .i_obase(me_obase), .i_mmode(me_mmode),
            .i_oen(me_oen), .i_fuse(me_fuse), .i_wts(me_wts),
            .x_re(e_vx_re[3*MP*G +: MP*G]), .x_addr(e_vx_addr[3*MP*G*AW +: MP*G*AW]), .x_q(vx_q),
            .ov(e_ov[3]), .o_we(e_we[3*MP*G +: MP*G]), .o_addr(e_addr[3*MP*G*AW +: MP*G*AW]),
            .o_mask(e_mask[3*MP*G*W +: MP*G*W]), .o_data(e_data[3*MP*G*W*32 +: MP*G*W*32]),
            .h_req_v(ikh_req_v), .h_req_rdy(ikh_req_rdy), .h_req_addr(ikh_req_addr), .h_req_len(ikh_req_len),
            .h_req_tag(ikh_req_tag), .h_rsp_v(ikh_rsp_v), .h_rsp_rdy(ikh_rsp_rdy), .h_rsp_tag(ikh_rsp_tag),
            .h_rsp_beat(ikh_rsp_beat), .h_rsp_data(ikh_rsp_data), .fault(f_eng),
            .dbg_ops(), .dbg_elems(), .dbg_keys_streamed(), .dbg_hbm_beats(), .dbg_keys_scored(),
            .dbg_headsums_fused());
        //: the key writer: every index-key row the stream unit writes goes to the HBM key image too
        ot_hdc_v41x_idx_kwr #(.AW(AW), .NW(NW), .NL(KNL), .HAW(28)) u_kwr (
            .clk(clk), .rst_n(rst_n), .cfg_ik_base(cfg_ik_base), .su_go(su_go), .i_dst(dst), .i_obase(o_base),
            .i_orow(o_row), .i_nout(su_nout), .kv_we(kwr_kv_we), .kv_waddr(kwr_kv_waddr), .kv_wdata(kwr_kv_wdata),
            .w_v(ikw_v), .w_csec(ikw_csec), .w_codes(ikw_codes), .w_ssec(ikw_ssec), .w_sslot(ikw_sslot),
            .w_scale(ikw_scale), .fault(f_kwr), .dbg_keys());
            assign pikh_req_v = 0; assign pikh_req_addr = 0; assign pikh_req_len = 0; assign pikh_req_tag = 0;
            assign pikh_rsp_rdy = 0; assign pikw_v = 0; assign pikw_stack_mask = 0; assign pikw_csec = 0;
            assign pikw_codes = 0; assign pikw_ssec = 0; assign pikw_sslot = 0; assign pikw_scales = 0;
        end
        assign e_fault[3] = f_eng || f_kwr;
        assign e_kv_re[3] = 1'b0; assign e_kv_raddr[3*G*AW +: G*AW] = 0;
        assign e_am_idx[3*MP*NW +: MP*NW] = 0; assign e_am_val[3*MP*32 +: MP*32] = 0;
        assign e_am_any[3*MP +: MP] = 0;
    end else begin : g_idx_n
        assign e_ready[3] = 1'b1; assign e_idle[3] = 1'b1; assign e_fault[3] = 1'b0; assign e_kv_re[3] = 1'b0;
        assign e_kv_raddr[3*G*AW +: G*AW] = 0; assign e_vx_re[3*MP*G +: MP*G] = 0;
        assign e_vx_addr[3*MP*G*AW +: MP*G*AW] = 0; assign e_ov[3] = 1'b0; assign e_we[3*MP*G +: MP*G] = 0;
        assign e_addr[3*MP*G*AW +: MP*G*AW] = 0; assign e_mask[3*MP*G*W +: MP*G*W] = 0;
        assign e_data[3*MP*G*W*32 +: MP*G*W*32] = 0; assign e_am_idx[3*MP*NW +: MP*NW] = 0;
        assign e_am_val[3*MP*32 +: MP*32] = 0; assign e_am_any[3*MP +: MP] = 0;
        assign ikh_req_v = 0; assign ikh_req_addr = 0; assign ikh_req_len = 0; assign ikh_req_tag = 0;
        assign pikh_req_v = 0; assign pikh_req_addr = 0; assign pikh_req_len = 0; assign pikh_req_tag = 0;
        assign pikh_rsp_rdy = 0; assign pikw_v = 0; assign pikw_stack_mask = 0; assign pikw_csec = 0;
        assign pikw_codes = 0; assign pikw_ssec = 0; assign pikw_sslot = 0; assign pikw_scales = 0;
        assign ikh_rsp_rdy = 0; assign ikw_v = 1'b0; assign ikw_csec = 0; assign ikw_codes = 0; assign ikw_ssec = 0;
        assign ikw_sslot = 0; assign ikw_scale = 0;
    end endgenerate

    // the stream unit.  X_SU: the vector unit behind its adapter (a batched op's m copies back to back);
    // else the as-built MP copies of ot_hdc_v41_stream
    genvar sp;
    generate if (X_SU != 0) begin : g_su_x
        wire [SUN-1:0] raw_kv_we;
        ot_hdc_v41x_su_adapt #(.N(SUN), .M(SUM), .LV(SULV), .AW(AW), .NW(NW), .CLS_DRAIN((NSLOT > 1) ? 1 : 0),
                               .BCAST_STAGES(VM_CROT ? CR_LEAD + CR_RD : SUBCAST),
                               .RET_STAGES(VM_CROT ? CR_WR : VM_DIST ? SU_EWR_STAGES : SURET),
                               .RES_STAGES(VM_CROT ? CR_RES : VM_DIST ? SU_RES_STAGES : SURET),
                               .VMD_NG((VM_DIST != 0 && VM_DIST_H != 0 && VM_CROT == 0) ? SUN / 8 : 0), .ROT_STAGES(SU_ROT_STAGES),
                               .GATH_STAGES(SU_GATH_STAGES), .SCAL_STAGES(SU_SCAL_STAGES),
                               .RD_LEAD(VM_CROT ? CR_LEAD : -1), .CROT_GX(VM_CROT ? CR_GX : 0))
            u_su (
            .clk(clk), .rst_n(rst_n), .go(su_go), .ready(su_ready), .idle(su_idle),
            .i_nout(su_nout), .i_nin(su_nin), .i_chase(su_chase), .i_asrc(a_src), .i_bsrc(b_src),
            .i_csrc(c_src), .i_dsrc(d_src), .i_abase(a_base), .i_aso(a_so), .i_asi(a_si), .i_aibase(a_ibase),
            .i_aind(a_ind), .i_bbase(b_base), .i_bso(b_so), .i_bsi(b_si), .i_bhalf(b_half),
            .i_cbase(c_base), .i_cso(c_so), .i_csi(c_si), .i_cpair(c_pair),
            .i_dbase(d_base), .i_dso(d_so), .i_dsi(d_si),
            .i_arnd(a_rnd), .i_arelu(a_relu), .i_amin(a_min), .i_cclip(c_clip),
            .i_m1(m1), .i_m2(m2), .i_qm(qm), .i_ad(ad), .i_sfu(sfu), .i_e1(e1), .i_e2(e2), .i_rnd(rnd),
            .i_dst(dst), .i_obase(o_base), .i_oso(o_so), .i_osi(o_si), .i_orow(o_row),
            .i_red(red), .i_redsq(red_sq), .i_redwhole(red_whole), .i_redtree(red_tree), .i_redrnd(red_rnd),
            .i_rbase(r_base), .i_rso(r_so), .i_imm1(imm1), .i_imm2(imm2), .i_imm3(imm3),
            .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
            .vi_re(xs_vi_re), .vi_addr(xs_vi_addr), .vi_q(xs_vi_q),
            .rd_addr(xs_rd_addr), .rd_re(xs_rd_re), .rd_src(xs_rd_src), .rd_q(xs_rd_q),
            .vm_we(xs_vm_we), .vm_waddr(xs_vm_waddr), .vm_wdata(xs_vm_wdata),
            .kv_we(raw_kv_we), .kv_waddr(xs_kv_waddr), .kv_wdata(xs_kv_wdata),
            .res_we(xs_res_we), .res_addr(xs_res_addr), .res_data(xs_res_data), .fault(su_fault),
            .dbg_ops(), .dbg_elems());
        assign xs_kv_we = raw_kv_we & {SUN{!win_scalar_suppress}};
        assign vi_re = 0; assign vi_addr = 0; assign vs_re = 0; assign vs_addr = 0; assign crom_re = 0;
        assign crom_addr = 0; assign ewrom_re = 0; assign ewrom_addr = 0; assign vw_su_we = 0; assign vw_su_addr = 0;
        assign vw_su_data = 0; assign kv_we = 0; assign kv_waddr = 0; assign kv_wdata = 0; assign vw_rd_we = 0;
        assign vw_rd_addr = 0; assign vw_rd_data = 0;
    end else begin : g_su_a
    // MP copies; copy p runs slot p of a batched op (mx_m), its vector-memory streams moved by p slot
    // strides (mx_xps reads, mx_ops writes)
    wire [MP-1:0] su_ready_v, su_idle_v, su_fault_v;
    wire [2:0]    su_m = (mx_m == 3'd0) ? 3'd1 : mx_m;
    assign su_ready = &su_ready_v;
    assign su_idle = &su_idle_v;
    assign su_fault = |su_fault_v;
        for (sp = 0; sp < MP; sp = sp + 1) begin : g_su
            wire [SW-1:0] raw_kv_we;
            wire [AW-1:0] xo = sp * mx_xps;
            wire [AW-1:0] oo = sp * mx_ops;
            ot_hdc_v41_stream #(.AW(AW), .NW(NW), .WR(G * W), .SW(SW)) u_su (
                .clk(clk), .rst_n(rst_n), .go(su_go && (sp < su_m)), .ready(su_ready_v[sp]), .idle(su_idle_v[sp]),
                .i_nout(su_nout), .i_nin(su_nin), .i_vec(su_vec), .i_chase(su_chase), .i_asrc(a_src), .i_bsrc(b_src),
                .i_csrc(c_src), .i_dsrc(d_src),
                .i_abase(a_base + ((a_src == 2'd0) ? xo : {AW{1'b0}})), .i_aso(a_so), .i_asi(a_si),
                .i_aibase(a_ibase), .i_aind(a_ind),
                .i_bbase(b_base + ((b_src == 2'd0) ? xo : {AW{1'b0}})), .i_bso(b_so), .i_bsi(b_si), .i_bhalf(b_half),
                .i_cbase(c_base + ((c_src == 2'd0) ? xo : {AW{1'b0}})), .i_cso(c_so), .i_csi(c_si), .i_cpair(c_pair),
                .i_dbase(d_base + ((d_src == 2'd0) ? xo : {AW{1'b0}})), .i_dso(d_so), .i_dsi(d_si),
                .i_arnd(a_rnd), .i_arelu(a_relu), .i_amin(a_min), .i_cclip(c_clip),
                .i_m1(m1), .i_m2(m2), .i_qm(qm), .i_ad(ad), .i_sfu(sfu), .i_e1(e1), .i_e2(e2), .i_rnd(rnd),
                .i_dst(dst), .i_obase(o_base + ((dst == 2'd1) ? oo : {AW{1'b0}})), .i_oso(o_so), .i_osi(o_si),
                .i_orow(o_row),
                .i_red(red), .i_redsq(red_sq), .i_redwhole(red_whole), .i_redtree(red_tree), .i_redrnd(red_rnd),
                .i_rbase(r_base + ((red != 2'd0) ? oo : {AW{1'b0}})), .i_rso(r_so),
                .i_imm1(imm1), .i_imm2(imm2), .i_imm3(imm3),
                .vi_re(vi_re[sp*SW +: SW]), .vi_addr(vi_addr[sp*SW*AW +: SW*AW]), .vi_q(vi_q[sp*SW*32 +: SW*32]),
                .vm_re(vs_re[sp*4*SW +: 4*SW]), .vm_addr(vs_addr[sp*4*SW*AW +: 4*SW*AW]),
                .vm_q(vs_q[sp*4*SW*32 +: 4*SW*32]),
                .cr_re(crom_re[sp*4*SW +: 4*SW]), .cr_addr(crom_addr[sp*4*SW*AW +: 4*SW*AW]),
                .cr_q(crom_q[sp*4*SW*64 +: 4*SW*64]),
                .wrom_re(ewrom_re[sp*SW +: SW]), .wrom_addr(ewrom_addr[sp*SW*AW +: SW*AW]),
                .wrom_q(ewrom_q[sp*SW*G*W*16 +: SW*G*W*16]),
                .vm_we(vw_su_we[sp*SW +: SW]), .vm_waddr(vw_su_addr[sp*SW*AW +: SW*AW]),
                .vm_wdata(vw_su_data[sp*SW*32 +: SW*32]),
                .kv_we(raw_kv_we), .kv_waddr(kv_waddr[sp*SW*AW +: SW*AW]),
                .kv_wdata(kv_wdata[sp*SW*32 +: SW*32]),
                .red_we(vw_rd_we[sp*SW +: SW]), .red_addr(vw_rd_addr[sp*SW*AW +: SW*AW]),
                .red_data(vw_rd_data[sp*SW*32 +: SW*32]), .fault(su_fault_v[sp]));
            assign kv_we[sp*SW +: SW] = raw_kv_we & {SW{!win_scalar_suppress}};
        end

        assign xs_vi_re = 0; assign xs_vi_addr = 0; assign xs_rd_re = 0; assign xs_rd_addr = 0; assign xs_rd_src = 0;
        assign xs_vm_we = 0; assign xs_vm_waddr = 0; assign xs_vm_wdata = 0; assign xs_kv_we = 0;
        assign xs_kv_waddr = 0; assign xs_kv_wdata = 0; assign xs_res_we = 0; assign xs_res_addr = 0;
        assign xs_res_data = 0;
    end endgenerate

    ot_hdc_v41_qe #(.AW(AW), .NW(NW), .BL(BL), .IL(IL), .NBMAX(FULL_SHAPE ? 192 : 32),
                     .CHUNK8(FULL_SHAPE),
                     .QLB(QLB), .MP(MP)) u_qe (
        .clk(clk), .rst_n(rst_n), .go(qe_go), .ready(qe_ready), .idle(qe_idle),
        .i_mode(qe_mode), .i_fp4(qe_fp4), .i_unrounded(qe_unrounded),
        .i_xbase(qe_xbase), .i_nb(qe_nb), .i_nout(qe_nout), .i_tiles(qe_tiles),
        .i_wbase(qe_wbase), .i_ind(qe_ind), .i_ibase(qe_ibase), .i_istride(qe_istride), .i_obase(qe_obase),
        .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
        .vi_re(vq_re), .vi_addr(vq_addr), .vi_q(vq_q),
        .xr_re(wqr_re), .xr_addr(wqr_addr), .xr_q(wqr_q),
        .w_we(u_q_we), .w_addr(u_q_addr), .w_mask(u_q_mask), .w_data(u_q_data),
        .kvb_v(win_capture_v), .kvb_src_addr(win_capture_addr),
        .kvb_codes(win_capture_codes), .kvb_scale(win_capture_scale),
        .kvb_fault(win_capture_fault),
        .qr_re(qrom_re), .qr_addr(qrom_addr), .qr_q(qrom_q), .fault(qe_fault));

    generate if (FULL_SHAPE && KV_HBM) begin : g_packed_window_write
        ot_hdc_v41x_window_kv_blocks #(.AW(AW), .POS_W(NW), .KVT_SH(13),
                                         .SEPARATE_ROWS(1)) u_blocks (
            .clk(clk), .rst_n(rst_n), .cap_v(win_capture_v),
            .cap_src_addr(win_capture_addr), .cap_codes(win_capture_codes),
            .cap_scale(win_capture_scale), .cap_ready(win_cap_ready),
            .cap_src_base(win_cap_src_base), .idle(win_idle),
            .issue(win_issue), .issue_src_base(a_base),
            .issue_kvt_base(o_base), .issue_row(o_row[NW-1:0]),
            .issue_abs_row(win_abs_row),
            .issue_ready(win_issue_ready), .blk_v(win_blk_v),
            .blk_ready(win_blk_ready), .blk_kvt_base(win_blk_kvt_base),
            .blk_row(win_blk_row), .blk_kvt_row(win_blk_kvt_row),
            .blk_idx(win_blk_idx),
            .blk_first_elem(win_blk_first_elem), .blk_codes(win_blk_codes),
            .blk_scale(win_blk_scale), .fault(win_fault));
    end else begin : g_no_packed_window_write
        assign win_idle = 1'b1; assign win_issue_ready = 1'b0;
        assign win_cap_ready = 1'b0; assign win_fault = 1'b0;
        assign win_cap_src_base = '0;
        assign win_blk_v = 1'b0; assign win_blk_kvt_base = '0;
        assign win_blk_row = '0; assign win_blk_kvt_row = '0;
        assign win_blk_idx = '0;
        assign win_blk_first_elem = '0; assign win_blk_codes = '0;
        assign win_blk_scale = '0;
    end endgenerate

    // the XU: the as-built unit, or (X_SEL / X_EG) its recomposition with the re-specified select and gather
    generate
        if (X_SEL != 0 || X_EG != 0) begin : g_xu_x
            ot_hdc_v41x_xu_adapt #(.AW(AW), .NW(NW), .K(TOPK), .IKW(XU_KW), .SK(FULL_SHAPE ? 2048 : 512), .X_SEL(X_SEL), .X_EG(X_EG), .SQ(XSQ), .SW(XSW)) u_xu (
                .clk(clk), .rst_n(rst_n), .go(xu_go), .ready(xu_ready), .idle(xu_idle),
                .i_op(xu_op), .i_src(xu_src), .i_dst(xu_dst), .i_n(xu_n), .i_k(xu_k), .i_layer(xu_layer), .i_bf16(xu_bf16),
                .token(xu_tok), .first(xu_first), .i_hslot(xu_hslot), .rst_v(xu_rst_v),
        `ifdef HDC_MUTATE_RESTORE
                .rst_slot(acc_a + 1'b1),                 // MUTATION CHECK ONLY: the wrong slot's history
        `else
                .rst_slot(acc_a),
        `endif
                .sel_first(xu_sel_first), .prime_v(prime_v && st == S_IDLE), .prime_first(prime_first),
                .prime_cid(prime_cid),
                .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .xr_re(wxr_re), .xr_addr(wxr_addr), .xr_q(wxr_q),
                .vsl_re(vsl_re), .vsl_addr(vsl_addr), .vsl_q(vsl_q),
                .vw_we(u_xe_we), .vw_addr(u_xe_addr), .vw_data(u_xe_data),
                .w_we(u_x_we), .w_addr(u_x_addr), .w_mask(u_x_mask), .w_data(u_x_data),
                .cr_re(xcrom_re), .cr_addr(xcrom_addr), .cr_q(xcrom_q),
                .er_re(erom_re), .er_addr(erom_addr), .er_q(erom_q), .fault(xu_fault));
        end else begin : g_xu_a
            ot_hdc_v41_xu #(.AW(AW), .NW(NW), .K(TOPK), .IKW(XU_KW)) u_xu (
                .clk(clk), .rst_n(rst_n), .go(xu_go), .ready(xu_ready), .idle(xu_idle),
                .i_op(xu_op), .i_src(xu_src), .i_dst(xu_dst), .i_n(xu_n), .i_k(xu_k), .i_layer(xu_layer),
                .token(xu_tok), .first(xu_first), .i_hslot(xu_hslot), .rst_v(xu_rst_v),
        `ifdef HDC_MUTATE_RESTORE
                .rst_slot(acc_a + 1'b1),                 // MUTATION CHECK ONLY: the wrong slot's history
        `else
                .rst_slot(acc_a),
        `endif
                .sel_first(xu_sel_first), .prime_v(prime_v && st == S_IDLE), .prime_first(prime_first),
                .prime_cid(prime_cid),
                .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .xr_re(wxr_re), .xr_addr(wxr_addr), .xr_q(wxr_q),
                .vw_we(u_xe_we), .vw_addr(u_xe_addr), .vw_data(u_xe_data),
                .w_we(u_x_we), .w_addr(u_x_addr), .w_mask(u_x_mask), .w_data(u_x_data),
                .cr_re(xcrom_re), .cr_addr(xcrom_addr), .cr_q(xcrom_q),
                .er_re(erom_re), .er_addr(erom_addr), .er_q(erom_q), .fault(xu_fault));
            assign vsl_re = {XSQ{1'b0}};
            assign vsl_addr = {(XSQ*AW){1'b0}};
        end
    endgenerate

    generate
        if (X_HE != 0) begin : g_he_x
            ot_hdc_v41x_he_adapt #(.HW(HHW), .TL(HTL), .PMAX((MP > 1) ? 8 : 2), .BAW(HBAW), .AW(AW), .NW(NW),
                                   .S(HS), .MP(MP), .KCMAX(FULL_SHAPE ? 2560 : 128)) u_he (
                .clk(clk), .rst_n(rst_n), .go(he_go), .ready(he_ready), .idle(he_idle),
                .i_nout(he_nout), .i_k(he_k), .i_wbase(he_wbase), .i_xbase(he_xbase), .i_obase(he_obase),
                .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
                .w_re(hb_re), .w_addr(hb_addr), .w_data(hb_q), .x_re(vh_re), .x_addr(vh_addr), .x_q(vh_q),
                .o_we(u_h_we), .o_addr(u_h_addr), .o_mask(u_h_mask), .o_data(u_h_data), .fault(he_fault));
            assign hrom_re = 1'b0;
            assign hrom_addr = {AW{1'b0}};
        end else begin : g_he_a
        ot_hdc_v41_hcproj #(.NL(HNL), .IL(IL), .S(HS), .AW(AW), .NW(NW), .MP(MP)) u_he (
            .clk(clk), .rst_n(rst_n), .go(he_go), .ready(he_ready), .idle(he_idle),
            .i_nout(he_nout), .i_k(he_k), .i_wbase(he_wbase), .i_xbase(he_xbase), .i_obase(he_obase),
            .i_m(mx_m), .i_xps(mx_xps), .i_ops(mx_ops),
            .hr_re(hrom_re), .hr_addr(hrom_addr), .hr_q(hrom_q), .x_re(vh_re), .x_addr(vh_addr), .x_q(vh_q),
            .o_we(u_h_we), .o_addr(u_h_addr), .o_mask(u_h_mask), .o_data(u_h_data), .fault(he_fault));
            assign hb_re = 8'd0;
            assign hb_addr = {(8*HBAW){1'b0}};
        end
    endgenerate

    assign unit_busy = ~idles;

    // -- VM_DIST: the matvec result scatter tree (RET_SCATTER_STAGES registers) -------------------------
    // Each unit's vector-memory writes cross the tree to the lane groups; `pend_*` holds the unit's idle and
    // ready until its last write has reached the last stage (ot_v41_vm_dist_pipe).
    localparam integer RSS = VM_DIST ? RET_SCATTER_STAGES : 0;
    localparam integer WME = MP*G + MP*G*AW + MP*G*W + MP*G*W*32;
    localparam integer WQ  = MP + MP*AW + MP*32 + MP*1024;
    localparam integer WX  = 1 + AW + 32 + 1 + AW + 32 + 1024;
    generate if (RSS == 0) begin : g_ret_flat
        assign {vw_me_we, vw_me_addr, vw_me_mask, vw_me_data} = {u_me_we, u_me_addr, u_me_mask, u_me_data};
        assign {ww_q_we, ww_q_addr, ww_q_mask, ww_q_data} = {u_q_we, u_q_addr, u_q_mask, u_q_data};
        assign {ww_h_we, ww_h_addr, ww_h_mask, ww_h_data} = {u_h_we, u_h_addr, u_h_mask, u_h_data};
        assign {vw_xe_we, vw_xe_addr, vw_xe_data, ww_x_we, ww_x_addr, ww_x_mask, ww_x_data} =
               {u_xe_we, u_xe_addr, u_xe_data, u_x_we, u_x_addr, u_x_mask, u_x_data};
        assign pend_me = 1'b0; assign pend_q = 1'b0; assign pend_h = 1'b0; assign pend_x = 1'b0;
    end else begin : g_ret_tree
        wire vme, vq, vh, vx;
        ot_v41_vm_dist_pipe #(.W(WME), .D(RSS)) u_ret_me (.clk(clk), .rst_n(rst_n), .v(|u_me_we),
            .d({u_me_we, u_me_addr, u_me_mask, u_me_data}), .v_o(vme),
            .d_o({vw_me_we, vw_me_addr, vw_me_mask, vw_me_data}), .pending(pend_me));
        ot_v41_vm_dist_pipe #(.W(WQ), .D(RSS)) u_ret_q (.clk(clk), .rst_n(rst_n), .v(|u_q_we),
            .d({u_q_we, u_q_addr, u_q_mask, u_q_data}), .v_o(vq),
            .d_o({ww_q_we, ww_q_addr, ww_q_mask, ww_q_data}), .pending(pend_q));
        ot_v41_vm_dist_pipe #(.W(WQ), .D(RSS)) u_ret_h (.clk(clk), .rst_n(rst_n), .v(|u_h_we),
            .d({u_h_we, u_h_addr, u_h_mask, u_h_data}), .v_o(vh),
            .d_o({ww_h_we, ww_h_addr, ww_h_mask, ww_h_data}), .pending(pend_h));
        ot_v41_vm_dist_pipe #(.W(WX), .D(RSS)) u_ret_x (.clk(clk), .rst_n(rst_n), .v(u_xe_we || u_x_we),
            .d({u_xe_we, u_xe_addr, u_xe_data, u_x_we, u_x_addr, u_x_mask, u_x_data}), .v_o(vx),
            .d_o({vw_xe_we, vw_xe_addr, vw_xe_data, ww_x_we, ww_x_addr, ww_x_mask, ww_x_data}), .pending(pend_x));
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (start && st == S_IDLE) fault <= 1'b0;
        else if (me_fault || su_fault || qe_fault || xu_fault || he_fault ||
                 (FULL_SHAPE && KV_HBM && (win_fault || win_capture_fault)) ||
                 (FULL_SHAPE && (coll_fault || rope_pf_fault ||
                  (st == S_ISSUE && d_unit == 3'd0 &&
                   (d_ctl == 3'd5 || d_ctl == 3'd6) && !rope_ctl_ok)))) fault <= 1'b1;
    end
endmodule
