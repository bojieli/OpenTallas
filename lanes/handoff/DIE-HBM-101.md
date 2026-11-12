# DIE-HBM-101 lane handoff (HBM die owner, phase 2). Updated 2026-11-12 09:40 PST.

## 1 Scope
Single HBM owner for phase 2. Succeeds DIE-HBM-100, HBM-HANDPLAN-1, DIE-LAYOUT-HBM, VISLAYOUT2-HBM, CORES-HBM-1, HBM-CORES-B and the hub/root/stale lanes.
Priorities: (1) watch builds; new forms only on COORD order; (2) hand floorplan v2 + SEAM corrected form (COORD: keep the channel, fix the G0 classes; the seam row is the biggest HBM overflow); (3) t40w event fold, then READY.
Visual gate: every new form stops at place until GEOM-VIS-6 says GOOD or ISSUES-ACCEPT. I view every render myself before the REVIEW-REQUEST.
FLEET BALANCE (COORD 08:4x): no HBM private job waits >20 min on a loaded host. Copy --dir to epyc9 (or the least-loaded host), re-submit, cancel the old waiter by exact client PID.

## 2 Work files (nothing committed by me; analysis plans DO_NOT_COUNT)
Plans: epyc9 AND epyc8 /srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/plans/ (hp3 baseline is on both; hp4b..hp4i are on epyc9 only).
Scripts in .../hp1lane/hbm101/ (epyc9) and localhost scratch /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/hbm/:
- seam_grow2.py IN OUT 10385.28 103.68 '' : inserts the per-type channel at the content top (y_ins); '' = no re-sites (re-sites made it worse, hp4d).
- seam_pair.py IN OUT 103.68 : pairs E/W windows across the seam (fixes the G0 schema short-circuit).
- seam_glue.py BASE(hp3) IN OUT : window stations keep their hp3 offset from their pins.
- seam_sta.py IN OUT 103.68 [R=385] (env ONLY=type:slot,...) : hops that overlap the channel band and exceed R: slide (0 cycles) else stations spaced evenly along the path (+1 cycle each, DECLARED via gen.py latency). Station 0 is measured at the in-pin (check.py stage 0 = pin); bit_sites_um[r-1] = stage r.
- then kw45 tools: ft_nudge.py PLAN OUT LEDGER (moves only macro-hitting stations), gen.py latency PLAN --inplace.
- G0: hbm101/g0_<plan>.sh via ~/.local/bin/ot-run --mem 32 --threads 1 --hosts epyc9 --dir .../hp1lane ; report .../g0_<plan>/g0_report.json/g0_report.json (fields level/check/msg). Schema errors short-circuit G0 (empty summary): never compare such a count.
- Compare against hp3 by exact message: scratch hbm/hp3_err.json vs <plan>_err.json.

## 3 SEAM status (G0 errors; hp3 = 544)
hp4 636 (withdrawn) -> hp4b 6 schema (short-circuit) -> hp4c 624 -> hp4d 627 / hp4e 611 -> hp4g 537 (latency 19 -> 0; +12 elsewhere) -> hp4h 557 (26 stations on macros; hub S0->S1 unchanged because station 0 is the pin) -> hp4i (sha 461809e8140c: glue + fixed sta, 81 added / 5 slid, ft_nudge 102 slots max slide 148 um) G0 RUNNING (intel2 ~/die-hbm-101-logs/g0_hp4i.otrun.log).
Next: if hp4i <= hp3 on every class except declared latency -> die triage on hp4i (run_tri pattern, ot-run epyc9), post G0 + triage, then ask COORD for the batch re-sign of the 13 grown types + hub beat freeze. Before/after drawing to GEOM-VIS-6 (v2/draw_seam.py).

