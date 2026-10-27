# S81-ROWX: held-row export for L14+ compressed attention (S81 877 die)

Lane started 2026-10-26 13:1x PDT (Claude). Source ruling: COORD 12:51 TOK-DS-3, option (a). Branch claude/s81-rowx-1026
(worktree epyc1:/srv/opentallas-scratch2/claude/wt/s81-rowx-1026, sparse). Owner rules applied: real hardware only,
static schedule (no credit / ready), no stubs / tied ports.

## Design spec (v1, 2026-10-26)

**Gap.** On the L14+ indexer layers every die needs all 512 selected compressed rows. Each (die, stack) holds about 1/16
of them (gid g: die g[5:4], stack g[7:6]; L14 die 0: 36/512). dsdv_svc_att fetches only its own held rows, into its own
landing store, and nothing exports them. The bench fed 476 ROWS words x 8 into both entries (3,809 q cycles).

**Where it sits.** All of it is in dsdv_svc_att (the attention share of every svc_rs slice, 16 per die), behind a new
parameter ROWX (0 = the pre-ROWX share, unchanged; LEC below). It needs no new port, no new die wire and no new core
pin.
- The export leaves on the slice's existing pv_ov / pv_od. That output feeds the P.V return tree, then the entry pv
  lane (w_pv_W / w_pv_E), then dsfd_dvland_pvrd, then the C3 slice band port bi (s_3S / s_4S) and its leaf store.
- From the leaf store, the existing xr send / ring / lep path carries the rows to the peer dies. There the C3 slice
  band port bo, then dsdv_idx_bsplit, then the peer svc entry q put them on the peer's q stream as ROWS frames.
- The transport hops are compiler programme (TOK-DS), not RTL.

**Held list.** The SEL_IDS scanner already walks the 512 ranks in order and pushes every own row (g_own) to the fetch
FIFO. With ROWX it also appends the rank to x_rk[0..XN-1] (XN = 128 ranks; fault 24 if the list overflows).

**Die position (fixes a pre-existing gap).** The die instantiates every dsdv_svc_rs with DIE_ID at its default of 0
(die_b178.v sets only PV_IDENTITY). One die type serves all TP positions, so g_own = (g[5:4] == 0) on every die, and
dies 1-3 would fetch die 0's rows. With ROWX, CFG [57] DP-valid and [56:55] DP set the position at run time, in the same
way CFG [32:30] sets ST. This needs no pin and no strap. DP-valid = 0 keeps the parameter.

**ROWX q frame (type 11, len 0, ALLQ jobs, before GO).**
- Header fields: [15:0] XO, [21:16] NXW (words per slice, a multiple of 5, at most 40), [28:22] XB (first list entry of
  this pass), [29] LAST.
- The start is ROWX + gd, the slice-aligned start, the same as GO.
- Word i (0 <= i < NXW) leaves pv_od in share cycle XO + pvs + 1 + i. pvs is the slice's compiled all-owner P.V drain
  slot, so the 8 tiles of a half arrive at the entry in disjoint 40-cycle windows, like their P.V drain. No
  arbitration is needed and the tree's two-words-in-a-cycle fault stays a schedule check.
- pv_od[512] = (i mod 5 == 0). To the entry and to dsfd_dvland_pvrd the export is therefore a P.V-shaped drain: word w
  lands at leaf w mod 5, rows rb + 4 (w div 5), as 2 row pairs.
- Word i carries list entries XB + 2i (half 0) and XB + 2i + 1 (half 1). A list entry past the held count gives an
  all-zero half (v = 0, padding).
- Rows are read from the landing store land[wcount + rank], which is the held-row fetch result, so the export makes no
  extra HBM read. The read goes through the engine's row read ports 0 / 1, which are shared; the engine program cannot
  run during an export. The export adds no landing read port.
- Faults (sticky, checks only):
  - 25: ROWX without an open ALLQ job, bad NXW, ROWX while armed / running / after GO, or GO during an export.
  - 26: LAST pass and held count > XB + 2 NXW (the budget overflowed).
  - 27: an exported row not landed at its cycle.
  - 28: an export word in the same cycle as a P.V drain word.

**ROW HALF (256 b, 1 row pair).**

| Bits | Field |
|---|---|
| [0] | v |
| [4:1] | tile |
| [14:5] | rank |
| [30:15] | the row's 2 E4M3 scales (land [143:128]) |
| [119:31] | nibbles [88:0] |
| [128:120] | 0 (on head words this is the dsdv_pv_den_stamp field, which PV_IDENTITY = 1 overwrites) |
| [167:129] | nibbles [127:89] |
| [255:168] | 0 |

