# B2r2 die top, early full-chip prototype (TRIAL-HBM step 1), 2026-10-24

Plan: `physical/die_plan/hbm_arch/B2r2/die_plan.json` (not edited). The die is 25194.24 x 18316.8 um = 461.48 mm2,
with 88 partitions of 49 types. Every partition view is a **mock plan abstract** (`gen.py mockview`: exact plan pins,
clock/reset tap pins on M7, M5/M6/M7 VDD/VSS stripes, full OBS on M1-M7). No B2r2 partition type is closed, so the
repo has no LEF for any of the 49 `hbm_arch_*` modules (see `real_views.json`).

## Verdicts

| Check | Result |
|---|---|
| Placement: 88 macros at their exact plan origin / orient | **PASS** (odb placement): 88 placed, 0 overlaps, 0 outside the die, 0 origin mismatches. Macro area 461,477,855.2 um2 = die area, so the partitions tile the die with no gap. |
| Placement through the kit's own `die_flow.tcl` (`place_macro` with `%g` origins) | **FAIL**: 23 of 88 refused (MPL-0041 overlap, MPL-0034 outside core). See finding F1. |
| `place_macro` with `%.4f` origins | **FAIL**: 3 of 88 refused (NE_mca, NE_su00, NE_su20). See finding F2. |
| Die PDN (pdngen M8/M9 + macro grid M7-M8) | **PASS**: 0 failed vias. VDD has M8 2119 / M9 2915 stripes, VSS has M8 2120 / M9 2916. |
| `check_power_grid` VDD / VSS | **PASS / PASS**. All 88 macros sit on both nets. |
| Macro PG connections (M7-M8 vias, partition M7 stripes to die M8) | VDD 6,197,000; VSS 6,181,920 |
| M8-M9 vias | VDD 6,176,885; VSS 6,181,920 |
| Keep-outs (M1-M9 obstructions, created after pdngen) | 7 rects: 5 SerDes, 1 host UCIe, 1 HBM PHY (= the whole PHY_N outline). |
| Partition pins inside keep-outs | **18,741** total: PHY_N 18,734 (incl. 2 tap pins); NW_io UCIe 7 (all 7 are clock/reset taps); the 5 SerDes 0. See F3. |
| Die GRT (die nets = clk, rst_n; abutted seams are pin-to-pin, so GRT skips them) | **FAIL**: 2 nets routed, 788,956 um wire, 9.6 um gcells (2624 x 1908). Total overflow **394** (M7 62, M8 142, M9 190). 289 of it is inside the PHY_N keep-out, 102 inside the NW_io UCIe keep-out, and 3 in the 8.64 um die-edge strip beside the UCIe keep-out. All 394 come from tap pins that sit under a keep-out. |
| DRT | **NOT RUN** (skipped on purpose: only 2 die nets, and the GRT already fails on the keep-outs). |
| Die ODB / DEF | written (scratch, below) |

## Findings (recorded, not fixed; the plan and tools/die_plan are unchanged)

**F1 (tools/die_plan bug).** `gen_phys.die_flow_tcl` and `macro_place_tcl` print origins with `{x:g}`, which keeps 6
significant digits.
- 50 of the 88 B2r2 origins are >= 10000 um, so they get rounded. Example: 11905.92 becomes 11905.9.
- Partitions shift by up to 0.06 um, and adjacent partitions overlap by 0.02-0.06 um. 23 `place_macro -exact` calls fail.
- Dies narrower than 10 mm never hit this.
- Fix: print `{x:.4f}`, or better, integer dbu (F2).

**F2 (OpenROAD).** `place_macro -location {21021.1200 ...}` lands at 21021.119 um, because it truncates when converting
um to dbu. This happened to 3 macros. The trial places with `dbInst setLocation` in integer dbu (`round(x*1000)`) instead.

**F3 (plan).** The keep-outs cover partition pins.
- The HBM PHY content `PHY_N.u_phy_Q` has no outline, so its keep-out (= its die.io window) is the whole PHY_N
  partition. That covers all 18,734 PHY_N pins: the HBM row/col/data faces and the clock/reset taps.
  - The PHY macro LEF (`physical/asap7_memory_macros/ot_hbm3e_phy_rc_e8p5`) is 8500.03 x 1177.2 um, so a 0.9 mm band
    of PHY_N is not PHY.
  - The plan should give `u_phy_Q` an outline (die edge band) and keep the taps out of it.
