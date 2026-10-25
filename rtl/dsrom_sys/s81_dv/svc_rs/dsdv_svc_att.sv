`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVC (2026-10-17, S81-DV p4h regional service slice dsdv_svc_rs x16): dsdv_svc_att, the slice's ATTENTION SHARE
// and its 2-PC HBM service.  Successor of one quarter of dsfd_svc_c (ot_s81_svch_attq + 8 x dsfd_svch_pcs + the home's
// window source / owned-row fetch / G router), generalised from quarter QID (D = 128) to one TD = 32 head-dim TILE.
//
// Data layout (compiler, dim-sliced): the slice of tile t holds dims 32 t .. 32 t + 31 of every KV row in its OWN two
// pseudo-channels (PC-local sector addresses, PC p = 0 / 1 of the slice):
//   window ring (user u, slot s = pos mod 128, base WB from CFG):
//     codes   sector WB + 68 u + s[6:1]        on PC s[0]      (32 E4M3 codes = 256 b, the OWN_ROW block t as written)
//     scales  sector WB + 68 u + 64 + s[6]     on PC s[5]      byte s[4:0] (UE8M0 of the tile; 32 slots a sector)
//   compressed rows owned by this die / stack (gid g, region base SB = WIN_LOAD rbase): 16-row block g >> 8 of
//     9 sectors on PC g[8] at SB + 9 (g >> 9); row k = g[3:0] at bits 144 k .. 144 k + 143 of the block
//     ({E4M3 scales 16, E2M1 nibbles 128}; capacity-exact, a row read is 1 or 2 sectors).  Only owned rows are read
//     here (about 1/16 of the selection); the others arrive on ROWS frames, so the dim slicing costs no HBM bandwidth.
// No window-beat / fetched-row / G lanes: each slice reads only its own 2 PCs.  The window source, owned-row fetch and
// result routing of the svc_c home are replicated per slice on the shared q stream (lockstep by data); the G router and
// the a0 / od result emitter disappear (scores go to the score exchange and the slice's SM head, P.V leaves the 4 owner
// slices on the half's P.V return tree to the p4j entry slice, in compiled windows).
//
// q frames (SVC FRAME PROTOCOL v1.1 header; payload as svc_c unless stated):
//   12 CFG      [29:0] WB (window ring base); TOK-S81-GAPS/SVCP (10-19, G10): [32] ST valid, [31:30] ST = the die's HBM
//               stack position (P.V quarter / held-row stack); [32] = 0 keeps the parameter ST (legacy frames)
//               RTLGAP-SO (10-21, -DOT_SVC_ALLQ only): [54] ALLQ = every slice is a P.V owner (all 4 quarters on THIS
//               die: the slice's tile P.V is a per-dim sum over rows inside the tile, its window rows are in its own 2 PCs
//               and its p store holds the job's P, so no other die is needed); every selected row is then needed by
//               every tile (ROWS for all pairs), and the drain slot pvs is the 10-b all-owner slot (rs_pvslot_all)
//    3 OWN_ROW  [479:459] pos, [458:449] user; payload block b = {scale 8, codes 256}: block t is written (2 writes)
//    2 WIN_LOAD as svc_c ([29:0] SB, [88:81] wcount, [98:89] nsel, [119:99] first window pos, [458:449] user, tag)
//    7 SEL_IDS  as svc_c; the slice records per rank whether the row is this stack's (held) and fetches its own rows
//    1 ATTN_Q   as svc_c; word r = head 8 b + r / 16, dims 32 (r % 16) .. : the slice keeps r % 16 == t
//    6 ROWS     as svc_c; the slice keeps pair t / 2, half t % 2
//    5 PV       as svc_c (stored by every slice, used by the 4 slices of quarter ST, which emit P.V)
//   13 GO       (new, len 0) the compiled start: the engine share starts gd cycles after GO reaches this slice;
//               [15:0] PO = the p-feed start, [31:16] PVO = the P.V drain base, both in cycles after the share's start;
//               TOK-S81-GAPS/SVCP (10-19): [47:32] PIO = the on-die P injection start (dsdv_svc_rs_c P path: the SM's e
//               rows enter the score exchange as P beats from PIO, the fold root packs the PV frame and the entries
//               put it on the dn stream); PIO = 0 = legacy (the PV frame comes from the host q stream)
//    9 SMJ      (new) SM head job / rows: [0] start, [4:1] kind, [12:5] jid, [13] operand rows (else parameter rows,
//               r_j = payload index), [29:14] head mask (operand rows only)
//   14 SOT      (S81-SMWIRE 10-19, len 2) the SO target config of the job: parsed by dsdv_svc_sot beside this share
//               (tools/s81_dv/sm_target/dsdv_sm_wire.sv); a legal frame type here, no state in the attention share
//   15 IK_ROW   (S81/H23 10-24, attn.idx.newkey, len 1) append ONE index-key row to the HBM index-key region that the
//               paired reader dsdv_idx_rg3 scans / gathers.  Header: [29:0] KB = the region base (PC-local sector, the
//               rg3 job header's KB of that layer / user), [63:32] the key's 4 UE8M0 scales, [479:459] pos p (key
//               position), [458:449] user (provenance only, not in the address).  Payload word = the 128 E2M1 codes.
//               Layout = rg3's (tb_dsdv_idx_rg3 preload, dsdv_idx_rg3 walker / gather issue): j = p >> 4, i = p[3:0],
//               region rg = i ^ j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12] (= the svc slice sid owning the two PCs), PC
//               p[8], n = p >> 9, c = p[7:4], a = KB + 34 n: codes[255:0] at a + 2c, codes[511:256] at a + 2c + 1,
//               scales at sector a + 32 + c[3], bytes 4 c[2:0] .. 4 c[2:0] + 3 (strobe 4 bytes).  Exactly ONE slice
//               (sid == rg) pushes the 3 writes (code lo / code hi on the payload beat, scales one edge later, all on
//               PC p[8]) into the OWN_ROW write FIFOs; every other slice drops the frame.  Writes before reads per PC
//               (the issue order below); the compiler keeps the writes out of the controller's rg3 reader slots and
//               before the next scan / gather of that layer (static schedule, no new pins).
//
// Static schedule (owner rule; no credit / ready on the on-die production path): from GO + gd the engine share runs a
// fixed program: job at cycle 0, q heads at 1 .. 16, row beats c at 1 + c (4 rows a beat, the job's row order: window
// oldest first, then the selected ranks).  Every row is CHECKED landed at its release cycle (fault, never a stall); rows
// another stack holds are fed as zero to the 12 tiles outside quarter ST (svc_c: those quarters' pairs as zero).
// The HBM boundary is elastic (owner 10-15): per-PC DQ request credits from the controller, reads into slot-addressed
// landing (no overflow possible), writes before reads per PC.  The closed engine's local valid / ready never stalls
// on this program; any refusal is a fault.
// Score beats go straight to the score exchange leaf (no FIFO, valid-only).  SVC-PV3 (10-18, owner rule): the score
// credit is REMOVED -- the engine runs with SC_CRED 0 (q.k issue never waits on a credit, no sc_cr); the exchange takes
// every beat the cycle it is produced, and a beat outside an active job is still fault 18.
// P.V (S81U-SVC4, owner rule): the p feed is COMPILED -- from cycle PO of the share it offers one step (2 p words) every
// cycle, never looking at the engine's p_ready; a step whose words have not landed (fault 20) or that the engine does
// not take (fault 21) is a sticky fault.  The 4 owner slices drain their 8 P.V beats (5 words each) in 40 consecutive
// cycles from PVO + pvs (rs_pvslot: owner k's window on the half's P.V return tree); a beat not produced by its slot is
// fault 19.  pvs puts the 4 owners of a quarter in disjoint windows at the entry's pv pins (no arbitration).
// SVC-PV (10-18): the P.V buffer pvq holds ALL 8 beats of a job (PVQ 8 = 8 beats x PVB bits).  The engine emits
// the 8 final-block beats as one 8-cycle burst; with 4 entries its pv_cr credit loop (~45 cycles) left a gap inside
// the 40-cycle drain window (fault 19, then the pointer wrap gave fault 15) and no p-feed offset can fix that
// (tb_dsdv_svc_pvdrain: depth 4 fails at every drain distance and T).  With 8 entries the credit never binds (the same
// probe passes with pv_cr never returned): the drain is purely static.  Compiler rule (tb_dsdv_svc_rs build_frames):
// PVO >= PO + 8 ceil(T / 32) + 55 (probe minimum 53 + 8 ceil(T / 32), every owner's slot pvs >= 0 on top).
// SVC-PV2 (10-18, owner rule: no runtime credit on ROM production paths): the P.V credit is REMOVED.  The engine runs
// with PV_CRED 0 (final-block p.v issue never waits on a credit, no pv_cr); pvq (PVQ 8) is sized by the compiler for
// one job's 8 beats and only the static checks remain: fault 15 = pvq overflow (a 9th beat before the drain popped),
// fault 19 = underflow (the drain slot finds no beat).
// MUT (bench negative controls): 1 = window scale byte of the neighbouring slot, 2 = ROWS half of the other tile of
// the pair, 3 = q chunk of the neighbouring tile, 4 = IK_ROW region hash without the j[15:12] term (wrong owner slice
// for p >= 2^16), 5 = IK_ROW scale bytes of the neighbouring key c ^ 1.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_att #(
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer PFIFO = 512,
    parameter integer PVQ = 8,                    // P.V buffer = the beats of one job (static drain, no credit)
    parameter integer DQ = 8,
    parameter bit SRAM_MACRO = 0,
    parameter integer PV_IDENTITY = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [3:0]           sid,
    input  wire [3:0]           tile,
    input  wire [7:0]           gd,
`ifdef OT_SVC_ALLQ
    input  wire [9:0]           pvs,               // compiled P.V drain slot after the job's PVO (ALLQ: rs_pvslot_all)
