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
//   12 CFG      [29:0] WB (window ring base)
//    3 OWN_ROW  [479:459] pos, [458:449] user; payload block b = {scale 8, codes 256}: block t is written (2 writes)
//    2 WIN_LOAD as svc_c ([29:0] SB, [88:81] wcount, [98:89] nsel, [119:99] first window pos, [458:449] user, tag)
//    7 SEL_IDS  as svc_c; the slice records per rank whether the row is this stack's (held) and fetches its own rows
//    1 ATTN_Q   as svc_c; word r = head 8 b + r / 16, dims 32 (r % 16) .. : the slice keeps r % 16 == t
//    6 ROWS     as svc_c; the slice keeps pair t / 2, half t % 2
//    5 PV       as svc_c (stored by every slice, used by the 4 slices of quarter ST, which emit P.V)
//   13 GO       (new, len 0) the compiled start: the engine share starts gd cycles after GO reaches this slice;
//               [15:0] PO = the p-feed start, [31:16] PVO = the P.V drain base, both in cycles after the share's start
//    9 SMJ      (new) SM head job / rows: [0] start, [4:1] kind, [12:5] jid, [13] operand rows (else parameter rows,
//               r_j = payload index), [29:14] head mask (operand rows only)
//   14 SOT      (S81-SMWIRE 10-19, len 2) the SO target config of the job: parsed by dsdv_svc_sot beside this share
//               (tools/s81_dv/sm_target/dsdv_sm_wire.sv); a legal frame type here, no state in the attention share
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
// the pair, 3 = q chunk of the neighbouring tile, 4 = p store: words read from the wrong (even / odd) bank,
// 5 = p store: no prefetch (the banks are read at the CURRENT pr, so the step gets the previous step's words).
// SVCB (HOURLY-S81/SVCB 10-19, COORD 0ix (2) option (b)): the p store pmem (was a 512 x 512 flop memory written in all
// 16 slices) is two banks (even / odd word address) of 2 x ot_sram_1r1w_256x256 (256 rows x 512 b a bank), so the
// step's two words pr / pr + 1 are one read in each bank.  The macros read on the clock edge (rd_out registered), so
// the banks are read ONE CYCLE AHEAD at the step's address pr_n = the pr the next cycle will hold (static: ep_v and
// pstep are known a cycle ahead from registered state).  Read schedule unchanged (0 cycles); the only cost is that a
// p word must land one cycle before its step's PREFETCH cycle (fault 20 now checks the words written up to the cycle
// before, pw_q; the compiler PO rule already leaves >= 1 cycle).  PMEM 0 drops the store (the slices that never own
// P.V: kits for the non-owner positions; pointers and fault checks stay); a PMEM 0 slice whose role is a P.V owner is
// fault 23 (static configuration error).
// MUT 6 (OT_SVC_LAND_SRAM only): the landing reads copy 0 (PC 0 writes) whatever the live-value table says.
// SVC2 (10-19, LEAD2-S81/SVC2, safe-design 5): -DOT_SVC_ATT_SRAM (with OT_SVC_LAND_SRAM) puts every runtime-indexed store
// > 2 kb in SRAM: wq classes 0 / 2, the SEL FIFO sw, the q store and the P.V buffer pvq become dsdv_svc_fmem rings of
// ot_sram_1r1w_32x128_m1 (registered read at the next-cycle address + one-word write-through = the flop array's
// combinational read, 0 cycles); the live-value table becomes 3 single-writer written-this-job vectors.
// MUT 7 (OT_SVC_ATT_SRAM only): no write-through (a word written and read on the same edge reads the old content).
// SVC2 (10-19, safe-design 1): dsdv_svc_att is a thin wrapper of dsdv_svc_att_core.  -DOT_SVC_ATT_PINREG registers every
// input pin (the broadcast stream copy q / hw and the two PC faces: +1 edge on each, priced in the compiler) and the
// fault OR (+1 edge on the sticky fault status); every other output is already a core flop.  Without the define the
// wrapper is wires only (existing users unchanged).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_att_core #(
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer PFIFO = 512,                // p store depth: 512 = 2 banks x 256 rows (the macro depth)
    parameter integer PMEM = 1,                   // 1: the p store (4 x ot_sram_1r1w_256x256), 0: dropped (non-owner)
    parameter integer PVQ = 8,                    // P.V buffer = the beats of one job (static drain, no credit)
    parameter integer DQ = 8,
    parameter bit SRAM_MACRO = 0,
    parameter bit QMEM_SRAM = 0,               // opt-in: native 8x32x64, same capture edge
    parameter integer TEXT = 0,                   // SVC4: 1 = engine tiles outside (landed parent dsdv_svc_attw_f_lp), see
    parameter integer TLX = 0,                    //   ot_hdc_v41x_attn_s TEXT / TLX / TXD; tile bundles on tx_i / tx_o
    parameter integer TXD = 0                     //   (4 tiles x 1,618 b out, 4 x 529 b back)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [3:0]           sid,
    input  wire [3:0]           tile,
    input  wire [7:0]           gd,
    input  wire [7:0]           pvs,               // compiled P.V drain slot after the job's PVO (255: not an owner)
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
    output wire [4*1618-1:0]    tx_i,
    input  wire [4*529-1:0]     tx_o
);
    localparam integer H = 16, D = 32, TD = 32, NL = 4, NT = NL * (D / TD), R = TD / H;
    localparam integer PFW = $clog2(PFIFO);
    localparam integer TR = 640;
    localparam [15:0] FT_KNOWN = 16'b0111_0010_1110_1110;   // bits 1 2 3 5 6 7 9 12 13 14 (14 = SOT, S81-SMWIRE)
    localparam [15:0] FT_JOB = 16'b0000_0000_1110_0010;     // bits 1 5 6 7
    reg [31:0] fc;
    assign fault_code = fc;
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
    reg [7:0] wcount; reg [9:0] nsel; reg [20:0] wfirst; reg [9:0] wuser;
    reg job_open, job_active;                       // job_open: WIN_LOAD seen, engine program not yet done
    wire start = hdr_mine && h_type == 4'd2;
    wire [9:0] tjob = 10'(wcount) + nsel;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wb <= 0; sb <= 0; wcount <= 0; nsel <= 0; wfirst <= 0; wuser <= 0; tagj <= 0; end
        else begin
            if (hdr_mine && h_type == 4'd12) wb <= q_d[29:0];
            if (start && !job_open) begin
                sb <= q_d[29:0]; wcount <= q_d[88:81]; nsel <= q_d[98:89]; wfirst <= q_d[119:99];
                wuser <= q_d[458:449]; tagj <= q_d[502:495];
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
`ifdef OT_SVC_ATT_SRAM
    // SVC2 (10-19, safe-design 5): classes 0 (OWN_ROW codes) and 2 (host words) in dsdv_svc_fmem SRAM rings (8 of 32
    // rows, {data 256, addr 30}: strobe / tag / len are constants of the class); class 1 (OWN_ROW scale byte) is 43 b an
    // entry {addr 30, byte index 5, byte 8} (2 x 8 x 43 = 688 b of flops).  Heads read at the next-pointer address with
    // write-through: the issue mux sees the identical word on the identical cycle (0 cycles).
    reg [42:0] wq1 [0:1][0:7];
    reg [42:0] wpush_c1;
`else
    reg [340:0] wq [0:2][0:1][0:7];
`endif
    wire [340:0] whead [0:2][0:1];                   // FIFO heads (class, PC)
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
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wpush <= 0;
        else wpush <= {hw_mine, ow_blk, ow_blk};
    always @(posedge clk) begin
        wpush_d[0] <= wr_req(ow_ring + 30'(ow_slot[6:1]), 32'hffffffff, q_d[255:0], 17'h1fffe);
        wpush_pc[0] <= ow_slot[0];
        wpush_d[1] <= wr_req(ow_ring + 30'd64 + 30'(ow_slot[6]), 32'd1 << ow_by, 256'(q_d[263:256]) << (8 * ow_by), 17'h1fffe);
`ifdef OT_SVC_ATT_SRAM
        wpush_c1 <= {ow_ring + 30'd64 + 30'(ow_slot[6]), ow_by, q_d[263:256]};
`endif
        wpush_pc[1] <= ow_slot[5];
        wpush_d[2] <= wr_req(hw_d[285:256], 32'hffffffff, hw_d[255:0], 17'h1ffff);
        wpush_pc[2] <= hw_pc[0];
    end

    // ------------------------------------------------------------------ SEL_IDS -> per-rank stack table + own-row fetch
    reg [9:0] s_first; reg [9:0] s_cnt;
`ifdef OT_SVC_ATT_SRAM
    // SVC2 (10-19, safe-design 5): the SEL word FIFO (32 x {n 5, base 10, word 512}) in a dsdv_svc_fmem SRAM ring (5 x 32x128),
    // head read at the next-pointer address with write-through (0 cycles)
    wire [526:0] sw_h;
`else
    reg [511:0] sw [0:31]; reg [9:0] sw_base [0:31]; reg [4:0] sw_n [0:31];
    wire [526:0] sw_h = {sw_n[sw_r[4:0]], sw_base[sw_r[4:0]], sw[sw_r[4:0]]};
`endif
    wire [9:0] sw_hb = sw_h[521:512];
    wire [4:0] sw_hn = sw_h[526:522];
    reg [5:0] sw_w, sw_r; reg [4:0] sw_i;
    always @(posedge clk) if (hdr_mine && h_type == 4'd7) begin s_first <= q_d[9:0]; s_cnt <= q_d[19:10]; end
    wire sel_pay = pay_mine && f_type == 4'd7;
    reg [511:0] sel_held;                            // rank -> the row is this stack's (all 16 tiles arrive)
    // fetch FIFOs per PC {k 4, rank 10, block 12}
    reg [25:0] fq [0:1][0:15]; reg [4:0] fq_w [0:1], fq_r [0:1];
    wire [511:0] swd = sw_h[511:0];
    wire [31:0] sid_g = swd[32*sw_i +: 32];
    wire [9:0] s_rank = sw_hb + 10'(sw_i);
    wire sw_have = sw_w != sw_r;
    wire g_own = sid_g[5:4] == 2'(DIE_ID) && sid_g[7:6] == 2'(ST);
    wire f_full = (fq_w[sid_g[8]] - fq_r[sid_g[8]]) >= 5'd16;
    wire sw_step = sw_have && !(g_own && f_full);    // the fetch side waits on the elastic HBM boundary only
    wire [9:0] sw_wb = 10'(s_first) + 10'(f_idx[5:0]) * 10'd16;
    wire [4:0] sw_wn = (32'(s_cnt) - 32'(f_idx) * 16 >= 16) ? 5'd16 : 5'(32'(s_cnt) - 32'(f_idx) * 16);
`ifdef OT_SVC_ATT_SRAM
    wire [5:0] sw_rn = sw_r + 6'(sw_step && (sw_i == 5'd15 || sw_i + 1'b1 >= sw_hn));   // sw_r of the next cycle
    dsdv_svc_fmem #(.W(527), .BYP((MUT == 7) ? 0 : 1)) u_swm (.clk(clk), .we(sel_pay), .wa(sw_w[4:0]),
        .wd({sw_wn, sw_wb, q_d}), .ra(sw_rn[4:0]), .rd(sw_h));
`else
    always @(posedge clk) if (sel_pay) begin
        sw[sw_w[4:0]] <= q_d; sw_base[sw_w[4:0]] <= sw_wb;
        sw_n[sw_w[4:0]] <= sw_wn;
    end
`endif

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
                if (wq_w[2][p] != wq_r[2][p]) begin nv[p] = 1; nreq[p] = whead[2][p]; npop[p] = 3'd2; end
                else if (wq_w[0][p] != wq_r[0][p]) begin nv[p] = 1; nreq[p] = whead[0][p]; npop[p] = 3'd0; end
                else if (wq_w[1][p] != wq_r[1][p]) begin nv[p] = 1; nreq[p] = whead[1][p]; npop[p] = 3'd1; end
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

    genvar wc, wp;
    generate for (wc = 0; wc < 3; wc = wc + 1) begin : g_wqh
        for (wp = 0; wp < 2; wp = wp + 1) begin : g_p
`ifdef OT_SVC_ATT_SRAM
            wire [3:0] rn = wq_r[wc][wp] + 4'(nv[wp] && npop[wp] == 3'(wc));               // read pointer of the next cycle
            if (wc == 1) begin : g_c1
                wire [42:0] e = wq1[wp][wq_r[1][wp][2:0]];
                assign whead[wc][wp] = {256'(e[7:0]) << (8 * e[12:8]), 32'd1 << e[12:8], 17'h1fffe, 4'd1, e[42:13], 2'b11};
            end else begin : g_m
                wire [285:0] rd;
                dsdv_svc_fmem #(.W(286), .BYP((MUT == 7) ? 0 : 1)) u_wqm (.clk(clk),
                    .we(wpush[wc] && wpush_pc[wc] == 3'(wp)), .wa({2'd0, wq_w[wc][wp][2:0]}),
                    .wd({wpush_d[wc][340:85], wpush_d[wc][31:2]}), .ra({2'd0, rn[2:0]}), .rd(rd));
                assign whead[wc][wp] = {rd[285:30], 32'hffffffff, (wc == 2) ? 17'h1ffff : 17'h1fffe, 4'd1, rd[29:0], 2'b11};
            end
`else
            assign whead[wc][wp] = wq[wc][wp][wq_r[wc][wp][2:0]];
`endif
        end
    end endgenerate

    // ------------------------------------------------------------------ landing (slot-addressed: no overflow)
`ifndef OT_SVC_LAND_SRAM
    reg [255:0] land [0:TR-1];
`endif
    reg [TR-1:0] pres;
    reg [1023:0] wsc;                                // window scales, 128 slots x 8
    reg [3:0] spres;
    reg [255:0] hold [0:1];
    // ROWS
    wire rows_mine = pay_mine && f_type == 4'd6 && q_d[33:31] == tile[3:1];
    wire rh = (MUT == 2) ? ~tile[0] : tile[0];
    wire [143:0] rows_bits = {q_d[290 + 16*rh +: 16], q_d[34 + 128*rh +: 128]};

    // ------------------------------------------------------------------ q store
    // QMEM_SRAM does not alter parser, GO, q_have or engine valid ages.
    reg [4:0] q_have;
    wire [3:0] qt = (MUT == 3) ? tile + 4'd1 : tile;
    wire q_word = pay_mine && f_type == 4'd1 && f_idx[3:0] == qt;

    // ------------------------------------------------------------------ static program (GO + gd)
    reg [7:0] go_cnt; reg go_arm; reg go;
    reg [15:0] po, pvo, jc;                         // compiled p-feed start / P.V drain base; cycles since the share's start
    reg dr_arm, dr_on; reg [2:0] dbeat;
    reg [9:0] rc; reg run;                           // program cycle
    wire [9:0] nbeat = (tjob + 10'd3) >> 2;
    // engine ports
    reg ej_v; reg eq_v; wire [D*16-1:0] eq_w; reg ekv_v; reg [NL-1:0] ekv_m, kc_m;
`ifndef OT_SVC_LAND_SRAM
    reg [NL*265-1:0] ekv_w, kc_w;
`else
    wire [NL*265-1:0] ekv_w;
    reg [NL-1:0] kc_win, kc_need; reg [NL*8-1:0] kc_sc;     // release side information of the 4 lanes
`endif
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
`ifndef OT_SVC_LAND_SRAM
        kc_w = '0;
`else
        kc_win = '0; kc_need = '0; kc_sc = '0;
`endif
        kc_m = '0; rel_bad = '0; row = 0; need = 1'b0; ok = 1'b0;
        for (j = 0; j < NL; j = j + 1) begin
            row = 4 * (32'(rc) - 1) + j; need = 1'b0; ok = 1'b0;
            if (row < 32'(tjob)) begin
                kc_m[j] = 1'b1;
                need = (row < 32'(wcount)) || sel_held[row - 32'(wcount)] || tile[3:2] == 2'(ST);
                ok = pres[row] && (row >= 32'(wcount) || spres[7'(wfirst[6:0] + 7'(row)) >> 5]);
`ifndef OT_SVC_LAND_SRAM
                kc_w[265*j +: 265] = rowword(row, land[row], wsc, wcount, wfirst, need);
`else
                // rowword() split: the row word itself comes from the land SRAM read at this edge (g_land)
                kc_win[j] = row < 32'(wcount); kc_need[j] = need;
                kc_sc[8*j +: 8] = wsc[8*(7'(wfirst[6:0] + 7'(row))) +: 8];
`endif
                rel_bad[j] = need && !ok;
            end
        end
    end

`ifdef OT_SVC_LAND_SRAM
    // ------------------------------------------------------------------ landing in SRAM (S81-CTRL-SVC 10-19, safe-design 5)
    // The 640 x 256 flop landing (3 runtime writes + 4 runtime reads a cycle: ~164 kb of flops and four 640:1 x 256 b
    // read muxes, the >8 h yosys OPT loop of the 369345 gates) becomes 12 x ot_sram_1r1w_256x256: bank b = row[1:0]
    // (the 4 rows a release beat reads, 4 (rc - 1) + j, are one row in each bank at address rc - 1) x write copy c
    // (c 0 / 1 = PC 0 / 1 responses, c 2 = ROWS: one writer a copy, so no bank write conflict exists by construction),
    // plus a live-value table lvt[row] (640 x 2 flops) naming the copy that holds the row's last write (same-cycle
    // priority as the flop version: ROWS > PC 1 > PC 0).  The banks read at the release edge itself (address rc - 1 from
    // registered rc) and rd_out replaces the ekv_w register: SRAM read-old == the flop version's nonblocking read, so
    // the engine sees the identical word on the identical cycle (0 cycles added).  Side information (lane mask, window /
    // need / scale byte, live copy) is registered on the same edge.
    reg [2:0] lw_v; reg [9:0] lw_a [0:2]; reg [255:0] lw_d [0:2];
    integer lk;
    always @(*) begin
        lw_v = '0;
        for (lk = 0; lk < 3; lk = lk + 1) begin lw_a[lk] = '0; lw_d[lk] = '0; end
        for (lk = 0; lk < 2; lk = lk + 1) begin : g_lw     // SVC2: temporaries assigned every pass (no latch)
            reg [16:0] tg; reg [11:0] o144; reg [511:0] two;
            tg = qr_tag[17*lk +: 17];
            o144 = 12'(tg[13:10]) * 12'd144;
            two = {qr_data[256*lk +: 256], hold[lk]};
            if (qrv[lk] && tg[16:15] == 2'd0) begin
                lw_v[lk] = 1'b1; lw_a[lk] = 10'(tg[7:0]); lw_d[lk] = qr_data[256*lk +: 256];
            end else if (qrv[lk] && tg[16:15] == 2'd2) begin
                lw_a[lk] = 10'(wcount) + tg[9:0];
                if (32'(o144[7:0]) + 144 <= 256 && qr_beat[4*lk +: 4] == 4'd0) begin
                    lw_v[lk] = 1'b1; lw_d[lk] = {112'd0, 144'(qr_data[256*lk +: 256] >> o144[7:0])};
                end else if (qr_beat[4*lk +: 4] == 4'd1) begin
                    lw_v[lk] = 1'b1; lw_d[lk] = {112'd0, 144'(two >> o144[7:0])};
                end
            end
        end
        if (rows_mine) begin lw_v[2] = 1'b1; lw_a[2] = 10'(wcount) + q_d[9:0]; lw_d[2] = {112'd0, rows_bits}; end
        for (lk = 0; lk < 3; lk = lk + 1) if (lw_a[lk] >= 10'(TR)) lw_v[lk] = 1'b0;   // flop version: out-of-range write dropped
    end
`ifdef OT_SVC_ATT_SRAM
    // SVC2 (10-19): the 640 x 2 live-value table (3 runtime writers into one array + 4 reads) becomes 3 single-writer
    // written-this-job vectors (copy c sets lv[c][row]; cleared with pres at the job start, as pres).  A row has one
    // writer per job (window row: PC wfirst[0] ^ row[0]; selected row: its fetch PC or ROWS), so the newest copy of a
    // row the job reads is the one copy whose bit is set (same-cycle priority ROWS > PC 1 > PC 0 kept).
    reg [TR-1:0] lv0, lv1, lv2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lv0 <= '0; lv1 <= '0; lv2 <= '0; end
        else if (start) begin lv0 <= '0; lv1 <= '0; lv2 <= '0; end
        else begin
            if (lw_v[0]) lv0[lw_a[0]] <= 1'b1;
            if (lw_v[1]) lv1[lw_a[1]] <= 1'b1;
            if (lw_v[2]) lv2[lw_a[2]] <= 1'b1;
        end
`else
    reg [1:0] lvt [0:TR-1];
    always @(posedge clk) for (int wl = 0; wl < 3; wl = wl + 1) if (lw_v[wl]) lvt[lw_a[wl]] <= 2'(wl);
`endif
    reg [NL*2-1:0] l_sel; reg [NL-1:0] l_win, l_need; reg [NL*8-1:0] l_sc;
    wire [9:0] l_row [0:NL-1];
    genvar lr;
    for (lr = 0; lr < NL; lr = lr + 1) begin : g_lrow
        assign l_row[lr] = {rc[7:0] - 8'd1, 2'(lr)};            // 4 (rc - 1) + j: rows of release beat rc
    end
    integer lj;
    always @(posedge clk) begin
        for (lj = 0; lj < NL; lj = lj + 1)       // only rows < tjob <= TR reach ekv_w (others: lane mask 0)
`ifdef OT_SVC_ATT_SRAM
            l_sel[2*lj +: 2] <= (l_row[lj] >= 10'(TR)) ? 2'd0 : lv2[l_row[lj]] ? 2'd2 : lv1[l_row[lj]] ? 2'd1 : 2'd0;
`else
            l_sel[2*lj +: 2] <= (l_row[lj] < 10'(TR)) ? lvt[l_row[lj]] : 2'd0;
`endif
        l_win <= kc_win; l_need <= kc_need; l_sc <= kc_sc;
    end
    wire [8:0] l_ra = 9'(rc - 10'd1);
    wire [3*NL*256-1:0] lq;
    genvar lc, lb;
    generate for (lc = 0; lc < 3; lc = lc + 1) begin : g_land
        for (lb = 0; lb < NL; lb = lb + 1) begin : g_b
            ot_sram_1r1w_256x256_m2_r2c2 u_mem (.clk(clk), .r_ce_in(1'b1), .r_addr_in(l_ra[7:0]),
                .rd_out(lq[256*(NL*lc + lb) +: 256]),
                .w_ce_in(lw_v[lc] && lw_a[lc][1:0] == 2'(lb)), .w_addr_in(lw_a[lc][9:2]), .wd_in(lw_d[lc]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        end
        for (lb = 0; lb < NL; lb = lb + 1) begin : g_lw_o
            wire [1:0] s = (MUT == 6) ? 2'd0 : l_sel[2*lb +: 2];      // MUT 6: no live-value table (copy 0 only)
            wire [255:0] l = (s == 2'd2) ? lq[256*(2*NL + lb) +: 256] : (s == 2'd1) ? lq[256*(NL + lb) +: 256]
                                                                        : lq[256*lb +: 256];
            assign ekv_w[265*lb +: 265] = !ekv_m[lb] ? 265'd0 : l_win[lb] ? {1'b0, l_sc[8*lb +: 8], l}
                                        : l_need[lb] ? {1'b1, 120'd0, l[143:0]} : {1'b1, 264'd0};
        end
    endgenerate
`endif

`ifdef OT_SVC_ATT_SRAM
    // SVC2 (10-19): q store 16 x 512 in a dsdv_svc_fmem (4 x 32x128), read at rc - 1 on the edge (read-old == the legacy
    // registered eq_w_q read; no write-through, as legacy): 0 cycles
    dsdv_svc_fmem #(.W(512), .BYP(0)) u_qmm (.clk(clk), .we(q_word), .wa({1'b0, f_hdr[448], f_idx[6:4]}), .wd(q_d),
        .ra({1'b0, 4'(rc - 10'd1)}), .rd(eq_w));
`else
    generate if (QMEM_SRAM) begin : g_qmem_sram
        dsdv_svc_qmem8 u_qmem (.clk(clk), .wr_v(q_word),
            .wr_head({f_hdr[448], f_idx[6:4]}), .wr_data(q_d),
            .rd_head(4'(rc - 10'd1)), .rd_data(eq_w));
    end else begin : g_qmem_legacy
        reg [D*16-1:0] qmem [0:H-1];
        reg [D*16-1:0] eq_w_q;
        always @(posedge clk) begin
            if (q_word) qmem[{f_hdr[448], f_idx[6:4]}] <= q_d;
            eq_w_q <= qmem[4'(rc - 10'd1)];
        end
        assign eq_w = eq_w_q;
    end endgenerate
`endif

    // ------------------------------------------------------------------ p store (SVCB: 2 SRAM banks even / odd, prefetch)
    reg [PFW:0] pw, pr, pw_q;
    wire [PFW:0] pcnt = pw - pr;
    reg [15:0] p_left;
    wire [1:0] pstep = (p_left >= 16'd2) ? 2'd2 : 2'(p_left);
    wire pvown = tile[3:2] == 2'(ST);
    wire ep_v = job_active && p_left != 0 && jc >= po;          // static: from PO, a step every cycle
    wire ep_ready;
    wire p_wr = pay_mine && f_type == 4'd5;
    // the pr of the next cycle (the step's address one cycle ahead): registered state only
    wire [PFW:0] pr_n = ep_v ? pr + (PFW+1)'(pstep) : pr;
    wire [PFW:0] pr_a = (MUT == 5) ? pr : pr_n;                 // MUT 5: no prefetch
    wire [2*TD*16-1:0] pb_rd;                                   // {bank 1, bank 0} read words
    reg pr_odd;                                                  // bank of word pr (registered with the read)
    generate if (PMEM != 0) begin : g_pmem
        // word a -> bank a[0], row a[PFW-1:1]; word pr_a in bank pr_a[0], word pr_a + 1 in the other bank
        wire [PFW-2:0] row_e = pr_a[PFW-1:1] + (PFW-1)'(pr_a[0]);
        wire [PFW-2:0] row_o = pr_a[PFW-1:1];
        genvar bk, hf;
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
            for (hf = 0; hf < 2; hf = hf + 1) begin : g_half
                ot_sram_1r1w_256x256_m2_r2c2 u_mem (.clk(clk), .r_ce_in(pvown),
                    .r_addr_in(bk == 0 ? row_e : row_o), .rd_out(pb_rd[TD*16*bk + 256*hf +: 256]),
                    .w_ce_in(p_wr && pvown && pw[0] == 1'(bk)), .w_addr_in(pw[PFW-1:1]), .wd_in(q_d[256*hf +: 256]),
                    .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            end
        end
        always @(posedge clk) pr_odd <= (MUT == 4) ? ~pr_a[0] : pr_a[0];
    end else begin : g_nopmem
        assign pb_rd = '0;
        always @(posedge clk) pr_odd <= 1'b0;
    end endgenerate
    wire [TD*16-1:0] pw0 = pr_odd ? pb_rd[TD*16 +: TD*16] : pb_rd[0 +: TD*16];   // word pr
    wire [TD*16-1:0] pw1 = pr_odd ? pb_rd[0 +: TD*16] : pb_rd[TD*16 +: TD*16];   // word pr + 1
    wire [2*TD*16-1:0] ep_w = pvown ? {(pstep == 2'd2) ? pw1 : {TD*16{1'b1}}, pw0} : '0;

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
                         .SC_CRED(0), .PV_CRED(0), .TEXT(TEXT), .TLX(TLX), .TXD(TXD)) u_eng (
        .clk(clk), .rst_n(rst_n), .job_v(ej_v), .job_t({6'd0, tjob}), .job_ready(ej_ready),
        .q_v(eq_v), .q_w(eq_w), .q_ready(eq_ready),
        .kv_v(ekv_v), .kv_m(ekv_m), .kv_w(ekv_w), .kv_ready(kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(1'b0),
        .p_v(ep_v), .p_w(ep_w), .p_ready(ep_ready),
        .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f), .pv_cr(1'b0),
        .qk_iss(), .pv_iss(), .tx_i(tx_i), .tx_o(tx_o));
    assign l_v = sc_v;
    assign l_d = {sc_row, sc_m, sc_y, sc_f};

    // ------------------------------------------------------------------ P.V words (owner slices)
    localparam integer PVB = 8 + NT*H*32 + NT*H;
    localparam integer PA = $clog2(PVQ);
`ifndef OT_SVC_ATT_SRAM
    reg [PVB-1:0] pvq [0:PVQ-1];
`endif
    reg [PA:0] pvw, pvr;
    reg [2:0] p_i;
    reg [3:0] pv_n;
`ifdef OT_SVC_ATT_SRAM
    // SVC2 (10-19): P.V buffer 8 x 2120 in a dsdv_svc_fmem (17 x 32x128) on the P.V owner kits (PMEM 1); head read at the
    // next pvr with write-through (0 cycles).  PMEM 0 slices never drain (dr_arm needs pvown; pvown there is fault 23).
    wire [PVB-1:0] pb;
    wire [PA:0] pvr_n = pvr + (PA+1)'(pvown && dr_on && p_i == 3'd4);
    generate if (PMEM != 0) begin : g_pvq
        dsdv_svc_fmem #(.W(PVB), .BYP((MUT == 7) ? 0 : 1)) u_pvm (.clk(clk), .we(pv_v), .wa(5'(pvw[PA-1:0])),
            .wd({pv_c, pv_y, pv_f}), .ra(5'(pvr_n[PA-1:0])), .rd(pb));
    end else begin : g_nopvq
        assign pb = '0;
    end endgenerate
`else
    always @(posedge clk) if (pv_v) pvq[pvw[PA-1:0]] <= {pv_c, pv_y, pv_f};
    wire [PVB-1:0] pb = pvq[pvr[PA-1:0]];
`endif
    always @(posedge clk) if (dr_on)
        pv_od <= (p_i == 0) ? {1'b1, 440'd0, pb[PVB-1 -: 8], pb[NT*H-1:0]} : {1'b0, pb[NT*H + 32'(p_i - 1)*H*32 +: H*32]};

    // ------------------------------------------------------------------ sequential
    // SVC2 (10-19): block-local loop variables (one shared 'integer k' in the clk and the clk/rst_n blocks was two
    // conflicting drivers in yosys: a dff and an adff on dsdv_svc_att.k)
    always @(posedge clk) begin
        // write FIFO pushes
`ifdef OT_SVC_ATT_SRAM
        if (wpush[1]) wq1[wpush_pc[1]][wq_w[1][wpush_pc[1]][2:0]] <= wpush_c1;
`else
        for (int k = 0; k < 3; k = k + 1) if (wpush[k]) wq[k][wpush_pc[k]][wq_w[k][wpush_pc[k]][2:0]] <= wpush_d[k];
`endif
        // q store

        // landing writes: PC responses, ROWS
        for (int k = 0; k < 2; k = k + 1) if (qrv[k]) begin
            reg [16:0] tg; reg [11:0] o144; reg [511:0] two; reg [9:0] slot;
            tg = qr_tag[17*k +: 17];
            case (tg[16:15])
`ifndef OT_SVC_LAND_SRAM
                2'd0: land[tg[7:0]] <= qr_data[256*k +: 256];
`endif
                2'd1: wsc[256 * {tg[1], tg[0]} +: 256] <= qr_data[256*k +: 256];
                2'd2: begin
                    o144 = 12'(tg[13:10]) * 12'd144;
                    two = {qr_data[256*k +: 256], hold[k]};
                    slot = 10'(wcount) + tg[9:0];
`ifndef OT_SVC_LAND_SRAM
                    if (32'(o144[7:0]) + 144 <= 256 && qr_beat[4*k +: 4] == 4'd0)
                        land[slot] <= {112'd0, 144'(qr_data[256*k +: 256] >> o144[7:0])};
                    else if (qr_beat[4*k +: 4] == 4'd1)
                        land[slot] <= {112'd0, 144'(two >> o144[7:0])};
`endif
                    if (qr_beat[4*k +: 4] == 4'd0) hold[k] <= qr_data[256*k +: 256];
                end
                default: ;
            endcase
        end
`ifndef OT_SVC_LAND_SRAM
        if (rows_mine) land[10'(wcount) + q_d[9:0]] <= {112'd0, rows_bits};
`endif
        // fetch FIFO push
        if (sw_step && sw_i < sw_hn && g_own)
            fq[sid_g[8]][fq_w[sid_g[8]][3:0]] <= {sid_g[3:0], s_rank, sid_g[20:9]};
        // SEL words
        // engine program inputs

`ifndef OT_SVC_LAND_SRAM
        ekv_w <= kc_w;
`endif
        ekv_m <= kc_m;
        // PC request flops
        for (int k = 0; k < 2; k = k + 1) qrq[341*k +: 341] <= nv[k] ? nreq[k] : '0;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int k = 0; k < 3; k = k + 1) begin wq_w[k][0] <= 0; wq_w[k][1] <= 0; wq_r[k][0] <= 0; wq_r[k][1] <= 0; end
            for (int k = 0; k < 2; k = k + 1) begin
                cr[k] <= 4'(DQ); wk_w[k] <= 0; wk_r[k] <= 0; wr_on[k] <= 0; wr_r[k] <= 0; sc_n[k] <= 0;
                fq_w[k] <= 0; fq_r[k] <= 0;
            end
            sw_w <= 0; sw_r <= 0; sw_i <= 0; sel_held <= 0; pres <= 0; spres <= 0; q_have <= 0;
            job_open <= 0; job_active <= 0; go_arm <= 0; go_cnt <= 0; go <= 0; run <= 0; rc <= 0;
            po <= 0; pvo <= 0; jc <= 0; dr_arm <= 0; dr_on <= 0; dbeat <= 0;
            ej_v <= 0; eq_v <= 0; ekv_v <= 0; pw <= 0; pw_q <= 0; pr <= 0; p_left <= 0;
            pvw <= 0; pvr <= 0; p_i <= 0; pv_n <= 0; pv_ov <= 0; done <= 0; go_o <= 0;
            hcr <= 0; hack <= 0; iss_host <= 0; fc <= 0;
            sm_st <= 0; sm_rv <= 0; sm_rp <= 0; sm_rj <= 0; sm_kind <= 0; sm_jid <= 0; sm_rd <= 0;
        end else begin
            // ---- write FIFO pointers
            for (int k = 0; k < 3; k = k + 1) if (wpush[k]) begin
                wq_w[k][wpush_pc[k]] <= wq_w[k][wpush_pc[k]] + 1'b1;
                if (wq_w[k][wpush_pc[k]] - wq_r[k][wpush_pc[k]] >= 4'd8) fc[0] <= 1'b1;
            end
            // ---- issue
            iss_host <= 0;
            for (int k = 0; k < 2; k = k + 1) begin
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
            for (int k = 0; k < 2; k = k + 1) if (qrv[k]) begin
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
                if (sw_i < sw_hn) begin
                    sel_held[s_rank] <= sid_g[7:6] == 2'(ST);
                    if (g_own) fq_w[sid_g[8]] <= fq_w[sid_g[8]] + 1'b1;
                end
                if (sw_i == 5'd15 || sw_i + 1'b1 >= sw_hn) begin sw_i <= 0; sw_r <= sw_r + 1'b1; end
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
                go_arm <= 1'b1; go_cnt <= gd; po <= q_d[15:0]; pvo <= q_d[31:16];
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
            if (p_wr) begin pw <= pw + 1'b1; if (pcnt >= (PFW+1)'(PFIFO)) fc[14] <= 1'b1; end
            pw_q <= pw;                                                   // words written before the prefetch cycle
            if (go && PMEM == 0 && pvown) fc[23] <= 1'b1;                 // a P.V owner role on a slice without the p store
            // ---- static p feed: the step is taken at its compiled cycle whatever the engine says; a refusal is a fault
            jc <= go ? 16'd1 : (jc == 16'hffff ? jc : jc + 1'b1);
            if (ep_v) begin
                pr <= pr + (PFW+1)'(pstep); p_left <= p_left - 16'(pstep);
                if ((PFW+1)'(pw_q - pr) < (PFW+1)'(pstep)) fc[20] <= 1'b1;    // p words not landed by the step's prefetch cycle
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
            if (hdr_mine && !FT_KNOWN[h_type]) fc[16] <= 1'b1;   // frame types 1 2 3 5 6 7 9 12 13 14 (yosys: no 'inside')
            if (hdr_mine && h_type == 4'd1 && h_len != 12'd128) fc[16] <= 1'b1;
            if (hdr_mine && h_type == 4'd3 && h_len != 12'd16) fc[16] <= 1'b1;
            if (hdr_mine && FT_JOB[h_type] && !job_open) fc[17] <= 1'b1;   // frame types 1 5 6 7
            if (sc_v && !job_active) fc[18] <= 1'b1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// SVC2 (10-19): 32-row 1R1W SRAM ring for the dsdv_svc_att FIFOs: ceil(W / 128) x ot_sram_1r1w_32x128_m1 side by side.
// ra is the address the read samples on the edge (a FIFO passes its NEXT-cycle read pointer); BYP 1 adds the
// write-through of a word written on that same edge, so rd equals the combinational read of a flop array mem[ra_q]
// (BYP 0: the registered read-old of mem[ra], as an always @(posedge clk) q <= mem[ra]).
module dsdv_svc_fmem #(parameter integer W = 128, parameter integer BYP = 1) (
    input  wire         clk,
    input  wire         we,
    input  wire [4:0]   wa,
    input  wire [W-1:0] wd,
    input  wire [4:0]   ra,
    output wire [W-1:0] rd
);
    localparam integer NM = (W + 127) / 128;
    wire [NM*128-1:0] q;
    wire [NM*128-1:0] wdp = (NM*128)'(wd);
    genvar b;
    generate for (b = 0; b < NM; b = b + 1) begin : g_m
        ot_sram_1r1w_32x128_m1 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(q[128*b +: 128]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdp[128*b +: 128]), .w_mask_in({128{1'b1}}));
    end
    if (BYP != 0) begin : g_byp
        reg byp; reg [W-1:0] bd;
        always @(posedge clk) begin byp <= we && wa == ra; if (we) bd <= wd; end
        assign rd = byp ? bd : q[W-1:0];
    end else begin : g_nobyp
        assign rd = q[W-1:0];
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_att #(
    parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0, parameter integer PFIFO = 512,
    parameter integer PMEM = 1, parameter integer PVQ = 8, parameter integer DQ = 8,
    parameter bit SRAM_MACRO = 0, parameter bit QMEM_SRAM = 0,
    parameter integer TEXT = 0, parameter integer TLX = 0, parameter integer TXD = 0
) (
    input  wire clk, input wire rst_n, input wire [3:0] sid, input wire [3:0] tile, input wire [7:0] gd,
    input  wire [7:0] pvs, input wire root,
    input  wire q_v, input wire [511:0] q_d, input wire hw_v, input wire [290:0] hw_d,
    output wire [2*341-1:0] qrq, input wire [1:0] qrk, input wire [1:0] qwd, input wire [1:0] qrv,
    input  wire [2*256-1:0] qr_data, input wire [2*17-1:0] qr_tag, input wire [2*4-1:0] qr_beat,
    output wire l_v, output wire [2131:0] l_d, output wire pv_ov, output wire [512:0] pv_od,
    output wire sm_st, output wire [3:0] sm_kind, output wire [7:0] sm_jid, output wire sm_rv, output wire sm_rp,
    output wire [2:0] sm_rj, output wire [511:0] sm_rd,
    output wire go_o, output wire [9:0] tjob_o, output wire done, output wire [7:0] tagj,
    output wire [1:0] hcr, output wire [1:0] hack, output wire fault, output wire [31:0] fault_code,
    output wire [4*1618-1:0] tx_i, input wire [4*529-1:0] tx_o
);
`ifdef OT_SVC_ATT_PINREG
    reg pq_v, phw_v; reg [511:0] pq_d; reg [290:0] phw_d;
    reg [1:0] pqrk, pqwd, pqrv; reg [2*256-1:0] pqr_data; reg [2*17-1:0] pqr_tag; reg [2*4-1:0] pqr_beat;
    reg fault_q; wire fault_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pq_v <= 1'b0; phw_v <= 1'b0; pqrk <= '0; pqwd <= '0; pqrv <= '0; fault_q <= 1'b0; end
        else begin pq_v <= q_v; phw_v <= hw_v; pqrk <= qrk; pqwd <= qwd; pqrv <= qrv; fault_q <= fault_c; end
    always @(posedge clk) begin pq_d <= q_d; phw_d <= hw_d; pqr_data <= qr_data; pqr_tag <= qr_tag; pqr_beat <= qr_beat; end
    assign fault = fault_q;
`else
    wire pq_v = q_v, phw_v = hw_v; wire [511:0] pq_d = q_d; wire [290:0] phw_d = hw_d;
    wire [1:0] pqrk = qrk, pqwd = qwd, pqrv = qrv; wire [2*256-1:0] pqr_data = qr_data; wire [2*17-1:0] pqr_tag = qr_tag;
    wire [2*4-1:0] pqr_beat = qr_beat; wire fault_c;
    assign fault = fault_c;
`endif
    dsdv_svc_att_core #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .PFIFO(PFIFO), .PMEM(PMEM), .PVQ(PVQ), .DQ(DQ),
                        .SRAM_MACRO(SRAM_MACRO), .QMEM_SRAM(QMEM_SRAM), .TEXT(TEXT), .TLX(TLX), .TXD(TXD)) u_core (
        .clk(clk), .rst_n(rst_n), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(root),
        .q_v(pq_v), .q_d(pq_d), .hw_v(phw_v), .hw_d(phw_d),
        .qrq(qrq), .qrk(pqrk), .qwd(pqwd), .qrv(pqrv), .qr_data(pqr_data), .qr_tag(pqr_tag), .qr_beat(pqr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go_o), .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault_c),
        .fault_code(fault_code), .tx_i(tx_i), .tx_o(tx_o));
endmodule
