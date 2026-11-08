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