`else
    input  wire [7:0]           pvs,               // compiled P.V drain slot after the job's PVO (255: not an owner)
`endif
    input  wire                 root,
    // the slice's copy of the broadcast stream (centre register)
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    input  wire                 hw_v,
    input  wire [290:0]         hw_d,
    // the slice's two PC faces (dsfd_svc_pc N faces)
    output reg  [2*341-1:0]     qrq,
    input  wire [1:0]           qrk,
    input  wire [1:0]           qwd,
    input  wire [1:0]           qrv,
    input  wire [2*256-1:0]     qr_data,
    input  wire [2*17-1:0]      qr_tag,
    input  wire [2*4-1:0]       qr_beat,
    // score beat -> score exchange leaf
    output wire                 l_v,
    output wire [2131:0]        l_d,
    // P.V words (owner slices): word 0 {1, 0, pv_c 8, flags 64}, words 1..4 tile j's 16 heads x FP32
    output reg                  pv_ov,
    output reg  [512:0]         pv_od,
    // SM head (SMJ frames)
    output reg                  sm_st,
    output reg  [3:0]           sm_kind,
    output reg  [7:0]           sm_jid,
    output reg                  sm_rv,
    output reg                  sm_rp,
    output reg  [2:0]           sm_rj,
    output reg  [511:0]         sm_rd,
    // job
    output reg                  go_o,
    output reg  [9:0]           tjob_o,
    output reg                  done,
    output reg  [7:0]           tagj,
    // host-write status: credits returned (words issued to a PC / root markers), completed sector writes
    output reg  [1:0]           hcr,
    output reg  [1:0]           hack,
    output wire                 fault,
    output wire [31:0]          fault_code,
    // TOK-S81-GAPS/SVCP (10-19): the compiled P path offsets of the job (GO frame), the share's cycle counter and the
    // stack position (CFG) for the slice's P path / P.V slot
    output wire [15:0]          pio_o,
    output wire [15:0]          pvo_o,
    output wire [15:0]          jc_o,
    output wire [1:0]           st_o
