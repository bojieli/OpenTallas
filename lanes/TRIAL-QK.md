# TRIAL-QK (lane file)
Scope: trial full-chip (die-level) prototype runs for qwen_compute and qwen_kvsys (v3.8s): abstracts + fixed placement +
die PDN + die IO; die clock H-tree to partition taps; die GRT of all inter-partition / ft nets; die STA (DIE-STA
die_sta.py ILM where closed, budgets elsewhere); PDNSim IR. Results -> results/die_trial_1024/<die>/.
Branch claude/trial-qk-1024, worktree localhost:~/wt/trial-qk. Hosts: 1 TB hosts (epyc3 / intel2 first) via ot-run.
## Status
- 07:45 PDT started; reading plans + gen_phys assembly/mock_lef + g2 die probe + die_sta.py + hbm_arch clock_htree.py.
- 08:20 tool tools/die_plan/die_trial.py (build/calib/ir/report) on claude/trial-qk-1024 (uncommitted yet). Tiny plan smoke PASS
  (route, clock, calib, PDNSim). Builds: QC 377 parts / 1.91M hop nets (1.05M abut + 0.86M ft) / 6684 taps;
  KV (main = v3.8u = v3.8s + hub_Wi pins) 160 parts / 0.94M nets / 2370 taps. Neither plan has @die ports (die IO = die_io windows).
  Calib (DFF->BUFx12f/250um->DFF, GRT RC): raw reach SS M8 1517 / M9 1628 um, TT 2252; FF 2-um flop-flop hold -2 ps (25 ps unc).
  Runs via ot-run on intel1/intel2: /srv/opentallas-scratch2/claude/trial-qk/{qwen_compute,qwen_kvsys}{,_ir}, calib;
  launcher logs localhost:~/ot-scratch/trial-qk/logs/*.log.
- NOTE PDNSim: -source_type BUMPS in this build puts all sources on the die LEFT EDGE (M8 x=0): use -vsrc CSV x,y,size,V.
- OWNER ORDER 08:05 visual review: renders (floorplan+lanes, clock, congestion, IR) -> results/geom_review + results/die_trial_1024.

## CODEX notes
- intel1 scratch2 trial-qk build artifacts both dies exist; QC route_g0 log present, IR power JSON exists. No final report collected yet. Next gather GRT/IR, diagnose resource/tool failures, retain abstract/budget qualification.

## RESUMED 2026-10-24 12:12 PDT (after 08:50-12:04 limit)
- Adopted Codex: codex/trial-qk-1024 (ff91e05b6d clock_pad_probe + KV padding TT 43/FF 58 ps spread, 0cbbf200ab KV IR retry review) fast-forwarded into claude/trial-qk-1024; live job intel2:/srv/opentallas-scratch2/claude/codex-qwen/kv_ir_retry256 (KV IR, 256 GB) adopted — my own KV IR (qwen_kvsys_ir) was EXIT 137 OOM, NOT relaunched.
- die_trial.py fixed (32d51a0067): TT setup / FF hold gating (SS informational), run_*.sh propagate the real exit code.
- Own live: intel1 trialqk-route_g0 (QC GRT, extra iter 30/30), intel2 trialqk-ir-759266 (QC IR, pdngen). KV route_g0 DONE EXIT 0 (10:52).

## 2026-10-24 18:52 status (after OWNER DECISIONS)
- Gate in die_trial report now = nominal TT setup / FF hold / seam spread <= 80 (decision 3); OCV 5 % kept as INFO column.
- KV v3.8u DONE (results/die_trial_1024/qwen_kvsys, 81277e4045 + pending commit): GRT ovf 3349 only in hub_Eo/hub_Wo 1118-bit station gcells; padded clock nominal seam max 33 ps (0>80), TT 5.57-5.61 ns; hop gate nominal 0 setup / 0 hold neg; ILM e5|e6 TT +20.8 / FF +232; IR (Codex 256 GB run adopted) VDD 67.4 / VSS 71.5 mV worst, avg 28/31 mV at 89 W est.
- QC v3.8s (old plan): GRT finished 4659 ovf (M5 2086, M4 980), writing wl/heatmap; clock padded TT 8.33-8.38 ns, nominal seam max 34/52 ps (0>80); IR (138 um tiles, 512 GB) in PSM on intel1.
- QC capacity plan (decision 1): building die trial on codex/qc-capacity-1024 @72ece79138 (plan sha 33c214a3) into localhost /srv/opentallas-scratch/claude/trial-qk/qwen_compute_cap; then clock+pad, GRT, IR, report.

## PARKED 2026-10-24 18:56
- Branch claude/trial-qk-1024 @be5dc2305e (pushed; not yet merged to main).
- Live jobs (own; leave running):
  - intel1:/srv/opentallas-scratch2/claude/trial-qk/qwen_compute (QC v3.8s route_g0, container trialqk-route_g0-1445030, ot-run pid 1635605 on localhost): GRT DONE (ovf 4659: M4 980, M5 2086, M6 227, M7 565, M8 456, M9 345; 4 h 06 m), writing grt_g0_wl.csv/heatmap -> EXIT line.
  - intel1:/srv/opentallas-scratch2/claude/trial-qk/qwen_compute_ir_t4 (QC IR, 138 um tiles, 512 GB, trialqk-ir-3298221): PDN done 1549 s, PSM running (165 GB at 13:5x).
  - localhost: python die_trial.py build of the QC CAPACITY plan (codex/qc-capacity-1024 @72ece79138, plan sha 33c214a3) -> /srv/opentallas-scratch/claude/trial-qk/qwen_compute_cap (log build_qwen_compute_cap.log; local process, not fleet).
  - stopped (own): intel2 trialqk-ir-759266 (old 69 um QC IR, superseded; STOPPED.txt in its dir).
- Results: results/die_trial_1024/qwen_kvsys (summary.json, die_trial*.json, ir.json, PNGs, ILM TT/FF) — KV gate PASS on padded clock (nominal TT/FF, seam max 33/29 ps), GRT ovf 3349 only in hub_Eo/hub_Wo 1118-bit station gcells, IR VDD 67.4 / VSS 71.5 mV worst; INFO 5 % OCV: 544-571 ps seam skew (root split through hub row). results/die_trial_1024/qwen_compute: QC v3.8s clock/pad + Manhattan hop report: seam max TT 34 / FF 52 ps (0 > 80) but hold window (insertion_tol 40) negative on 27,474 hops (FF skew > 40) -> FAIL; INFO OCV 5 %: 854 ps.
- Failures: own KV IR 128 GB EXIT 137 (Codex 256 GB retry used instead); old QC IR (69 um tiles) pdngen > 4 h single-thread -> replaced.
- NEXT: (1) when QC route EXIT: rsync route files to localhost qwen_compute + symlink into qwen_compute_clkpad, report (--g2 physical/die_plan/qwen_compute/g2_report.json --ir-dir ..._ir_t4 after irsum), render, Read images, summary.json; (2) capacity plan: run_clock.sh + clock_pad_probe + run_route_g0.sh 192 16 on intel1 + ir --tile-pitches 4 at 512 GB; (3) share QC findings with QC-A0/HBM-ARCH; merge via flock per BRIEFING.
- OWNER?: plan seam skew rule 80 ps vs kit hold window insertion_tol 40 ps: die skew 40-80 ps passes the seam rule but breaks the kit hold contract (QC FF). Which binds?
- Findings already shared: KV-G3, DIE-STA, HBM-ARCH lane files (FROM TRIAL-QK sections).
  (capacity build pids on localhost: /usr/bin/time 2331863, python 2331864)
- 18:57 capacity-plan build DONE exit 0 (5 m 18 s, 2.6 GB) -> localhost /srv/opentallas-scratch/claude/trial-qk/qwen_compute_cap (plan sha 33c214a3); no clock/route launched (parked).

## CODEX notes 2026-10-24 21:10 PDT
Collected QC old-plan IR EXIT0 (VDD89.6/VSS130mV worst,224.1GiB,28282s); combined supply drop exceeds5% for377parts,diagnostic FAIL. Receipt epyc1:/srv/opentallas-scratch2/claude/codex-trial-qk/qc_old_ir/ir.json. Existing capacity GRT/IR still running,no duplicate. codex/trial-qk-1024r@9188ddba07 clean. Claude reset notified;parked. Details CODEX-LOG handoff.
- 2026-10-25 01:03 PDT CLOCK -> TRIAL-QK (QC + KV): die clock v11 + die STA (intel2 die-sta/trial/{qwen_compute,qwen_kvsys}/sta/run_ttff_v11): QC TT +702.9 / FF -8.51 (was -46.4), pair skew 5.3/5.2; KV +705.4 / -5.81 (was -173.4, hub tap spread 216 -> 2.3), pair 2.8/2.5. Residual = stand-in floor. Spines intel2 /srv/opentallas-scratch2/claude/clock/v11/<die>/spine_{TT,FF}.json. No tap fixes needed; QC long last-mile hops now get local repeaters (0 slew violations). claude/clock-1024@161826bb16 results/die_clock_1024

## CODEX notes 2026-10-25 02:49 PDT
CODEX took over current meth-plan full-hop trial preparation on codex/qc-trial-1025. BUILD RUNNING epyc2:/srv/opentallas-scratch2/claude/codex-qc-trial-1025/qc_meth, ot-run16GB/4threads client epyc1 PID2057049, unit oth-ubuntu-3698683-1792921307, launcher log epyc1:/srv/opentallas-scratch2/claude/codex-qc-trial-1025.build.log. Source = own TRIAL-QK standalone tool with meth@a281ceb5ce plan + matching helper snapshot. Render qc_meth_plan.png viewed; PASS-COND BUILD ONLY (central SU/FT band capacity stays PROTO-owned). NO route/STA submitted. Important tool collision: TRIAL-QK tip die_trial.py is a different full-hop implementation than current main TRIAL-S81 die_trial.py; stale tip route M4-M9 fixed locally but MUST NOT replace main (main already M4-M7). Target commit2a8451f47 is NOT merge-ready against main, source-only port aborted cleanly. Keep own staged source and await batch+current CLOCK spine+PROTO before physical runs.

## CODEX notes 2026-10-25 03:09 PDT
Current meth full-hop build EXIT0 on epyc2; plan sha d27c37880fe8d8244f6ff0daec39477325b2b32c9465564032c85b162900db91,377parts56types,2,706,968nets,6699taps. No physical route/STA. Read-only per-bit audit found32,155legs>405um; current G2 independently confirms true plan geometry (not legacy-tool ambiguity). QC repairs actual-bit tails/core sites on codex/qc-bitstations-1025; trial physical runs held until successor passes. Legal M6/M7 wire calibration EXIT0 intel2:400um TTsetup+388.30/+420.97;2um FFholdM6-1.70FAIL/M7+2.26PASS. Data-only resultbranch codex/qc-trial-policy-1025@e423c458a (based root integration) ready; no source/plan replacement or405um rule change.

## CODEX handoff 2026-10-25 03:35 PDT
All own trial/calibration jobs done; no route/STA launched. Baseline meth full-hop build EXIT0 epyc2codex-qc-trial-1025/qc_meth; exposed true bit-tail failure now repaired in QC strict successor. Snapshot96a44be4c diagnostic only (do not merge stale trialtool2a845); authoritative main tool already M7. Data-only legal M6/M7 calibration branch e423c458a ready; short FF M6hold-1.70 remains expected padding issue. Details CODEX-LOG03:35.
