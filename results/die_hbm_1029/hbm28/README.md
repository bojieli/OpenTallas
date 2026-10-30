# DIE-HBM-28 (HBM die owner, 2026-10-29 20:42- PDT): HBM-004 plan event V-R1 + L202m on d26a

Run dirs: `intel1:/srv/opentallas-scratch2/claude/die-hbm-28` (plan/d28c = candidate, plan/d28a = same before re-pin,
b28a/b28c = strict all-gap binds), sub-lane K: `intel1:/srv/opentallas-scratch2/claude/die-hbm-28k`.
Tools = main ac0b29e7fa5 (`tools/die_plan`), die-local scripts here (no shared tool changed).

## Plan event (COORD 20:4x approved (A))
Base d26a (die_plan 77fb5f395968 + HBM-053 core_macros) ->
1. `lane_presplit.py d28p/die_plan.json L6 3`: L6/L6m hub->b100 2,484 b split into 3 x 828 b lanes (L6, L6b, L6c; +m),
   latency group `L6_word`/`L6m_word` (one as-built bus, one cycle).  Needed because after V-R1 the 734-um hub|b100
   face cannot carry L6 + L7 (2 x 414 um) + the small lanes.
2. `replan_event11.py` (fork of hbm23 replan_event10: street reuse accepts a one-sided slot declaration, e.g. b101
   slots without windows) with `VR1.json` = V-R1 S-row order `[su30][su31][b110][b100][b101]` (NE mirror) and
   phase-2 rows limited to the 6 approved pairs (`rows_vr1.json`: su30<->su31, b100->b101 per half).
3. hbm23 post-fixes (`order_fix.py`, `post_fix_h28.py` = post_fix with "failed run later rebuilt != failed lane",
   `post_fix2.py`, `post_fix3.py`), `add_l202m.py` (NE mirror of L202 root->NE_hub->NE_b000 180 b, 25 cyc),
   `gen.py latency --inplace` -> **d28a 4723a1f69ae7**.  (`build_event.sh d28a "L6 3"` reproduces it.)
4. `tools/die_plan/core_face_repin.py d28a ... --types q_hub_nw,q_hub_ne --suffix fr28`: 1 table
   (ot_hbm_idx_query_static 170.64x164.16, 4 instances u_hb_idx__q_Q__q1) ports ql_codes/ql_head/ql_sc/ql_v/ql_w W->N
   (b100 moved 2.2 mm E) -> **d28c 57e3ad3cb729** (pins only; re-kit of that core owed).

| check | result (CHECKED) |
|---|---|
| G0 d28a / d28c | PASS 0 errors |
| G0C d28a | 12 = d26a 8 + 4 new core_faces (hub idx_query ports face W, partners S/E) |
| G0C d28c | 8 = exactly the d26a set (diff empty), 0 new |
| strict all-gap bind d28a, d28c (g4 manifest, 3:15 min, 7.2 GB) | 85 UNPLANNED / 65,930 b (from 92 / 82,285), 0 EMIT, tied/undriven/multi 0/0/0; gone: su30<->su31 x2 halves (4,755 b/half), b100->b101 x2 (3,333/3,332), root->NE_b000 180; 0 new pairs, 0 changed |
| clock taps moved (die frame) | NW/NE b100 2,246 um, b110 1,097 um, su31 1,149 um (`d28a_tap_moves.json`); clock sidecars (clock_taps_die/htree/entries) NOT updated by the event -> ot_clk on GRT0 owed after bind 0 |
| render S row (d28c vs d26a) | VIEWED: order su30 su31 b110 b100 b101 |

