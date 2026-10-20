# qfd_coll_split_q5 -- Qwen collective split Q leaf successor (QW-ORPHANS 10-20) -- DRAFT, NOT GATED

Source: branch claude/qw-orphans-coll-1020 (from Codex codex/qw-coll-native32-main-1020 a769f0544 + LAT7 wrapper 383f29dea),
top ot_coll_split_q_native32 LU66 LS391 FAN32=1 ADD_FAN32=1. Released MAIN fold/bench untouched (namespaced copies).

## Pre-gate native census (tools/ref_tile/native_census.py, actual ASAP7 RVT TT Liberty roles, ORFS synth-only)
- r1 (509d6e044, q4w synth template): FAIL roots 77243, max 35, 4 violations, all sequential = reset leaves
  u_pf/u_xf g_rsg[2|3].g_l.u_rs (edl 7 + 4 native adders x 7 RESETN). No functional/input/comb violation
  (was 262 non-tie >32, max 165 on the legacy adder). Synth area 24149.3 um2 = 13159.4 macros + ~10990 std; 18347 DFFHQN + 383 ASR.
- r2 (6aed70dd7): second identical two-flop leaf per stage for lanes 2..3 (same rst_n, same release edge). Census r2 LIVE (pending_results).

## SAFE-DESIGN checklist (draft; final numbers from r2 census + gate)
1 Pins: pin regs ON (OT_KEEP_PIN_REGS=1), rst_n lands in 2-stage ot_coll_rst_leaf leaves -- PASS (source)
2 Reach: outline 259.2x216, all single-cycle nets <= ~240 um by geometry; SerDes/UCIe face data registered at faces -- PASS by construction, gate audit owed
3 Fanout: r1 max 35 (4 reset leaves) -> fixed r2; r2 census must show 0 >32 incl reset -- PENDING r2
4 Depth: native LAT7 adder 288.4 ps / 9 levels per stage (Codex 89d0bac6a) -- PASS
5 Storage: 12 SRAMs (4x256x64, 8x128x64) hold rings; remaining token rings < 2 kb each -- PASS (Codex MODEL.md)
6 Floorplan: macros on the LITERAL 43.2 lattice (q4w y=84.576/125.952... was non-literal): 4x3 abutted block,
  x {43.2,86.4,129.6,172.8}, y {43.2,86.4,129.6}; no macro at a pin face (>= 43.2 um from every face);
  std cells in a closed ring band (S/N 43 um full width, W 43 um, E 43-52 um) = one connected std region, no island.
  Fill ~29% (10990 / ~38k free) is macro-lattice bound (12 macros need the 4x3 block + 43.2 face margins);
  recorded as fill_reason, ROOT to accept or pick the 345.6x172.8 2x6 alternative (aspect 2.0, worse).
  Pins: N in/out/straps 261, W SerDes1/2 512 (1.9/um), E UCIe 512 (2.4/um), S SerDes0+tokens ~300 -- all <= 6/um.
7 Clock: q4/q4w failed pin-flop spread 100.6/96.7 & 86.9/83.7 ps with one tree over 220-233 x 259 and pin flops at all
  4 faces. q5: centre-fed root at the block's N edge centre (129.6, 172.8) + 4 regional face leaves (N/S/E/W pin-flop
  bands) built as balanced H-branches of equal length (OT_SPINE regional entries), macros clocked from the block
  spine; target TT/FF pin-flop spread <= 80 judged per face vs the face neighbour (C c2 / die link) reference.
  io_hold_margin 0.03 -- clock model (insertion per face) must be run before the gate.
8 Schedule: zero added edges (Codex model; EX2 schedule LU66/LS391/SL23 unchanged) -- PASS

Gate ONLY after r2 census PASS + gold/mutant benches PASS (V5.050) + clock model. Not a critical prefix? check critical_tiles.txt.

## Q.SAFE.COLL.1 parent bind plan (landed 2x2 + C)
- tools/landed_parent/lp.py landed cluster, multiple_cts_roots/entries: clk = C (qfd_coll_split_c2, 103.68x181.44,
  tokens on its S face), clk_q0..3 = Q leaves; no glue logic in the parent.
- Placement: 2x2 Q (right column MY so SerDes W faces stay outward) with C in the centre; each C<->Qi token leg
  <= 405 um else one relay row (C taps its token rings one edge early: 0 data edges, static schedule unchanged).
- Clock: judge each C<->Qi pair at child flops, TT and FF spread <= 80 (parent entry compensation: C c2 insertion vs Q ~400 ps).
- Q data pins pass straight to parent faces (SerDes outward, UCIe inward/E).
- Pre-requisite: one Q leaf CLOSED (q5) and C c2 view current; then GEN/bind + parent native census + GRT/STA.
