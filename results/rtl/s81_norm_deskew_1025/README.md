# S81 NORM-DESKEW (TOK-DS, 2026-10-25)

COORD ruling 01:34 (lanes/TOK-DS.md, gap NORM-ISSUE): the xrt partial collector of the slice control plane
(`ot_s81sl_xrt`, u_sl.u_xr) faulted on every 16-slice norm.  Its fault term `(|pv) && pv != 5'b11111` needs all 5 leaf
norm partials on ONE edge, but one CTL beat per edge carries the 5 per-leaf NORMRs (leaf k needs its own a1), so the
partials arrive one edge apart.  Fix: static per-leaf deskew registers in front of the collector.

## RTL

`rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv`:
- core parameter `PDSK [14:0]`: 3-bit depth per leaf.  Leaf k's `p_v` / `p_d` pass through `PDSK[3k +: 3]` registers
  (valid flops reset by a local `ot_rst_relay`, data flops without reset).  Depth 0 is a plain wire.
- wrappers `ot_s81sl_xrt1` / `ot_s81sl_xrt3` pass `` `OT_S81SL_XRT_PDSK_DEF `` = `15'o01234` (leaf 0..4 depth 4, 3, 2, 1,
  0): the plan's fixed offsets (NORMR k issued k edges after NORMR 0) line up on leaf 4's arrival edge.
  `+define+OT_S81SL_XRT_NO_DSK` gives `PDSK = 0`, the pre-deskew module exactly.
- negative control `+define+OT_S81SL_XRT_MUT_DSK`: leaf 2 is one edge too deep, so the set splits and must raise the
  fault.
- Landed slices instantiate `ot_s81sl_xrt1 u_xr` without parameters, so they pick up the default.

## Contract for the compiler

A slice's 5 NORMRs reach it on 5 CONSECUTIVE edges in leaf order (k at base + k).  Any other spacing is a sticky
collector fault.
- `dv_layer_compile.lower_norm_smoke` and `layer_prog/lower_head.py` already issue k on t + k: no change.
- `layer_prog/entry_norm.py` used `first_issue + 8*leaf + col`.  It is changed to `first_issue + 5*col + leaf`
  (checked on a 16-slice die: offsets 0..4 per slice, XFIN_GO after the last NORMR, 96 rows, no duplicate engine edge).
  Existing entry programmes and the fc30 / fc31 entry replays must be recompiled.
- `xr_timing.XRT_MODEL`: new entries for the deskewed main xrt (18850f53) and the deskewed fc31 xrt (ec43bbd4), both
  with V-CTL inject 7 (the change touches only the leaf-partial path).

## Price

- Cycles: +4 edges per norm step (the partial set leaves the collector on leaf 4's edge, 4 edges after leaf 0's).  The
  NX flit leaves 142 edges after the last NORMR instead of 138 (`norm_nx.NX_AFTER_LAST_NORMR`), so rstd and everything
  after it are 4 edges later.
- Area (ORFS synth, canonical ELEM-S81 kit config): xrt1 20,659 flops / 9,938.2 um^2 vs 20,328 / 9,822.1 NO_DSK
  (+331 flops, +1.18 %); xrt3 24,017 / 11,510.8 vs 23,686 / 11,398.4 (+331, +0.99 %).  331 = 10 stages x 33 b + the
  relay.

## Evidence (epyc3 `/srv/opentallas-scratch2/claude/tok-ds/dsk/`, Verilator 5.050)

`tools/s81_slice/xrt_bench.sh` with `XR_DSK=1` (default) runs the tb in DSK mode (`OT_XR_DSK_TB`: staggered partial
sets, partial j at xfin on n + 6 + j, i.e. 4 edges later; illegal cases 5 / 6 restaged as two overlapping staggered
sets / leaves 0..2 only, and 3 new ones that must fault: 15 an old-style aligned 5'b11111 set, 16 a staggered set
without leaf 3, 17 a staggered set with leaves 0 and 1 swapped).

| run | result |
|---|---|
| base hb0 / hb1 x seeds 1..3 x XR_LAND 0 / 1 (12 runs) | PASS, err=0, XRILL missed 0 of 16 (hb0) / 17 (hb1) |
| FOREG, PDC, FOREG+PDC+LAND, hb0 / hb1 | PASS err=0 |
| legacy `XR_DSK=0` (NO_DSK + aligned-set tb), with and without LAND | PASS err=0, XRILL 0 of 13 / 14 |
| `XR_DSK=2` (old aligned-set tb on the deskew masters) | FAIL as expected, err=8191 / 8469 (the old schedule now faults) |
| mutant dsk (hb0 / hb1, and with LAND) | FAILED AS EXPECTED, err 7254 / 7425 / 7285 / 7379 |
| mutants hops, row, porder, nocol, xhold, landpv | FAILED AS EXPECTED (hb0 and hb1) |
| mutant bwide | hb1 FAILED AS EXPECTED; hb0 passes (bench blind: the hb0 seed has bsends=0) |
| `xrt_land_eq.sh` REF=WT, hb0 / hb1 x LAND 0 / 1, and SPARSE | PASS, err=0 over 20,000 cycles |
| `xrt_land_eq.sh` NO_DSK vs gh/main (pre-deskew) | PASS, err=0: PDSK = 0 is the old module bit for bit |
| `xrt_land_eq.sh` mutant land_pv | FAILED AS EXPECTED |

Gates (kits/ot_s81sl_xrt1, xrt3):
- LEC: EQUIVALENT.  xrt1 28,507 / 28,507 compare points proved (25,054 by name, 2,554 register pairs / merges and 48
  constant registers proved inductively, 0 unmatched); xrt3 32,651 / 32,651 (28,974 by name, 3,242 pairs, 29 constant).
  Run with the LEC lane's current `lec.py` (rtx-pro ~/wt/lec-1024r working copy).  The committed
  claude/lec-gate-1024 `lec.py` stopped in `gold.ys` on this 4.6M-anyseq design.
- SELRANGE: FAIL, 4 unwaived hits at xrt.sv:434 (`vb2[16 + k]`, `rsv_c[k / 8]`) and :583 (`pair_word[i + 1]`,
  `pvs_c[i / 16]`).  PRE-EXISTING: the NO_DSK kits give the same 4 hits on the same lines.  They are guarded selects
  (`k < 256 && ...`, `i < V - 1 && ...`); the deskew adds none.  They need a waiver or a rewrite by the xrt owner.

## Other benches

- `results/rtl/s81_rtlgap_ffn_1021/scripts/ub_xr.sh` (archived RG-FFN evidence) drives aligned 5'b11111 partials, so it
  FAILS on the deskew masters (err 8191 / 8469) and passes with `+define+OT_XR_DSK_TB` (0 of 16 / 17 missed) or on
  NO_DSK.  Not edited (archived).
- Benches that tie `p_v` to 0 or use the legacy xr1 / xr3 masters are unaffected.
- `landed/c3x/ot_s81sl_slice_c3x_lp_bench.sh` was already broken (SRCS list predates the xrt binding) and is not a
  deskew issue.