**ROWS PK2 ingress (type 6, header spec [0] = 1).**
- Each payload word holds 2 ROW HALVES of two different tiles.
- Every slice already has one ROWS landing write port. The slice of tile t lands the half with v and tile == t through
  that port, so no new write port is added.
- Fault 29: both halves are for this tile, rank >= nsel, or the slot is already landed (this also catches a die-position
  error).
- spec [0] = 0 keeps the pair-format ROWS word, unchanged.
- The transport must re-pair the export's same-tile halves into mixed-tile words. Each half is one 256-b leaf row pair,
  and the xr send packs pairs from any leaves / rows. This is a compiler rule for TOK-DS.

**Schedule and numbers.** All UNCHECKED arithmetic from the fixture counts unless marked.
- Export per die and half: 8 x NXW words inside 8 x 40 = 320 entry cycles.
  - Before GO, the return tree and pv lane are idle, because the P window [PIO, PVO) and the drain both follow GO.
  - The half's export word count must be a multiple of the pvrd strap nw = 160, so NXW is 20 or 40 (budget 40 / 80
    rows per (die, stack) per pass).
  - XB / LAST give more passes if the compiler books them.
- Ingress per half (PK2, static booking B = 2 NXW rows per owner, 15 peer owners): 60 B words + 1 header.
  - B = 40 gives 2,401 q cycles per half. The two halves run in parallel because E and W each carry only their own
    8 tiles.
  - Measured bench: 3,809 (both halves get all 8 pairs).
  - Data-exact (fixture counts known): 476 x 8 / 2 + 1 = 1,905 per half. That is the same as the legacy pair format
    filtered per half (476 x 4 + 1). The pair format cannot be built from per-slice exports (a word needs 2 slices'
    data, and its fields straddle 128-b rows).
  - 4.5-word packing (2304 b/row) needs a real row assembler (more area). It is not built and not proposed.
- Budget: with B = 40, any layer where one (die, stack) holds more than 40 selected rows (average 32; L14 die 0 = 36)
  raises fault 26. That needs a second booked pass or an owner bound (ASK below).

**Area estimate (UNCHECKED, before synthesis; per slice, x16 per die).**
- Held list: 128 x 10 = 1,280 FF.
- Export state: about 60 FF.
- Two 128:1 x 10-b list read muxes: about 2.6k mux2.
- Two 10-b land read-index muxes.
- The 513-b pv_od third source: about 0.5k cells.
- PK2 decode plus the 10-b / 144-b mux on the existing write port: about 0.4k cells.
- DP: 3 FF.
- Total: about 1.3k FF + 3.5k comb cells per slice, roughly 2-3k um2 / slice in ASAP7. That is under 1% of a svc_rs slice
  (the svc_tile alone is 353k um2).
- No macro change. No new die wire.

**Partition / plan touched.** Only the dsdv_svc_rs core content: all 16 hardened slices (both port variants) change
RTL when ROWX = 1. That means re-synthesis and re-sign-off of the svc_rs types. There is no die-plan wire delta, no
change to pin faces, landings or lanes, and no new straps. The CFG DP field replaces the missing die-position strap.

## Results

- 2026-10-26 17:28 PDT Claude S81-ROWX: RTL + bench + LEC script PUSHED claude/s81-rowx-1026@ee24aba28. Verdicts PENDING.
  - RTL: dsdv_svc_att.sv gets parameter ROWX (default 0) with the held list, the ROWX type-11 export, PK2 ingress, CFG DP and faults 24-29, per the spec above.
    Lint is clean on Verilator 5.050 (a single share lints at 26.5 GB / 5 min for orig, ROWX 0 and ROWX 1 alike, so ROWX adds no build cost. CHECKED, from /usr/bin/time).
  - Bench gate: rtl/dsrom_sys/s81_dv/svc_rs/test/run_svc_rowx.sh, variants base / miter / mut6 / mut7. It is split into one svc_att module per build because four shares in one build OOM'd at 96 GB.
    - Running now via ot-run: epyc1:/srv/opentallas-scratch2/claude/s81-rowx-1026/bench3/gate_{base,miter,mut6,mut7}.log, with ROWX_TIMING in run_base_s*.log.
    - The fleet is memory-queued (load 177), and the -O0 C++ build alone takes over 30 min.
    - Not yet PASS. Treat it as untested until those logs say SVCROWX_GATE PASS.
  - LEC: Yosys RTL-vs-RTL (results/rtl/s81_rowx_1026/lec.sh, engine blackboxed, ROWX=0 vs main) is NOT CLOSED.
    - equiv_simple -seq 2 ran over 3 h on land[] bits and I killed it.
    - With equiv_simple only plus equiv_induct, it timed out at 45 min with 239,283 unproven $equiv cells (land 640x256 as flops).
    - The ROWX=0 regression evidence is therefore the lockstep MITER build (pending) plus the code structure: every new term is ANDed with the constant RX.
    - A real ROWX=0 LEC needs a commercial-style memory-aware LEC, or a blackboxed land array. That is open.
  - Cycle receipt for the TOK-DS ledger: per die, per half, UNCHECKED arithmetic.
    - Export: 8 tiles x NXW 40 words = 320 entry cycles, before GO.
    - Ingress PK2 at static B=40: 2,401 q cycles per half, both halves in parallel, vs 3,809 measured.
    - Data-exact: 1,905. The measured export cycle (ROWX hdr + gd + XO + pvs + 1) comes from ROWX_TIMING once base passes.
  - No new die wires and no plan delta. The core content of all 16 svc_rs slices changes only when ROWX=1.
