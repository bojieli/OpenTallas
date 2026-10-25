# CODEX S81 takeover 2026-10-25 06:00 PDT

S81-PORTS: newer rewrite claude/s81-i13r-1025@36364ebdb already exists beyond handoff: O(1) ordered duplicate check+SRAM rows+streaming merge-join. R3, native SRAM, two-source, two-job and mutant controls PASS; generic552/native554cycles (old612). Original failed synth is superseded but preserved in lane record. Own codex/s81-i13-0553. Plan image viewed PASS-COND for synthesis/floorplan. Gate2 NOT RUN stale daemon path missing cg_pushdown.tcl, corrected explicit own OT_CLOSURE_DAEMON_TREE for gate3; source missing leaf_inhold_release.tcl fixed by sparse materialization. Strict die bind remains token owner; idx_tx_n32 parent parameter mismatch next.


# CODEX S81 PLAN2 inventory 2026-10-25 05:58 PDT
Current: own branch codex/s81-plan2-1025 from claude/s81-plan2-1025r@77789afa6b; gathers full-width B, IR split12/14, R3 RTL. No final merged plan yet.
Running: epyc1:/srv/opentallas-scratch2/claude/s81-plan2/g2svc 16 gather-B probes; 8 terminal clean logs, 5 still GRT congestion; full collection ongoing. epyc1:.../s81-plan-leaf/r3 72 FT allocator jobs (not GRT): ledger geometry max386.91um; r3 combined plan exists but not yet committed/reviewed/G2.
Paused source: CCONN branch has no new commit; partial source/results in epyc1:.../s81-plan2-cconn; filters shared input/input nets before derived connection enumeration, v3 plan/rep exists. XFIN branch no new commit; search.py only, approved outline growth >=120kum2 needed. STFG branch no new commit; relay output dangling BUFx2 cause, fixed source in paused wt uncommitted to be harvested separately.
Failures: r2 leaf geometry PASS but G2 worse7/8; fixed template lacks FT corridors. Original svc/col corridors overflow; FTCHAN9 prototype fixes3 CLEAN/5 HOTSPOT/1 STRUCTURAL (737). 4766 derived internal-station +84 core-face baseline findings, most input-input fanout false pairs need accurate driver-sink correction; remaining true crossings need stations. WS3 IR50.4/40.3mV >35mV and7 PHY_SHORT remain. Stale VS XM pins widths and IDX parent removed RIC contracts need refresh.
Next: harvest existing results and paused uncommitted source into own branch without touching original worktrees, inspect actual images, integrate per-field deltas, run smallest geometry/G0C/prototype fixes. No new heavy job launched yet.


# CODEX S81 cores takeover 2026-10-25 05:56 PDT
- S81-CORES: 15 actual signed views on main; vq old r12 stale versus changed RTL. Core work assigned physical worker (RV/EH/SW), legacy worker (LA/NC), boundary worker (LB cfg7/l0r).
- Live RV: epyc2:/srv/opentallas-scratch2/claude/s81-cores2-rv/kits/dsfd_su_t_rxsf_ftz; epyc3:.../ot_s81sl_vq_bfq. 0-cycle exact fixes claude/s81-cores2-rv-1025@5d10e4293. Collect CTS, review, route only when acceptable.
- EH: eng e1/e1r epyc2:/srv/opentallas-scratch2/claude/s81-cores2-eh/dsdv_eng_rr_e_e1*. Macro LEFs have pins both W/E; original outline channels too narrow. e1 grew width345.6->410.4 (+18.75%), preliminary overflow6437 versus12269, GRT pending; requires plan delta. Aq ordering fixed41f01591c2; token_lec notified to prove.
- SPLIT vn_a t42 PASS-COND postCTS; vn_b/vsw FAIL F6 interface placement. epyc2:/srv/opentallas-scratch2/claude/s81-cores-split/{vn_a_t42,vn_b_t42,vsw_t22}. ~360ps insertion must bind per corner/early parent tap; no assumption of signed status.
- LEGACY stage1 epyc3 + copies epyc1:/srv/opentallas-scratch2/claude/s81-cores-legacy; live bksel_c,l5_n32,eg,xrt3,xfin. qbankN/l1c/l3/l4 queued but l4 LEC-HOLD. Failure diagnoses: bk_g macro clock mismatch; l0/l1/l2/xrt1 late single-tree clock -> regional taps; qbankS utilization118%; xfin cell area72.5k>32.9k outline; cfg7 shared14/l0r sticky output sharing -> RTL duplicated output flops.
- NC: VS stage1 epyc2 unit3509677. XM pin tables stale widths need parent regenerate. BF roots slang conflicting-driver keep-hook failure; legacy worker diagnosing. bf_col/elem_q/idx native old views NOT SIGNED; idx params mismatch requires plan/RTL adoption. capc5r/bksel_q children unsigned; cfifo multi-clock contract remains owner item.
- ELEM-S81 old B station views obsolete versus wavefront/adopt178; current t6/t27 place jobs physical geometry parent-owned. No obsolete station reroute. Existing failed evidence retained.
- FLOW owns ve_m/ve_s/rr_h0 proof routes. leaf_affinity local/global Tcl bug already reported05:48, forward to flow owner.


# CODEX S81-HEAD 2026-10-25 05:58 PDT
- Elements: s3 A/B c50/c60 LIVE epyc1:/srv/opentallas-scratch2/claude/s81-head-elem/kits; FF hold repair -36..-47ps after 500-1400 iterations. Diagnosed incorrect vclk -max250/-min155/170 early/late semantics; own codex/head-elems-0555 successor adopting shared FLOW per-corner mechanism. No original mutation.
- Tile: actual source anchor proof PASS max402.192um, 0>405, reset max369.4; blocked on current SIGNED elements. Keep actual placement/previews, no old LEF route.
- Spines: latest origin/claude/s81-head-spine2-1025@5dfdf7e84 actual placements terminal; newly viewed FAIL (23/1078 reg hops>405 max424.7/551um), own spine worker fixing leaf endpoint anchors, zero new cycles planned. Six FT wave source existed but no kits generated before pause; same worker owns wave.
- hd_ctl/host/mesh: missing release RTL; endpoint worker mapping existing H10/H11 real contracts, implementing smallest real gap with miter+mutant, no stubs.
- hd_lep0N/serdes: need regenerated layer binder kit RTL (previous sources pruned); endpoint worker owns.
- Existing OWNER? host 553b/2beats requires279 wires vs276; calendar slots and H4 endpoint authority; actual PHY/package contract remain unresolved, logged earlier. Other work continues.