`ifdef OT_SVC_ALLQ
    , output wire               allq_o             // CFG [54] (RTLGAP-SO): all-quarter P.V ownership of the job
`endif
);
    localparam integer H = 16, D = 32, TD = 32, NL = 4, NT = NL * (D / TD), R = TD / H;
    localparam integer PFW = $clog2(PFIFO);
    localparam integer TR = 640;
    reg [31:0] fc;
    assign fault_code = fc;
    assign pio_o = pio; assign pvo_o = pvo; assign jc_o = jc; assign st_o = st_r;
    assign fault = |fc;

    // ------------------------------------------------------------------ frame parser (as ot_s81_svch_attq)
    reg in_frame; reg [11:0] left; reg [3:0] f_type; reg f_mine; reg [511:0] f_hdr; reg [11:0] f_idx;
    wire [3:0]  h_type = q_d[511:508];
    wire [3:0]  h_mask = q_d[506:503];
    wire [11:0] h_len  = q_d[491:480];
    wire is_hdr = q_v && !in_frame;
    wire is_pay = q_v && in_frame;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; end
        else if (is_hdr) begin
            f_type <= h_type; f_mine <= h_mask[0]; f_idx <= 0; left <= h_len; in_frame <= h_len != 0;
        end else if (is_pay) begin
            f_idx <= f_idx + 1'b1; left <= left - 1'b1; if (left == 12'd1) in_frame <= 1'b0;
        end
    end
    always @(posedge clk) if (is_hdr) f_hdr <= q_d;
    wire hdr_mine = is_hdr && h_mask[0];
    wire pay_mine = is_pay && f_mine;

    // ------------------------------------------------------------------ CFG / job state
    reg [29:0] wb, sb;
    reg [1:0] st_r;                                 // stack position: CFG [31:30] when [32], else the parameter ST
`ifdef OT_SVC_ALLQ
    reg allq_r;                                     // RTLGAP-SO: CFG [54], all 16 slices own their tile's P.V
    always @(posedge clk or negedge rst_n)
        if (!rst_n) allq_r <= 1'b0;
        else if (hdr_mine && h_type == 4'd12) allq_r <= q_d[54];
    assign allq_o = allq_r;
`endif
    reg [7:0] wcount; reg [9:0] nsel; reg [20:0] wfirst,wposition; reg [9:0] wuser;
`ifdef OT_SVC_ALLQ
    wire [1:0] pv_owner_quarter=allq_r?tile[3:2]:st_r;
`else
    wire [1:0] pv_owner_quarter=st_r;
`endif
    wire [439:0] pv_provenance;wire pv_identity_bad;
    dsdv_pv_source_identity #(.ENABLE(PV_IDENTITY)) u_pv_identity (
      .clk(clk),.rst_n(rst_n),.cfg_v(hdr_mine && h_type==4'd12),.cfg_owner(q_d[52:33]),.cfg_valid(q_d[53]),
      .launch(go),.launch_ok(job_open && !job_active && !run && !dr_arm && !dr_on),.user_id(wuser),.tag_id(tagj),.quarter(pv_owner_quarter),.tile(tile),.position(wposition),
      .provenance(pv_provenance),.bad(pv_identity_bad));
    reg job_open, job_active;                       // job_open: WIN_LOAD seen, engine program not yet done
    wire start = hdr_mine && h_type == 4'd2;
    wire [9:0] tjob = 10'(wcount) + nsel;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wb <= 0; sb <= 0; wcount <= 0; nsel <= 0; wfirst <= 0; wposition <= 0; wuser <= 0; tagj <= 0; st_r <= 2'(ST); end
        else begin
            if (hdr_mine && h_type == 4'd12) begin wb <= q_d[29:0]; if (q_d[32]) st_r <= q_d[31:30]; end
            if (start && !job_open) begin
                sb <= q_d[29:0]; wcount <= q_d[88:81]; nsel <= q_d[98:89]; wfirst <= q_d[119:99];
                wuser <= q_d[458:449]; tagj <= q_d[502:495];wposition<=q_d[479:459];
            end
        end
    always @(posedge clk) tjob_o <= tjob;

    // ------------------------------------------------------------------ PC request words
    function automatic [340:0] rd_req(input [29:0] a, input [3:0] len, input [16:0] tg);
        rd_req = {256'd0, 32'd0, tg, len, a, 1'b0, 1'b1};
    endfunction
    function automatic [340:0] wr_req(input [29:0] a, input [31:0] strb, input [255:0] d, input [16:0] tg);
        wr_req = {d, strb, tg, 4'd1, a, 1'b1, 1'b1};
    endfunction
    function automatic [4:0] pcmap(input [29:0] s);
        reg [29:0] x; x = (s >> 2) ^ (s >> 7) ^ (s >> 12); pcmap = x[4:0];
    endfunction
    wire [29:0] ring = wb + 30'(wuser) * 30'd68;

    // ------------------------------------------------------------------ write FIFOs per PC: OWN_ROW codes / scales, host
    // depth 8 each (OWN_ROW: 1 code + 1 scale write per 17-word frame; host: <= 8 words in flight on the 8 host credits)
    reg [340:0] wq [0:2][0:1][0:7];
    reg [3:0] wq_w [0:2][0:1], wq_r [0:2][0:1];
    reg [2:0] wpush; reg [340:0] wpush_d [0:2]; reg [2:0] wpush_pc;   // registered pushes (one per FIFO class)
    reg [6:0] ow_slot; reg [9:0] ow_user;
    always @(posedge clk) if (hdr_mine && h_type == 4'd3) begin ow_slot <= q_d[465:459]; ow_user <= q_d[458:449]; end
    wire [29:0] ow_ring = wb + 30'(ow_user) * 30'd68;
    wire ow_blk = pay_mine && f_type == 4'd3 && f_idx[3:0] == tile;
    wire [4:0] ow_by = (MUT == 1) ? ow_slot[4:0] + 5'd1 : ow_slot[4:0];
    // host words
    wire hw_mark = hw_d[287:256] == 32'hffffffff;
    wire hw_sec = hw_d[288] && hw_d[290:289] < 2'd2 && !hw_mark;
    wire [4:0] hw_pc = pcmap(hw_d[285:256]);
    wire hw_mine = hw_v && hw_sec && hw_pc[4:1] == sid;
    // IK_ROW (type 15): owner decode + region base at the header (registered), 3 writes from the payload beat
    function automatic [3:0] ik_rg(input [20:0] p);                       // rg3 key region of position p
        ik_rg = p[3:0] ^ p[7:4] ^ p[11:8] ^ p[15:12] ^ ((MUT == 4) ? 4'd0 : 4'(p[19:16]));
    endfunction
    wire        ik_hdr = hdr_mine && h_type == 4'd15;
    reg  [29:0] ik_base;                                                   // KB + 34 n (n = p >> 9)
    reg  [3:0]  ik_c;                                                      // key word c = p[7:4]
    reg         ik_pc, ik_own;
    reg  [31:0] ik_sc;
    always @(posedge clk) if (ik_hdr) begin
        ik_base <= q_d[29:0] + 30'({q_d[479:468], 5'd0}) + 30'({q_d[479:468], 1'b0});
        ik_c <= q_d[466:463]; ik_pc <= q_d[467]; ik_sc <= q_d[63:32];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ik_own <= 1'b0;
        else if (ik_hdr) ik_own <= ik_rg(q_d[479:459]) == sid;
    wire        ik_pay = pay_mine && f_type == 4'd15 && f_idx == 12'd0 && ik_own;
    reg         ik_scl;                                                    // scale write: the edge after the payload
    always @(posedge clk or negedge rst_n) if (!rst_n) ik_scl <= 1'b0; else ik_scl <= ik_pay;
    wire [2:0]  ik_by = (MUT == 5) ? ik_c[2:0] ^ 3'd1 : ik_c[2:0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wpush <= 0;
        else wpush <= {hw_mine, ow_blk | ik_pay | ik_scl, ow_blk | ik_pay};
    always @(posedge clk) begin
        // class 0: OWN_ROW codes | IK_ROW codes[255:0]; class 1: OWN_ROW scale | IK_ROW codes[511:256], then its scales
        // (an IK payload beat and its scale edge can never meet an OWN_ROW push: one q word a cycle, a following frame's
        // first payload beat is >= 2 edges after this payload beat)
        wpush_d[0] <= ik_pay ? wr_req(ik_base + 30'({ik_c, 1'b0}), 32'hffffffff, q_d[255:0], 17'h1fffe)
                             : wr_req(ow_ring + 30'(ow_slot[6:1]), 32'hffffffff, q_d[255:0], 17'h1fffe);
        wpush_pc[0] <= ik_pay ? ik_pc : ow_slot[0];
        wpush_d[1] <= ik_pay ? wr_req(ik_base + 30'({ik_c, 1'b1}), 32'hffffffff, q_d[511:256], 17'h1fffe)
                    : ik_scl ? wr_req(ik_base + 30'd32 + 30'(ik_c[3]), 32'hf << (4 * ik_by), 256'(ik_sc) << (32 * ik_by), 17'h1fffe)
                    : wr_req(ow_ring + 30'd64 + 30'(ow_slot[6]), 32'd1 << ow_by, 256'(q_d[263:256]) << (8 * ow_by), 17'h1fffe);
        wpush_pc[1] <= (ik_pay || ik_scl) ? ik_pc : ow_slot[5];
        wpush_d[2] <= wr_req(hw_d[285:256], 32'hffffffff, hw_d[255:0], 17'h1ffff);
        wpush_pc[2] <= hw_pc[0];
    end

    // ------------------------------------------------------------------ SEL_IDS -> per-rank stack table + own-row fetch
    reg [9:0] s_first; reg [9:0] s_cnt;
    reg [511:0] sw [0:31]; reg [9:0] sw_base [0:31]; reg [4:0] sw_n [0:31];
    reg [5:0] sw_w, sw_r; reg [4:0] sw_i;
    always @(posedge clk) if (hdr_mine && h_type == 4'd7) begin s_first <= q_d[9:0]; s_cnt <= q_d[19:10]; end
    wire sel_pay = pay_mine && f_type == 4'd7;
    reg [511:0] sel_held;                            // rank -> the row is this stack's (all 16 tiles arrive)
    // fetch FIFOs per PC {k 4, rank 10, block 12}
    reg [25:0] fq [0:1][0:15]; reg [4:0] fq_w [0:1], fq_r [0:1];
    wire [511:0] swd = sw[sw_r[4:0]];
    wire [31:0] sid_g = swd[32*sw_i +: 32];
    wire [9:0] s_rank = sw_base[sw_r[4:0]] + 10'(sw_i);
    wire sw_have = sw_w != sw_r;
    wire g_own = sid_g[5:4] == 2'(DIE_ID) && sid_g[7:6] == st_r;
    wire f_full = (fq_w[sid_g[8]] - fq_r[sid_g[8]]) >= 5'd16;
    wire sw_step = sw_have && !(g_own && f_full);    // the fetch side waits on the elastic HBM boundary only
    always @(posedge clk) if (sel_pay) begin
        sw[sw_w[4:0]] <= q_d; sw_base[sw_w[4:0]] <= 10'(s_first) + 10'(f_idx[5:0]) * 10'd16;
        sw_n[sw_w[4:0]] <= (32'(s_cnt) - 32'(f_idx) * 16 >= 16) ? 5'd16 : 5'(32'(s_cnt) - 32'(f_idx) * 16);
    end

    // ------------------------------------------------------------------ window read generators (per PC), scale reads
    reg [7:0] wr_r [0:1]; reg wr_on [0:1]; reg [1:0] sc_n [0:1];

    // ------------------------------------------------------------------ PC issue (per PC): writes before reads
    reg [3:0] cr [0:1];
    reg [15:0] wk [0:1]; reg [4:0] wk_w [0:1], wk_r [0:1];   // write-kind FIFO (1 = host) for the wd pulses
    reg [1:0] iss_host;
    integer p, c3;
    reg [340:0] nreq [0:1]; reg [1:0] nv; reg [2:0] npop [0:1]; reg [1:0] nwin, nsc, nf;
    reg [25:0] e; reg [11:0] o144;
    always @(*) begin
        e = '0; o144 = '0;
        for (p = 0; p < 2; p = p + 1) begin
            nreq[p] = '0; nv[p] = 1'b0; npop[p] = 3'd7; nwin[p] = 1'b0; nsc[p] = 1'b0; nf[p] = 1'b0;
            if (cr[p] != 0) begin
                if (wq_w[2][p] != wq_r[2][p]) begin nv[p] = 1; nreq[p] = wq[2][p][wq_r[2][p][2:0]]; npop[p] = 3'd2; end
                else if (wq_w[0][p] != wq_r[0][p]) begin nv[p] = 1; nreq[p] = wq[0][p][wq_r[0][p][2:0]]; npop[p] = 3'd0; end
                else if (wq_w[1][p] != wq_r[1][p]) begin nv[p] = 1; nreq[p] = wq[1][p][wq_r[1][p][2:0]]; npop[p] = 3'd1; end
                else if (wr_on[p]) begin
                    nv[p] = 1; nwin[p] = 1;
                    nreq[p] = rd_req(ring + 30'(7'(wfirst[6:0] + 7'(wr_r[p])) >> 1), 4'd1, {2'd0, 7'd0, wr_r[p]});
                end else if (sc_n[p] != 0) begin
                    nv[p] = 1; nsc[p] = 1;
                    nreq[p] = rd_req(ring + 30'd64 + 30'(sc_n[p] == 2'd2 ? 1'b0 : 1'b1), 4'd1,
                                     {2'd1, 13'd0, (sc_n[p] == 2'd2) ? 1'b0 : 1'b1, 1'(p)});
                end else if (fq_w[p] != fq_r[p]) begin
                    e = fq[p][fq_r[p][3:0]];
                    o144 = 12'(e[25:22]) * 12'd144;
                    nv[p] = 1; nf[p] = 1;
                    nreq[p] = rd_req(sb + 30'd9 * 30'(e[11:0]) + 30'(o144[11:8]),
                                     (32'(o144[7:0]) + 144 > 256) ? 4'd2 : 4'd1, {2'd2, 1'b0, e[25:22], e[21:12]});
                end
            end
        end
    end

    // ------------------------------------------------------------------ landing (slot-addressed: no overflow)
    reg [255:0] land [0:TR-1];
    reg [TR-1:0] pres;
    reg [1023:0] wsc;                                // window scales, 128 slots x 8
    reg [3:0] spres;
    reg [255:0] hold [0:1];
    // ROWS
    wire rows_mine = pay_mine && f_type == 4'd6 && q_d[33:31] == tile[3:1];
    wire rh = (MUT == 2) ? ~tile[0] : tile[0];
    wire [143:0] rows_bits = {q_d[290 + 16*rh +: 16], q_d[34 + 128*rh +: 128]};

    // ------------------------------------------------------------------ q store
    reg [D*16-1:0] qmem [0:H-1];
    reg [4:0] q_have;
    wire [3:0] qt = (MUT == 3) ? tile + 4'd1 : tile;
    wire q_word = pay_mine && f_type == 4'd1 && f_idx[3:0] == qt;

    // ------------------------------------------------------------------ static program (GO + gd)
    reg [7:0] go_cnt; reg go_arm; reg go;
    reg [15:0] po, pvo, pio, jc;                    // compiled p-feed start / P.V drain base / P injection start; cycles since the share's start
    reg dr_arm, dr_on; reg [2:0] dbeat;
    reg [9:0] rc; reg run;                           // program cycle
    wire [9:0] nbeat = (tjob + 10'd3) >> 2;
    // engine ports
    reg ej_v; reg eq_v; reg [D*16-1:0] eq_w; reg ekv_v; reg [NL-1:0] ekv_m, kc_m; reg [NL*265-1:0] ekv_w, kc_w;
    wire ej_ready, eq_ready, kv_ready;
    reg [NL-1:0] rel_bad;
    // row word at release
    function automatic [264:0] rowword(input integer row, input [255:0] l, input [1023:0] sc, input [7:0] wc,
                                       input [20:0] wf, input need);
        reg [6:0] sl;
        if (row < wc) begin
            sl = 7'(wf[6:0] + 7'(row));
            rowword = {1'b0, sc[8*sl +: 8], l};
        end else rowword = need ? {1'b1, 120'd0, l[143:0]} : {1'b1, 264'd0};
    endfunction
    integer j;
    integer row; reg need, ok;
    always @(*) begin
        kc_w = '0; kc_m = '0; rel_bad = '0; row = 0; need = 1'b0; ok = 1'b0;
        for (j = 0; j < NL; j = j + 1) begin
            row = 4 * (32'(rc) - 1) + j; need = 1'b0; ok = 1'b0;
            if (row < 32'(tjob)) begin
                kc_m[j] = 1'b1;
`ifdef OT_SVC_ALLQ
                need = (row < 32'(wcount)) || sel_held[row - 32'(wcount)] || tile[3:2] == st_r || allq_r;
`else
                need = (row < 32'(wcount)) || sel_held[row - 32'(wcount)] || tile[3:2] == st_r;
`endif
                ok = pres[row] && (row >= 32'(wcount) || spres[7'(wfirst[6:0] + 7'(row)) >> 5]);
                kc_w[265*j +: 265] = rowword(row, land[row], wsc, wcount, wfirst, need);
                rel_bad[j] = need && !ok;
            end
        end
    end

    // ------------------------------------------------------------------ p FIFO (stored in all; used by quarter ST)
    reg [TD*16-1:0] pmem [0:PFIFO-1];
    reg [PFW:0] pw, pr;
    wire [PFW:0] pcnt = pw - pr;
    reg [15:0] p_left;
    wire [1:0] pstep = (p_left >= 16'd2) ? 2'd2 : 2'(p_left);
`ifdef OT_SVC_ALLQ
    wire pvown = tile[3:2] == st_r || allq_r;
`else
    wire pvown = tile[3:2] == st_r;
`endif
    wire ep_v = job_active && p_left != 0 && jc >= po;          // static: from PO, a step every cycle
    wire ep_ready;
`ifdef RTLGAP_MUT_ALLQ_NOP
    // RTL MUTANT (bench only): ALLQ drains every slice, but P stays gated to quarter ST -> 12 tiles of zero P.V
    wire [2*TD*16-1:0] ep_w = (tile[3:2] == st_r) ? {(pstep == 2'd2) ? pmem[pr[PFW-1:0] + 1'b1] : {TD*16{1'b1}}, pmem[pr[PFW-1:0]]} : '0;
`else
    wire [2*TD*16-1:0] ep_w = pvown ? {(pstep == 2'd2) ? pmem[pr[PFW-1:0] + 1'b1] : {TD*16{1'b1}}, pmem[pr[PFW-1:0]]} : '0;
`endif

    // ------------------------------------------------------------------ engine (unchanged, D = 32: S = 1, LS = 0)
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
`ifdef SVCQ_ENG_FG3
    localparam integer E_FPL = 3, E_FML = 3, E_TS = 0, E_NAR = 0, E_MF = 0, E_TRX = 0, E_F12 = 0, E_FX = 0;
`else
    localparam integer E_FPL = 4, E_FML = 6, E_TS = 1, E_NAR = 1, E_MF = 1, E_TRX = 1, E_F12 = 1, E_FX = 5;
`endif
    ot_hdc_v41x_attn_s #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(TR), .SRAM_MACRO(SRAM_MACRO), .PWORDS(2),
                         .ILV(1), .REPL(2), .NSTAGE(2), .FPL(E_FPL), .FML(E_FML), .NBANKP(0), .TILE_S(E_TS),
                         .NARROW(E_NAR), .MFAN(E_MF), .TRX(E_TRX), .F12(E_F12), .FPLX(E_FX),
                         .SC_CRED(0), .PV_CRED(0)) u_eng (
        .clk(clk), .rst_n(rst_n), .job_v(ej_v), .job_t({6'd0, tjob}), .job_ready(ej_ready),
        .q_v(eq_v), .q_w(eq_w), .q_ready(eq_ready),
        .kv_v(ekv_v), .kv_m(ekv_m), .kv_w(ekv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(1'b0),
        .p_v(ep_v), .p_w(ep_w), .p_ready(ep_ready),
        .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(1'b0),
        .qk_iss(), .pv_iss());
    assign l_v = sc_v;
    assign l_d = {sc_row, sc_m, sc_y, sc_f};

    // ------------------------------------------------------------------ P.V words (owner slices)
    localparam integer PVB = 8 + NT*H*32 + NT*H;
    localparam integer PA = $clog2(PVQ);
    reg [PVB-1:0] pvq [0:PVQ-1];
    reg [PA:0] pvw, pvr;
    reg [2:0] p_i;
    reg [3:0] pv_n;
    always @(posedge clk) if (pv_v) pvq[pvw[PA-1:0]] <= {pv_c, pv_y, pv_f};
    wire [PVB-1:0] pb = pvq[pvr[PA-1:0]];
    always @(posedge clk) if (dr_on)
        pv_od <= (p_i == 0) ? {1'b1, pv_provenance, pb[PVB-1 -: 8], pb[NT*H-1:0]} : {1'b0, pb[NT*H + 32'(p_i - 1)*H*32 +: H*32]};

    // ------------------------------------------------------------------ sequential
    integer k;
    always @(posedge clk) begin
        // write FIFO pushes
        for (k = 0; k < 3; k = k + 1) if (wpush[k]) wq[k][wpush_pc[k]][wq_w[k][wpush_pc[k]][2:0]] <= wpush_d[k];
        // q store
        if (q_word) qmem[{f_hdr[448], f_idx[6:4]}] <= q_d;
        // p store
        if (pay_mine && f_type == 4'd5) pmem[pw[PFW-1:0]] <= q_d;
        // landing writes: PC responses, ROWS
        for (k = 0; k < 2; k = k + 1) if (qrv[k]) begin
            reg [16:0] tg; reg [11:0] o144; reg [511:0] two; reg [9:0] slot;
            tg = qr_tag[17*k +: 17];
            case (tg[16:15])
                2'd0: land[tg[7:0]] <= qr_data[256*k +: 256];
                2'd1: wsc[256 * {tg[1], tg[0]} +: 256] <= qr_data[256*k +: 256];
                2'd2: begin
                    o144 = 12'(tg[13:10]) * 12'd144;
                    two = {qr_data[256*k +: 256], hold[k]};
                    slot = 10'(wcount) + tg[9:0];
                    if (32'(o144[7:0]) + 144 <= 256 && qr_beat[4*k +: 4] == 4'd0)
                        land[slot] <= {112'd0, 144'(qr_data[256*k +: 256] >> o144[7:0])};
                    else if (qr_beat[4*k +: 4] == 4'd1)
                        land[slot] <= {112'd0, 144'(two >> o144[7:0])};
                    if (qr_beat[4*k +: 4] == 4'd0) hold[k] <= qr_data[256*k +: 256];
                end
                default: ;
            endcase
        end
        if (rows_mine) land[10'(wcount) + q_d[9:0]] <= {112'd0, rows_bits};
        // fetch FIFO push
        if (sw_step && sw_i < sw_n[sw_r[4:0]] && g_own)
            fq[sid_g[8]][fq_w[sid_g[8]][3:0]] <= {sid_g[3:0], s_rank, sid_g[20:9]};
        // SEL words
        // engine program inputs
        eq_w <= qmem[4'(rc - 10'd1)];
        ekv_w <= kc_w; ekv_m <= kc_m;
        // PC request flops
        for (k = 0; k < 2; k = k + 1) qrq[341*k +: 341] <= nv[k] ? nreq[k] : '0;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < 3; k = k + 1) begin wq_w[k][0] <= 0; wq_w[k][1] <= 0; wq_r[k][0] <= 0; wq_r[k][1] <= 0; end
            for (k = 0; k < 2; k = k + 1) begin
                cr[k] <= 4'(DQ); wk_w[k] <= 0; wk_r[k] <= 0; wr_on[k] <= 0; wr_r[k] <= 0; sc_n[k] <= 0;
                fq_w[k] <= 0; fq_r[k] <= 0;
            end
            sw_w <= 0; sw_r <= 0; sw_i <= 0; sel_held <= 0; pres <= 0; spres <= 0; q_have <= 0;
            job_open <= 0; job_active <= 0; go_arm <= 0; go_cnt <= 0; go <= 0; run <= 0; rc <= 0;
            po <= 0; pvo <= 0; pio <= 0; jc <= 0; dr_arm <= 0; dr_on <= 0; dbeat <= 0;
            ej_v <= 0; eq_v <= 0; ekv_v <= 0; pw <= 0; pr <= 0; p_left <= 0;
            pvw <= 0; pvr <= 0; p_i <= 0; pv_n <= 0; pv_ov <= 0; done <= 0; go_o <= 0;
            hcr <= 0; hack <= 0; iss_host <= 0; fc <= 0;
            sm_st <= 0; sm_rv <= 0; sm_rp <= 0; sm_rj <= 0; sm_kind <= 0; sm_jid <= 0; sm_rd <= 0;
        end else begin
            // ---- write FIFO pointers
            for (k = 0; k < 3; k = k + 1) if (wpush[k]) begin
                wq_w[k][wpush_pc[k]] <= wq_w[k][wpush_pc[k]] + 1'b1;
                if (wq_w[k][wpush_pc[k]] - wq_r[k][wpush_pc[k]] >= 4'd8) fc[0] <= 1'b1;
            end
            // ---- issue
            iss_host <= 0;
            for (k = 0; k < 2; k = k + 1) begin
                cr[k] <= cr[k] - 4'(nv[k]) + 4'(qrk[k]);
                if (nv[k] && npop[k] != 3'd7) begin
                    wq_r[npop[k]][k] <= wq_r[npop[k]][k] + 1'b1;
                    wk[k][wk_w[k][3:0]] <= npop[k] == 3'd2;
                    wk_w[k] <= wk_w[k] + 1'b1;
                end
                if (qwd[k]) begin
                    wk_r[k] <= wk_r[k] + 1'b1;
                    if (wk_w[k] == wk_r[k]) fc[1] <= 1'b1;            // a write done with no write outstanding
                end
                if (nwin[k]) begin
                    if (32'(wr_r[k]) + 2 >= 32'(wcount)) wr_on[k] <= 1'b0;
                    wr_r[k] <= wr_r[k] + 8'd2;
                end
                if (nsc[k]) sc_n[k] <= sc_n[k] - 2'd1;
                if (nf[k]) fq_r[k] <= fq_r[k] + 1'b1;
                if (qrk[k] && cr[k] == 4'(DQ) && !nv[k]) fc[2] <= 1'b1;      // credit overflow
            end
            iss_host <= {nv[1] && npop[1] == 3'd2, nv[0] && npop[0] == 3'd2};
            hcr <= 2'(iss_host[0]) + 2'(iss_host[1]) + 2'(root && hw_v && hw_mark);
            hack <= 2'(qwd[0] && wk[0][wk_r[0][3:0]]) + 2'(qwd[1] && wk[1][wk_r[1][3:0]]);
            if (root && hw_v && !hw_sec && !(hw_mark && hw_d[288] && hw_d[290:289] < 2'd2)) fc[3] <= 1'b1;
            // ---- responses
            for (k = 0; k < 2; k = k + 1) if (qrv[k]) begin
                reg [16:0] tg; reg [11:0] o144;
                tg = qr_tag[17*k +: 17];
                o144 = 12'(tg[13:10]) * 12'd144;
                case (tg[16:15])
                    2'd0: pres[tg[7:0]] <= 1'b1;
                    2'd1: spres[{tg[1], tg[0]}] <= 1'b1;
                    2'd2: if ((32'(o144[7:0]) + 144 <= 256 && qr_beat[4*k +: 4] == 4'd0) || qr_beat[4*k +: 4] == 4'd1)
                              pres[10'(wcount) + tg[9:0]] <= 1'b1;
                    default: fc[4] <= 1'b1;                                   // a response to no read
                endcase
            end
            if (rows_mine) pres[10'(wcount) + q_d[9:0]] <= 1'b1;
            // ---- SEL words / scanner
            if (sel_pay) begin sw_w <= sw_w + 1'b1; if (sw_w - sw_r >= 6'd32) fc[5] <= 1'b1; end
            if (sw_step) begin
                if (sw_i < sw_n[sw_r[4:0]]) begin
                    sel_held[s_rank] <= sid_g[7:6] == st_r;
                    if (g_own) fq_w[sid_g[8]] <= fq_w[sid_g[8]] + 1'b1;
                end
                if (sw_i == 5'd15 || sw_i + 1'b1 >= sw_n[sw_r[4:0]]) begin sw_i <= 0; sw_r <= sw_r + 1'b1; end
                else sw_i <= sw_i + 1'b1;
            end
            // ---- job start (WIN_LOAD)
            if (start) begin
                if (job_open) fc[6] <= 1'b1;                                  // a job while one is open
                if (h_len != 0 || q_d[88:81] > 8'd128 || q_d[98:89] > 10'd512) fc[7] <= 1'b1;
                job_open <= 1'b1; done <= 1'b0; pres <= 0; spres <= 0; q_have <= 0;
                wr_r[0] <= 8'(q_d[99] ^ 1'b0); wr_r[1] <= 8'(q_d[99] ^ 1'b1);
                wr_on[0] <= 32'(q_d[99]) < 32'(q_d[88:81]); wr_on[1] <= 32'(!q_d[99]) < 32'(q_d[88:81]);
                sc_n[0] <= 2'd2; sc_n[1] <= 2'd2;
            end
            if (q_word && !start) q_have <= q_have + 1'b1;
            // ---- GO
            go <= 1'b0; go_o <= 1'b0;
            if (hdr_mine && h_type == 4'd13) begin
                if (!job_open || go_arm || run) fc[8] <= 1'b1;
                go_arm <= 1'b1; go_cnt <= gd; po <= q_d[15:0]; pvo <= q_d[31:16]; pio <= q_d[47:32];
            end else if (go_arm) begin
                if (go_cnt == 0) begin go_arm <= 1'b0; go <= 1'b1; go_o <= 1'b1; end
                else go_cnt <= go_cnt - 1'b1;
            end
            // ---- the static program
            ej_v <= 1'b0; eq_v <= 1'b0; ekv_v <= 1'b0;
            if (go) begin
                run <= 1'b1; rc <= 10'd1; ej_v <= 1'b1; job_active <= 1'b1; pv_n <= 0;
                if (dr_arm || dr_on) fc[22] <= 1'b1;                          // a start while P.V of the last job drains
                dr_arm <= pvown;
                if(pv_identity_bad) fc[23]<=1'b1;
                p_left <= (16'(tjob) + 16'(R) - 1) / 16'(R);
                if (q_have != 5'd16) fc[9] <= 1'b1;                           // q not loaded at the compiled start
            end else if (run) begin
                eq_v <= rc <= 10'd16;
                ekv_v <= rc <= nbeat;
                if (rc <= nbeat && |rel_bad) fc[10] <= 1'b1;                  // a row not landed at its release cycle
                if (rc >= 10'd16 && rc >= nbeat) run <= 1'b0;
                rc <= rc + 1'b1;
            end
            if (ej_v && !ej_ready) fc[11] <= 1'b1;
            if (eq_v && !eq_ready) fc[12] <= 1'b1;
            if (ekv_v && !kv_ready) fc[13] <= 1'b1;
            // ---- p feed (local: P.V is not cross-slice aligned)
            if (pay_mine && f_type == 4'd5) begin pw <= pw + 1'b1; if (pcnt >= (PFW+1)'(PFIFO)) fc[14] <= 1'b1; end
            // ---- static p feed: the step is taken at its compiled cycle whatever the engine says; a refusal is a fault
            jc <= go ? 16'd1 : (jc == 16'hffff ? jc : jc + 1'b1);
            if (ep_v) begin
                pr <= pr + (PFW+1)'(pstep); p_left <= p_left - 16'(pstep);
                if (pcnt < (PFW+1)'(pstep)) fc[20] <= 1'b1;                   // p words not landed at the step's cycle
                if (!ep_ready) fc[21] <= 1'b1;                                // the engine did not take the compiled step
            end
            // ---- scores: straight to the score exchange (valid-only, no credit)
            // ---- P.V words: owner slices emit 5 words a beat (valid-only, never stalled)
            pv_ov <= 1'b0;
            if (pv_v) begin
                pv_n <= pv_n + 1'b1;
                if (pv_n == 4'd7) begin job_active <= 1'b0; job_open <= 1'b0; done <= !pvown; end   // owners: at drain end
            end
            if (pvown) begin
                if (pv_v) begin pvw <= pvw + 1'b1; if ((PA+1)'(pvw - pvr) >= (PA+1)'(PVQ)) fc[15] <= 1'b1; end
                // compiled drain window: 8 beats x 5 words from PVO + pvs, back to back
                if (dr_arm && !go && jc == pvo + 16'(pvs)) begin dr_arm <= 1'b0; dr_on <= 1'b1; p_i <= 0; dbeat <= 0; end
                if (dr_on) begin
                    pv_ov <= 1'b1;
                    if (p_i == 3'd0 && pvw == pvr) fc[19] <= 1'b1;            // the beat is not produced at its slot
                    p_i <= (p_i == 3'd4) ? 3'd0 : p_i + 1'b1;
                    if (p_i == 3'd4) begin
                        pvr <= pvr + 1'b1; dbeat <= dbeat + 1'b1;
                        if (dbeat == 3'd7) begin dr_on <= 1'b0; done <= 1'b1; end
                    end
                end
            end
            // ---- SMJ frames -> SM head
            sm_st <= 1'b0; sm_rv <= 1'b0;
            if (hdr_mine && h_type == 4'd9) begin
                sm_st <= q_d[0]; sm_kind <= q_d[4:1]; sm_jid <= q_d[12:5];
            end
            if (pay_mine && f_type == 4'd9) begin
                sm_rv <= !f_hdr[13] || f_hdr[14 + tile];
                sm_rp <= !f_hdr[13]; sm_rj <= 3'(f_idx); sm_rd <= q_d;
            end
            // ---- other frame checks
            if (hdr_mine && !(h_type inside {4'd1, 4'd2, 4'd3, 4'd5, 4'd6, 4'd7, 4'd9, 4'd12, 4'd13, 4'd14, 4'd15})) fc[16] <= 1'b1;
            if (hdr_mine && h_type == 4'd1 && h_len != 12'd128) fc[16] <= 1'b1;
            if (hdr_mine && h_type == 4'd3 && h_len != 12'd16) fc[16] <= 1'b1;
            if (hdr_mine && h_type == 4'd15 && h_len != 12'd1) fc[16] <= 1'b1;            // IK_ROW: exactly 1 payload word
            if (hdr_mine && (h_type inside {4'd1, 4'd5, 4'd6, 4'd7}) && !job_open) fc[17] <= 1'b1;
            if (sc_v && !job_active) fc[18] <= 1'b1;
        end
    end
endmodule
// Exact source-owned identity used by the real ATT header above. Keeping launch
// context separate from CFG prevents later configuration from relabelling an old
// P.V drain. No numerical payload enters this block.
module dsdv_pv_source_identity #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cfg_v,input wire[19:0]cfg_owner,input wire cfg_valid,
 input wire launch,launch_ok,input wire[9:0]user_id,input wire[7:0]tag_id,
 input wire[1:0]quarter,input wire[3:0]tile,input wire[20:0]position,
 output wire[439:0]provenance,output wire bad
);
 generate if(ENABLE==0)begin:g_disabled assign provenance=440'd0;assign bad=1'b0;end
 else begin:g_enabled
  reg[19:0]pending,owner;reg valid,live;reg[1:0]q;reg[3:0]t;reg[20:0]pos;
  always @(posedge clk or negedge rst_n)if(!rst_n)begin pending<=0;owner<=0;valid<=0;live<=0;q<=0;t<=0;pos<=0;end
  else begin
   if(cfg_v)begin pending<=cfg_owner;valid<=cfg_valid;end
   if(launch)begin owner<=pending;live<=launch_ok && valid && pending[17:0]=={user_id,tag_id};q<=quarter;t<=tile;pos<=position;end
  end
  assign provenance={392'd0,pos,live,t,q,owner};
  assign bad=launch && (!launch_ok || !valid || pending[17:0]!={user_id,tag_id});
 end endgenerate
endmodule