## 4 Running builds / agents (my subagents; all report to me)
- VP4-RST-1 (a451df755f3d2c1c8): vPose3R PLACED on epyc9 (moved from epyc7), kit epyc9 .../cores-hbm-1/ot_hgi_dma_back_static_vp4_banks_cp/vPose3R, log vp4cp_vPose3R_e9.otrun.log. Agent renders + reset-copy check + a_mv path, then I post the REVIEW-REQUEST. Cancel R if vPose3G signs off clean.
- Q2N2-C2-1 (a4ef59c02a414ba7e): q2n2 C2 PLACED, REVIEW-REQUEST posted (W cluster, vmasm_sel pins x~11 -> t40w pin fold, as_il depth). C2 EQ: positives PASS, sim negatives FAIL as required, yosys neg_select pending. vecd4ae form P (S pins M5 -> alternate M3/M5) PLACED, LEC EQUIVALENT, REVIEW-REQUEST posted; hold CTS+GRT for verdict.
- HBM-CORES-B (adf5204cb4034d7c1): TREG READY posted (02b406d779, default-off merge). RDREG=1 UNPROVEN: BMC44 m0 timeout, bounded-24 WITHDRAWN (mutants not caught at 24). k-induction (gated on no-fault-yet, no assume) on epyc9, time box ~12:10 PST; fault BMC + window check; FMUT1 fails OK, FMUT2 replaced. kshare LCREP READY waits on eq0g.
- HBM-CORES-C (aa7c81666cfdde1de): WBQ READY 6a6561ee2d is ON HOLD (stale: module __fcore). Re-point to 8390fd372e5b ONLY after yosys EQ on the committed file closes 0 unproven. H13+DCHK1 kit placing epyc9 (oth-ubuntu-552413-1794504319). opsa_group0 lattice fix branch 45e7794faa11 placed; REVIEW-REQUEST posted. The 9 dropped pins are rd_addr[375..383] (unread): plan event approved (drop from group0+group1 tables, tie 0, own commit). fanout_spread = br_q broadcast, a design property. WBQ eq2 on 8390fd running (oth-ubuntu-572806-1794504407).
- topk: C2 settings arm stopped at GRT (congested); D and A2 running.
- Watcher: bash <scratch>/hbm/w101.sh (background; re-run after each event).

## 5 Posted today (COORD-REVIEW-QUEUE, DIE-HBM-101)
post101_25..34: topk C2 result; FLEET BALANCE moves; failure owners (1) vecd4ae -> Q2N2-C2-1 (class: S pin clump, not C2), (2) opsa_group0 -> HBM-CORES-C (half-pitch DX 135.0 in opsa_b.py; snap fix), (3) PHY_NE -> KW-FIX-46; C2 + vecd4ae P REVIEW-REQUESTs; STATE; TREG READY; WBQ READY then HOLD; INFRA core_clock_regions.json missing on epyc2/epyc9/intel2; KW-FIX request to keep grt artifacts of sealed route-FAIL jobs.

## 6 Next steps
1. hp4i G0 -> compare -> triage -> post (section 3).
2. Re-point WBQ READY when the EQ on 8390fd372e5b lands.
3. vPose3R / opsa_group0 / H13 renders: view, then REVIEW-REQUEST.
4. GEOM-VIS-6 verdicts on C2 and vecd4ae P -> route only on GOOD / ISSUES-ACCEPT.
5. t40w fold: beat-lane latency (gen.py latency covers word_cycles), q2n2 pins + q_hub_ne window, vmasm_sel pin move, i8w pins (d672043013f3), opsa_g0 lattice (opsa_b.py snap; t39w W-face re-edge is a provenance gap), vecd4ae P pins if GOOD, G1e if GOOD.
6. STATE every 60 min (last ~09:05).

## 7 Gotchas
- check.py: station 0 of a normal ft slot is the in-window pin; regs_um[0] "is not a native placement". bit_sites_um has one fewer entry than regs_um.
- G0 schema errors short-circuit the whole run.
- coord-commit can lose an append: verify with `git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md | grep -c <text>`.
- Branches are pushed to hub:OpenTallas, not GitHub: verify with `git ls-remote hub:OpenTallas <branch>` from /tmp on intel2 (never git inside /home/ubuntu/OpenTallas).
- On intel2 under nohup use ~/.local/bin/ot-run. Kill only exact PIDs.
- Sealed ot-job dirs are deleted with their GRT logs: plain ot-run --dir kits keep artifacts.
