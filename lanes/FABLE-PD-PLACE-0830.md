# FABLE-PD-PLACE-0830: 18 place-stage failures, 07:29-08:29 PST (2026-11-15 08:40 PST)

Read-only. MEASURED = read from logs/kits today; INFERENCE marked.

**Headline: 14 of the 18 are not placement failures.** Place finished (KW_PLACE_RC=0, 3_place.odb written, 40-41 %
utilization), but on a different host than the one the wave probes. Both wave labels are wrong: "PLAN: plan geometry /
site" is the classifier quoting the `GRTM mode edge_outline` banner line; no item has a geometry, site, macro or IO error.

| class | n | items | root cause (MEASURED) | fix, owner | hold? |
|---|---|---|---|---|---|
| A. kit-host mismatch (wave tool) | 14 | QC sle_fe_v1 x2, sle_su_l0, sle_su_l1, slw_su_l0 x2; KV hgi_v1__cl42bc8b12, hgi_v4, hroot, io_cor, pc_v1 x2; S81 station t17, t26 | Place ran on host X, probe looked on gen host G, found no odb. Two paths: (1) ot-run-sealed submits `--hosts G`, backend ot-run "INPUT HOLD ... candidates G -> all 6 holders" moves it to X; no copy-back record. (2) ISOLATE-GAP unsealed rerun (`~/.local/bin/ot-job-docker` missing until 07:24 PST) also lands on X. Example hgi_v4 a14: G epyc10, odb (355 MB) only on epyc8. | kit_wave.py `copy_back_hosts()`: add the host of the last `ot-run: RAN on H ... exit 0` line as first candidate; set `ran_on` from it. Classifier: RC=0 + no odb = INFRA, uncharged; never quote the GRTM banner. Then re-judge the placed kits in place (odb still on X), no rebuild. **KIT-OPS-5** | No type hold. Fix within the hour: each false fail discards a good place and restarts from synth |
| B. Tcl uninitialised global | 2 (+3 same hour) | KV hgi a21, a22 (also io_cor_v1, io_ft_v1 x2) | `landing_placement.tcl`: `cland_ring_place` (l.1402) and `cland_column_select` (l.884) read `$cland_col_cursor`; it is set only inside other procs (l.378/1094/1188/1246). Top level sets `cland_cursor {}` (l.709) but not this one. Dies when a ring band is the first band after reader-start grows (176 grow lines, then error; 4 min). | One line: `set cland_col_cursor {}` beside l.709 in tools/die_plan/landing_placement.tcl, into the wave source. **KIT-OPS-5** (tool), KV-102 confirms on kv3_hgi | Hold these 3 types until the line lands (deterministic, 5 fails today) |
| C. ring band blocked | 1 | KV hgi_v8 (same form: hgi_v6 x3 today) | ring:ft20_i band 8.64 x 84.24 um at x 298-307, y 127-212: 651 cells need 222.5 um2 of 727.8 (ratio 0.31) yet first flop finds no legal site. Not capacity. INFERENCE: band already occupied by firm cells placed earlier (ft17_i S-face pinslot strip 67 um deep at x 238-286, 361 grown start/collector cells) or one-column-wide rows cut by taps. | Generator: bands at least 2 columns wide or ordered before grown cells; report occupant on BAND FAIL. **KV-102** | Hold hgi_v6, hgi_v8 on kvgeom6 |
| D. LEC not equivalent | 1 | QC slw_hc3__clccfc3e6b (sibling cld86a7ad4) | Place RC 5 = pre-route LEC stopped the flow: 51 of 112,450 compare points SAT; async-reset registers gold 367 vs gate 365. LEC ran 9.8 h. Event S3R (old). | RTL/bound diff of the 2 lost async-reset registers; rebuild on S4Q2 only. **DIE-QC-103** | Hold slw_hc3 forms until explained |

## Numbers behind A
- Last 8 h, places ending RC=0: run host = probed host 80, all pass. Different host 64: 39 FAIL, 25 pass (the pass cases have a SPILL or sealed copy-back record).
- Since 07:10: 15 of 22 finished places false-failed (68 %). The gap path closed at 07:24, the sealed INPUT HOLD path did not (08:12, 08:23 cases are sealed), so the rate stays high.
- Cost: t17 at attempt 28, hgi at 22, sle_su_l1 at 18.

## KV 7j
- A and B are tool defects, independent of the plan: 7j kits fail the same way. Fix both before the 7j wave.
- C is kvgeom6 band geometry on hg/hgi frames. 7j regenerates these kits (ECTL station changes), so do not tune kvgeom6 bands; apply the generator rule and judge on 7j kits. hgi_v1/v4 placed fine on kvgeom6 (class A), so the frames are placeable.

## Advisory, not blocking
Placed kits flag local_density 1.385 (KV hgi_v1, hgi_v4, io_cor) and 0.98-1.00 (QC sle_su_l0/l1, slw_su_l0); fanout_spread 2666-2775 um on hgi. Watch at GRT. Clock entries over macros on hgi_v4 (16) and pc_v1 (8) are preflight advisories.
