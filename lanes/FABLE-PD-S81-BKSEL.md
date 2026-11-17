# FABLE-PD-S81-BKSEL — review of dsdv_bksel_q fx6 (2026-11-16 17:50 PST)

Read-only review. Nothing launched, stopped or edited. Sources: epyc2
`/srv/opentallas-scratch2/claude/fable-fix-bksel/fx6/bksel_vC9fx6` (`run_finish.log`, `fx_repair.tcl`, `etm_land.tcl`,
`setRC_rcx.tcl`, `orfs_hold_mm.tcl`, `config.mk`), `lanes/handoff/S81-BKSEL-O.md`, `S81-CORES-1115.md`, `CODEX-LOG.md`,
lane posts. I ran no STA of my own: the current netlist exists only inside the live OpenROAD process (PID 2831006);
`fx_pre_repair.odb` is the state before repair.

## State at 17:46 PST
- GRT overflow 0. Post-GRT `repair_design`: 1840 slew / 5 cap violations, 1997 buffers.
- Pass 1 (setup margin 30): TT setup -16.78 -> 0.00 (29 endpoints, 59 resized, 2 buffers). FF hold -39.36 -> +10.236
  with 2084 HB4 buffers, then stopped by the 1.6 % buffer cap (RSZ-0060). The last ~90 buffers of the pass gained
  nothing (flat at +10.236 on `ot_fcap_00010_ff/D`).
- Pass 2 (setup margin 10): 8 setup endpoints left inside the margin, WNS 0.00. Hold started at +6.92 with 2820
  endpoints under the 20 ps margin; now iteration 1610, 1576 buffers, +14.70, TNS 0.
- Projection: the cap (about 2084 buffers) ends pass 2 near 18:45 PST at about +15.5 to +16; then legalize, incremental
  GRT, detailed route, sign-off. No routed number exists yet.
- LEC: standalone container still in cone jobs; `lec/hyp0_failed.txt` holds alias candidates (b_idx, c1_eq), no verdict.

## 1. Will fx6 close the four gates?

| Gate | Call | Numbers |
|---|---|---|
| DRC 0 | likely | GRT overflow 0, utilization 43.4 %; every earlier routed form of this core was DRC 0 / antenna 0 |
| TT >= -42 | probable, not certain | 0.00 at GRT on the C x1.40 table. That table is the b1p routed fit (x1.3 -112.7, x1.5 -216.1, routed -157.6, about 5 ps per 0.01 of scale), so the 42 ps allowance covers a scale error of about 0.08. Pass 2 adds about 2084 hold buffers after the last setup repair; pass 1 did the same and setup stayed 0.00 |
| Internal FF hold >= 0 | NOT assured, below even odds | see below |
| LEC (advisory) | open | no verdict; does not block the physical sign-off |

Hold in detail:
- The same netlist reads FF hold **-28.38** on the kit table (`setRC_rcx.tcl`, C x1.40 on M2-M7) and **+6.92** on the
  hold-repair table (`OT_RC_CAL hold`). The two tables differ only in M6/M7 C (0.183 / 0.130 against 0.105 / 0.105
  fF/um). Pass 1 shows the same gap (-73.13 against -39.36). So the hold result moves **about 35 ps** with the M6/M7
  capacitance alone, and the repair will end with about 16 ps of margin on the optimistic table.
- The measured routed clock-net C (header of `setRC_rcx.tcl`: M6 0.132, M7 0.087) lies between the two tables. The
  routed result therefore lies between about -20 and +15, depending on how the 17 landing feeders split between
  M6 and M7. That is an estimate, not a measurement.
- History on this core: forms that left GRT hold repair came out negative at routed (vF -47.35, vI -27.96 / 332
  endpoints, H -39.30 / 217, b1p -67.78). Those carried the late pk2 landing, which fx6 fixes, so they are an upper
  bound on the loss, not a forecast.
- The 12 paths into pk2 (b1p routed -22): this family is no longer the limit. pk2 pin minus registers is -156.9 ps at
  CTS (fx1: +27), and no pk2 input appears among the 439 logged worst-endpoint rows of the two hold passes (pass 1:
  bank 44, latch 45, other 127; pass 2: bank 12, latch 137, other 13). They hold at least +14.7 on the hold table. The
  exposed families are the hist-bank inputs (`i_dg`, `i_en`) and the `$_DLATCH_N_` stages.

## 2. Root cause and ranked fix

Mechanism: the 17 ETM macros (16 hist banks + pk2) have 112-192 ps FF of internal clock latency and pin hold up to
138 ps, so each needs its clock 150-200 ps before its interface registers. fx6 builds that offset from **unbalanced
wire**: one BUFx24 per pin, fed over 28-210 um from whichever tree node happens to have the right arrival. Two
consequences:
1. The offset depends on the wire model (35 ps for M6/M7 C alone), and hold repair and setup repair run on different
   tables, so "+16" is not a routed margin.
2. The landing is uneven: 16 macros sit at -149 to -202 against the -180 target, but `u_hc.g_bank[0]` reached only
   -78.9 (no tap within 220 um was early enough), so its inputs need about 100 ps of padding each. 4985 endpoints were
   under the margin in pass 1 and about 4170 HB4 buffers go in overall.

Ranked fix:
1. **Flow, now: let fx6 finish untouched and read the routed sign-off.** If TT >= -42 holds and the FF residue is
   small (roughly <= 30 ps, a few hundred endpoints), run ONE hold-only ECO: HB4 pads at the failing endpoint pins,
   no `repair_design`, no allow-setup, setup margin kept. This is not the b1o/b1g/b1p ECO, which ran `repair_design`
   with allow-setup and ripped 5,000-7,000 nets.
2. **Flow, fx7 kit prepared in parallel, launched only on a larger miss:** (a) final hold pass with `OT_RC_CAL=0`, so
   hold is repaired on the same C x1.40 table that reproduces routed (the pessimistic side of the 35 ps gap);
   (b) hold margin 10, not 20, with the buffer cap raised to about 4 %, since the 20 ps sweep is where the passes
   stall; (c) land `g_bank[0]` properly (wider tap radius or a two-buffer feeder) so all 17 sit at -150 to -200.
   Start from the fx6 `4_cts.odb`; no new placement.
3. **Structural, if fx7 also misses:** stop making the offset from wire. Either let CTS balance the macros natively
   (both ETM libs already carry `clock_tree_path` attributes, 2 lines each, which the post-CTS re-hook bypasses), or
   put the existing low-phase latch stage (`g_lat`) on every ETM input bus, which makes input hold independent of
   landing skew at a half-cycle setup cost on those buses.

## 3. What the lane should stop doing
- Stopping or patching the live job to change settings. The 13:26 relaunch from GRT cost about 4 h.
- Sweeping to the 20 ps hold margin until a cap: run 1 spent about 3,900 iterations flat at +10.236.
- Reading "FF hold +x" from the hold table as progress toward sign-off; quote both tables.
- Placement-reweight forms (fx5: -186 against fx1 -150 after slew repair, same stall).
- Route-keep ECOs with `repair_design` or allow-setup (three lost 160-450 ps of setup).
- Waiting on LEC before the physical sign-off and export.
