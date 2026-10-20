# qfd_coll_split_q5 -- Qwen collective split Q leaf successor (QW-ORPHANS 10-20) -- gates q5/q5w --cts

Source: branch claude/qw-orphans-coll-1020 (from Codex codex/qw-coll-native32-main-1020 a769f0544 + LAT7 wrapper 383f29dea),
top ot_coll_split_q_native32 LU66 LS391 FAN32=1 ADD_FAN32=1. Released MAIN fold/bench untouched (namespaced copies).

## Pre-gate native census (tools/ref_tile/native_census.py, actual ASAP7 RVT TT Liberty roles, ORFS synth-only)
- r1 (509d6e044, q4w synth template): FAIL roots 77243, max 35, 4 violations, all sequential = reset leaves
  u_pf/u_xf g_rsg[2|3].g_l.u_rs (edl 7 + 4 native adders x 7 RESETN). No functional/input/comb violation
  (was 262 non-tie >32, max 165 on the legacy adder). Synth area 24149.3 um2 = 13159.4 macros + ~10990 std; 18347 DFFHQN + 383 ASR.
- r2 (6aed70dd7): second identical two-flop leaf per stage for lanes 2..3 (same rst_n, same release edge). Census r2 LIVE (pending_results).

## Census r2/r3
- r2 (6aed70dd7): FAIL max 34, 1 violation: Q face leaf u_rs drives 34 leaf RESETN (17 leaves x 2 flops).
- r3 (4499163b3): second identical face leaf u_rs2 for the FAN32 fold slices -> PASS 77257 roots, max 32, 0 violations,
  0 role errors (results/rtl/coll_native32_1020/census_r3/). Synth area 24155.9 um2 (macros 13159.4 + std ~10997).

## SAFE-DESIGN checklist (q5 = q4 geometry 220.32x259.2, q5w = q4w 233.28x259.2; both balanced spine)
1 Pins: RTL registers every pin at the face (q4 lineage), rst_n -> 2-flop face leaves u_rs/u_rs2 -- PASS
2 Reach: tile <= 260 um per side, no single-cycle net > 405 um by construction; gate textbook >500um check -- PASS(geom), gate audit
3 Fanout: census r3 max 32 incl reset, 0 violations -- PASS
4 Depth: native LAT7 adder 288.4 ps / 9 levels (Codex 89d0bac6a); gate path classes -- PASS(model)
5 Storage: 12 SRAMs hold all rings/skew lines; token rings < 2 kb each -- PASS
6 Floorplan: 12 natives in two abutted N-S stacks (origins on the 43.2 lattice; ref_tile abutted_stack rule; a
  per-macro literal 43.2 grid with >=20 um channels needs >= 345x259 = ~25% fill and fails the channel rule when
  abutted E-W, tried in the first q5 draft: REF_TILE channel FAIL 9.5/15.6 um), centre std channel, >= 20 um from pin faces;
  fill 42% / 40% (WARN, synth std 10989); pins N261/W512/E512/S~300 <= 2.4/um -- PASS/WARN fill
7 Clock: q4/q4w single TritonCTS tree FAIL pin-flop spread 100.6/96.7 & 86.9/83.7; q5/q5w use the balanced symmetric
  spine (OT_SPINE_SYM/SAFE_BALANCE/MACRO_LEAF/TREE_PAD; same mechanism gave sysface bc3 48.3/44.5 ps). io_hold_margin 0.03.
  Gate verdict on TT/FF pin-flop spread <= 80 decides; if both fail -> regional face roots (multiple_cts_roots) + landing.
8 Schedule: zero added edges (EX2 LU66/LS391/SL23 unchanged); reset leaves release on the same edge -- PASS
Benches: full 8-die gold (unit+production) + 6 mutants on V5.050 LIVE (pending_results) -- needed before submit.

## Q.SAFE.COLL.1 parent bind plan (landed 2x2 + C)
- tools/landed_parent/lp.py landed cluster, multiple_cts_roots/entries: clk = C (qfd_coll_split_c2, 103.68x181.44,
  tokens on its S face), clk_q0..3 = Q leaves; no glue logic in the parent.
- Placement: 2x2 Q (right column MY so SerDes W faces stay outward) with C in the centre; each C<->Qi token leg
  <= 405 um else one relay row (C taps its token rings one edge early: 0 data edges, static schedule unchanged).
- Clock: judge each C<->Qi pair at child flops, TT and FF spread <= 80 (parent entry compensation: C c2 insertion vs Q ~400 ps).
- Q data pins pass straight to parent faces (SerDes outward, UCIe inward/E).
- Pre-requisite: one Q leaf CLOSED (q5) and C c2 view current; then GEN/bind + parent native census + GRT/STA.
