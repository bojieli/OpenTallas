# GPL-TD-AB handoff (11-20 evening)
## Finding (step 1, V from source and logs)
- S81 kits: GLOBAL_PLACEMENT_ARGS = -overflow 0.2 (gen_phys.gpl_overflow, FABLE-PD-S81-STRIP 11-16: ORFS 0.1 end gave HPWL x1.6-2.4 on sparse strips), GPL_KEEP_OVERFLOW 0.25 (RFLOW; first pass at 0.41-0.63 added +18..51 % area), OT_GPL_SPARSE_OVERFLOW 0.25 (inert when the call names -overflow).
- OpenROAD default reweight list is 2 entries (64, 20): pass 1 virtual at iteration 1-5 (overflow 0.47-0.63, buffers dropped), pass 2 at 0.20 never fires with end 0.2. col_h9_r0_p1 baseline: 1 pass, overflow 0.466, worst slack -322 ps, GPL 1392 s.
- QC/KV end at the ORFS default 0.1 and get both passes.
## A/B (queued, not finished when this was written)
Source kits on epyc10: .../224567138ab/items/col_h9_r0_p1__t1__pvb49c16c8/attempt_2/gen/<type> and items/ot_s81sl_leaf__t10/gen/<type>.
Variants (script /srv/opentallas-scratch/claude/gpltdab/ab.sh on epyc10, dirs gpltdab/{col,leaf}_{base,e10,rw4,rw3}): base = -overflow 0.2; e10 = -overflow 0.1; rw4 = -overflow 0.2 reweight {64 40 28 22}; rw3 = -overflow 0.2 reweight {64 30 22}. Place only via run_kit.sh GOAL=place.
Launched from intel2 ~/gpltdab-logs/*.out (ot-run, OT_LANE=GPL-TD-AB, waiting on epyc10 memory admission). Each .out ends with the GPL args, timing-driven passes, HPWL, GPL time and 3_detailed_place WNS.
## Next
Compare place WNS / DPL HPWL / GPL time per kit vs base. Post READY only if WNS gain exceeds cost and HPWL stays <= ~1.1x base; e10 is expected to lose on HPWL.

## FINAL (8 of 8 done, place stage only, 3_detailed_place; kits from event 224567138ab)
| kit | variant | passes | WNS ps | TNS | legal HPWL um | GPL s | TD area |
| col_h9_r0_p1__t1__pvb49c16c8 | base (end 0.2, {64 20}) | 1 | -181 | -27.7k | 13.93e6 | 1143 | +0 |
| col | e10 (end 0.1) | 2 | -196 | -79.5k | 13.89e6 | 1492 | +56.6 % |
| col | rw3 {64 30 22} | 3 | -166 | -59.7k | 13.92e6 | 1599 | +56.6 % |
| col | rw4 {64 40 28 22} | 4 | -94 | -20.3k | 13.92e6 | 1776 | +56.6 % |
| ot_s81sl_leaf__t10 | base | 1 | -759 | -24.3k | 9.76e6 | 978 | +0 |
| leaf | e10 | 2 | -705 | -68.1k | 10.13e6 | 1389 | +60.6 % |
| leaf | rw3 | 3 | -674 | -44.9k | 9.92e6 | 1418 | +60.4 % |
| leaf | rw4 | 4 | -893 | -33.8k | 9.92e6 | 1608 | +60.4 % |
Verdict: COORD test (leaf rw3/rw4 WNS gain >= 50 ps with TNS no worse) NOT met: leaf rw3 +85 ps but TNS -44.9k vs -24.3k, rw4 WNS worse. No READY, defaults unchanged.
Observation for COORD: col rw4 alone gives +87 ps WNS and better TNS (-20.3k) for +55 % GPL time and +56.6 % buffer area; one kit, not reproduced on leaf, so not proposed.
Note: pre-GPL hook cons_gpl_pre.tcl takes ~26 min on the leaf kit before GPL starts.
