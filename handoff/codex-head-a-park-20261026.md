# Codex HEAD elemA parked on explicit reset, 2026-10-26 21:0x PDT

No new engineering or launches after root's explicit reset. Existing jobs below may continue. No DRT or sign-off started; nothing is SIGNED in this task.

## Source
- Own sparse WT `/srv/opentallas-scratch/claude/wt/codex-head-a-2025`, branch `codex/head-a-2025` based on HEAD lane r9 `e146c67812`.
- Pushed work commits `7186939cb` (actual standalone primary clock + four FT arcs, STA/miter/read-review), `5338856f5` (guarded DRT resume recipe), plus the final parking commit of `tools/s81_head/grt_input_hold_coupon.tcl` (tip recorded by parent from branch).
- Cherry-pick only these concrete commits for integration; the lane ancestry includes prior work. No canonical RTL/plan was edited.
- Reusable helpers under `tools/s81_head/`: `prepare_actual_head_contract.py`, `actual_head_sta.tcl`, `actual_head_grt_repair.sh`, `actual_head_route.sh`, `functional_head_export.py`, `head_clock_interface_probe.py`, `dump_core_review.py`, `grt_input_hold_coupon.tcl`.

## Actual interface and results
The accepted R8 physical patch destroyed BTerm `clk`. Its real primary clock is `ft_mstrap_i -> u_isl_root -> internal clk`, source offset ZERO. Four other pairs are actual die-timed FT arcs (`u_isl_ck0`, `u_isl_ck1`, `u_isl_m0`, `u_isl_rstft`), eight ports total. Root approved this explicit standalone contract. Modern `ft_ports` installs an FT-safe SDC; actual clock is not declared as FT. Canonical HEAD pin/header binding remains OPEN: the old manifest counted a phantom extra clock port. A source-consistent alias back to canonical `clk` or a primary-port rename must be folded once into HEAD infra.

- Actual GRT image rendered and VIEWED: `results/geom_review/codex_head_a_2025/actual_grt.png` (28,721 sequential cells,699 clock/island cells,152 M4/M5 PG rectangles). PASS-COND for actual STA/data hold repair; DRT after real gates.
- Real standalone GRT STA (833ps, TT setup / FF hold,60/25ps, rc_cal0.8,0.9): TT setup +118.46801365ps /0 endpoints; FF hold -73.67755047ps /707 negative endpoints. UNCHECKED by independent NUMBER-CHECK. TT min is info only. No timing gate relaxed.
- Extracted actual interface miter:128 checks,64 clock edges,0 added cycles. FT reset-polarity mutant caught immediately. Logs in own kit `if_base.log`, `if_mut.log`, committed results.
- Original whole-core LEC attempt UNPROVEN because `write_verilog` exported physical-only TAP cells lacking liberty models. Original gate retained as `actual_grt.v`; `functional_head_export.py` removes ONLY8,176 exact portless TAP instances, refuses any with a functional port, changes zero functional cells/nets. Retry below uses main qualified `lec.py` SHA256 `0b650fe626086893d76d17781a13257e34e98ab1de2e3e0480fcd009dbb4a058`.

## Running jobs (leave them running)
1. **Whole actual core LEC retry**: intel1 `/srv/opentallas-scratch2/claude/codex-head-a-2025/kit/lec_actual_r2`. Client on epyc1 `2001766`; unit `oth-ubuntu-2428351-1793072017`. Check epyc1 `/srv/opentallas-scratch2/claude/codex-head-a-2025-lec-r2.otrun.log` and final `kit/lec_actual_r2/lec.json`. Gold/gate AIGs and hyp0/hyp0_swept existed; no final verdict at parking. Do not assume EQUIVALENT.
2. **Qualified HB4 FF GRT repair successor**: intel1 `/srv/opentallas-scratch2/claude/codex-head-a-2025/repair_hb4`. Epyc1 client `3625034`; unit `oth-ubuntu-2546893-1793073679`. Check epyc1 `/srv/opentallas-scratch2/claude/codex-head-a-2025-repair-hb4.otrun.log` and runtime `ff_repair.log`; script then writes `repaired_sta_TT.log`, `repaired_sta_FF.log`, `actual_sta_{TT,FF}.json`. Launched from untouched accepted source, same constraints, same margin15, only missing shared HB4 hold-phase helper restored. No clock ECO.

## Diagnosed failed repair / limits on diagnosis
Own original repair at intel1 `.../codex-head-a-2025/repair` plateaued: WNS -61.568ps /TNS -14,985.943ps stayed exact across hundreds of iterations while ordinary-buffer count grew beyond2,300. It was a real single bc/FF scene with vclk202.5, not a dual-scene problem. Exact own container `7549280a5105` was stopped AFTER diagnosis; original accepted checkpoints remain in `kit/`, and failed log + `repair/diagnosed_plateau.json` remain.

The custom PRE_GRT hook omitted the already-qualified `physical/common_flow/hold_pad_hb4.tcl` from main (f7dd829445-era helper with implicit setup+hold dispatch). Native `*xp*` dont-use policy therefore barred HB4 and ordinary BUFx2 cells were used. The corrected successor sources that current helper only in the hold phase; fractional compute cells stay barred. This missing-hook defect is confirmed. **It is NOT yet proved to be the sole cause of the large-core plateau**; the corrected real run must establish the effect.

Minimum PI coupons disprove a generic incremental-GRT timing-update failure:
- Default policy: one HB4xp67 adds47.63ps; hold -47.6003 -> +0.3698ps, in-repair equals after-reroute. Epyc1 `codex-head-a-2025-coupon-r3.otrun.log`.
- Native fractional-cell exclusion: four ordinary buffers close the scalar coupon to +1.7199ps in-repair /+1.8304ps after-reroute. Epyc1 `codex-head-a-2025-coupon-native.otrun.log`.
- Earlier coupon setup failures (missing track helper, invalid percent; then bus escaped-name lookup) remain separate logs; none is core closure evidence. The later source fixes the lookup by enumerating the sole receiver, but no new bus run was launched after reset.
- Flow-kits independently checked actual B x158/x179 net and instance DNT=false; their additional pin/BTerm check was pending elsewhere. Do not call the plateau a proven stale-parasitic bug.

## Next concrete steps after resume
- Collect both running results; diagnose actual failures instead of duplicating proofs or routes.
- If LEC EQUIVALENT and repaired TT setup >=0 /FF hold >=0 with zero endpoints, copy the completed LEC receipt into `repair_hb4/lec_actual_r2/lec.json` (the successor copied a still-in-progress receipt directory).
- Copy `tools/s81_head/actual_head_route.sh` from the own WT into the repaired kit, then run through ot-run48GB/16threads. It refuses nonpassing STA/LEC, resumes explicit `do-5_2_route` rather than aggregate `do-route` (which would rebuild GRT), restores TT250 SDC in final output, finishes/abstracts, then invokes signoff.py with declared FF202.5, real primary clock, all four FT arcs. Only actual `signoff.py` SIGNED counts.
- Corrected repair may still fail; collect before routing. The current HB4 run is the experiment that decides whether the missing hook fixes the production plateau.
- Parent handled B using the same portable contract/helpers; no B files were edited by this child.

## OWNER?
None newly opened. Standalone interface ruling already received; canonical HEAD infra fold remains a technical integration task.
