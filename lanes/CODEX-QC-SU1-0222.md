# QC SU1 production read-calendar followthrough — 2026-11-08 02:2x PST

CODEX took over: numerical requalification on codex/qc-su1-prod-0222, intel1 /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222, source 895234baeda based on b629fb69693.

Current step: run1 compile/sim admitted via ot-run24GB/4T/disk8, intel1 unit oth-ubuntu-3814669-1794133582. Controller codex-qc-su1-prod-0222-run1.service on intel2, log /home/ubuntu/coord/runlogs/codex-qc-su1-0222/run1.log. Results intel1 /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222-run1/{build.log,run.log}.

Model: true pin-to-pin providers VM6/CROM9; parent request5 + answer4 gives read roundtrip15/18. Proposed private head EXTRA9 and independent WROM compensation9, ingress4/outgoing5 => requests+9 and results+18 against unchanged zero-transport oracle. Five parallel instances: oracle, compensated candidate, WROM4 mutant, EXTRA4 mutant, uncompensated parent. No POR/default/interface or physical change.

Limits: this isolates ordinary read/reply transport. Actual lane0 request-derived WROM, VM write pad14 feedback, production scheduling and composed reset remain obligations. No whole-parent exactness or signed-off claim.

Publication: branch pushed to local source origin; push to hub failed DNS intel2 on intel1. Source remains committed, can fetch by intel1 path from hub.

## CODEX notes

Run6 prior result retained: zero-transport provider calendar PASS, not production calendar. New run1 pending.

## 2026-11-08 02:37 PST RESULT

Run1 TERMINAL PASS (ot-run exit0), source RTL/bench895234baeda, checker66b7594c8dd, final source+results2a102b5c539. 288 result words across five classes (32/64/64/64/64), VM writes64, KV writes96, actual scheduled faults40. Correct compensated form requests0/data0, scheduled fault uniquely+18 (adjacent lag17/19 each80 errors), independent BYP golden32/32/error0, warm reset leaks0. WROM4 mutant52 data differences, EXTRA4 mutant406, unchanged head under parent transport478, all request comparisons0.

Diagnosis: current read transport5+4 adds9 roundtrip edges; unchanged head has no compensating metadata alignment, so matching request addresses alone conceal wrong numeric results. Head EXTRA9 plus matching global WROM9 fixes the private read capsule. Last observed qc53v4s lane table is unchanged5/4; experiment is relevant to current candidate. Transport state6584 bits/lane before head/reset/clock overhead.

Next: actual lane0 request-derived WROM and mutable VM write pad14 feedback + compiler scheduling must compose before whole-parent adoption; neither is claimed here. No physical work launched. Source remains ownbranch; request parent publish2a102b5c539 to hub.

## Followthrough 02:43–02:52 PST

Actual lane0 WROM fixture running intel1 unit oth-ubuntu-235634-1794134601, out /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222-wrom-run1, runtime sourcea70ed396e26. Intel1 waiter had admitted during attempted migration: own client was cancelled, real producer was detected and left running; NO epyc6 staging or duplicate producer. Compile/mutant chain remains active. Source is actual current bind_v4s qfd_qc_su_lane_w_l0 with exported co301 re/co300:277 address. Provider is finite actual MIF0 BTAB plus official table load and SRAMs,8-edge branch. Baseline and private EXTRA9 each have one lane0 and one lane4; no synthetic WROM compensation, source request5/reply4 naturally carries9 extra edges.

Mutable VM provider-only mechanism DONE PASS, unit oth-ubuntu-417528-1794134924 exit0 (log coord/runlogs/codex-qc-su1-0222/vmfeedback1.log), source12e27c9516c, out intel1 /srv/opentallas-scratch2/claude/codex-qc-su1-prod-0222-vmfeedback-run1/run.log. Nativegap3 and productiongap17 read new lane0/lane4 words40400000/40800000. Unchanged productiongap3 and one-edge-early gap16 retain old3f000000/3f800000. Allfault0. This proves real mutable storage+collision suppression requires boundary gap17=3native+14transport. HeadEXTRA9 is separate; compiler producer-consumer readiness can need23 extra edges relative to unmodified asbuilt.

Plan helper derive_read_transport.py on current qc53v4s: all24 SU groups uniformly request5+answer4, head extra9; no divergent bus depth. Released safe2 simulation assertion supports MEMORY_READ_EXTRA only0or1, so adoption needs the private structural successor and its own physical proof, not a parameter flip on the closed source.

## 2026-11-08 03:01 PST WROM RESULT and production source READY

Actual lane0+lane4 WROM capsule TERMINAL PASS (runtimea70ed396e26; terminal logs/results5badf7e8f84): both lanes request0/data0, scheduled fault uniquely+18, two finiteBTAB providers160checks/error0 each at8-edge calendar, golden32/32 and warm0. Returned-WROM+1edge mutant14 dataerrors EACHlane, provider160/160 stillcorrect. No synthetic WCOMP; actual lane0 exportedco301/300:277 is sole source. Mutable VM proof separately terminal and committeda288556fc94. Tokenchild /root/svc_token/token received exact paths/sourcecalendar and is binding explicit source-negedgeN→input-samplingN+1 conversion; derived dates are not mislabeled measured events.

Production source READY a6215bdf39c on sameownbranch. New rtl/physical/qfd_qc_su_lane_w_l4_mem9_form.sv (same selectedtop/ports, READ_EXTRAdefault0,pilot9) and rtl/physical/qfd_dv_lane_h_su_mem9.sv (renamedML12, D13 synchronousroot2edges, pipelinedbranches). Canonical qfd_qc_su_lane_w_l4.sv unchanged/byte-identical. Exact production filelist tools/qwen_dv/su1_mem9_physical_0222/sources.f; portable numericallintclosure kept separately. Model parent4/5outside, PINcycles0, head+9, compilerdependency+23. Parent /root/qc now owns model/elaboration/kitgeometry/ONEPLACE on conservativeform, so no duplicatepilot here. Clockwarning: canonical clkSedge207.324/0.096; geometriccenter207.36/133.92 insideTLSstack, choose clearchannelroot only after actualmacro/pin image review.

No ownheavy jobs pending now. No merges/tags/POR/defaultadoption or deletion performed. Next sourcefixes depend on parent's actualproduction elaboration/geometry findings; fullparentcompiler/token/physical qualification remainsopen.