- Next / ASKs:
  - (1) S81 plan owner: rebuild svc_rs with ROWX=1, plus the CFG DP field (a pre-existing bug: DIE_ID is never set on the die, so every die fetches die 0's rows).
  - (2) OWNER: static per-owner budget B (40 or 80 rows, or 2 passes). It overflows (fault 26) when one (die, stack) holds more than B.
  - (3) TOK-DS: per-half ROWS filtering, PK2 re-pairing in the xr transport, and the export words per half must be a multiple of 160 (the pvrd nw strap).
- 2026-10-26 17:38 PDT Claude ROWX-BUDGET (analysis only): claude/rowx-budget-1026@9f97c5c993 results/rowx_budget_1026/README.md.
  - NO real-prompt indexer selections exist in the repo/fixtures. The only top-512 sets are the 1M golden reference token (released weights, SYNTHETIC i.i.d. KV / index keys, 1 token). Real evidence needs a GPU forward of the V4.1-Flash checkpoint over real >=32K-128K prompts dumping index_select of L2/8/14/20/24/28/32/36 (~3e4 tokens for p<1e-4/token).
  - Fixture token per-(die,stack) max: 43/42/41/43/46/49/43/47 (L2..L36). All 8/8 layers > 40, none > 80. CHECKED (recomputed; L14 d0s0 36 matches).
  - Uniform i.i.d. REFERENCE ONLY: layer max p50 42, p99.9 55, p99.99 58. B=40 overflows 71 % of layers / 99.996 % of tokens. B=80: ~3e-12 per token. >128: ~1e-40.
  - Price (TOK-DS-6b composition, baseline 1259.6/3655.3 reproduced, CHECKED tool output): B=40 2401 -> MTP 3704.9 (+49.6) but NOT schedulable. B=80 1-pass 4801 -> MTP 3621.1 (-34.2), AR 1249.2 (-10.4), ledger ~17.97 % (+0.93 pp, UNCHECKED sum). 2x B=40 = 4802 is the same cost, no benefit. Data-exact 1905 -> 3722.7.
  - RECOMMEND B=80 single pass (NXW=40).
  - OWNER ASKs: accept B=80 without real traces? What happens at run time on fault 26/24? Optional rank-ordered export slots (~2049, no budget; RTL change, UNCHECKED).
- 2026-10-26 19:00 PDT Claude S81-ROWX: SVCROWX_GATE PASS. Branch claude/s81-rowx-1026@489441e63; receipts in results/rtl/s81_rowx_1026/bench/.
  - CHECKED (read from the run logs):
    - base P1 PASS on seeds 1-3, err 0. Export words match the independent golden. rx landed every row ex holds plus its own fetched rows, and no decoy row. The fault-29 and fault-25 negatives fire.
    - miter (ROWX 1 vs 0, legacy traffic, all outputs every cycle) PASS on 3 seeds: 3,219 cycles, 0 mismatches, 16 score beats, 40 P.V words.
    - mut6 is caught (err 86-92), and so is mut7 (err 41, plus neg29 missing).
  - Measured export timing (CHECKED, ROWX_TIMING): first word 98 cycles after the ROWX header, which is gd 16 + XO 8 + pvs 70 + 4 cycles of q/pv pipeline. Then 40 consecutive words per slice.
    - Per half: 8 slices x 40 = 320 entry cycles, as designed.
    - Held rows in the bench: ex 40, rx 29-40. ex was 40 on all three seeds; I did not look into why.
  - Ingress cycle count is still the UNCHECKED arithmetic: 2,401 per half at B=40, or 1,905 data-exact, vs 3,809 measured. The bench proves PK2 landing correct, not this count.
  - LEC for ROWX=0 is still not closed in Yosys (239k unproven). The regression evidence is the miter above.
