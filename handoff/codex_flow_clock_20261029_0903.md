# Shared flow/clock handoff — explicit Claude reset, 2026-10-29 09:03 PDT

Stopped engineering, new jobs, routes and merges immediately. Both children received the reset. Live jobs remain untouched. Aggregate details are in CODEX-LOG.md, section “Handoff to Claude 2026-10-29 09:03 PDT — CODEX shared flow/clock aggregate”; 32-lane inventory is handoff/codex_shared_coverage_0822.tsv.

- **Integrated:** actual BUFx10/12/12f/16f calibration acedd3ef7 +947dd4bf1 (codex/buf-cal-0827); BUFx8 already9023.64 measured TT/FF rise/fall rows, zero calibration-bound violations,39 tests pass; old84 deck files unchanged. Intel2 codex-buf-cal-intel-0827 unit2001498 EXIT0, no live own calibration job. Failed EPYC OSDI SIGILL evidence retained. Source WT removed after integration.
- **Integrated shared flow:** parent receipt writer/core metadata e6d564618; exact-library RC probe65bb9a7ca; actual FF-only warm-ECO6be8c010c.6be corrects make overrides that loaded TC+BC without MM runtime support. Actual q3 correct initial hold−30.317 matches real reference−30.32; wrong frame gave−61.791. No constraint relaxation.
- **Integrated clock tools:** four paused Claude polarity commits34b/df51/0fb/7e92 +387 evidence; HEAD735tap routed proof0 duty failures both corners, frozenhk5 unchanged. Generic local entry aca469fad+e45 evidence. Actual HBM1x stage fitter1a3/1d599 +registry/config4dfbcaca2, no die-gate qualification.
- **PENDING ROOT, not main at reset:** f28c64757 +e86c02839 lane_add on codex/lane-add-0850. Own clean pushed WT /srv/opentallas-scratch/claude/wt/codex-lane-add-0850. Enforces canonical final latency incl landing with late full rollback, equal actual split-word cycles, preserved mirror split key, existing4.32um macro halo.10 tests pass; all4 new controls catch old faults. Do not adopt failed D18 plan; rebuild only in owner's next plan event.

Live jobs (child hold, branch codex/flow-eco-ff-1029; source6be):

- **E0 fresh FF15:** Intel2 real host/hub (“localhost” in ot-run), /srv/opentallas-scratch2/claude/codex-flow-hold-0830/e0_ff15, unit oth-ubuntu-2828389-1793289392. Same5513 RTL/pins/outline/clock/reset geometry, personally viewed prior image. Fresh64GB/16thread route, then script automatically runs true post-route ECO after actual6_final and signoff exist. Check `ssh intel2 'tail -30 /srv/opentallas-scratch2/claude/codex-flow-hold-0830/e0_ff15/run.log'` or inspect sibling e0 logs/run_e0_ff15.sh when filename differs.
- **q3 actual FF-only post-route:** Intel1 /srv/opentallas-scratch2/claude/codex-flow-hold-0830/q3_ffonly_holdeco, unit oth-ubuntu-1787016. Only FF libraries,202.5 reference, all411 clock wires FIXED;15ps hold repair/DRT. Check `ssh intel1 'ls -lt /srv/opentallas-scratch2/claude/codex-flow-hold-0830/q3_ffonly_holdeco; tail -20 /srv/opentallas-scratch2/claude/codex-flow-hold-0830/q3_ffonly_holdeco/run_eco.log'`. Original inherited pre-DRT1253686 remains untouched. Own wrong-mode post2 was stopped by exact container, failure kept.
- **Current canaries:** existing A592 HEAD + KV core canaries remain collector-owned. No repeat builds. Child hold has exact canonical paths in its CODEX-LOG handoff.

HCP proof blocker:

- WIP **codex/hcp-const-0848@b8d5a3b5d**, diagnosis only; results/hbm_hcp_correspondence_1029/README.md. Child duty parks/pushes it; **not a closure candidate**.
- Runtime Intel1 /srv/opentallas-scratch2/claude/codex-hcp-0848: inputs/, normalized.pkl, proof1..4, baseline5, truth6.log. No live own HCP jobs. Check `ssh intel1 'tail -12 /srv/opentallas-scratch2/claude/codex-hcp-0848/{prove4,baseline5,truth6}.log'`.
- Exact baseline9658/9246/412 reproduced.16 gold constant facts prove526 joint obligations and remove8 boundary NV failures;404 original failures remain. BOTH nout-constant hypothesis correctly refuted gate-side. Actual three-input truth: gold nout_r[1] D=(~cmd_valid)&Q, gate nout_r[1] D=cmd_valid|Q. False single-survivor vector name match: gate survivor is loaded ONE, matching gold nout[3]/[4], while gold bit1 loads ZERO.
- Next: re-key that gate survivor, prove equality to the correct gold bit and gold-only zero/NV facts with actual reset bases, joint induction and full compares. No engine weakening, X-mask bypass, RTL resets or rekey/proof work performed after reset.

Other open failures / next steps:

- **HEAD canary:** original REG preserved. Old gold signoff was pre-corner PROTO; old05f9/currenta592 source also changes mandatory START/reset RTL2651→6119bytes, local reset taps3→8, despite identical pins/SDC/clock binding. Root authorizes successor compare existing A445 vs A592/current on the SAME current source/pins/SDC/binding. Only actual comparable NO-REG permits a separate source-scoped baseline/tag; never overwrite old REG or waive current hold/DRV FAIL. Last ruling is for successor only; not acted on after reset.
- **QC START join:** tokens/qwen owns live current functional bind. Existing start_provider_bind accepts only scalar top reset input; actual plan needs internal rstw_sl_E0_fw_rst_o_0 from sl_E0_fw.rst_o_0. Future narrow adapter must privately export the exact plan-validated carrier through u_bound, not reference an invisible internal net or substitute raw reset. No implementation started.
- **PG:** historical KV glue IR collected rc0/co-located3.270mV on old placed/activity0.263 diagnostic only. HBM hub activity145/150 FAIL remains tokens-owned. New KV provider PG belongs /root/kv_pg; no duplication.
- **Fleet:** use explicit commit SHAs for new worktrees; epyc2 has literal FETCH_HEAD ref that can override the pseudo-ref. No refs or peer work removed.

OWNER? None in this shared group.