- The NW_io clock/reset taps (7) fall inside the host UCIe content `u_host_N` (8.64..267.84 x 6056.64..7611.84).
- The die spine cannot reach taps under a full-stack keep-out. That is the whole GRT overflow.

**F4 (plan, IO).** Two SerDes contents are more than `io_edge_max_um` = 200 um from the die edge. Their die.io windows
pass only because a window is the whole io partition.
- `NW_io.u_lk_N0` is 276.5 um from the W edge, behind the UCIe column.
- `NE_io.u_lk_N2` is 341.7 um from the E edge. NE_io is its own R0 type with the SerDes at type x = 8.64, which puts the
  SerDes on the inner (W) side of the E io partition.
- The other 3 SerDes and the UCIe are 8.64 um from the edge. The PHY touches the edge.

**F5 (netlist).** The die top netlist (`gen_rtl.die_top`) has only clk and rst_n as top ports.
- The off-die IO signals are not netlisted at die level: UCIe 144, 5 SerDes x 26, HBM 1900.
- So the die.io windows are recorded as geometry only (`die_io.json`), with no bump or IO-pin placement.

**F6 (die PG).** VDD has one fewer M8 and M9 stripe than VSS. pdngen drops the last VDD stripe at the die edge with the
plan offset 4.32 / pitch 8.64 and no `-spacing`. This is harmless, but the die PG is not exactly symmetric.

## Hard cores with real views

- 25 of the 210 hard-core modules (71 of 436 instances) have a name-matching LEF in the repo. Examples: ep_static,
  host_cp_rxs, collar_idx256r, argmax_sw_vm_r2, calendar_f20, pc_ctrl_leaf_cfg_h9b (16), vms_bank_native_q0_faces (8),
  xload_cl2_bfqg (8), vmdel_lane_n (8), ot_pdie_serdes (4).
- None of the 64 SM cores (`hnx_rp3lp3h_s/n`) has one.
- A name match is not a pin match. CORE-HBM: the pdie_serdes view LEF does not match the plan pins.
- Cores sit inside partitions, so they do not enter the die top. Full list and paths: `real_views.json`.

## Commands, host, runtime

```
python3 tools/die_plan/gen.py mockview physical/die_plan/hbm_arch/B2r2/die_plan.json --out views     # localhost 4m47s
python3 tools/die_plan/gen.py assembly physical/die_plan/hbm_arch/B2r2/die_plan.json --out kit --views views   # ~8 min
python3 tools/die_trial/hbm_b2_top.py physical/die_plan/hbm_arch/B2r2/die_plan.json --kit kit/die   # trial_flow.tcl, keepouts.json, trial_post.py
ot-run --mem 250 --threads 16 --hosts intel1 --dir /srv/opentallas-scratch/claude/trial-hbm/top --priority die -- ./run_top.sh kit/die 16 250
```

- Run on intel1, `/srv/opentallas-scratch/claude/trial-hbm/top/kit/die`, image openroad/orfs:asap7lock (OpenROAD 26Q3),
  16 threads.
- Wall time 54:00. Peak RSS 41.0 GB.
- Phase times: read 17 s, place 0 s, pdngen 333 s, check_power_grid VDD+VSS 2629 s, keep-outs + pin scan 6 s,
  GRT 218 s, write 30 s.
- PG statistics pass (`trial_post.py`): 3:55, 4.6 GB.

Big outputs, kept on intel1 under `/srv/opentallas-scratch/claude/trial-hbm/top/kit/die/`:
- `die_top.odb` (1.5 GB), `die_top.def` (1.9 GB), `die_pdn.odb` (1.2 GB)
- `die_top.v`, `trial_flow.log`, `trial_post.log`, `die_grt_congestion.rpt`
- the generated kit: `trial_flow.tcl`, `pdn.tcl`, mock LEFs. The views are in `../../views`.

Small files here:
- `trial_flow_summary.log`: OT_ lines + GRT congestion table.
- `pg_stats.json`: stripes / vias / iterms per net.
- `die_io.json`: die.io windows, keep-outs, edge distances.
- `real_views.json`.