Lane cycle changes (d26a -> d28c, per half, CHECKED from the latency table): DOWN L5 14->9, L34/L35 10->8, L203 12->4,
L70/L100 8->7; UP **L6 word 7->8 (+1, hub->scorer row-0 b100)**, **L181 su31->hub 1,108 b 2->5 (+3)** (hub|su31 face now
also carries L5 2,725 b); new L400/L401/L402 (+m) adjacent 2 cyc; L202m 25.  Tok/s of the two UPs: UNCHECKED
(IDX +1 ~0.008 %; L181 is SU3->hub, needs the token model if it is on the SU path).  Tried d28b (L6 1322/1162 + L5
2269/456 splits): worse (L23 2->6, L6b 10) -> discarded.

## (B) pgp command broadcast (RTL/bind fact, CHECKED from die-hbm-26/p_all bind_sinks + map)
su00/su01 (su20/su21) are the two halves of ONE SU instance su_NW0 (su_NW2); every pgp bit has one driver
pgp_NW.command[i] (u_pgp_Q__q1 in hub); su00 consumes 1,904 bits, su01 1,402 (all shared, su01-only 0); all 32 lanes
load the command in lockstep (ot_hbm_su_static_pgslice_s.sv:132-137).  Relay = plan/bind change only (no SU RTL):
carry all 1,904 b on L0 (2,999 planned, 1,402 used) / L2 (2,999 / 1,386) and branch su01->su00 / su21->su20 next to
L162; removes 1,904 b per SU from the hub face (WIDEN hub->su00/su20 2,846 -> 942 each); su01|su00 face 0.72, su21|su20
0.86 (UNCHECKED); lockstep -> equal latency on both halves: +2 cyc (pad su01 copy) or L0 re-station to stay at 14.
Note su21 already gets the family at two latencies (L2 6 cyc, L112 2 cyc) - unresolved.

## (C) token run (CHECKED, claude/die-hbm-28c-1029@5f2ba79b41a, results/die_hbm_1029/hbm28c)
Scorer row-1 feed hop chain +30 IDX cycles -> 1808.1 tok/s (-0.237 % vs 1812.4); +32 (with row-1 result return)
1807.9; linear 0.008 %/cycle.  Not an OWNER item (<5 %), but ~4 tok/s below the accepted 1812-1830 band low end.

## COORD 21:0x items (sub-lane K, `k/`; NOT applied to d28c)
- opstore_a: 32 x ot_sram_1r1w_256x256_m2_r2c2 (CHECKED, yosys flatten of the K24 kit RTL; other 2 recipe masters
  not instantiated) = 227,099 um2 of macros > outline 388.8x345.6 (134,369) and > die_plan hard core 390.528x436.32
  (stale mismatch in q_b113/q_b113__physical_v1).  Proposed 760.32x483.84 (4x8 grid like opstore_b): kit_contract
  macro_channels / clock_entry_clear / macro_pin_grid PASS on a staged copy, but **no free 760x484 slot in q_b113**
  -> needs a q_b113 repack (or sizing ruling) before it can enter a plan event.
- xq_pegress: 6,033 um2 cells; current die_plan outline 362.88x276.48 -> fill 0.060 (core_macros 369.36^2 stale).
  5,184 pins (N 2048, S 752, W 1298, E 1081).  One pin layer per face: best fill 0.111-0.125 (< 0.15/0.20) - cannot
  pass.  Option B 190.08x146.88 (fill 0.216) needs 2 pin layers per face (M5+M7 / M4+M6), i.e. pins above M5 on a
  hard core and >6 pins/um per face -> ruling; fallback = fold xq_pegress into the hub as soft logic.

## Remaining (bind 85 / 65,930 b)
HBM-055 scorer contents (b101/b102/b103 hard-core + glue moves; -2,047 +~73 b/half) not built: needs a die-local
hard-core move between types (hard_cores, internal_stations, clock taps, core_conns) + compose-manifest glue map
for tail0/score reg - next event.  Scorer row-1 feed b100->b102 2,777 b (token price above), SFU b110-b113, NEW 16k,
WIDEN su00/su20 (pgp relay above), NW_hub->root 2,065 etc.
