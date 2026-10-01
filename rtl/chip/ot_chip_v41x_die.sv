`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ADOPTED DeepSeek-V4.1 layer die top: the adopted decode core tile, four
// HBM3E stack interfaces, UCIe to the package peer, the board-link SerDes
// ports, the one-shot collective engine and the package controller.
//
// KV lives in HBM.  u_kv (ot_chip_v41x_kv_prefetch.sv) serves the core's
// KV_HBM handshake: it prefetches each attention op's words from the four
// stacks' KV region into two staging slots and raises kv_ok; runtime K / V
// writes are written through.  Its tests and their verdicts are in
// results/rtl/hdc_v41x_die_top_smoke.json (tools/rtl_chip_v41x_die_smoke.py:
// the focused bench and the one-token die smoke with the KV starting in HBM).
//
// Block list against the die-assembly floorplan study (docs/ARCH_V41_DIE_ASSEMBLY.md,
// results/arch/v41_die_assembly.json ledger.layer.rows, on claude/v41-die-assembly):
//
//   floorplan block                          here
//   spine: sequencer, vector unit, HC        u_tile.u_core (ot_hdc_core_v41x: sequencer, X_SU
//     projection, select, Sinkhorn, ...        vector unit, X_HE HCP, X_SEL select, XU, SFUs)
//   48 tiles, ROM | lane column | ROM        u_tile: the pooled engines' lane columns are the
//                                              core's engine widths (MG, HHW, SUN, SUM, BL); the ROM
//                                              banks beside them are the tile's ROMs.  One core
//                                              drives all tiles: the 48 are a physical partition of
//                                              ONE core's pools, not 48 sequencers
//   block-dot pool / BF16 pool / HCP         u_tile.u_core (X_ME wgt tile, QE, X_ATT, X_IDX pooled)
//   mask-ROM array                           u_tile ROM banks (prog, wrom, hrom, hbank, mbank,
//                                              erom, crom, qlist)
//   HBM3E PHY + controller x 4               g_hbm[0..3].u_hbm (ot_chip_v41x_hbm3e_phy, behavioural),
//                                              K ports shared through g_hbm[s].u_arb
//                                              (ot_chip_v41x_hbm_karb: indexer / KV prefetch)
//   KV / key streamer (one per stack)        key streamer: u_tile.u_kb (the pooled indexer's
//                                              four-stack key path); KV: u_kv (HBM prefetch)
//   KV row staging buffer                    u_kv staging: 2 slots x KV_STG words (256 KiB)
//   HBM request / beat queues                inside u_hbm (model queues) and u_tile.u_qs
//   vector memory                            u_tile.vm
//   one-shot collective engine               u_coll (ot_rom_oneshot_die_px: relay_add3 lever,
//                                              RELAY = 1, ADD_LAT = 3; results/arch/
//                                              v41_collective_levers.json picks) + u_cdma
//   package controller                       u_ctrl (ot_rom_pkg_ctrl_x)
//   fabric router                            u_rtr (ot_rom_fabric_router, 3 ports)
//   package link endpoint                    OUTSIDE the die: the ucie_* / bl_* flit ports are
//                                              ready/valid; the link (ot_rom_pkg_link, PHY, FEC)
//                                              sits between dies in the package / board model
//   UCIe-A modules (package peer)            ucie_* ports: fabric flits, collective records to
//                                              the in-package peer, relay records
//   112G SerDes lanes                        bl_* ports: stage-hop flits, T1 collective records
//                                              to the two partner-package dies
//   Engram gather slices                     u_tile.u_core X_EG gather (one ROM port stands in)
//   PLL / clock / reset / DFT                clk in (one clock domain; the plan's regional trees
//                                              and mesochronous crossings are not modelled), reset
//                                              synchroniser, no DFT
//
// HBM MAP (per stack, 32-byte sectors; checked at elaboration, and at run time
// on every KV prefetch sector and every K request):
//   [0, KEY_USERS * IKH_SLICE)             index keys (the pooled indexer's user slices)
//   [KV_SBASE, KV_SBASE + KV_SECTORS)      attention KV, KV_SBASE = the keys' end
//   K_MEM                                  the stack model's capacity (a request past it faults)
// Defaults (reduced vehicle, one user): IKH_SLICE = 2^18, KV_SBASE = 2^18,
// KV_SECTORS = 2 * (KV_USERS * 2^KV_AW / 4) = 2^14, K_MEM = 2^19.
//
// KV INTERFACE (declared stable; changes are flagged):
//   tile -> die, the core's KV_HBM handshake (ot_hdc_core_v41x, KV_HBM = 1):
//     kvd_v          1   pulse when the sequencer decodes an attention-class ME op
//     kvd_wbase      24  KV word base of the op        kvd_ts, kvd_ks, kvd_js  24 each: strides
//     kvd_tiles      16  output tiles                  kvd_k   16: k steps (words per tile)
//     kvd_nout       16  outputs                       kvd_pos 16: position
//     kvd_hg         2   head-group shift              kvd_mmode 1: masked mode
//     kv_ok          1   die -> core: the newest descriptor's words are staged; the
//                        core holds the op's issue until kv_ok (and one cycle after kvd_v)
//   KV port (latency 1, no stall): kv_re, kv_raddr[4 x 24] -> kv_q[4 x 512];
//     element writes kv_we[SW], kv_waddr[SW x 24], kv_wdata[SW x 32] and
//     xs_kv_we[SUN], xs_kv_waddr[SUN x 24], xs_kv_wdata[SUN x 32]
//     (address = word << 4 | lane).
//   Address layout: an op reads words A(c) = wbase + t*ts + k*ks, c = t*k_n + k,
//     t < tiles * (4 >> hg), k < k_n (js = 0), G = 4 a cycle in order c.  Word A
//     of the running user is U = kv_base + A (host mode: 0): stack U mod 4,
//     sectors KV_SBASE + 2 (U >> 2) + {0, 1} (low half first).
//   Each stack's K port: 32 pseudo-channel request / response ports of the
//     ot_hdc_v41x_idx_hbm protocol with 17-bit tags, the top bit the requester
//     (0 the pooled indexer's bridge, 1 the KV prefetch), arbitrated per channel
//     (ot_chip_v41x_hbm_karb).
//
// STAND-INS AND LIMITS:
//   * The KV prefetch issues one word request a cycle; its cost shows as the
//     smoke's cycle difference against the adopted single-token gate.
//   * The HBM3E interfaces are the adopted gates' simulation timing models, not
//     PHY RTL.
//   * One collective engine (the ledger has 8 per die, one per pattern and
//     level), GW = 1: the gather lever gw4 needs a GW-word result port.  The
//     package controller, router, collective engine and link ports are linted
//     and synthesised, not exercised by the smoke.
// ---------------------------------------------------------------------------
module ot_chip_v41x_die #(
    parameter integer FULL_SHAPE = 0,
    // tile (core + ROM + buffers)
    parameter integer SW      = 8,
    parameter integer MG      = 8,
    parameter integer MBAW    = FULL_SHAPE ? 18 : 17,
    parameter integer HHW     = 8,
    parameter integer HBAW    = 16,
    parameter integer SUN     = 16,
    parameter integer SUM     = 8,
    parameter integer PROG_AW = 14,
    parameter integer WROM_AW = 19,
    parameter integer HROM_AW = 16,
    parameter integer EROM_AW = 19,
    parameter integer CROM_AW = 15,
    parameter integer VM_AW   = FULL_SHAPE ? 19 : 16,
    // opt-in distributed vector memory (ot_chip_v41x_tile VM_DIST; spec results/floorplan/v41_vm_dist_spec.json)
    parameter integer VM_DIST = 0,
    parameter integer X_GATHER_STAGES = 10,
    parameter integer RET_SCATTER_STAGES = 10,
    parameter integer SU_RES_STAGES = 7,
    // the stream unit's broadcast / return stages (ot_hdc_core_v41x SUBCAST / SURET) and option H of the distributed
    // VM (ot_hdc_core_v41x VM_DIST_H: the residual rotate / gather / scalar networks, held per op)
    parameter integer SUBCAST = 0,
    parameter integer SURET = 0,
    parameter integer SU_EWR_STAGES = 1,
    parameter integer VM_DIST_H = 0,
    parameter integer SU_ROT_STAGES = 17,
    parameter integer SU_GATH_STAGES = 18,
    parameter integer SU_SCAL_STAGES = 8,
    parameter integer COLL_WRITE_STAGES = 15,
    // C_rotate VM (ot_chip_v41x_tile VM_CROT; rtl/chip/ot_v41_vm_crot.sv)
    parameter integer VM_CROT = 0,
    parameter integer CR_LEAD = 1,
    parameter integer CR_RD = 8,
    parameter integer CR_GX = 1,
    parameter integer CR_WR = 8,
    parameter integer CR_RES = 8,
    parameter integer LWIN    = 10,
    parameter integer LAW     = 12,
    parameter integer NPC_W   = 8,
    parameter integer W_HBM   = 1,
    parameter integer IDX_SHARDED = 0, // opt-in; reader and writer must share one layout
    parameter integer IDX_RING = 0,    // opt-in W11 quarter-per-stack ring key layout (replaces the replicated
                                       // key images: ot_hdc_v41x_idx_ring_port in the tile, ring readers in
                                       // the pooled adapter); regions are rings of IDX_RING_RSB super-blocks
    parameter integer IDX_RING_RSB = 1,   // + an IDX_RING_RTAIL-key tail at the legacy region base
    parameter integer IDX_RING_RTAIL = 0,
    parameter integer IDX_RING_MU = 0,    // opt-in with IDX_RING: key the index-key user base from the step's
                                          // 10-bit user id (host_user / the controller's core_user): user u's
                                          // key slice is [u IKH_SLICE, (u+1) IKH_SLICE) sectors, its key region
                                          // r at block u IKH_SLICE / 128 + r UBLK (UBLK = 17 IDX_RING_RSB + tail);
                                          // 0: the key user base is tied low (one user)
    parameter bit WINDOW_RETAIN_L0 = 0, // opt-in single-use QK->PV packed-stage retention
    parameter bit WINDOW_HBM_ATTENTION = 0, // opt-in L0 WINDOW-only internal source
    parameter bit KARB_LOCAL = 0,  // opt-in: per-PC local K arbitration (ot_chip_v41x_hbm_karb_local)
    parameter bit KARB_FENCE = 1,  // with KARB_LOCAL: explicit same-PC K read-after-write fence
    parameter integer WINDOW_REFILL_CREDITS = 1, // opt-in bounded tagged WINDOW refill (8: results/rtl/v41x_window_refill_credits.json)
    parameter bit WINDOW_STREAM_II1 = 0,  // opt-in one-beat-a-cycle packed WINDOW stream
    // Tile engine selection. Defaults are the adopted all-unit tile; focused
    // connected-execution gates may select the as-built units of engines their
    // program slice never issues (the tile's own X_* meanings).
    parameter integer X_HE  = 1,
    parameter integer X_ME  = 1,
    parameter integer X_IDX = 2,
    parameter integer X_SEL = 1,
    parameter integer X_EG  = 1,
    // HBM address map and KV prefetch
    parameter integer K_HAW   = FULL_SHAPE ? 30 : 28, // HBM sector address
    parameter integer KEY_USERS = 1,          // index-key user slices (the pooled indexer's)
    parameter integer IKH_SLICE = 1 << 18,    // index-key sectors a user slice
    parameter integer KV_USERS  = 1,          // attention-KV user slices
    parameter integer KV_AW   = 15,           // KV words a user slice (log2)
    parameter integer K_MEM   = 1 << 19,      // K-port sectors a stack (the model's capacity)
    parameter integer ROPE_MAX_POS = 1048576, // rows in each deployed read-only table
    parameter integer KV_STG  = 2048,         // KV staging words a slot (two slots)
    parameter integer KV_SAW  = 11,
    parameter integer KV_WQD  = 128,          // KV write-queue sectors a stack
    parameter integer WIN_STACK = 0,          // stack holding the packed FP8 window ring
    parameter integer W_MEM   = 1 << 20,
    parameter integer W_STACK = 0,            // stack that holds the QE weight region
    parameter integer CLK_PS  = 1000,
    // tensor group: die RANK of N (package pairs, PKG_DIES dies a package)
    parameter integer RANK    = 0,
    parameter integer N_TP    = 4,
    parameter integer PKG_DIES = 2,
    parameter integer CL_LANES = 16,
    // GW4 requires 256 receive words to cover the T1 credit round trip.
    // The reduced one-word interface retains its qualified 16-word depth.
    parameter integer CL_DEPTH = FULL_SHAPE ? 256 : 16,
    parameter integer CL_RELAY = 1,
    parameter integer CL_ADD_LAT = 3,
    parameter integer CL_TAGW = 32,
    // fabric (router ports: 0 package controller, 1 UCIe, 2 board link)
    parameter integer DESTS   = 64,
    parameter [DESTS*3-1:0] ROUTE_INIT = {DESTS*3{1'b0}},
    // package controller (ot_rom_pkg_ctrl_x)
    parameter integer PKG_ID   = 0,
    parameter integer MAXU     = FULL_SHAPE ? 866 : 16,
    parameter integer KVW      = 32768,
    parameter integer XWORDS   = 1,
    parameter integer RXWORDS  = 1,
    parameter integer RXB      = 0,
    parameter integer TXB      = 0,
    parameter integer SOURCE   = 0,
    parameter integer RESULT_PARTS = 1,
    parameter integer SEND_HIDDEN  = 0,
    parameter integer HID_DEST     = 0,
    parameter integer SEND_RESULT  = 0,
    parameter integer RES_DEST     = 0,
    parameter integer COMBINE_IN   = 0,
    parameter integer ROW0         = 0,
    parameter integer FWD_TOKEN    = 1,
    // derived
    parameter integer CL_FW   = 32 * CL_LANES,
    parameter integer CL_PW   = CL_FW + 3 + CL_TAGW
) (
    input  wire              clk,
    input  wire              rst_n,            // asynchronous assert, synchronised release
    // -- host / CSR ----------------------------------------------------------------------
    input  wire              host_mode,        // 1: the host drives the core's step port; 0: u_ctrl does
    input  wire              host_start,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] host_token,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] host_pos,
    input  wire [9:0]        host_user,        // packed window owner in host mode
    input  wire [13:0]       host_entry,
    input  wire              host_prime_v,
    input  wire              host_prime_first,
    input  wire [11:0]       host_prime_cid,
    // Runtime-verified packed WINDOW region. The unapproved candidate ledger
    // is never silently bound as a die address map.
    input  wire              window_region_valid,
    input  wire [K_HAW-1:0]  window_region_base,
    input  wire [K_HAW-1:0]  window_region_count,
    input  wire              window_prime_v,
    output wire              window_prime_ready,
    input  wire [9:0]        window_prime_user,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] window_prime_row,
    output wire              core_done,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] core_next_token,
    output wire [31:0]       core_next_val,
    output wire [31:0]       core_cycles,
    output wire [3:0]        core_acc_n,
    // Full-shape packed attention service boundary. A harness or array
    // service stages one tagged descriptor and supplies chronological stored
    // rows. This is an external service boundary until the die HBM source is
    // wired; reduced mode retains the existing KV prefetch.
    output wire              att_packed_desc_v,
    output wire              att_packed_desc_accept,
    output wire [15:0]       att_packed_desc_gen,
    output wire [10:0]       att_packed_desc_rows,
    output wire [9:0]        att_packed_desc_user,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] att_packed_desc_pos,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] att_packed_desc_tiles,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] att_packed_desc_nout,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] att_packed_desc_k,
    output wire [1:0]        att_packed_desc_hg,
    output wire              att_packed_desc_mmode,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] att_packed_desc_wbase,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] att_packed_desc_ts,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] att_packed_desc_ks,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] att_packed_desc_js,
    input  wire              att_packed_stage_v,
    input  wire [15:0]       att_packed_stage_gen,
    input  wire [10:0]       att_packed_stage_rows,
    input  wire              att_packed_wrap_drained,
    input  wire              att_packed_kv_v,
    output wire              att_packed_kv_ready,
    input  wire [15:0]       att_packed_kv_gen,
    input  wire [3:0]        att_packed_kv_m,
    input  wire [4*((FULL_SHAPE ? 512 : 32)/32)*265-1:0] att_packed_kv_w,
    input  wire              att_packed_kv_fault,
    output wire              att_packed_desc_done,
    output wire              att_packed_desc_fault,
    output wire [3:0]        att_packed_desc_fault_code,
    input  wire [(FULL_SHAPE ? 30 : 24)-1:0] cfg_ik_base,
    input  wire [3:0]        cfg_me_xs,
    input  wire [(FULL_SHAPE ? 30 : 24)-1:0] cfg_q_base,
    input  wire [LAW-1:0]    cfg_q_lbase,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] cfg_q_lead,
    input  wire [15:0]       cfg_q_rate,
    // External logical QE ROM service when W_HBM=0. The physical 274-bit
    // qtile bank mapping is a separate implementation boundary.
    output wire              qr_compact_re,
    output wire [(FULL_SHAPE ? 30 : 24)-1:0] qr_compact_addr,
    input  wire              qr_compact_valid,
    input  wire              qr_compact_fp4,
    input  wire [4351:0]     qr_compact_fp8,
    input  wire [2303:0]     qr_compact_fp4_word,
    // Runtime HBM region placement. reserved_end includes keys, window KV,
    // selected CKV and all other state on each stack; zero fails closed.
    input  wire [1:0]        rope_table_present,
    input  wire [4*K_HAW-1:0] rope_reserved_end,
    input  wire [4*K_HAW-1:0] rope_plain_base,
    input  wire [4*K_HAW-1:0] rope_yarn_base,
    input  wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] cfg_users,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] cfg_prompt_len,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] cfg_gen_len,
    output wire              pr_re,
    output wire [(FULL_SHAPE ? 10 : 8)-1:0] pr_user,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] pr_pos,
    input  wire [(FULL_SHAPE ? 21 : 16)-1:0] pr_q,
    output wire              tok_valid,
    output wire [(FULL_SHAPE ? 10 : 8)-1:0] tok_user,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] tok_pos,
    output wire [(FULL_SHAPE ? 21 : 16)-1:0] tok_id,
    output wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] users_done,
    input  wire              rcfg_we,
    input  wire [7:0]        rcfg_dest,
    input  wire [2:0]        rcfg_mask,
    input  wire              coll_go,
    input  wire              coll_mode,
    input  wire [CL_TAGW-1:0] coll_tag,
    input  wire [VM_AW-5:0]  coll_src,
    input  wire [VM_AW-5:0]  coll_n,
    input  wire [VM_AW-5:0]  coll_dst,
    output wire              coll_busy,
    // -- UCIe to the package peer ------------------------------------------------------------
    output wire              ucie_tx_valid,
    input  wire              ucie_tx_ready,
    output wire [511:0]      ucie_tx_data,
    output wire              ucie_tx_last,
    input  wire              ucie_rx_valid,
    output wire              ucie_rx_ready,
    input  wire [511:0]      ucie_rx_data,
    input  wire              ucie_rx_last,
    output wire              ucie_ctx_valid,   // collective records to the peer
    input  wire              ucie_ctx_ready,
    output wire [CL_PW-1:0]  ucie_ctx_rec,
    input  wire [1:0]        ucie_ccr_in,      // parity credits from the peer
    input  wire              ucie_crx_valid,   // collective records from the peer
    input  wire [CL_PW-1:0]  ucie_crx_rec,
    output wire [1:0]        ucie_ccr_out,
    output wire [N_TP-1:0]   ucie_rl_tx_valid, // relay records to the peer, per source rank
    output wire [N_TP*CL_PW-1:0] ucie_rl_tx_rec,
    input  wire [N_TP-1:0]   ucie_rl_rx_valid,
    input  wire [N_TP*CL_PW-1:0] ucie_rl_rx_rec,
    // -- board-link SerDes ------------------------------------------------------------------
    output wire              bl_tx_valid,      // stage-hop flits
    input  wire              bl_tx_ready,
    output wire [511:0]      bl_tx_data,
    output wire              bl_tx_last,
    input  wire              bl_rx_valid,
    output wire              bl_rx_ready,
    input  wire [511:0]      bl_rx_data,
    input  wire              bl_rx_last,
    output wire [PKG_DIES-1:0] bl_ctx_valid,   // T1 collective records to the partner package's dies
    input  wire [PKG_DIES-1:0] bl_ctx_ready,
    output wire [CL_PW-1:0]  bl_ctx_rec,
    input  wire [2*PKG_DIES-1:0] bl_ccr_in,
    input  wire [PKG_DIES-1:0] bl_crx_valid,
    input  wire [PKG_DIES*CL_PW-1:0] bl_crx_rec,
    output wire [2*PKG_DIES-1:0] bl_ccr_out,
    // -- status -----------------------------------------------------------------------------
    output wire [7:0]        fault,            // {HBM out of range, KV prefetch, rtr overflow, coll, ctrl proto,
                                               //  qstream, 0, core}, sticky
    output wire [4:0]        unit_busy,
    output wire [2:0]        issue_unit,
    output wire [31:0]       qs_fetched,
    output wire [31:0]       qs_consumed,
    output wire [3:0]        qs_why,
    output wire [31:0]       kb_records,
    output wire [31:0]       kb_writes,
    output wire [31:0]       kb_highwater,
    output wire [31:0]       kb_stalls,
    output wire [63:0]       hbm_refreshes,
    output wire [31:0]       hbm_w_reads,
    output wire [31:0]       rtr_drops,
    output wire [31:0]       kv_ops,
    output wire [31:0]       kv_words,
    output wire [31:0]       kv_sectors_written,
    output wire [31:0]       kv_refetches,
    output wire [31:0]       kv_wq_high,
    output wire [31:0]       kv_hold_cycles,
    output wire [31:0]       kv_hbm_grants,
    output wire [4:0]        kv_fault_code,
    output wire              rope_region_ok,
    output wire              rope_fault,
    output wire [31:0]       rope_hbm_grants,
    output wire [31:0]       rope_hbm_wait_cycles
);
    localparam integer AW = FULL_SHAPE ? 30 : 24;
    localparam integer NW = FULL_SHAPE ? 21 : 16;
    localparam integer G = 4, W = 16, FLIT = 512;
    localparam integer VWA = VM_AW - 4;
    localparam integer PEER = RANK ^ 1;
    localparam integer CL_RB = (N_TP > 1) ? $clog2(N_TP) : 1;

    // -- reset synchroniser ----------------------------------------------------------------
    reg [1:0] rst_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];

    // -- core step port: host or package controller ------------------------------------------
    wire c_start; wire [NW-1:0] c_token, c_pos; wire [AW-1:0] kv_base;
    wire [(FULL_SHAPE ? 10 : 8)-1:0] c_user;
    reg [9:0] step_user;
    reg capture_ctrl_user;
    wire t_start = host_mode ? host_start : c_start;
    wire [NW-1:0] t_token = host_mode ? host_token : c_token;
    wire [NW-1:0] t_pos = host_mode ? host_pos : c_pos;
    // The controller registers core_user on the same edge as core_start.
    // Capture that new value one edge later; host mode captures at start.
    // QDQ8 block production follows the start edge by many core cycles.
    always @(posedge clk or negedge rn)
        if (!rn) begin step_user <= 0; capture_ctrl_user <= 0; end
        else begin
            capture_ctrl_user <= !host_mode && c_start;
            if (host_mode && host_start) step_user <= host_user;
            if (capture_ctrl_user) step_user <= 10'(c_user);
        end
    wire t_fault, qs_fault, kb_busy;
    // IDX_RING_MU: the step's index-key user base (sampled by the tile with the step's start); a user id
    // at or past KEY_USERS faults (its slice would overlap the KV region)
    wire [9:0] key_user = host_mode ? host_user : 10'(c_user);
    wire [K_HAW-1:0] idx_key_user_base = (IDX_RING_MU != 0) ? K_HAW'(key_user) * K_HAW'(IKH_SLICE) : '0;
    reg key_user_fault;
    always @(posedge clk or negedge rn)
        if (!rn) key_user_fault <= 1'b0;
        else if (IDX_RING_MU != 0 && t_start && 32'(key_user) >= KEY_USERS) key_user_fault <= 1'b1;
    initial if (IDX_RING_MU != 0 && (IDX_RING == 0 || IKH_SLICE % 128 != 0))
        $fatal(1, "ot_chip_v41x_die: IDX_RING_MU needs IDX_RING and a block-aligned IKH_SLICE");
    wire [31:0] kb_rs, kb_ws;
    assign kb_stalls = kb_rs + kb_ws;

    // -- tile <-> die wiring ---------------------------------------------------------------------
    wire kv_re; wire [G*AW-1:0] kv_raddr; wire [G*W*32-1:0] kv_q;
    wire [SW-1:0] kv_we; wire [SW*AW-1:0] kv_waddr; wire [SW*32-1:0] kv_wdata;
    wire [SUN-1:0] xs_kv_we; wire [SUN*AW-1:0] xs_kv_waddr; wire [SUN*32-1:0] xs_kv_wdata;
    wire wq_v, wq_rdy; wire [(FULL_SHAPE ? 30 : 24)-1:0] wq_addr; wire [5:0] wq_len; wire [LWIN-1:0] wq_tag;
    wire [NPC_W-1:0] wq_room, wr_v, wr_rdy; wire [NPC_W*LWIN-1:0] wr_tag;
    wire [NPC_W*5-1:0] wr_beat; wire [NPC_W*256-1:0] wr_data;
    wire [127:0] kh_v, kh_rdy, kh_we, kh_wr_done, kr_v, kr_rdy;
    wire [128*K_HAW-1:0] kh_addr; wire [128*4-1:0] kh_len, kr_beat; wire [128*16-1:0] kh_tag, kr_tag;
    wire [128*256-1:0] kh_wdata, kr_data; wire [128*32-1:0] kh_wstrb;
    wire kvd_v, kv_ok, kvd_mmode; wire [AW-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js;
    wire [NW-1:0] kvd_tiles, kvd_k, kvd_nout, kvd_pos; wire [1:0] kvd_hg;
    wire win_service_v, win_service_staged, win_service_done, win_service_fault;
    wire win_service_busy, win_service_start_ready, tile_packed_ready;
    wire [3:0] win_service_m;
    wire [4*16*265-1:0] win_service_w;
    reg [15:0] win_service_gen;
    wire tile_packed_v = WINDOW_HBM_ATTENTION ? win_service_v : att_packed_kv_v;
    wire [3:0] tile_packed_m = WINDOW_HBM_ATTENTION ? win_service_m : att_packed_kv_m;
    wire [4*16*265-1:0] tile_packed_w = WINDOW_HBM_ATTENTION ? win_service_w : att_packed_kv_w;
    wire tile_packed_fault = WINDOW_HBM_ATTENTION ? win_service_fault : att_packed_kv_fault;
    assign att_packed_kv_ready = WINDOW_HBM_ATTENTION ? 1'b0 : tile_packed_ready;
    assign att_packed_desc_v = FULL_SHAPE && kvd_v;
    assign att_packed_desc_user = step_user;
    assign att_packed_desc_pos = kvd_pos;
    assign att_packed_desc_tiles = kvd_tiles;
    assign att_packed_desc_nout = kvd_nout;
    assign att_packed_desc_k = kvd_k;
    assign att_packed_desc_hg = kvd_hg;
    assign att_packed_desc_mmode = kvd_mmode;
    assign att_packed_desc_wbase = kvd_wbase;
    assign att_packed_desc_ts = kvd_ts;
    assign att_packed_desc_ks = kvd_ks;
    assign att_packed_desc_js = kvd_js;
    wire att_packed_issue, att_packed_idle, packed_desc_ok;
    wire rope_pf_v, rope_pf_rdy, rope_pf_kind, rope_pf_done, rope_pf_release, rope_pf_fault;
    wire [NW-1:0] rope_pf_pos, rope_cache_pos;
    wire rope_cache_valid, rope_cache_hold, rope_cache_kind;
    wire [2047:0] rope_cache_pairs;
    wire win_blk_v, win_blk_ready;
    wire [9:0] win_blk_user;
    wire [AW-1:0] win_blk_kvt_base, win_blk_first_elem;
    wire [NW-1:0] win_blk_row, win_blk_kvt_row;
    wire [3:0] win_blk_idx;
    wire [255:0] win_blk_codes;
    wire [7:0] win_blk_scale;
    wire xa_we, xa_re, xb_we, xb_re; wire [VWA-1:0] xa_waddr, xa_raddr, xb_waddr, xb_raddr;
    wire [3:0] xb_we4; wire [4*VWA-1:0] xb_waddr4; wire [4*512-1:0] xb_wdata4;
    wire [511:0] xa_wdata, xa_rq, xb_wdata, xb_rq;
    localparam integer COLL_AW = FULL_SHAPE ? 30 : 24;
    localparam integer COLL_NW = FULL_SHAPE ? 21 : 16;
    wire core_coll_go, core_coll_rnd;
    wire [1:0] core_coll_op;
    wire [COLL_AW-1:0] core_coll_src, core_coll_dst, core_coll_ibase;
    wire [COLL_NW-1:0] core_coll_n;
    wire [11:0] core_coll_k;
    wire [7:0] core_coll_seq;
    wire die_coll_fault;

    ot_chip_v41x_tile #(.FULL_SHAPE(FULL_SHAPE), .X_HE(X_HE), .X_ME(X_ME), .X_IDX(X_IDX), .X_SEL(X_SEL), .X_EG(X_EG), .PIKH_HAW(K_HAW), .IDX_SHARDED(IDX_SHARDED), .IDX_RING(IDX_RING), .IDX_RING_RSB(IDX_RING_RSB), .IDX_RING_RTAIL(IDX_RING_RTAIL), .IDX_MULTIUSER(IDX_RING_MU), .IDX_KEY_SLICE_SECTORS((IDX_RING_MU != 0) ? IKH_SLICE : 0), .SW(SW), .HHW(HHW), .HBAW(HBAW), .MG(MG), .MBAW(MBAW), .SUN(SUN), .SUM(SUM), .W_HBM(W_HBM),
                        .NPC_W(NPC_W), .LWIN(LWIN), .LAW(LAW), .PROG_AW(PROG_AW), .WROM_AW(WROM_AW),
                        .HROM_AW(HROM_AW), .EROM_AW(EROM_AW), .CROM_AW(CROM_AW), .VM_AW(VM_AW),
                        .VM_DIST(VM_DIST), .X_GATHER_STAGES(X_GATHER_STAGES), .RET_SCATTER_STAGES(RET_SCATTER_STAGES),
                        .SU_RES_STAGES(SU_RES_STAGES), .COLL_WRITE_STAGES(COLL_WRITE_STAGES),
                        .SUBCAST(SUBCAST), .SURET(SURET), .SU_EWR_STAGES(SU_EWR_STAGES), .VM_DIST_H(VM_DIST_H),
                        .SU_ROT_STAGES(SU_ROT_STAGES), .SU_GATH_STAGES(SU_GATH_STAGES), .SU_SCAL_STAGES(SU_SCAL_STAGES),
                        .VM_CROT(VM_CROT), .CR_LEAD(CR_LEAD), .CR_RD(CR_RD), .CR_GX(CR_GX), .CR_WR(CR_WR),
                        .CR_RES(CR_RES)) u_tile (
        .clk(clk), .rst_n(rn),
        .start(t_start), .token(t_token), .pos(t_pos), .entry(host_mode ? host_entry : 14'd0),
        .done(core_done), .next_token(core_next_token), .next_val(core_next_val), .cycles(core_cycles),
        .fault(t_fault), .acc_n(core_acc_n),
        .prime_v(host_prime_v), .prime_first(host_prime_first), .prime_cid(host_prime_cid),
        .window_user(step_user),
        .win_blk_v(win_blk_v), .win_blk_ready(win_blk_ready), .win_blk_user(win_blk_user),
        .win_blk_kvt_base(win_blk_kvt_base), .win_blk_row(win_blk_row),
        .win_blk_kvt_row(win_blk_kvt_row), .win_blk_idx(win_blk_idx),
        .win_blk_first_elem(win_blk_first_elem), .win_blk_codes(win_blk_codes), .win_blk_scale(win_blk_scale),
        .cfg_ik_base(cfg_ik_base), .idx_user_base_sec(idx_key_user_base), .cfg_me_xs(cfg_me_xs), .cfg_q_base(cfg_q_base), .cfg_q_lbase(cfg_q_lbase),
        .cfg_q_lead(cfg_q_lead), .cfg_q_rate(cfg_q_rate),
        .qr_compact_re(qr_compact_re), .qr_compact_addr(qr_compact_addr),
        .qr_compact_valid(qr_compact_valid), .qr_compact_fp4(qr_compact_fp4),
        .qr_compact_fp8(qr_compact_fp8), .qr_compact_fp4_word(qr_compact_fp4_word),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .att_packed_kv_v(tile_packed_v), .att_packed_kv_ready(tile_packed_ready),
        .att_packed_kv_m(tile_packed_m), .att_packed_kv_w(tile_packed_w),
        .att_packed_kv_fault(tile_packed_fault),
        .att_packed_issue(att_packed_issue), .att_packed_idle(att_packed_idle),
        .xs_kv_we(xs_kv_we), .xs_kv_waddr(xs_kv_waddr), .xs_kv_wdata(xs_kv_wdata),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout), .kvd_hg(kvd_hg), .kvd_mmode(kvd_mmode),
        .kvd_pos(kvd_pos), .kv_ok(kv_ok),
        .rope_pf_v(rope_pf_v), .rope_pf_rdy(rope_pf_rdy), .rope_pf_kind(rope_pf_kind),
        .rope_pf_pos(rope_pf_pos), .rope_pf_done(rope_pf_done),
        .rope_pf_release(rope_pf_release), .rope_pf_fault(rope_pf_fault),
        .rope_cache_valid(rope_cache_valid), .rope_cache_hold(rope_cache_hold),
        .rope_cache_kind(rope_cache_kind), .rope_cache_pos(rope_cache_pos),
        .rope_cache_pairs(rope_cache_pairs),
        .wq_v(wq_v), .wq_rdy(wq_rdy), .wq_addr(wq_addr), .wq_len(wq_len), .wq_tag(wq_tag), .wq_room(wq_room),
        .wr_v(wr_v), .wr_rdy(wr_rdy), .wr_tag(wr_tag), .wr_beat(wr_beat), .wr_data(wr_data),
        .kh_v(kh_v), .kh_rdy(kh_rdy), .kh_addr(kh_addr), .kh_len(kh_len), .kh_tag(kh_tag), .kh_we(kh_we),
        .kh_wdata(kh_wdata), .kh_wstrb(kh_wstrb), .kh_wr_done(kh_wr_done),
        .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data),
        .xa_we(xa_we), .xa_waddr(xa_waddr), .xa_wdata(xa_wdata), .xa_re(xa_re), .xa_raddr(xa_raddr), .xa_rq(xa_rq),
        .xb_we4(xb_we4), .xb_waddr4(xb_waddr4), .xb_wdata4(xb_wdata4),
        .xb_re(xb_re), .xb_raddr(xb_raddr), .xb_rq(xb_rq),
        .coll_go(core_coll_go), .coll_op(core_coll_op), .coll_src(core_coll_src), .coll_dst(core_coll_dst),
        .coll_ibase(core_coll_ibase), .coll_n(core_coll_n), .coll_k(core_coll_k), .coll_seq(core_coll_seq),
        .coll_rnd(core_coll_rnd), .coll_busy(coll_busy), .coll_fault(die_coll_fault),
        .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qs_fault(qs_fault), .qs_why(qs_why), .qs_fetched(qs_fetched), .qs_consumed(qs_consumed),
        .kb_busy(kb_busy), .kb_records(kb_records), .kb_writes(kb_writes), .kb_highwater(kb_highwater),
        .kb_read_stalls(kb_rs), .kb_writer_stalls(kb_ws));

    // -- HBM address map (per stack, 32-byte sectors) ----------------------------------------------
    //   [0, KEY_SECTORS)                      index keys: the pooled indexer's user slices of IKH_SLICE
    //                                         sectors (its bridge addresses csec / ssec < IKH_SLICE a user)
    //   [KV_SBASE, KV_SBASE + KV_SECTORS)     attention KV: KV_USERS slices of 2^KV_AW words, a word on
    //                                         stack U mod 4 as two sectors at KV_SBASE + 2 (U >> 2)
    localparam integer KEY_SECTORS = KEY_USERS * IKH_SLICE;
    localparam integer KV_SBASE    = KEY_SECTORS;
    localparam integer KV_SECTORS  = 2 * ((KV_USERS << KV_AW) / 4);
    localparam integer WIN_SECTORS = KV_USERS * 128 * 17;

    // -- attention KV prefetch (the core's KV_HBM handshake) ------------------------------------------
    wire [3:0] pm_v, pm_rdy, pm_we, ps_v, ps_rdy, pk_wd;
    wire [4*K_HAW-1:0] pm_addr; wire [4*4-1:0] pm_len, ps_beat; wire [4*16-1:0] pm_tag, ps_tag;
    wire [4*256-1:0] pm_wdata, ps_data; wire [4*32-1:0] pm_wstrb;
    wire kv_fault; wire [4:0] kv_code;
    generate if (!FULL_SHAPE) begin : g_reduced_kv
    assign win_service_v=1'b0; assign win_service_m=4'd0;
    assign win_service_w=16960'd0; assign win_service_staged=1'b0;
    assign win_service_done=1'b0; assign win_service_fault=1'b0;
    assign win_service_busy=1'b0; assign win_service_start_ready=1'b1; assign window_prime_ready=1'b0;
        assign att_packed_desc_accept = 1'b0;
        assign att_packed_desc_gen = 16'd0;
        assign att_packed_desc_rows = 11'd0;
        assign att_packed_desc_done = 1'b0;
        assign att_packed_desc_fault = 1'b0;
        assign att_packed_desc_fault_code = 4'd0;
    assign rope_pf_rdy=1'b0; assign rope_pf_done=1'b0; assign rope_pf_fault=1'b0;
    assign rope_cache_valid=1'b0; assign rope_cache_hold=1'b0;
    assign rope_cache_kind=1'b0; assign rope_cache_pos='0; assign rope_cache_pairs='0;
    assign rope_region_ok=1'b0; assign rope_fault=1'b0;
    assign rope_hbm_grants=0; assign rope_hbm_wait_cycles=0;
    assign win_blk_ready = 1'b0;
    ot_chip_v41x_kv_prefetch #(.G(G), .W(W), .SW(SW), .SUN(SUN), .AW(AW), .STG(KV_STG), .SAW(KV_SAW),
                               .KV_SBASE(KV_SBASE), .KV_SECTORS(KV_SECTORS), .HAW(K_HAW), .TAGW(16), .WQD(KV_WQD)) u_kv (
        .clk(clk), .rst_n(rn), .base(host_mode ? {AW{1'b0}} : kv_base),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_hg(kvd_hg), .kv_ok(kv_ok),
        .re(kv_re), .raddr(kv_raddr), .q(kv_q), .we(kv_we), .waddr(kv_waddr), .wdata(kv_wdata),
        .xwe(xs_kv_we), .xwaddr(xs_kv_waddr), .xwdata(xs_kv_wdata),
        .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len), .m_tag(pm_tag), .m_we(pm_we),
        .m_wdata(pm_wdata), .m_wstrb(pm_wstrb), .s_v(ps_v), .s_rdy(ps_rdy), .s_tag(ps_tag), .s_beat(ps_beat),
        .s_data(ps_data), .fault(kv_fault), .fault_code(kv_code), .st_ops(kv_ops), .st_words(kv_words),
        .st_sectors_written(kv_sectors_written), .st_refetches(kv_refetches), .st_wq_high(kv_wq_high),
        .st_hold_cycles(kv_hold_cycles));
    end else begin : g_packed_kv
        wire [10:0] life_beats;
        ot_chip_v41x_attn_desc_lifecycle #(.AW(AW), .NW(NW), .L0_ONLY(1)) u_desc_life (
            .clk(clk), .rst_n(rn), .desc_v(kvd_v && (!WINDOW_RETAIN_L0 || !WINDOW_HBM_ATTENTION || win_service_start_ready || win_service_busy)), .desc_user(step_user),
            .desc_pos(kvd_pos), .desc_tiles(kvd_tiles), .desc_k(kvd_k), .desc_nout(kvd_nout),
            .desc_wbase(kvd_wbase), .desc_ts(kvd_ts), .desc_ks(kvd_ks), .desc_js(kvd_js),
            .desc_hg(kvd_hg), .desc_mmode(kvd_mmode),
            .desc_accept(att_packed_desc_accept), .desc_gen(att_packed_desc_gen),
            .desc_rows(att_packed_desc_rows),
            .stage_v(WINDOW_HBM_ATTENTION ? win_service_staged : att_packed_stage_v),
            .stage_gen(WINDOW_HBM_ATTENTION ? win_service_gen : att_packed_stage_gen),
            .stage_rows(WINDOW_HBM_ATTENTION ? 11'd128 : att_packed_stage_rows),
            .beat_v(tile_packed_v), .beat_ready(tile_packed_ready),
            .beat_gen(WINDOW_HBM_ATTENTION ? win_service_gen : att_packed_kv_gen),
            .beat_mask(tile_packed_m),
            .issue_v(att_packed_issue), .engine_idle(att_packed_idle),
            .service_fault(tile_packed_fault),
            .wrap_drained(WINDOW_HBM_ATTENTION ?
                (!win_service_busy && window_prime_ready && !win_blk_v) :
                att_packed_wrap_drained),
            .issue_ok(packed_desc_ok),
            .done(att_packed_desc_done), .fault(att_packed_desc_fault),
            .fault_code(att_packed_desc_fault_code), .beats_accepted(life_beats));
        // This path publishes only the 128-row FP8 window.  A selected main
        // CKV row is FP4/288 B and needs its SEL source ID plus a remote-row
        // all-gather.  Until the mixed-row scheduler is wired, any legacy
        // scalar KVD read faults and cannot release the core's kv_ok barrier.
        wire [3:0] w_v, w_rdy, w_we, w_wdone, w_sv, w_srdy;
        wire [4*K_HAW-1:0] w_addr;
        wire [15:0] w_len, w_s_beat;
        wire [4*16-1:0] w_tag, w_s_tag;
        wire [1023:0] w_wdata, w_s_data;
        wire [127:0] w_wstrb;
        wire win_fault;
        wire [4:0] win_code;
        wire [31:0] rows_fetched, blocks_written, sectors_read, sectors_written;
        wire packed_valid;
        wire [4223:0] packed_row;
        wire [255:0] packed_codes;
        wire [7:0] packed_scale;
        reg [NW-1:0] step_pos;
        always @(posedge clk or negedge rn)
            if (!rn) step_pos <= '0;
            else if (t_start) step_pos <= t_pos;
        wire bad_block_addr;
        ot_chip_v41x_window_block_guard #(.AW(AW), .POS_W(NW)) u_blk_guard (
            .step_pos(step_pos), .blk_abs_row(win_blk_row),
            .blk_kvt_row(win_blk_kvt_row), .blk_idx(win_blk_idx),
            .kvt_base(win_blk_kvt_base), .first_elem(win_blk_first_elem),
            .hbm_slot(), .expected_first(), .bad(bad_block_addr));
        reg unsupported_read;
        reg bad_block;
        always @(posedge clk or negedge rn)
            if (!rn) begin unsupported_read <= 0; bad_block <= 0; end
            else begin
                if (kv_re) unsupported_read <= 1;
                if (win_blk_v && win_blk_ready && bad_block_addr) bad_block <= 1;
            end
        wire [K_HAW:0] window_region_end = {1'b0,window_region_base} +
                                          {1'b0,window_region_count};
        wire window_region_ok = window_region_valid &&
            window_region_base >= K_HAW'(KEY_SECTORS) &&
            window_region_count >= K_HAW'(WIN_SECTORS) &&
            !window_region_end[K_HAW] &&
            window_region_end <= (K_HAW+1)'(K_MEM);
        wire window_source_start = WINDOW_HBM_ATTENTION &&
            att_packed_desc_accept && window_region_ok && kvd_mmode &&
            att_packed_desc_rows == 11'd128 && kvd_pos >= NW'(127);
        always @(posedge clk or negedge rn)
            if (!rn) win_service_gen <= 16'd0;
            else if (window_source_start) win_service_gen <= att_packed_desc_gen;
        if (WINDOW_HBM_ATTENTION) begin : g_window_hbm_attention
        wire source_fault;
        wire source_prime_ready;
        wire retention_shape = kvd_mmode && kvd_wbase==0 && kvd_js==0 && kvd_hg==1;
        wire retention_qk=retention_shape && kvd_ts==512 && kvd_ks==1 &&
                          kvd_k==512 && kvd_nout==128 && kvd_tiles==4;
        wire retention_pv=retention_shape && kvd_ts==1 && kvd_ks==32 &&
                          kvd_k==128 && kvd_nout==512 && kvd_tiles==16;
        assign window_prime_ready = window_region_ok && source_prime_ready;
        assign win_service_fault = source_fault ||
            (att_packed_desc_accept && !window_region_ok);
        ot_chip_v41x_window_attn_source #(.POS_W(NW), .SEC_W(K_HAW),
            .HAW(K_HAW), .TAGW(16), .USER_W(10), .WIN_STACK(WIN_STACK), .RETAIN_L0(WINDOW_RETAIN_L0),
            .REFILL_CREDITS(WINDOW_REFILL_CREDITS), .STREAM_II1(WINDOW_STREAM_II1)) u_source (
            .clk(clk), .rst_n(rn),
            .retain_qk(retention_qk),.retain_pv(retention_pv),
            .retain_generation(att_packed_desc_gen),
            .retain_complete(att_packed_desc_done && att_packed_idle),
            .retain_invalidate(t_start || !window_region_ok),
            .region_base_sector(window_region_base),
            .region_sector_count(window_region_count),
            .prime_v(window_prime_v && window_region_ok),
            .prime_ready(source_prime_ready),
            .prime_user(window_prime_user), .prime_row(window_prime_row),
            .blk_v(win_blk_v && !bad_block_addr && !bad_block),
            .blk_ready(win_blk_ready), .blk_user(win_blk_user),
            .blk_row(win_blk_row), .blk_idx(win_blk_idx),
            .blk_codes(win_blk_codes), .blk_scale(win_blk_scale),
            .start_v(window_source_start), .start_ready(win_service_start_ready),
            .start_user(step_user), .start_first(kvd_pos - NW'(127)),
            .start_count(8'd128), .staged_v(win_service_staged),
            .stream_go(att_packed_issue),
            .busy(win_service_busy), .done(win_service_done),
            .fault(source_fault), .fault_code(win_code),
            .refill_cycles(), .sectors_read(sectors_read),
            .rows_refilled(), .rows_fetched(rows_fetched),
            .blocks_written(blocks_written), .sectors_written(sectors_written),
            .kv_v(win_service_v), .kv_ready(tile_packed_ready),
            .kv_m(win_service_m), .kv_w(win_service_w),
            .m_v(w_v), .m_rdy(w_rdy), .m_addr(w_addr), .m_len(w_len),
            .m_tag(w_tag), .m_we(w_we), .m_wdata(w_wdata),
            .m_wstrb(w_wstrb), .m_wr_done(w_wdone),
            .s_v(w_sv), .s_rdy(w_srdy), .s_tag(w_s_tag),
            .s_beat(w_s_beat), .s_data(w_s_data));
        assign win_fault = win_service_fault;
        end else begin : g_window_external_attention
        assign win_service_v=1'b0; assign win_service_m=4'd0;
        assign win_service_w=16960'd0; assign win_service_staged=1'b0;
        assign win_service_done=1'b0; assign win_service_fault=1'b0;
        assign win_service_busy=1'b0; assign win_service_start_ready=1'b1; assign window_prime_ready=1'b0;
        ot_chip_v41x_window_kv_prefetch #(.POS_W(NW), .SEC_W(K_HAW),
            .HAW(K_HAW), .TAGW(16), .USER_W(10), .WIN_STACK(WIN_STACK)) u_window (
            .clk(clk), .rst_n(rn),
            .region_base_sector(K_HAW'(KV_SBASE)),
            .region_sector_count(K_HAW'(WIN_SECTORS)),
            .prime_v(1'b0), .prime_ready(), .prime_user(10'd0), .prime_row(NW'(0)),
            .blk_v(win_blk_v && !bad_block_addr && !bad_block),
            .blk_ready(win_blk_ready), .blk_user(win_blk_user),
            .blk_row(win_blk_row), .blk_idx(win_blk_idx),
            .blk_codes(win_blk_codes), .blk_scale(win_blk_scale),
            .prefetch_v(1'b0), .prefetch_ready(),
            .prefetch_user(10'd0), .prefetch_row(NW'(0)), .kv_ok(),
            .re(1'b0), .ruser(10'd0), .rrow(NW'(0)), .relem(9'd0), .q(),
            .packed_re(1'b0), .packed_ruser(10'd0), .packed_rrow(NW'(0)),
            .packed_ridx(4'd0), .packed_valid(packed_valid), .packed_row(packed_row),
            .packed_codes(packed_codes), .packed_scale(packed_scale),
            .fault(win_fault), .fault_code(win_code),
            .st_rows_fetched(rows_fetched), .st_blocks_written(blocks_written),
            .st_sectors_read(sectors_read), .st_sectors_written(sectors_written),
            .m_v(w_v), .m_rdy(w_rdy), .m_addr(w_addr), .m_len(w_len),
            .m_tag(w_tag), .m_we(w_we), .m_wdata(w_wdata), .m_wstrb(w_wstrb),
            .m_wr_done(w_wdone), .s_v(w_sv), .s_rdy(w_srdy),
            .s_tag(w_s_tag), .s_beat(w_s_beat), .s_data(w_s_data));
        end
        // Runtime allocates the RoPE tables after every key/KV state region.
        // Its four stack-local sector bases must fit inside the same 0.9 HBM
        // capacity reserve as those regions; an unset layout cannot prefetch.
        wire [3:0] region_bad, floor_bad;
        wire region_valid, cache_fault, mux_fault;
        wire [3:0] p_v,p_rdy,p_we,p_sv,p_srdy;
        wire [4*K_HAW-1:0] p_addr;
        wire [15:0] p_len,p_sbeat;
        wire [4*16-1:0] p_tag,p_stag;
        wire [1023:0] p_wdata,p_sdata;
        wire [127:0] p_wstrb;
        genvar rs;
        for(rs=0;rs<4;rs=rs+1) begin : g_region_floor
            wire [K_HAW-1:0] known_end = (rs==WIN_STACK) ?
                (WINDOW_HBM_ATTENTION ? K_HAW'(window_region_end) :
                 K_HAW'(KV_SBASE+WIN_SECTORS)) : K_HAW'(KEY_SECTORS);
            assign floor_bad[rs]=rope_reserved_end[rs*K_HAW +: K_HAW] < known_end;
        end
        ot_chip_v41x_rope_region_guard #(.HAW(K_HAW), .K_MEM(K_MEM),
            .MAX_POS(ROPE_MAX_POS)) u_rope_region (
            .present(rope_table_present), .reserved_end(rope_reserved_end),
            .plain_base(rope_plain_base), .yarn_base(rope_yarn_base),
            .valid(region_valid), .bad_stack(region_bad));
        assign rope_region_ok=region_valid && !(|floor_bad);
        ot_chip_v41x_rope_hbm_cache #(.HAW(K_HAW), .TAGW(16),
            .PW(NW), .MAX_POS(ROPE_MAX_POS)) u_rope (
            .clk(clk), .rst_n(rn), .pf_v(rope_pf_v), .pf_rdy(rope_pf_rdy),
            .pf_kind(rope_pf_kind), .pf_pos(rope_pf_pos),
            .pf_release(rope_pf_release), .pf_done(rope_pf_done),
            .cache_valid(rope_cache_valid), .cache_hold(rope_cache_hold),
            .cache_kind(rope_cache_kind), .cache_pos(rope_cache_pos),
            .cache_pairs(rope_cache_pairs),
            .table_present(rope_table_present & {2{rope_region_ok}}),
            .plain_base(rope_plain_base), .yarn_base(rope_yarn_base),
            .req_v(p_v), .req_rdy(p_rdy), .req_addr(p_addr), .req_len(p_len),
            .req_tag(p_tag), .req_we(p_we), .req_wdata(p_wdata),
            .req_wstrb(p_wstrb), .rsp_v(p_sv), .rsp_rdy(p_srdy),
            .rsp_tag(p_stag), .rsp_beat(p_sbeat), .rsp_data(p_sdata),
            .fault(cache_fault), .issued_sectors(), .received_sectors(),
            .stalled_cycles(), .cache_hits());
        // All three consumers share the existing per-stack K channel; the
        // next arbiter still contends that channel with the pooled indexer.
        ot_chip_v41x_kv_rope_reqmux #(.HAW(K_HAW), .TAGW(16)) u_kv_mux (
            .clk(clk), .rst_n(rn),
            .w_v(w_v), .w_rdy(w_rdy), .w_addr(w_addr), .w_len(w_len),
            .w_tag(w_tag), .w_we(w_we), .w_wdata(w_wdata), .w_wstrb(w_wstrb),
            .w_wr_done(w_wdone), .w_sv(w_sv), .w_srdy(w_srdy),
            .w_stag(w_s_tag), .w_sbeat(w_s_beat), .w_sdata(w_s_data),
            .c_v(4'b0), .c_rdy(), .c_addr('0), .c_len('0), .c_tag('0),
            .c_we(4'b0), .c_wdata('0), .c_wstrb('0), .c_wr_done(),
            .c_sv(), .c_srdy(4'b0), .c_stag(), .c_sbeat(), .c_sdata(),
            .p_v(p_v), .p_rdy(p_rdy), .p_addr(p_addr), .p_len(p_len),
            .p_tag(p_tag), .p_we(p_we), .p_wdata(p_wdata), .p_wstrb(p_wstrb),
            .p_wr_done(), .p_sv(p_sv), .p_srdy(p_srdy), .p_stag(p_stag),
            .p_sbeat(p_sbeat), .p_sdata(p_sdata),
            .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len),
            .m_tag(pm_tag), .m_we(pm_we), .m_wdata(pm_wdata),
            .m_wstrb(pm_wstrb), .m_wr_done(pk_wd),
            .s_v(ps_v), .s_rdy(ps_rdy), .s_tag(ps_tag),
            .s_beat(ps_beat), .s_data(ps_data),
            .fault(mux_fault), .rope_grants(rope_hbm_grants),
            .rope_wait_cycles(rope_hbm_wait_cycles));
        assign rope_pf_fault=cache_fault || mux_fault ||
            ((rope_pf_v || rope_pf_release) && !rope_region_ok);
        assign rope_fault=rope_pf_fault;
        assign kv_ok = packed_desc_ok;
        assign kv_q = '0;
        assign kv_fault = win_fault | unsupported_read | bad_block | rope_fault |
                          att_packed_desc_fault;
        assign kv_code = win_code | {rope_fault, unsupported_read, bad_block, 2'b0};
        assign kv_ops = 0;
        assign kv_words = rows_fetched * 32;
        assign kv_sectors_written = sectors_written;
        assign kv_refetches = 0;
        assign kv_wq_high = 0;
        assign kv_hold_cycles = 0;
    end endgenerate

    // -- four HBM3E stacks: K ports shared by the pooled indexer (pseudo-channels [32s, 32s + 32) of
    //    u_tile's key bridge) and the KV prefetch through a per-stack arbiter; W_STACK the weights --------
    wire [4*64-1:0] refs; wire [4*32-1:0] wreads; wire [3:0] oor, w_oor;
    wire [4-1:0] s_w_rdy; wire [4*NPC_W-1:0] s_w_room, s_wr_v; wire [4*NPC_W*LWIN-1:0] s_wr_tag;
    wire [4*NPC_W*5-1:0] s_wr_beat; wire [4*NPC_W*256-1:0] s_wr_data;
    wire [4*32-1:0] kgr;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_hbm
        wire [31:0] h_v, h_rdy, h_we, h_wr_done, r_v, r_rdy;
        wire [32*K_HAW-1:0] h_addr; wire [32*4-1:0] h_len, r_beat; wire [32*17-1:0] h_tag, r_tag;
        wire [32*256-1:0] h_wdata, r_data; wire [32*32-1:0] h_wstrb;
        if (KARB_LOCAL) begin : g_karb_local
        ot_chip_v41x_hbm_karb_local #(.NPC(32), .AW(K_HAW), .TAGW(16), .K_RD_FENCE(KARB_FENCE)) u_arb (
            .clk(clk), .rst_n(rn),
            .b_v(kh_v[s*32 +: 32]), .b_rdy(kh_rdy[s*32 +: 32]), .b_addr(kh_addr[s*32*K_HAW +: 32*K_HAW]),
            .b_len(kh_len[s*32*4 +: 32*4]), .b_tag(kh_tag[s*32*16 +: 32*16]), .b_we(kh_we[s*32 +: 32]),
            .b_wdata(kh_wdata[s*32*256 +: 32*256]), .b_wstrb(kh_wstrb[s*32*32 +: 32*32]),
            .b_wr_done(kh_wr_done[s*32 +: 32]),
            .b_rsp_v(kr_v[s*32 +: 32]), .b_rsp_rdy(kr_rdy[s*32 +: 32]), .b_rsp_tag(kr_tag[s*32*16 +: 32*16]),
            .b_rsp_beat(kr_beat[s*32*4 +: 32*4]), .b_rsp_data(kr_data[s*32*256 +: 32*256]),
            .k_v(pm_v[s]), .k_rdy(pm_rdy[s]), .k_addr(pm_addr[s*K_HAW +: K_HAW]), .k_len(pm_len[s*4 +: 4]),
            .k_tag(pm_tag[s*16 +: 16]), .k_we(pm_we[s]), .k_wdata(pm_wdata[s*256 +: 256]),
            .k_wstrb(pm_wstrb[s*32 +: 32]), .k_wr_done(pk_wd[s]),
            .k_rsp_v(ps_v[s]), .k_rsp_rdy(ps_rdy[s]), .k_rsp_tag(ps_tag[s*16 +: 16]),
            .k_rsp_beat(ps_beat[s*4 +: 4]), .k_rsp_data(ps_data[s*256 +: 256]),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),
            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),
            .k_grants(kgr[s*32 +: 32]), .b_grants(), .contended());
        end else begin : g_karb
        ot_chip_v41x_hbm_karb #(.NPC(32), .AW(K_HAW), .TAGW(16)) u_arb (
            .clk(clk), .rst_n(rn),
            .b_v(kh_v[s*32 +: 32]), .b_rdy(kh_rdy[s*32 +: 32]), .b_addr(kh_addr[s*32*K_HAW +: 32*K_HAW]),
            .b_len(kh_len[s*32*4 +: 32*4]), .b_tag(kh_tag[s*32*16 +: 32*16]), .b_we(kh_we[s*32 +: 32]),
            .b_wdata(kh_wdata[s*32*256 +: 32*256]), .b_wstrb(kh_wstrb[s*32*32 +: 32*32]),
            .b_wr_done(kh_wr_done[s*32 +: 32]),
            .b_rsp_v(kr_v[s*32 +: 32]), .b_rsp_rdy(kr_rdy[s*32 +: 32]), .b_rsp_tag(kr_tag[s*32*16 +: 32*16]),
            .b_rsp_beat(kr_beat[s*32*4 +: 32*4]), .b_rsp_data(kr_data[s*32*256 +: 32*256]),
            .k_v(pm_v[s]), .k_rdy(pm_rdy[s]), .k_addr(pm_addr[s*K_HAW +: K_HAW]), .k_len(pm_len[s*4 +: 4]),
            .k_tag(pm_tag[s*16 +: 16]), .k_we(pm_we[s]), .k_wdata(pm_wdata[s*256 +: 256]),
            .k_wstrb(pm_wstrb[s*32 +: 32]), .k_wr_done(pk_wd[s]),
            .k_rsp_v(ps_v[s]), .k_rsp_rdy(ps_rdy[s]), .k_rsp_tag(ps_tag[s*16 +: 16]),
            .k_rsp_beat(ps_beat[s*4 +: 4]), .k_rsp_data(ps_data[s*256 +: 256]),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),
            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),
            .k_grants(kgr[s*32 +: 32]), .b_grants(), .contended());
        end

        ot_chip_v41x_hbm3e_phy #(.NPC(32), .K_AW(K_HAW), .K_MEM(K_MEM), .W_PORT(s == W_STACK), .W_AW(FULL_SHAPE ? 30 : 24), .NPC_W(NPC_W), .W_MEM(W_MEM),
                                 .LWIN(LWIN), .KTAGW(17), .CLK_PS(CLK_PS)) u_hbm (
            .clk(clk), .rst_n(rn),
            .k_v(h_v), .k_rdy(h_rdy), .k_addr(h_addr), .k_len(h_len), .k_tag(h_tag), .k_we(h_we),
            .k_wdata(h_wdata), .k_wstrb(h_wstrb), .k_wr_done(h_wr_done),
            .kr_v(r_v), .kr_rdy(r_rdy), .kr_tag(r_tag), .kr_beat(r_beat), .kr_data(r_data),
            .w_v(s == W_STACK ? wq_v : 1'b0), .w_rdy(s_w_rdy[s]), .w_addr(wq_addr), .w_len(wq_len), .w_tag(wq_tag),
            .w_room(s_w_room[s*NPC_W +: NPC_W]), .wr_v(s_wr_v[s*NPC_W +: NPC_W]),
            .wr_rdy(s == W_STACK ? wr_rdy : {NPC_W{1'b0}}),
            .wr_tag(s_wr_tag[s*NPC_W*LWIN +: NPC_W*LWIN]), .wr_beat(s_wr_beat[s*NPC_W*5 +: NPC_W*5]),
            .wr_data(s_wr_data[s*NPC_W*256 +: NPC_W*256]),
            .k_oor(oor[s]), .w_oor(w_oor[s]), .refreshes(refs[s*64 +: 64]), .w_reads(wreads[s*32 +: 32]));
    end endgenerate
    assign kv_hbm_grants = kgr[0 +: 32] + kgr[32 +: 32] + kgr[64 +: 32] + kgr[96 +: 32];
    assign wq_rdy  = s_w_rdy[W_STACK];
    assign wq_room = s_w_room[W_STACK*NPC_W +: NPC_W];
    assign wr_v    = s_wr_v[W_STACK*NPC_W +: NPC_W];
    assign wr_tag  = s_wr_tag[W_STACK*NPC_W*LWIN +: NPC_W*LWIN];
    assign wr_beat = s_wr_beat[W_STACK*NPC_W*5 +: NPC_W*5];
    assign wr_data = s_wr_data[W_STACK*NPC_W*256 +: NPC_W*256];
    assign hbm_refreshes = refs[0 +: 64] + refs[64 +: 64] + refs[128 +: 64] + refs[192 +: 64];
    assign hbm_w_reads = wreads[W_STACK*32 +: 32];

    // -- package controller ----------------------------------------------------------------------
    wire pc_in_valid, pc_in_ready, pc_in_last, pc_out_valid, pc_out_ready, pc_out_last;
    wire [FLIT-1:0] pc_in_data, pc_out_data;
    wire proto_fault, ctrl_busy;
    ot_rom_pkg_ctrl_x #(.PKG_ID(PKG_ID), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(VWA),
                        .USER_W(FULL_SHAPE ? 10 : 8), .MAXU(MAXU), .KVW(KVW),
                        .XWORDS(XWORDS), .RXWORDS(RXWORDS), .RXB(RXB), .TXB(TXB), .SOURCE(SOURCE),
                        .RESULT_PARTS(RESULT_PARTS), .SEND_HIDDEN(SEND_HIDDEN), .HID_DEST(HID_DEST),
                        .SEND_RESULT(SEND_RESULT), .RES_DEST(RES_DEST), .COMBINE_IN(COMBINE_IN), .ROW0(ROW0),
                        .FWD_TOKEN(FWD_TOKEN)) u_ctrl (
        .clk(clk), .rst_n(rn),
        .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
        .in_valid(pc_in_valid), .in_ready(pc_in_ready), .in_data(pc_in_data), .in_last(pc_in_last),
        .out_valid(pc_out_valid), .out_ready(pc_out_ready), .out_data(pc_out_data), .out_last(pc_out_last),
        .core_start(c_start), .core_token(c_token), .core_pos(c_pos), .core_user(c_user),
        .core_done(host_mode ? 1'b0 : core_done),
        .core_next_token(core_next_token), .core_next_val(core_next_val), .kv_base(kv_base),
        .vm_we(xa_we), .vm_waddr(xa_waddr), .vm_wdata(xa_wdata), .vm_re(xa_re), .vm_raddr(xa_raddr), .vm_rq(xa_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
        .core_busy(ctrl_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault));

`ifndef SYNTHESIS
    // The full-shape four-bank collective reserves the VM while COLL blocks
    // the core. The package controller must not inject a concurrent VM access.
    always @(posedge clk) if (rn && FULL_SHAPE && coll_busy && (xa_we || xa_re))
        $fatal(1, "package-controller VM access overlaps blocking COLL");
