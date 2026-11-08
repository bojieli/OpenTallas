# CODEX HEAD CTL takeover 2026-11-08 02:30 PST

## Current step
CODEX took over: hd_ctl vG private PLACE pilot on codex/head-ctl-vg-0222, I1 /srv/opentallas-scratch2/claude/codex-head-ctl-0222/source, fork 256a8a35f05 (prior published codex/head-ctl-vf-1551).

## CODEX notes
- vF PLACE + official kit LEC collected: EQUIVALENT 61636/61636, 0 differs/undecided. vF is NOT route-ready: prior actual review found xb2 raw reach 509.868um and ideal placement TT wcnt -> st1 -33.71ps. Original E4 scratch3/claude/dh83/hd_ctl_vF/hd_ctl unchanged; HOLD_ROUTE/PRIVATE kept. It was already diagnosed at the 17:06 handback; no unchanged rerun.
- vG source/model already proved by prior lane: CTL_WINDOW_PRE projects exact nonzero counter state, 10000 counter checks/80 resets + off-by-one mutant caught83; START integration9530 cycles/2START/1retire and ownership/window mutants202/125. No re-run of finished proofs.
- Viewed actual planned image /tmp/codex-head-ctl-0222/planned.png (from source geometry_vG/planned.svg). GEOMETRY: eight compact 32bit XB mux/capture groups in the clear XA macro channel, XA anchors retained, 25.896um macro gap/21.792um usable corridor. Planned ingress317.574um / return342.198um; actual PLACE/GRT still required. SMELLS: sparse upper half remains due fixed parent slot, no new macro/pin/clock obstruction in the modified corridor. Verdict PASS-COND for ONE private PLACE only, matching prior parent ruling.
- New kit E4 /srv/opentallas-scratch2/claude/codex-head-ctl-0222/hd_ctl_vG: vF frozen RTL/wrapper/macros, only new CTL_WINDOW_PRE=1 and 1025 compact mux/capture/window sites. No run DB, LEC receipt or process state copied. 71 current generic helper overlays from kw33/src_d95ec via established stage_current_helpers.py, preserving generated prologues/epilogues; current RUN_KIT extracted. Fresh synth/official LEC required. HOLD_ROUTE + DO_NOT_COUNT + PRIVATE_DO_NOT_COUNT.
- PIN CYCLES: vG adds0 vs vF. Existing private x_o[564:0]+1 from vE retained; epoch[565] unchanged. No plan/compiler adoption.

## Running
I2 controller /home/ubuntu/codex-head-ctl-0222/vG-place.log; ot-run client PID3604751 reported by launch shell (actual admission scope pending); host E4 only --no-spill, 48GB8T20GB, goal PLACE. 02:30 waiting for memory: admits22GB, needs34GB. No physical job yet, not a failure. All bulk on E4 scratch2 (677GB free).

## Next
Read admission and fresh official LEC; view actual placed density/layout and mux reach before any CTS/GRT. No route release, no merged/tag/count claim. Any failure gets class diagnosis, never an unchanged retry. Source wrapper/model remains private.

### 02:31 admission correction
First admission scope oth-ubuntu-3682234-1794133775 exited10 in kit_preflight: my source copy excluded lec* and omitted lec.py, so no P&R ran. Canonical kw33/src_d95ec/tools/die_plan/lec.py staged. Kept FAIL_PREFLOOR.missing_lec_tool and timestamped preflight JSON. Corrected admission E4 oth-ubuntu-3733334-1794133860 starts from no DB, fresh synth. New intel2 log /home/ubuntu/codex-head-ctl-0222/vG-place-fixed.log; preflight PASS0. Former vG-place.log preserved. OT_VCLK_TT450/FF342 unchanged native HEAD contract carries standard preflight advisory; no signoff claim.

### 02:43 source-hook class fix
Fresh synth completed SELRANGE/PORT_BIND4502/FACE_GUARD4424/REG_FANOUT47715 PASS. First3_3 PLACE stopped before GPL on the committed planned hook: cm_site read ::cm_ff but initialization was local to ORFS caller procedure. Read-only source-under-proc probe then caught ODB-0360: xa2 was already FIRM and orientation changes need release first. Fixed generator+emitted Tcl with explicit global aliases and targeted PLACED-before-reorient/FIRM-after. All1025 actual mapped mux/capture/window targets now pass the8GB2T direct probe on3_2 ODB (scope_probe/probe2.log CTL_SCOPE_PASS). Kept first failing probe and original3_3 logs in failure_cm_scope; failed evidence not overwritten.
Hub branch codex/head-ctl-vg-0222@ff383026c2a (source/report previous4744a03c72e). Incremental native PLACE continuation same own kit/unchanged RTL: normal make selects missing3_3; no forced reuse, no route, no seed/knob retry. Intel2 controller PID4012221, log /home/ubuntu/codex-head-ctl-0222/vG-place-scopefix.log. Await admission/actual final PLACE and fresh official LEC. First prereoute proof was automatically aborted by runner at flow failure, no verdict reused.

### 02:47 queue balance
E4 admitted -13GB while I2 had188GB; unpinned the same corrected continuation. Cancelled only own unstarted client4012222. ot-run printed START STATE UNKNOWN, so checked E4 ps/docker/systemd: no matching own payload/queued process/unit remained. No duplicate. New client4043134 standard spill copied1.0GB E4->intel2(localhost compute, not coordinator ubuntu); admitted oth-ubuntu-4054213-1794134844, preflightPASS0. Log intel2 /home/ubuntu/codex-head-ctl-0222/vG-place-scopefix-spill.log; active kit same path on intel2 with standard copyback to E4 after run. E4 remains canonical saved failure location. No source/PIN change in relocation; no forced checkpoint reuse.
