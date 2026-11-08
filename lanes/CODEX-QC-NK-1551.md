# NK core continuation — 2026-11-07 15:51 takeover

Owner: Codex `nl_clock_form`, under `watch_qc`. Continue until explicit reset. No merges, tags, plan-of-record changes or deletions.

## Actual state at 16:00 PST

- Keep-go full LEC is RUNNING on intel1, `/srv/opentallas-scratch2/claude/dq90/nk_go_keep`, Docker `7cf75179f52e` (`dq90-nk-gokeep-lec`). No terminal `lec/lec.json`. Last actual stage: `rawprefix5_gold_64.aig`, ABC CPU 99.9%; hypothesis 7 induction has no failed hypotheses. The 64-edge reset receipt is present. Outer log on intel2: `/home/ubuntu/dq90/nk_gokeep_lec.log`. This is the current producer; the earlier Codex proof without its reset receipt is historical.
- Current real M7 physical build is RUNNING on intel1, `/srv/opentallas-scratch2/claude/dq90/qfd_tile_nk_a0c_vR5b_m7`, Docker `79e5bdd6ce20` (`kqc-qfd_tile_nk_a0c_vR5b_m7-1930426`), started 14:49. OpenROAD CPU 233%. First M7 GRT had zero overflow; current phase is **post-repair incremental GRT, not DRT yet**. Existing wire repair added 9263 buffers in 7649 nets, then legalized in 109 iterations, max displacement 91.5um. Final producer result is pending. The old outer log's exit137 belongs to the stopped M6 attempt and is not this live run's verdict.
- Original vR4 lec2 completed EQUIVALENT 49506/49506, synth scope only. NL is accepted SIGNED/EQUIVALENT and owned by the parent lane; no duplicate work here.

## Geometry and class

Actual final vR5b `4_cts.odb` rendered and both images VIEWED on this takeover: intel2 `/srv/opentallas-scratch2/claude/codex-nk-1551-review/png/{floorplan,density}.png`. Guarded reader unit `oth-ubuntu-1374717-1794095668` completed exit0. Narrow west ROM channel and central density concentrations near (285,640) and (250,400) persist; no new macro overlap. The named controller cluster fits the open central channel near y560. SMELLS: 3 narrow channels, 4 divergent clock ownership, 5 ENA driver spread, 8 central density concentrations. Timing target remains open, so this is not closure clearance.

Final vR5b CTS was TT -98.70ps on three endpoints, TNS -164.7. The merged body go/controller go_f launches late after face-clock lift and feeds the early controller. Its QN polarity inverter also remained near the old gate home. M6 routing failure is a separate layer-ceiling class; actual M7 has closed first-pass overflow, with routed timing/DRV/DRC still pending. No ECO: the setup miss is too large.

## Prepared source step, not launched

`codex/nk-vr7-control-home-1107@2092c02a586`, base `66d55c026ad`, adds `tools/die_plan/nk_vr7_form.py`. This constructor refuses to prepare a kit until the current keep-go producer returns EQUIVALENT and its mapped SHA is exactly `31aba5840ec08378358b3954494cfb8479b52e57fcc8bb2353b20ac6f314e8ed`. No new kit or physical run has been created yet.

vR7 preserves RTL, reset receipt, parameters, SDC and PIN cycles (added 0). It explicitly assigns tap[0]'s face role to body `u_g.go$_DFF_P_`, while kept `g_icg.go_f$_DFF_P_` remains an internal controller copy; both D/CLK connections are checked by the private face hook. Named controls and exclusive Q polarity/buffer cones move together. M7 is set before floorplan. The body copy loses its obsolete controller retap; go_f receives the existing 320ps class before en_g auto-balancing. Short go_f-to-go_h hold must be priced in the actual CTS result.

Do not reuse vR5b `dq89/plan.tcl`: it contains old anonymous cell IDs that changed in keep-go synthesis. The constructor carries the existing census/gate_rehome algorithm and deliberately refuses CTS until a new plan from vR7's own PLACE exists. Source-only B3 branch `codex/b3-retap-owner-1107@56906bf9d99` supplies selected-tap repeater geometry ownership; its prior bounded witness passed, but it has not been physically deployed.

Next: collect actual keep-go and real-M7 producer terminals. On EQ, prepare vR7, render its unchanged macro/pin frame with declared control placement, run ONE PLACE, view actual images and inspect actual FACE ownership, then regenerate its gate plan. CTS is a separate reviewed step. Preserve all healthy jobs and failed evidence.