`endif

    // -- fabric router: package controller, UCIe, board link ----------------------------------------
    wire [2:0] r_in_valid, r_in_ready, r_in_last, r_out_valid, r_out_ready, r_out_last;
    wire [3*FLIT-1:0] r_in_data, r_out_data;
    wire rtr_overflow;
    assign r_in_valid = {bl_rx_valid, ucie_rx_valid, pc_out_valid};
    assign r_in_data  = {bl_rx_data, ucie_rx_data, pc_out_data};
    assign r_in_last  = {bl_rx_last, ucie_rx_last, pc_out_last};
    assign pc_out_ready = r_in_ready[0];
    assign ucie_rx_ready = r_in_ready[1];
    assign bl_rx_ready = r_in_ready[2];
    assign pc_in_valid = r_out_valid[0]; assign pc_in_data = r_out_data[0 +: FLIT]; assign pc_in_last = r_out_last[0];
    assign ucie_tx_valid = r_out_valid[1]; assign ucie_tx_data = r_out_data[FLIT +: FLIT];
    assign ucie_tx_last = r_out_last[1];
    assign bl_tx_valid = r_out_valid[2]; assign bl_tx_data = r_out_data[2*FLIT +: FLIT]; assign bl_tx_last = r_out_last[2];
    assign r_out_ready = {bl_tx_ready, ucie_tx_ready, pc_in_ready};
    ot_rom_fabric_router #(.NP(3), .FW(FLIT), .BUF(4), .DESTS(DESTS), .INPUT_READY_VALID(1),
                           .ROUTE_INIT(ROUTE_INIT)) u_rtr (
        .clk(clk), .rst_n(rn),
        .in_valid(r_in_valid), .in_ready(r_in_ready), .in_credit(), .in_data(r_in_data), .in_last(r_in_last),
        .out_valid(r_out_valid), .out_ready(r_out_ready), .out_data(r_out_data), .out_last(r_out_last),
        .cfg_we(rcfg_we), .cfg_dest(rcfg_dest), .cfg_mask(rcfg_mask),
        .drops(rtr_drops), .overflow(rtr_overflow));

    // -- one-shot collective engine + DMA ----------------------------------------------------------
    wire e_valid, e_ready, e_last, e_mode; wire [CL_FW-1:0] e_data; wire [CL_TAGW-1:0] e_tag;
    localparam integer CL_GW = FULL_SHAPE ? 4 : 1;
    wire o_valid, o_ready, o_last, o_err, cl_fault;
    wire [CL_GW*CL_FW-1:0] o_data; wire [CL_RB-1:0] o_rank; wire [2:0] cl_code;
    wire [N_TP-1:0] tx_valid, tx_ready, rx_valid; wire [CL_PW-1:0] tx_rec; wire [N_TP*CL_PW-1:0] rx_rec;
    wire [2*N_TP-1:0] cr_in, cr_out;
    wire dma_fault;
    reg coll_issue_fault;
    wire coll_issue_bad = core_coll_op[1] ||
        (core_coll_src[3:0] != 0) || (core_coll_dst[3:0] != 0) ||
        (core_coll_n[3:0] != 0) || (core_coll_n == 0) ||
        (64'(core_coll_src) >= (64'd1 << VM_AW)) ||
        (64'(core_coll_dst) >= (64'd1 << VM_AW)) ||
        (64'(core_coll_n) >= (64'd1 << VM_AW));
    always @(posedge clk or negedge rn)
        if (!rn) coll_issue_fault <= 1'b0;
        else if (FULL_SHAPE && core_coll_go && coll_issue_bad)
            coll_issue_fault <= 1'b1;
    assign die_coll_fault = dma_fault | coll_issue_fault | cl_fault | o_err;
    wire cmd_go = FULL_SHAPE ? (core_coll_go && !coll_issue_bad) : coll_go;
    wire cmd_mode = FULL_SHAPE ? core_coll_op[0] : coll_mode;
    wire [CL_TAGW-1:0] cmd_tag = FULL_SHAPE ? CL_TAGW'(core_coll_seq) : coll_tag;
    wire [VWA-1:0] cmd_src = FULL_SHAPE ? VWA'(core_coll_src >> 4) : coll_src;
    wire [VWA-1:0] cmd_dst = FULL_SHAPE ? VWA'(core_coll_dst >> 4) : coll_dst;
    wire [VWA-1:0] cmd_n = FULL_SHAPE ? VWA'(core_coll_n >> 4) : coll_n;
    ot_rom_oneshot_die_px #(.N(N_TP), .RANK(RANK), .LANES(CL_LANES), .TAGW(CL_TAGW), .DEPTH(CL_DEPTH),
                            .PKG_DIES(PKG_DIES), .RELAY(CL_RELAY), .ADD_LAT(CL_ADD_LAT),
                            .PAIRWISE(FULL_SHAPE), .GW(CL_GW), .OUT_BP(FULL_SHAPE)) u_coll (
        .clk(clk), .rst_n(rn),
        .in_valid(e_valid), .in_ready(e_ready), .in_data(e_data), .in_last(e_last), .in_mode(e_mode), .in_tag(e_tag),
        .tx_valid(tx_valid), .tx_rec(tx_rec), .tx_ready(tx_ready), .cr_in(cr_in),
        .rx_valid(rx_valid), .rx_rec(rx_rec), .cr_out(cr_out),
        .rl_tx_valid(ucie_rl_tx_valid), .rl_tx_rec(ucie_rl_tx_rec),
        .rl_rx_valid(ucie_rl_rx_valid), .rl_rx_rec(ucie_rl_rx_rec),
        .out_valid(o_valid), .out_ready(o_ready), .out_data(o_data), .out_last(o_last),
        .out_rank(o_rank), .out_err(o_err),
        .fault(cl_fault), .fault_code(cl_code));
    ot_chip_v41x_coll_dma #(.WA(VWA), .FW(CL_FW), .TAGW(CL_TAGW), .N(N_TP), .GW(CL_GW),
                            .VM_ALWAYS_READY(FULL_SHAPE)) u_cdma (
        .clk(clk), .rst_n(rn), .go(cmd_go), .mode(cmd_mode), .rnd(FULL_SHAPE ? core_coll_rnd : 1'b0),
        .tag(cmd_tag), .src(cmd_src), .n(cmd_n), .dst(cmd_dst),
        .busy(coll_busy), .fault(dma_fault), .words_out(), .words_in(),
        .vm_re(xb_re), .vm_raddr(xb_raddr), .vm_rq(xb_rq), .vm_we(xb_we),
        .vm_waddr(xb_waddr), .vm_wdata(xb_wdata), .vm_ready4(1'b1),
        .vm_we4(xb_we4), .vm_waddr4(xb_waddr4), .vm_wdata4(xb_wdata4),
        .e_valid(e_valid), .e_ready(e_ready), .e_data(e_data), .e_last(e_last), .e_mode(e_mode), .e_tag(e_tag),
        .o_valid(o_valid), .o_ready(o_ready), .o_data(o_data), .o_last(o_last), .o_rank(o_rank),
        .o_err(o_err), .engine_fault(cl_fault));
    // per-destination ports: self (unused), the in-package peer (UCIe), the partner package (T1)
    assign ucie_ctx_rec = tx_rec;
    assign bl_ctx_rec = tx_rec;
    genvar t;
    generate for (t = 0; t < N_TP; t = t + 1) begin : g_rank
        if (t == RANK) begin : g_self
            assign tx_ready[t] = 1'b1;
            assign cr_in[2*t +: 2] = 2'b00;
            assign rx_valid[t] = 1'b0;
            assign rx_rec[t*CL_PW +: CL_PW] = {CL_PW{1'b0}};
        end else if (t / PKG_DIES == RANK / PKG_DIES) begin : g_ucie
            assign ucie_ctx_valid = tx_valid[t];
            assign tx_ready[t] = ucie_ctx_ready;
            assign cr_in[2*t +: 2] = ucie_ccr_in;
            assign rx_valid[t] = ucie_crx_valid;
            assign rx_rec[t*CL_PW +: CL_PW] = ucie_crx_rec;
            assign ucie_ccr_out = cr_out[2*t +: 2];
        end else begin : g_t1
            localparam integer J = t % PKG_DIES;
            assign bl_ctx_valid[J] = tx_valid[t];
            assign tx_ready[t] = bl_ctx_ready[J];
            assign cr_in[2*t +: 2] = bl_ccr_in[2*J +: 2];
            assign rx_valid[t] = bl_crx_valid[J];
            assign rx_rec[t*CL_PW +: CL_PW] = bl_crx_rec[J*CL_PW +: CL_PW];
            assign bl_ccr_out[2*J +: 2] = cr_out[2*t +: 2];
        end
    end endgenerate

    // -- sticky faults -------------------------------------------------------------------------------
    reg [7:0] fault_r;
    always @(posedge clk or negedge rn)
        if (!rn) fault_r <= 8'd0;
        else fault_r <= fault_r | {(|oor || |w_oor), kv_fault, rtr_overflow, die_coll_fault, proto_fault, qs_fault, 1'b0, t_fault | key_user_fault};
    assign kv_fault_code = kv_code;
    assign fault = fault_r;

    // elaboration checks
`ifndef SYNTHESIS
    initial begin
        if (N_TP != 2 * PKG_DIES || PKG_DIES != 2)
            $fatal(1, "ot_chip_v41x_die: the port map assumes a 4-die group of two 2-die packages");
        if (CL_FW != FLIT) $fatal(1, "ot_chip_v41x_die: the collective word must be one vector-memory word");
        if (KV_SBASE < KEY_SECTORS)
            $fatal(1, "ot_chip_v41x_die: KV region [%0d, ..) overlaps the index keys [0, %0d)", KV_SBASE, KEY_SECTORS);
        if (!FULL_SHAPE && KV_SBASE + KV_SECTORS > K_MEM)
            $fatal(1, "ot_chip_v41x_die: KV region ends at %0d, past the stack's %0d sectors", KV_SBASE + KV_SECTORS,
                   K_MEM);
        if (FULL_SHAPE && (K_HAW < 30 || WIN_STACK < 0 || WIN_STACK > 3 ||
                           KV_SBASE + WIN_SECTORS > K_MEM))
            $fatal(1, "ot_chip_v41x_die: packed window region exceeds HBM or HAW<30");
    end
`endif
endmodule
